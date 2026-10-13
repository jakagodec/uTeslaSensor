# CLAUDE.md

Desktop reader for the MicroteslaSensor (3-axis magnetometer, firmware by Natan Osterman) over USB serial. Python + tkinter + pyserial only; keep it that way (no matplotlib/Qt/numpy) unless there is a strong reason.

## Commands

```bash
.venv/bin/python -m utesla_reader              # run GUI (auto-detects port)
.venv/bin/python -m utesla_reader --simulate   # run without hardware
.venv/bin/python -m unittest discover -s tests # tests (stdlib unittest, no pytest)
```

Supports Python 3.9+. Keep `from __future__ import annotations` and don't use 3.10+ syntax (`match`, runtime `X | Y`).

## Architecture

- `sensor.py`: `parse_line()` (regex on `Bx:/By:/Bz:`), `list_ports()`/`find_sensor_port()` (match VID 0x1A86), `SerialReader` and `SimulatedReader` threads. Both readers push `("sample"|"info"|"error"|"closed", payload)` tuples into a `queue.Queue`.
- `gui.py`: `App.tick()` runs every 50 ms on the Tk thread. It empties the queue, appends samples to a deque, writes them to the recorder, and redraws three `AxisPlot` canvases. Only the Tk thread touches widgets.
- `recorder.py`: `CsvRecorder` writes `timestamp,bx,by,bz`. The timestamp is host receive time in ISO 8601 local time with offset and milliseconds. The file is flushed after every batch.
- `tests/fixtures/sample_output.txt`: a real 15 s capture from the device, including the truncated first line, the banner, and a truncated last line.

## Device facts (learned on real hardware, 2026-10-13)

- USB bridge: **WCH CH341**, VID:PID `1a86:7523`. It is a USB 1.1 full-speed device.
- macOS: the built-in DriverKit driver `com.apple.DriverKit-AppleUSBCHCOM` handles it, so no install is needed. The port is `/dev/cu.usbserial-<location>` (it was `/dev/cu.usbserial-2110`). Use `cu.*`, not `tty.*`.
- Windows: the CH341SER driver from WCH, usually installed automatically. The port is `COMx`.
- Serial: **115200 baud, 8N1**, ASCII, `\r\n` line endings.
- **Opening the port resets the board** (through DTR). It prints:
  ```
  MicroteslaSensor by Natan Osterman
  Averaging NumReads=
  50
  ```
  The first reading arrives about 2 s after opening. A partial line from before the reset may come in first; the parser simply skips it.
- Data line:
  ```
  Bx: 21.57 By: 3.23 Bz: -26.88 Magnitude: 34.6 TrueField: (x y z) Elapsed_ms:274
  ```
  - `Magnitude` = √(Bx²+By²+Bz²).
  - `TrueField` looks like a corrected or calibrated vector; what it means is unknown, and it isn't recorded.
  - `Elapsed_ms` (~274) is the duration of the 50-sample average, **not** the time between lines.
- Actual line rate: about every **0.37 s** in normal operation. While the sensor was stuck at its limit it was about every **0.55 s**.
- Units are assumed to be µT ("Microtesla" sensor; the normal values are about 35 µT total, which fits Earth's field). This hasn't been confirmed against a reference instrument.
- **Saturation or failure state:** once, all three axes were pinned at about +199.99/−200.00/−200.00 with no noise, and `TrueField` was constant. It later recovered on its own after a reconnect or reset, with the device moved away from a USB hub/SSD. The GUI warns when |value| ≥ 199.9 (`RANGE_LIMIT` in `gui.py`).
- No command protocol is known yet; the firmware just streams. `NumReads` may be configurable, but it hasn't been tested.

## Gotchas

- **Only one process may read the port.** When two readers were open at once, each received interleaved ~32-byte chunks, which looked like corrupted, out-of-order data. If output looks scrambled, run `lsof /dev/cu.usbserial-*`.
- **USB-C hubs/dongles:** behind a VIA VL817 hub (`2109:0817`) on a USB-C dongle, only the USB 3 side enumerated, so the USB 2 companion hub, and therefore the CH341, never appeared. The Mac showed no USB errors in the logs. Fix: plug the sensor directly into the Mac. Look in `ioreg -p IOUSB -l` for vendor ID `6790` (0x1a86) before suspecting drivers.
- Raw `os.read` on a non-blocking fd raises `BlockingIOError` (EAGAIN). pyserial handles this, but ad-hoc scripts must too.
- Anaconda's Python ships a module named `serial` that is **not** pyserial (it has no `__version__` and no `Serial`). Always use the project `.venv`.
- `/usr/bin/python3` on macOS (Command Line Tools 3.9) has Tk 8.5, which is deprecated and buggy. `start_mac.command` requires Tk ≥ 8.6.
- `start_windows.bat` must keep CRLF line endings (enforced by `.gitattributes`). Avoid `%errorlevel%` inside `( … )` blocks; it is expanded when the block is parsed, before it runs.
