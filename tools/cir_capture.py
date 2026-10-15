#!/usr/bin/env python3
"""
cir_capture.py - Capture CIR (channel impulse response) data from the DWM3000EVB.

Use with the SDK example TEST_SIMPLE_RX_CIR flashed on the receiving board.
This script replaces `uwbterm`: it opens the board's serial port itself, shows
progress, and saves every received packet's CIR to CSV files.

Install once:    python3 -m pip install pyserial
Run:             python3 tools/cir_capture.py                 (auto-detect board, run until Ctrl-C)
                 python3 tools/cir_capture.py -n 50           (stop after 50 packets)
                 python3 tools/cir_capture.py --port COM5     (Windows, choose the port)
                 python3 tools/cir_capture.py --port /dev/cu.usbmodem103
                 python3 tools/cir_capture.py --echo          (also print every raw line)
                 python3 tools/cir_capture.py --list          (list serial ports and exit)

Output (one folder per run, e.g. captures/2026-10-15_18-02-11/):
    raw_log.txt          everything the board printed, untouched (backup)
    packets.csv          one summary row per packet
    packet_0001.csv      the CIR of packet 1: section, index, real, imag, magnitude
    packet_0002.csv      ...

`section` is ipatov, sts0 or sts1 - the three CIRs the example prints per packet.
"""

import argparse
import csv
import datetime as dt
import math
import os
import re
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial is not installed. Run:  python3 -m pip install pyserial")

ST_VID = 0x0483  # STMicroelectronics USB vendor ID (the Nucleo's ST-Link)

RE_FRAME = re.compile(r"Frame Received len (\d+)")
RE_SECTION = re.compile(r"Printing (\w+) CIR")
RE_SAMPLE = re.compile(r"^\s*(-?\d+),(-?\d+),?\s*$")
RE_DIVIDER = re.compile(r"^_{5,}$")


# --------------------------------------------------------------------------- #
#  Parser: turns the example's text output into packets. No serial code here, #
#  so it can be tested by feeding it lines from a saved raw_log.txt.           #
# --------------------------------------------------------------------------- #
class CirParser:
    SECTIONS = ("ipatov", "sts0", "sts1")

    def __init__(self, on_packet):
        self.on_packet = on_packet  # called with a finished packet dict
        self.packet = None
        self.section = None
        self.in_block = False

    def _new_packet(self, frame_len):
        self.finish()
        self.packet = {"frame_len": frame_len, "time": dt.datetime.now(),
                       "cir": {s: [] for s in self.SECTIONS}}
        self.section = None
        self.in_block = False

    def finish(self):
        """Emit the current packet (if it has any samples)."""
        if self.packet and any(self.packet["cir"].values()):
            self.on_packet(self.packet)
        self.packet = None
        self.section = None
        self.in_block = False

    def feed_line(self, line):
        line = line.strip()
        if not line:
            return

        m = RE_FRAME.search(line)
        if m:
            self._new_packet(int(m.group(1)))
            return

        if self.packet is None:
            return  # text before the first packet (app name, "Waiting...", etc.)

        m = RE_SECTION.search(line)
        if m:
            name = m.group(1).lower()
            self.section = name if name in self.SECTIONS else None
            self.in_block = False
            return

        if RE_DIVIDER.match(line):
            if self.in_block and self.section == self.SECTIONS[-1]:
                self.finish()  # STS1 block closed -> packet complete
            else:
                self.in_block = not self.in_block
            return

        if self.in_block and self.section:
            m = RE_SAMPLE.match(line)
            if m:
                self.packet["cir"][self.section].append((int(m.group(1)), int(m.group(2))))
            return

        if "RX error" in line:
            self.finish()


# --------------------------------------------------------------------------- #
#  Saving                                                                      #
# --------------------------------------------------------------------------- #
class Saver:
    def __init__(self, out_dir):
        self.out_dir = out_dir
        self.count = 0
        os.makedirs(out_dir, exist_ok=True)
        self.summary_f = open(os.path.join(out_dir, "packets.csv"), "w", newline="")
        self.summary = csv.writer(self.summary_f)
        self.summary.writerow(["packet", "timestamp", "frame_len",
                               "n_ipatov", "n_sts0", "n_sts1",
                               "ipatov_peak_index", "ipatov_peak_magnitude", "file"])

    def save(self, pkt):
        self.count += 1
        fname = f"packet_{self.count:04d}.csv"
        with open(os.path.join(self.out_dir, fname), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["section", "index", "real", "imag", "magnitude"])
            for sec, samples in pkt["cir"].items():
                for i, (re_, im) in enumerate(samples):
                    w.writerow([sec, i, re_, im, f"{math.hypot(re_, im):.1f}"])

        ip = pkt["cir"]["ipatov"]
        peak_i, peak_m = (None, None)
        if ip:
            mags = [math.hypot(a, b) for a, b in ip]
            peak_i = max(range(len(mags)), key=mags.__getitem__)
            peak_m = mags[peak_i]
        self.summary.writerow([self.count, pkt["time"].isoformat(timespec="milliseconds"),
                               pkt["frame_len"], len(ip), len(pkt["cir"]["sts0"]),
                               len(pkt["cir"]["sts1"]), peak_i,
                               f"{peak_m:.1f}" if peak_m is not None else "", fname])
        self.summary_f.flush()
        return self.count, len(ip), peak_i, peak_m

    def close(self):
        self.summary_f.close()


# --------------------------------------------------------------------------- #
#  Serial port helpers                                                         #
# --------------------------------------------------------------------------- #
def find_board():
    ports = [p for p in list_ports.comports() if p.vid == ST_VID]
    if not ports:
        ports = [p for p in list_ports.comports()
                 if "usbmodem" in p.device or "STLink" in (p.description or "")]
    if not ports:
        return None
    if len(ports) > 1:
        print("More than one board found; using the first. Pick one with --port:")
        for p in ports:
            print(f"   {p.device}   {p.description}")
    return ports[0].device


def list_all():
    for p in list_ports.comports():
        tag = "  <- ST board" if p.vid == ST_VID else ""
        print(f"{p.device:28s} {p.description}{tag}")


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Capture DWM3000 CIR data from TEST_SIMPLE_RX_CIR.")
    ap.add_argument("--port", help="serial port (default: auto-detect the ST board)")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("-n", "--packets", type=int, default=0, help="stop after N packets (default: run until Ctrl-C)")
    ap.add_argument("--out", help="output folder (default: captures/<date_time>)")
    ap.add_argument("--echo", action="store_true", help="print every raw line from the board")
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    args = ap.parse_args()

    if args.list:
        list_all()
        return

    port = args.port or find_board()
    if not port:
        sys.exit("No board found. Check the data cable, or run with --list and pass --port.")

    out_dir = args.out or os.path.join("captures", dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    saver = Saver(out_dir)
    raw = open(os.path.join(out_dir, "raw_log.txt"), "w", newline="")

    def on_packet(pkt):
        n, n_ip, pi, pm = saver.save(pkt)
        pk = f"peak at index {pi} (|h| = {pm:.0f})" if pi is not None else "no Ipatov samples"
        print(f"  packet {n:4d}: frame len {pkt['frame_len']}, {n_ip} Ipatov samples, {pk}")

    parser = CirParser(on_packet)

    try:
        ser = serial.Serial(port, args.baud, timeout=0.2)
    except serial.SerialException as e:
        sys.exit(f"Could not open {port}: {e}\n"
                 "Is another viewer (uwbterm, screen, PuTTY, CubeIDE Terminal) still open?")

    print(f"Listening on {port} at {args.baud} baud.")
    print(f"Saving to {os.path.abspath(out_dir)}")
    print("Press RESET on the receiver board if nothing appears. Ctrl-C to stop.\n")

    buf = ""
    try:
        while True:
            chunk = ser.read(4096)
            if not chunk:
                continue
            text = chunk.decode("ascii", errors="replace")
            raw.write(text)
            buf += text
            *lines, buf = buf.split("\n")
            for line in lines:
                if args.echo:
                    print(line.rstrip("\r"))
                elif line.strip() and not RE_SAMPLE.match(line) and not RE_DIVIDER.match(line.strip()):
                    print("  board:", line.strip())
                parser.feed_line(line)
            if args.packets and saver.count >= args.packets:
                break
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        ser.close()
        raw.close()
        saver.close()
        print(f"\n{saver.count} packet(s) saved in {os.path.abspath(out_dir)}")


if __name__ == "__main__":
    main()
