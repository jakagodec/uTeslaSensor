"""Tkinter GUI: live Bx/By/Bz plots plus start/stop CSV recording."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import time
import tkinter as tk
from collections import deque
from tkinter import messagebox, ttk
from typing import Deque, List, Optional

from .recorder import CsvRecorder
from .sensor import DEFAULT_BAUD, Sample, SerialReader, SimulatedReader, find_sensor_port, list_ports

AXES = (("Bx", "bx", "#d62728"), ("By", "by", "#2ca02c"), ("Bz", "bz", "#1f77b4"))
WINDOWS_S = {"10 s": 10, "30 s": 30, "1 min": 60, "5 min": 300}
UNIT = "µT"
# Readings observed pinned at exactly ±200 when the sensor is saturated or not
# actually being read; flag values this close to that limit.
RANGE_LIMIT = 199.9
REFRESH_MS = 50
STALE_AFTER_S = 2.0


class AxisPlot(tk.Canvas):
    """Scrolling time-series plot for one axis."""

    PAD_L, PAD_R, PAD_T, PAD_B = 62, 12, 28, 20

    def __init__(self, master, label: str, attr: str, color: str):
        super().__init__(master, background="white", highlightthickness=1,
                         highlightbackground="#cccccc", height=160)
        self.label, self.attr, self.color = label, attr, color

    def redraw(self, samples: Deque[Sample], now: float, window_s: float) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 100 or h < 60:
            return
        x0, x1 = self.PAD_L, w - self.PAD_R
        y0, y1 = self.PAD_T, h - self.PAD_B
        t_min = now - window_s

        pts = [(s.t, getattr(s, self.attr)) for s in samples if s.t >= t_min]
        latest = getattr(samples[-1], self.attr) if samples else None

        if pts:
            lo = min(v for _, v in pts)
            hi = max(v for _, v in pts)
        else:
            lo, hi = -1.0, 1.0
        span = max(hi - lo, 1.0)
        lo, hi = lo - 0.1 * span, hi + 0.1 * span

        def sx(t: float) -> float:
            return x0 + (t - t_min) / window_s * (x1 - x0)

        def sy(v: float) -> float:
            return y1 - (v - lo) / (hi - lo) * (y1 - y0)

        # Horizontal grid + value labels.
        for i in range(5):
            v = lo + (hi - lo) * i / 4
            y = sy(v)
            self.create_line(x0, y, x1, y, fill="#eeeeee")
            self.create_text(x0 - 6, y, text=f"{v:.1f}", anchor="e", fill="#666666",
                             font=("TkDefaultFont", 9))
        # Vertical grid + "seconds ago" labels.
        for i in range(6):
            t = t_min + window_s * i / 5
            x = sx(t)
            self.create_line(x, y0, x, y1, fill="#eeeeee")
            ago = now - t
            self.create_text(x, y1 + 3, text="now" if ago < 1e-6 else f"-{ago:.0f} s",
                             anchor="n", fill="#666666", font=("TkDefaultFont", 9))
        self.create_rectangle(x0, y0, x1, y1, outline="#bbbbbb")

        if len(pts) >= 2:
            coords: List[float] = []
            for t, v in pts:
                coords += (sx(t), sy(v))
            self.create_line(*coords, fill=self.color, width=2)
        elif len(pts) == 1:
            x, y = sx(pts[0][0]), sy(pts[0][1])
            self.create_oval(x - 2, y - 2, x + 2, y + 2, fill=self.color, outline="")

        title = f"{self.label}  {latest:+.2f} {UNIT}" if latest is not None else f"{self.label}  —"
        self.create_text(x0, 6, text=title, anchor="nw", fill=self.color,
                         font=("TkDefaultFont", 12, "bold"))
        if latest is not None and abs(latest) >= RANGE_LIMIT:
            self.create_text(x1, 6, text="⚠ at range limit (saturated or not read?)",
                             anchor="ne", fill="#c00000", font=("TkDefaultFont", 10))


class App:
    def __init__(self, root: tk.Tk, port: Optional[str], baud: int, out_dir: str, simulate: bool):
        self.root = root
        self.baud = baud
        self.simulate = simulate
        self.queue: "queue.Queue" = queue.Queue()
        self.reader = None
        self.samples: Deque[Sample] = deque(maxlen=20000)
        self.last_sample_at: Optional[float] = None
        self.recorder = CsvRecorder(out_dir)

        root.title("uTesla Reader")
        root.minsize(640, 520)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # --- connection row
        top = ttk.Frame(root, padding=(8, 8, 8, 0))
        top.pack(fill="x")
        ttk.Label(top, text="Port:").pack(side="left")
        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(top, textvariable=self.port_var, width=28)
        self.port_box.pack(side="left", padx=(4, 2))
        self.refresh_btn = ttk.Button(top, text="Refresh", command=self.refresh_ports)
        self.refresh_btn.pack(side="left", padx=2)
        self.connect_btn = ttk.Button(top, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side="left", padx=2)
        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(top, textvariable=self.status_var, foreground="#555555").pack(side="right")

        # --- recording row
        rec = ttk.Frame(root, padding=(8, 6, 8, 4))
        rec.pack(fill="x")
        self.record_btn = ttk.Button(rec, text="● Start recording", command=self.toggle_recording,
                                     state="disabled")
        self.record_btn.pack(side="left")
        ttk.Button(rec, text="Open folder", command=self.open_folder).pack(side="left", padx=4)
        self.rec_var = tk.StringVar(value="Not recording")
        self.rec_label = ttk.Label(rec, textvariable=self.rec_var)
        self.rec_label.pack(side="left", padx=8)
        self.window_var = tk.StringVar(value="30 s")
        ttk.Combobox(rec, textvariable=self.window_var, values=list(WINDOWS_S), width=6,
                     state="readonly").pack(side="right")
        ttk.Label(rec, text="Window:").pack(side="right", padx=4)

        # --- plots
        plots = ttk.Frame(root, padding=(8, 0, 8, 0))
        plots.pack(fill="both", expand=True)
        self.plots = []
        for label, attr, color in AXES:
            p = AxisPlot(plots, label, attr, color)
            p.pack(fill="both", expand=True, pady=3)
            self.plots.append(p)

        # --- device messages
        self.info_var = tk.StringVar(value="")
        ttk.Label(root, textvariable=self.info_var, foreground="#777777",
                  padding=(8, 2, 8, 8)).pack(fill="x")

        if simulate:
            self.port_var.set(SimulatedReader.port)
            self.port_box.configure(state="disabled")
            self.refresh_btn.configure(state="disabled")
            self.connect()
        else:
            self.refresh_ports()
            if port:
                self.port_var.set(port)
            if self.port_var.get() and (port or find_sensor_port()):
                self.connect()

        self.root.after(REFRESH_MS, self.tick)

    # ---------------------------------------------------------------- ports
    def refresh_ports(self) -> None:
        ports = list_ports()
        self.port_box["values"] = [dev for dev, _ in ports]
        if not self.port_var.get() and ports:
            self.port_var.set(find_sensor_port() or ports[0][0])
        if not ports:
            self.status_var.set("No serial ports found — is the sensor plugged in?")

    def toggle_connection(self) -> None:
        if self.reader is None:
            self.connect()
        else:
            self.disconnect()

    def connect(self) -> None:
        if self.simulate:
            self.reader = SimulatedReader(self.queue)
        else:
            port = self.port_var.get().strip()
            if not port:
                messagebox.showwarning("uTesla Reader", "Select a serial port first.")
                return
            self.reader = SerialReader(port, self.queue, self.baud)
        self.samples.clear()
        self.last_sample_at = None
        self.reader.start()
        self.status_var.set(f"Connecting to {self.reader.port}…")
        self.connect_btn.configure(text="Disconnect")
        self.record_btn.configure(state="normal")

    def disconnect(self) -> None:
        if self.reader is not None:
            self.reader.stop()

    def on_reader_closed(self) -> None:
        self.reader = None
        self.stop_recording()
        self.connect_btn.configure(text="Connect")
        self.record_btn.configure(state="disabled")
        if not self.status_var.get().startswith(("Could not", "Connection lost")):
            self.status_var.set("Disconnected")

    # ------------------------------------------------------------ recording
    def toggle_recording(self) -> None:
        if self.recorder.active:
            self.stop_recording()
        else:
            try:
                path = self.recorder.start(time.time())
            except OSError as e:
                messagebox.showerror("uTesla Reader", f"Could not create recording file:\n{e}")
                return
            self.record_btn.configure(text="■ Stop recording")
            self.rec_label.configure(foreground="#c00000")
            self.rec_var.set(f"Recording → {os.path.basename(path)}")

    def stop_recording(self) -> None:
        path = self.recorder.stop()
        self.record_btn.configure(text="● Start recording")
        self.rec_label.configure(foreground="")
        if path:
            self.rec_var.set(f"Saved {self.recorder.count} samples → {path}")

    def open_folder(self) -> None:
        folder = self.recorder.out_dir
        os.makedirs(folder, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    # ----------------------------------------------------------------- loop
    def tick(self) -> None:
        new: List[Sample] = []
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "sample":
                    new.append(payload)
                elif kind == "info":
                    self.info_var.set(payload)
                    if payload.startswith("Connected to") or payload.startswith("Simulated"):
                        self.status_var.set(payload)
                elif kind == "error":
                    self.status_var.set(payload)
                elif kind == "closed":
                    self.on_reader_closed()
        except queue.Empty:
            pass

        now = time.time()
        if new:
            self.samples.extend(new)
            self.last_sample_at = now
            self.recorder.write(new)

        if self.recorder.active:
            dur = now - (self.recorder.started_at or now)
            self.rec_var.set(f"● REC {int(dur // 60):02d}:{int(dur % 60):02d} · "
                             f"{self.recorder.count} samples → {os.path.basename(self.recorder.path or '')}")
        if self.reader is not None and self.last_sample_at is not None \
                and now - self.last_sample_at > STALE_AFTER_S:
            self.status_var.set(f"No data from {self.reader.port} for {now - self.last_sample_at:.0f} s")
        elif self.reader is not None and self.last_sample_at is not None:
            self.status_var.set(f"Streaming from {self.reader.port}")

        window = WINDOWS_S.get(self.window_var.get(), 30)
        for p in self.plots:
            p.redraw(self.samples, now, window)
        self.root.after(REFRESH_MS, self.tick)

    def on_close(self) -> None:
        self.recorder.stop()
        if self.reader is not None:
            self.reader.stop()
            self.reader.join(timeout=1.0)
        self.root.destroy()


def run(port: Optional[str] = None, baud: int = DEFAULT_BAUD, out_dir: str = "recordings",
        simulate: bool = False) -> None:
    root = tk.Tk()
    App(root, port, baud, out_dir, simulate)
    root.mainloop()
