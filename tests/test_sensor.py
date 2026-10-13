import csv
import os
import tempfile
import unittest

from utesla_reader.recorder import HEADER, CsvRecorder
from utesla_reader.sensor import Sample, parse_line

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_output.txt")


class ParseLineTest(unittest.TestCase):
    def test_full_line(self):
        line = ("Bx: 199.99 By: -200.00 Bz: -200.00 Magnitude: 346.4 "
                "TrueField: (220.32 -245.11 -216.83) Elapsed_ms:274")
        self.assertEqual(parse_line(line), (199.99, -200.0, -200.0))

    def test_banner_and_settings_are_not_readings(self):
        for line in ("MicroteslaSensor by Natan Osterman", "Averaging NumReads=", "50", ""):
            self.assertIsNone(parse_line(line))

    def test_truncated_line_is_rejected(self):
        self.assertIsNone(parse_line("Bx: 199.99 By: -200.00 Bz:"))

    def test_real_capture(self):
        # Real output captured from the device at 115200 baud. The first line is
        # cut off mid-way (the board resets when the port opens) and is followed
        # by the banner; every complete reading line must parse.
        with open(FIXTURE, encoding="latin-1") as f:
            lines = f.read().splitlines()
        readings = [parse_line(l) for l in lines]
        complete = [l for l in lines if "Elapsed_ms" in l and l.startswith("Bx:")]
        self.assertGreater(len(complete), 20)  # ~1.8 lines/s over 15 s
        for l in complete:
            self.assertEqual(parse_line(l), (199.99, -200.0, -200.0))
        self.assertGreaterEqual(sum(r is not None for r in readings), len(complete))


class CsvRecorderTest(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            rec = CsvRecorder(d)
            path = rec.start(1_760_000_000.0)
            rec.write([Sample(1_760_000_000.123, 1.0, -2.5, 3.25),
                       Sample(1_760_000_000.397, 4.0, 5.0, -6.0)])
            self.assertEqual(rec.stop(), path)
            self.assertFalse(rec.active)
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
        self.assertEqual(rows[0], HEADER)
        self.assertEqual(rows[1][1:], ["1.00", "-2.50", "3.25"])
        self.assertEqual(len(rows), 3)
        self.assertIn(".123", rows[1][0])  # millisecond precision

    def test_same_second_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            rec = CsvRecorder(d)
            p1 = rec.start(1_760_000_000.0)
            rec.stop()
            p2 = rec.start(1_760_000_000.5)
            rec.stop()
            self.assertNotEqual(p1, p2)


if __name__ == "__main__":
    unittest.main()
