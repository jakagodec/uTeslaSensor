# uTesla Reader

Live viewer and CSV recorder for the MicroteslaSensor (3-axis magnetometer, CH341 USB-serial).

## Install

Requires Python 3.9+ ([python.org](https://www.python.org/downloads/)). On Windows, if the sensor doesn't appear as a COM port, install the [CH341SER driver](https://www.wch-ic.com/downloads/CH341SER_EXE.html).

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip install -r requirements.txt
```

## Run

```bash
.venv/bin/python -m utesla_reader              # Windows: .venv\Scripts\python -m utesla_reader
```

The app connects to the sensor automatically. Click **Start recording** and **Stop recording** to save a CSV (`timestamp,bx,by,bz`, µT) to `recordings/`.

Options: `--port PORT`, `--out-dir DIR`, `--simulate` (no hardware needed).
