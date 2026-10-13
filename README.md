# uTesla Reader

A small desktop app for the **MicroteslaSensor** (by Natan Osterman), a 3-axis magnetometer that connects over USB through a CH341 USB-serial chip.

- Live scrolling plots of **Bx, By, Bz** (µT)
- **Start/stop recording** to CSV (`timestamp, bx, by, bz`)
- Auto-detects the sensor's serial port
- Runs on macOS and Windows. The only dependency is `pyserial`; the GUI uses Python's built-in tkinter.

## Installation

### Requirements

- Python **3.9 or newer** with Tk 8.6 (tkinter)
- The sensor connected with a USB **data** cable (some cables only carry power)

### macOS

1. **Install Python** (skip this if you already have Python 3.9+ with Tk 8.6):
   - Recommended: the installer from [python.org](https://www.python.org/downloads/macos/), or
   - Homebrew: `brew install python python-tk`

   > The `/usr/bin/python3` that ships with Xcode Command Line Tools uses an outdated Tk 8.5. The launcher skips it.

2. **Driver:** nothing to install. macOS 11+ has a built-in CH34x driver. The sensor shows up as `/dev/cu.usbserial-XXXX`.

3. **Start the app:** double-click `start_mac.command` in Finder, or run:

   ```bash
   ./start_mac.command
   ```

   The first run creates a local virtual environment in `.venv/` and installs `pyserial`. Later runs start immediately.

   If macOS says the file can't be opened because it's from an unidentified developer, right-click it and choose **Open** once, or run `chmod +x start_mac.command` after cloning.

### Windows

1. **Install Python** from [python.org](https://www.python.org/downloads/windows/). During setup, tick **"Add python.exe to PATH"**. tkinter is included by default.

2. **Driver:** Windows usually installs the CH341 driver automatically through Windows Update. Plug in the sensor and open **Device Manager → Ports (COM & LPT)**. You should see *USB-SERIAL CH340 (COMx)*. If the device has a yellow warning icon instead, install the official **CH341SER** driver from WCH: <https://www.wch-ic.com/downloads/CH341SER_EXE.html>.

3. **Start the app:** double-click `start_windows.bat`. The first run creates `.venv\` and installs `pyserial`.

### Manual setup (any OS)

```bash
python3 -m venv .venv
# macOS/Linux:
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m utesla_reader
# Windows:
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m utesla_reader
```

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
