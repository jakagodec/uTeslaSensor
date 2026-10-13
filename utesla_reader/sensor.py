"""Serial communication with the MicroteslaSensor (CH341 USB-serial bridge).

The firmware streams one ASCII line per averaged reading, e.g.::

    Bx: 199.99 By: -200.00 Bz: -200.00 Magnitude: 346.4 TrueField: (220.32 -245.11 -216.83) Elapsed_ms:274

Only Bx/By/Bz are extracted; everything else (startup banner, settings echo)
is passed through as an informational message.
"""

from __future__ import annotations

import math
import queue
import random
import re
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

DEFAULT_BAUD = 115200
CH34X_VID = 0x1A86  # WCH (Nanjing Qinheng), maker of the CH340/CH341

_NUM = r"([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)"
_LINE_RE = re.compile(rf"Bx:\s*{_NUM}\s+By:\s*{_NUM}\s+Bz:\s*{_NUM}")


@dataclass(frozen=True)
class Sample:
    t: float  # host time (time.time()) when the line was received
    bx: float
    by: float
    bz: float


def parse_line(line: str) -> Optional[Tuple[float, float, float]]:
    """Return (bx, by, bz) from one sensor line, or None if it is not a reading."""
    m = _LINE_RE.search(line)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def list_ports() -> List[Tuple[str, str]]:
    """Return [(device, description)] with likely sensor ports first."""
    from serial.tools import list_ports as lp

    ports = []
    for p in lp.comports():
        desc = p.description or ""
        is_ch34x = p.vid == CH34X_VID or "CH34" in desc.upper()
        ports.append((not is_ch34x, p.device, desc))
    ports.sort()
    return [(dev, desc) for _, dev, desc in ports]


def find_sensor_port() -> Optional[str]:
    """Best guess for the sensor's port: the first CH34x device, if any."""
    from serial.tools import list_ports as lp

    for p in lp.comports():
        if p.vid == CH34X_VID or "CH34" in (p.description or "").upper():
            return p.device
    return None


class SerialReader(threading.Thread):
    """Background thread that reads lines from the sensor.

    Puts ``("sample", Sample)``, ``("info", str)`` and ``("error", str)``
    tuples into ``out_queue``. Call :meth:`stop` to close the port.
    """

    def __init__(self, port: str, out_queue: "queue.Queue", baud: int = DEFAULT_BAUD):
        super().__init__(daemon=True)
        self.port = port
        self.baud = baud
        self.out = out_queue
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        import serial

        try:
            # Opening the port toggles DTR, which resets the board: expect the
            # startup banner first and ~0.5 s before the first reading.
            ser = serial.Serial(self.port, self.baud, timeout=0.5)
        except (serial.SerialException, OSError) as e:
            self.out.put(("error", f"Could not open {self.port}: {e}"))
            return

        self.out.put(("info", f"Connected to {self.port} @ {self.baud} baud"))
        try:
            while not self._stop_event.is_set():
                raw = ser.readline()
                if not raw:
                    continue
                now = time.time()
                line = raw.decode("ascii", errors="replace").strip()
                values = parse_line(line)
                if values is not None:
                    self.out.put(("sample", Sample(now, *values)))
                elif line:
                    self.out.put(("info", line))
        except (serial.SerialException, OSError) as e:
            self.out.put(("error", f"Connection lost: {e}"))
        finally:
            ser.close()
            self.out.put(("closed", self.port))


class SimulatedReader(threading.Thread):
    """Fake sensor for trying the GUI without hardware (``--simulate``)."""

    port = "simulator"

    def __init__(self, out_queue: "queue.Queue", period_s: float = 0.37):
        super().__init__(daemon=True)
        self.out = out_queue
        self.period = period_s
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        self.out.put(("info", "Simulated MicroteslaSensor"))
        t0 = time.time()
        while not self._stop_event.wait(self.period):
            t = time.time() - t0
            self.out.put(("sample", Sample(
                time.time(),
                22.0 + 3.0 * math.sin(t / 3.0) + random.gauss(0, 0.2),
                -4.0 + 2.0 * math.cos(t / 5.0) + random.gauss(0, 0.2),
                -42.0 + 1.5 * math.sin(t / 2.0) + random.gauss(0, 0.2),
            )))
        self.out.put(("closed", self.port))
