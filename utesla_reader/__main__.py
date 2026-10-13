"""Entry point: ``python -m utesla_reader [--port PORT] [--simulate]``."""

import argparse
import os

from .sensor import DEFAULT_BAUD

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    ap = argparse.ArgumentParser(prog="utesla_reader", description="Live viewer and CSV recorder for the MicroteslaSensor.")
    ap.add_argument("--port", help="serial port, e.g. /dev/cu.usbserial-2110 or COM3 (default: auto-detect CH34x)")
    ap.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"baud rate (default {DEFAULT_BAUD})")
    ap.add_argument("--out-dir", default=os.path.join(REPO_ROOT, "recordings"),
                    help="folder for CSV recordings (default: ./recordings)")
    ap.add_argument("--simulate", action="store_true", help="use a fake sensor (no hardware needed)")
    args = ap.parse_args()

    from .gui import run

    run(port=args.port, baud=args.baud, out_dir=args.out_dir, simulate=args.simulate)


if __name__ == "__main__":
    main()
