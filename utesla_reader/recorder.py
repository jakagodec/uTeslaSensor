"""CSV recording of sensor samples."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Iterable, Optional

from .sensor import Sample

HEADER = ["timestamp", "bx", "by", "bz"]


def format_timestamp(t: float) -> str:
    """ISO 8601 local time with UTC offset and millisecond precision."""
    return datetime.fromtimestamp(t).astimezone().isoformat(timespec="milliseconds")


class CsvRecorder:
    """Writes samples to ``<out_dir>/utesla_YYYYmmdd_HHMMSS.csv``."""

    def __init__(self, out_dir: str):
        self.out_dir = out_dir
        self.path: Optional[str] = None
        self.count = 0
        self.started_at: Optional[float] = None
        self._file = None
        self._writer = None

    @property
    def active(self) -> bool:
        return self._file is not None

    def start(self, started_at: float) -> str:
        os.makedirs(self.out_dir, exist_ok=True)
        stamp = datetime.fromtimestamp(started_at).strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.out_dir, f"utesla_{stamp}.csv")
        n = 1
        while os.path.exists(path):  # two recordings in the same second
            n += 1
            path = os.path.join(self.out_dir, f"utesla_{stamp}_{n}.csv")
        self._file = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(HEADER)
        self.path = path
        self.count = 0
        self.started_at = started_at
        return path

    def write(self, samples: Iterable[Sample]) -> None:
        if not self.active:
            return
        for s in samples:
            self._writer.writerow([format_timestamp(s.t), f"{s.bx:.2f}", f"{s.by:.2f}", f"{s.bz:.2f}"])
            self.count += 1
        self._file.flush()

    def stop(self) -> Optional[str]:
        if not self.active:
            return None
        self._file.close()
        self._file = None
        self._writer = None
        return self.path
