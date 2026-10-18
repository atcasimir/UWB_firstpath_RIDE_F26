
import serial
import csv
from pathlib import Path
from datetime import datetime

PORT = "COM4"
BAUD = 115200
OUTPUT = Path(r"C:\Qorvo\UWB_firstpath_RIDE_F26\F401RE")

FIELDS = [
    "ipatovPeak",
    "ipatovPower",
    "ipatovF1",
    "ipatovF2",
    "ipatovF3",
    "ipatovFpIndex",
    "ipatovAccumCount",
    "stsPeak",
    "stsPower",
    "stsF1",
    "stsF2",
    "stsF3",
    "stsFpIndex",
    "stsAccumCount",
    "sts2Peak",
    "sts2Power",
    "sts2F1",
    "sts2F2",
    "sts2F3",
    "sts2FpIndex",
    "sts2AccumCount"
]

OUTPUT.mkdir(parents=True, exist_ok=True)

with serial.Serial(PORT, BAUD, timeout=1) as ser:
    print(f"Listening on {PORT} at {BAUD} baud")

    while True:
        line = ser.readline().decode(
            "utf-8", errors="replace"
        ).strip()

        if not line.startswith("RX_DIAG,"):
            continue

        values = line.split(",")[1:]

        if len(values) != len(FIELDS):
            print("Invalid record:", line)
            continue

        filename = datetime.now().strftime(
            "rx_diag_%Y%m%d_%H%M%S_%f.csv"
        )

        filepath = OUTPUT / filename

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Field", "Value"])

            for field, value in zip(FIELDS, values):
                writer.writerow([field, value])

        print("Saved:", filepath.name)
