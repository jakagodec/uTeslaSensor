# uTesla Reader

A small desktop app for the **MicroteslaSensor** (by Natan Osterman), a 3-axis magnetometer that connects over USB through a CH341 USB-serial chip.

- Live scrolling plots of **Bx, By, Bz** (µT)
- **Start/stop recording** to CSV (`timestamp, bx, by, bz`)
- Auto-detects the sensor's serial port
- Runs on macOS and Windows. The only dependency is `pyserial`; the GUI uses Python's built-in tkinter.

## Installation

You need **Python 3.9 or newer** with tkinter (Tk 8.6), and a USB **data** cable (some cables only carry power).

- **macOS:** get Python from [python.org](https://www.python.org/downloads/macos/) or install it with `brew install python python-tk`. Don't use `/usr/bin/python3`; its Tk 8.5 is outdated. macOS has a built-in CH341 driver, so there's nothing else to install.
- **Windows:** get Python from [python.org](https://www.python.org/downloads/windows/) and tick **"Add python.exe to PATH"** during setup. The CH341 driver usually installs automatically. If the sensor doesn't appear under **Device Manager → Ports (COM & LPT)**, install [CH341SER](https://www.wch-ic.com/downloads/CH341SER_EXE.html) from WCH.

Then, from the repository folder:

```bash
python -m venv .venv
```

| | macOS | Windows |
|---|---|---|
| Install pyserial (once) | `.venv/bin/pip install -r requirements.txt` | `.venv\Scripts\pip install -r requirements.txt` |
| Run | `.venv/bin/python -m utesla_reader` | `.venv\Scripts\python -m utesla_reader` |

On macOS, use `python3` instead of `python` if `python` isn't found.

## Usage

1. Plug in the sensor. The app picks the CH34x port automatically and connects. Otherwise, choose the port and click **Connect**.
2. The three plots scroll in real time. Use **Window** to show the last 10 s to 5 min.
3. Click **● Start recording**, then **■ Stop recording**. Files go into `recordings/` as `utesla_YYYYMMDD_HHMMSS.csv`. **Open folder** takes you there.

Command-line options:

```
python -m utesla_reader [--port PORT] [--baud 115200] [--out-dir DIR] [--simulate]
```

`--simulate` runs the app with a fake sensor, so you can try it without hardware.

### CSV format

```csv
timestamp,bx,by,bz
2026-10-13T11:40:38.845+02:00,21.57,3.23,-26.88
2026-10-13T11:40:39.213+02:00,21.49,3.27,-26.90
```

- `timestamp`: the time the computer received the reading, in ISO 8601 local time with UTC offset and milliseconds.
- `bx, by, bz`: field components as reported by the sensor (µT).

The sensor sends about 2–3 readings per second. Each reading is an average of 50 measurements, set in the firmware (`NumReads`).

## Troubleshooting

| Symptom | Fix |
|---|---|
| No port in the list | Use a USB **data** cable. Plug the sensor directly into the computer instead of a hub or dongle (some USB-C hubs don't pass USB 2.0 devices through). On Windows, check Device Manager or install the CH341SER driver. |
| "Could not open …" / port busy | Only one program can use the port at a time. Close Arduino IDE serial monitors, `screen`, other copies of this app, and similar programs. |
| Values stuck at about ±200 with "⚠ at range limit" | The sensor is saturated or the sensor chip isn't being read. Move it away from magnets, speakers and other electronics, then reconnect to reset the board. |
| A short pause after connecting | Normal. Opening the port resets the board, which prints a startup banner before the first reading. |

## Development

```bash
.venv/bin/python -m unittest discover -s tests     # Windows: .venv\Scripts\python ...
```

Project layout:

```
utesla_reader/
  sensor.py     line parser, port detection, serial and simulated reader threads
  recorder.py   CSV writer
  gui.py        tkinter app (canvas plots, controls)
  __main__.py   command-line entry point
tests/          unit tests + a real capture from the device (fixtures/)
```
