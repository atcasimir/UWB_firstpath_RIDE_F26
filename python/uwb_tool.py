#!/usr/bin/env python3
"""
uwb_tool.py - run 3-CIR double-sided two-way-ranging trials on the F401RE + DWM3000
boards and save everything as JSON.

Run it once per board (one PC per board, or two terminals on one PC):

    python uwb_tool.py

It asks for the COM port, baud rate, role, real distance, labels and file name
(Enter keeps the previous answer), starts the trial on the board, shows progress,
and writes one .json file per trial. Press  q  to stop a trial early: the board is
told to stop and it tells the other board over UWB, so both sides end cleanly.

Both boards run the same firmware; the role is chosen here. The initiator ("TX")
decides the trial length and capture settings and sends them over the air, so the
responder ("RX") side only needs to be started.

Requires: pip install pyserial        (numpy is optional but recommended)
Analysis / merging of the two sides:  python uwb_analyze.py --help
"""

import argparse
import binascii
import csv
import datetime
import json
import math
import os
import queue
import random
import re
import socket
import statistics
import struct
import sys
import threading
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # pragma: no cover
    serial = None
    list_ports = None

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

# --------------------------------------------------------------------------------------
# Protocol constants (mirror of Functions/uwb_proto.h)
# --------------------------------------------------------------------------------------
PROTO_VERSION = 1
SYNC = b"\xA5\x5A"
BOOT_BAUD = 115200

PKT_INFO, PKT_ACK, PKT_LOG = 0x01, 0x02, 0x03
PKT_TRIAL_BEGIN, PKT_TRIAL_END = 0x10, 0x11
PKT_CIR, PKT_EXCHANGE = 0x20, 0x21
CMD_PING, CMD_SET_BAUD, CMD_START, CMD_STOP = 0x80, 0x81, 0x82, 0x83

ROLE_INITIATOR, ROLE_RESPONDER = 1, 2
ROLE_NAMES = {ROLE_INITIATOR: "initiator", ROLE_RESPONDER: "responder"}
CIR_KINDS = {0: "poll", 1: "response", 2: "final"}
START_FLAG_DUMP_FAILED = 0x01

ACK_TEXT = {
    0: "ok",
    1: "bad parameter",
    2: "board is busy with a trial",
    3: "DW3000 not found (dwt_probe failed) - is the shield seated?",
    4: "DW3000 did not initialise",
    5: "DW3000 configuration failed (PLL / RX calibration)",
    6: "unknown command (firmware older than this tool?)",
}
STATUS_TEXT = {0: "ok", 1: "no_response", 2: "no_final", 3: "late_tx", 4: "tx_fail", 5: "peer_done", 6: "peer_stop", 7: "peer_late"}
END_TEXT = {0: "done", 1: "stopped_here", 2: "stopped_by_other_side", 3: "idle_timeout", 4: "radio_error"}
VERIFY_TEXT = {0: "not_run", 1: "ok", 2: "MISMATCH"}

FMT_RADIO = "<BHBBBBBHBIHH"
FMT_START = "<BBIHHHHHHH"
FMT_INFO = "<HBBIIH"
FMT_ACK = "<BB"
FMT_BEGIN = "<BIHHHHHHIII8shH"
FMT_END = "<BIBIIHHHHBHH"
FMT_CIR = "<IIBBHHI5s5sBHIIIIIHHhhBI"
FMT_EXCH = "<IIBBBBHIIHH5s5s5sIIIdI"
assert struct.calcsize(FMT_RADIO) == 19 and struct.calcsize(FMT_START) == 20
assert struct.calcsize(FMT_INFO) == 14 and struct.calcsize(FMT_BEGIN) == 41
assert struct.calcsize(FMT_END) == 27 and struct.calcsize(FMT_CIR) == 64 and struct.calcsize(FMT_EXCH) == 65

# Physical constants (same values as the firmware / Qorvo examples)
DTU_S = 1.0 / 499.2e6 / 128.0  # one device time unit, about 15.65 ps
SPEED_OF_LIGHT = 299702547.0   # in air, m/s
SAMPLE_NS = 1e9 / 998.4e6      # one accumulator sample, about 1.0016 ns

RX_STATUS_FLAGS = {
    0: "no strong first-path rising edge (noise sensitive)",
    1: "noise threshold had to be lowered",
    2: "CIR too weak for an estimate",
    3: "coarse first path implausibly close to CIR end",
    4: "first path implausibly close to CIR end",
}

DEFAULT_SETTINGS = {
    "port": "",
    "baud": 1000000,
    "role": "responder",
    "data_dir": "data",
    "distance_m": 1.0,
    "group": "",
    "condition": "LOS",
    "notes": "",
    "count": 100,
    "advanced": {
        "interval_ms": 0,       # 0 = as fast as the link allows
        "cir_start": 0,         # first accumulator sample to capture
        "cir_len": 0,           # 0 = the whole CIR (1016 samples)
        "resp_delay_us": 0,     # 0 = automatic (sized to the measured CIR read time)
        "final_delay_us": 0,    # 0 = automatic
        "idle_timeout_s": 30,   # give up after this long without a completed exchange
        "dump_failed": False,   # also save CIRs of exchanges that did not complete
        "radio": {
            "chan": 9,
            "preamble_len": 128,
            "pac": 8,
            "tx_code": 9,
            "rx_code": 9,
            "sfd_type": 1,
            "data_rate": "6M8",   # "6M8" or "850K"
            "sfd_timeout": 0,     # 0 = automatic
            "pg_delay": 0,        # 0 = driver default 0x34
            "tx_power": 0,        # 0 = default for the channel (0xfdfdfdfd ch5, 0xfefefefe ch9)
            "tx_ant_dly": 16385,  # Qorvo's default antenna delay, applied in the chip so that raw ranges
            "rx_ant_dly": 16385,  # are already close to true; calibration (uwb_calib.py) removes the rest
        },
    },
}

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uwb_tool_settings.json")


# --------------------------------------------------------------------------------------
# Serial link
# --------------------------------------------------------------------------------------
def crc16(data):
    """CRC-16/CCITT-FALSE, same as the firmware."""
    return binascii.crc_hqx(bytes(data), 0xFFFF)


def make_packet(ptype, payload=b""):
    body = struct.pack("<BH", ptype, len(payload)) + payload
    return SYNC + body + struct.pack("<H", crc16(body))


class Link:
    """Packet link to one board. A background thread drains the serial port so that
    nothing is lost while the main thread is busy decoding or prompting."""

    def __init__(self, port, baud=BOOT_BAUD):
        if serial is None:
            raise SystemExit("pyserial is not installed. Run:  pip install pyserial")
        self.port = port
        self.ser = serial.Serial(port, baud, timeout=0.02)
        try:
            self.ser.set_buffer_size(rx_size=1 << 20, tx_size=1 << 12)  # Windows only
        except Exception:
            pass
        self.buf = bytearray()
        self.rxq = queue.Queue()
        self.crc_errors = 0
        self.bytes_in = 0
        self._run = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self):
        while self._run:
            try:
                data = self.ser.read(self.ser.in_waiting or 1)
            except Exception:
                if self._run:
                    self.rxq.put(None)  # port went away
                return
            if data:
                self.rxq.put(data)

    def close(self):
        self._run = False
        try:
            self.ser.close()
        except Exception:
            pass

    def set_baud(self, baud):
        self.ser.baudrate = baud
        self.flush_input()

    def flush_input(self):
        time.sleep(0.05)
        while True:
            try:
                self.rxq.get_nowait()
            except queue.Empty:
                break
        self.buf.clear()
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass

    def send(self, ptype, payload=b""):
        self.ser.write(make_packet(ptype, payload))
        self.ser.flush()

    def _parse(self):
        """Return one (type, payload) from the buffer, or None if incomplete."""
        buf = self.buf
        while True:
            i = buf.find(SYNC)
            if i < 0:
                del buf[: max(0, len(buf) - 1)]
                return None
            if i:
                del buf[:i]
            if len(buf) < 5:
                return None
            ptype, length = struct.unpack_from("<BH", buf, 2)
            total = 5 + length + 2
            if length > 8192:
                del buf[:1]
                continue
            if len(buf) < total:
                return None
            (crc,) = struct.unpack_from("<H", buf, 5 + length)
            if crc16(buf[2 : 5 + length]) == crc:
                payload = bytes(buf[5 : 5 + length])
                del buf[:total]
                return ptype, payload
            self.crc_errors += 1
            del buf[:1]

    def get(self, timeout=0.1):
        """Next packet, or None after timeout. Raises IOError if the port disappears."""
        deadline = time.monotonic() + timeout
        while True:
            pkt = self._parse()
            if pkt:
                return pkt
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                data = self.rxq.get(timeout=remaining)
            except queue.Empty:
                return None
            if data is None:
                raise IOError("serial port %s closed" % self.port)
            self.bytes_in += len(data)
            self.buf += data

    def wait_for(self, ptype, timeout, sink=None):
        """Wait for a packet of the given type; other packets go to sink(type, payload)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            pkt = self.get(min(0.1, max(0.0, deadline - time.monotonic())))
            if not pkt:
                continue
            if pkt[0] == ptype:
                return pkt[1]
            if sink:
                sink(*pkt)
        return None

    def ping(self, timeout=0.4, tries=2):
        for _ in range(tries):
            self.send(CMD_PING)
            payload = self.wait_for(PKT_INFO, timeout)
            if payload and len(payload) == struct.calcsize(FMT_INFO):
                return decode_info(payload)
        return None


def connect(port, baud, log=print):
    """Open the port, find the board at whatever baud it is using, make it idle and
    switch it to the requested baud. Returns (link, info)."""
    link = Link(port, BOOT_BAUD)
    info = None
    tried = []
    for rate in [BOOT_BAUD, baud, 1000000, 921600, 460800, 230400, 2000000]:
        if rate in tried:
            continue
        tried.append(rate)
        link.set_baud(rate)
        info = link.ping()
        if info:
            break
    if not info:
        link.close()
        raise SystemExit(
            "No reply from the board on %s.\n"
            "  - Is this the right COM port, and is no other program (terminal, old script) using it?\n"
            "  - Is the board flashed with the uwb_app firmware? Press the black reset button and try again."
            % port
        )
    if info["proto_version"] != PROTO_VERSION:
        link.close()
        raise SystemExit("Firmware protocol v%d, this tool expects v%d: re-flash the board or update the tool."
                         % (info["proto_version"], PROTO_VERSION))

    if info["state"] != 0:
        log("Board is still running a trial from an earlier session: stopping it...")
        link.send(CMD_STOP)
        link.wait_for(PKT_TRIAL_END, 6.0)
        info = link.ping() or info

    if info["baud"] != baud:
        link.send(CMD_SET_BAUD, struct.pack("<I", baud))
        ack = link.wait_for(PKT_ACK, 1.0)
        if not ack or ack[1] != 0:
            link.close()
            raise SystemExit("Board refused baud rate %d." % baud)
        time.sleep(0.15)
        link.set_baud(baud)
        info = link.ping(tries=3)
        if not info:
            link.close()
            raise SystemExit(
                "Board stopped answering after switching to %d baud. The ST-LINK virtual COM port may not "
                "support this rate: reset the board and choose a lower one (460800 or 115200)." % baud
            )
    return link, info


# --------------------------------------------------------------------------------------
# Decoding
# --------------------------------------------------------------------------------------
def decode_info(p):
    fw, proto, state, baud, uptime, max_cir = struct.unpack(FMT_INFO, p)
    return {"fw_version": "%d.%d" % (fw >> 8, fw & 0xFF), "proto_version": proto, "state": state, "baud": baud,
            "uptime_ms": uptime, "max_cir_len": max_cir}


def radio_to_bytes(r):
    rate = r["data_rate"]
    rate = 0 if str(rate).upper() in ("0", "850K") else 1
    return struct.pack(FMT_RADIO, int(r["chan"]), int(r["preamble_len"]), int(r["pac"]), int(r["tx_code"]),
                       int(r["rx_code"]), int(r["sfd_type"]), rate, int(r["sfd_timeout"]), int(r["pg_delay"]),
                       int(r["tx_power"]), int(r["tx_ant_dly"]), int(r["rx_ant_dly"]))


def radio_from_bytes(p):
    v = struct.unpack(FMT_RADIO, p)
    return {"chan": v[0], "preamble_len": v[1], "pac": v[2], "tx_code": v[3], "rx_code": v[4], "sfd_type": v[5],
            "data_rate": "850K" if v[6] == 0 else "6M8", "sfd_timeout": v[7], "pg_delay": v[8],
            "tx_power": "0x%08X" % v[9], "tx_ant_dly": v[10], "rx_ant_dly": v[11]}


def decode_trial_begin(p):
    n = struct.calcsize(FMT_BEGIN)
    v = struct.unpack(FMT_BEGIN, p[:n])
    return {
        "role": ROLE_NAMES.get(v[0], str(v[0])),
        "trial_id": "%08X" % v[1],
        "target_count": v[2],
        "interval_ms": v[3],
        "cir_start": v[4],
        "cir_len": v[5],
        "resp_delay_us": v[6] * 10,
        "final_delay_us": v[7] * 10,
        "cir_read_us": v[8],
        "device": {"dev_id": "0x%08X" % v[9], "part_id": "0x%08X" % v[10], "lot_id": v[11].hex(),
                   "temp_c": v[12] / 100.0, "vbat_v": v[13] / 1000.0},
        "radio": radio_from_bytes(p[n:]),
    }


def decode_trial_end(p):
    v = struct.unpack(FMT_END, p)
    return {"trial_id": "%08X" % v[1], "reason": END_TEXT.get(v[2], str(v[2])), "attempts": v[3], "completed": v[4],
            "n_timeout": v[5], "n_late_tx": v[6], "n_rx_error": v[7], "n_foreign": v[8],
            "cir_verify": VERIFY_TEXT.get(v[9], str(v[9])), "resp_delay_us": v[10] * 10, "final_delay_us": v[11] * 10}


def unpack_cir(raw):
    """Raw accumulator bytes (I lo,mid,hi, Q lo,mid,hi per sample; 24-bit signed) -> two int lists."""
    if np is not None:
        a = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 6).astype(np.int32)
        i = a[:, 0] | (a[:, 1] << 8) | (a[:, 2] << 16)
        q = a[:, 3] | (a[:, 4] << 8) | (a[:, 5] << 16)
        i -= (i & 0x800000) << 1
        q -= (q & 0x800000) << 1
        return i.tolist(), q.tolist()
    i, q = [], []
    for k in range(0, len(raw), 6):
        i.append(int.from_bytes(raw[k : k + 3], "little", signed=True))
        q.append(int.from_bytes(raw[k + 3 : k + 6], "little", signed=True))
    return i, q


def decode_diag(v, prf64=True):
    """v = unpacked uwb_cir_hdr_t. Bit fields per DW3000 User Manual section 8.2.13."""
    (ip_toa, status, poa, peak, power, f1, f2, f3, fp_index, accum, xtal, clock_offset, dgc, cia_diag1) = v
    d = {
        "ip_toa": int.from_bytes(ip_toa, "little"),
        "status": status,
        "status_flags": [text for bit, text in RX_STATUS_FLAGS.items() if status & (1 << bit)],
        "timestamp_reliable": (status & 0x1F) == 0,
        "fp_index": fp_index / 64.0,                      # 10.6 fixed point, accumulator samples
        "peak_index": (peak >> 21) & 0x3FF,
        "peak_amp": (peak & 0x1FFFFF) / 4.0,              # 2 fractional bits
        "channel_area": power & 0x1FFFF,
        "f1": (f1 & 0x3FFFFF) / 4.0,
        "f2": (f2 & 0x3FFFFF) / 4.0,
        "f3": (f3 & 0x3FFFFF) / 4.0,
        "accum_count": accum & 0xFFF,
        "clock_offset_ppm": clock_offset / float(1 << 26) * 1e6,
        "dgc_decision": dgc,
        "poa": poa,
        "raw": {"ip_peak": peak, "ip_power": power, "ip_f1": f1, "ip_f2": f2, "ip_f3": f3, "ip_fp_index": fp_index,
                "ip_accum": accum, "xtal_offset": xtal, "clock_offset": clock_offset, "cia_diag1": cia_diag1},
    }
    # Estimated power levels, DW3000 User Manual section 4.7 (A = 121.7 dB for 64 MHz PRF Ipatov).
    n = d["accum_count"]
    a_const = 121.7 if prf64 else 113.8
    dgc_db = 6.0 * dgc if prf64 else 0.0
    d["rx_power_dbm"] = d["fp_power_dbm"] = None
    if n > 0:
        if d["channel_area"] > 0:
            d["rx_power_dbm"] = round(10 * math.log10(d["channel_area"] * 2.0 ** 21 / n ** 2) + dgc_db - a_const, 2)
        s = d["f1"] ** 2 + d["f2"] ** 2 + d["f3"] ** 2
        if s > 0:
            d["fp_power_dbm"] = round(10 * math.log10(s / n ** 2) + dgc_db - a_const, 2)
    return d


def decode_cir(p, prf64=True):
    n = struct.calcsize(FMT_CIR)
    v = struct.unpack(FMT_CIR, p[:n])
    trial_id, xid, kind, acc, start, length, read_us, rx_stamp = v[:8]
    i, q = unpack_cir(p[n:])
    if len(i) != length:
        raise ValueError("CIR packet length mismatch")
    return {
        "trial_id": "%08X" % trial_id,
        "xid": xid,
        "kind": CIR_KINDS.get(kind, str(kind)),
        "record": {
            "cir_start": start,
            "cir_len": length,
            "read_us": read_us,
            "rx_timestamp": int.from_bytes(rx_stamp, "little"),
            "diag": decode_diag(v[8:], prf64),
            "cir": {"i": i, "q": q},
        },
    }


def tof_dtu_from_timestamps(poll_rx, resp_tx, final_rx, peer):
    """Asymmetric double-sided TWR, exact integer arithmetic (32-bit wrapping differences)."""
    m = 0xFFFFFFFF
    ra = (peer[1] - peer[0]) & m   # initiator: poll TX -> response RX
    rb = (final_rx - resp_tx) & m  # responder: response TX -> final RX
    da = (peer[2] - peer[1]) & m   # initiator: response RX -> final TX
    db = (resp_tx - poll_rx) & m   # responder: poll RX -> response TX
    den = ra + rb + da + db
    return (ra * rb - da * db) / den if den else float("nan")


def decode_exchange(p):
    v = struct.unpack(FMT_EXCH, p)
    (trial_id, xid, role, status, peer_flags, n_cir, completed, t_ms, proc_us, resp_d, final_d,
     ts0, ts1, ts2, p0, p1, p2, tof_mcu, sys_status) = v
    ts = [int.from_bytes(t, "little") for t in (ts0, ts1, ts2)]
    ex = {
        "xid": xid,
        "status": STATUS_TEXT.get(status, str(status)),
        "t_ms": t_ms,
        "completed": completed,
        "proc_us": proc_us,
        "resp_delay_us": resp_d * 10,
        "final_delay_us": final_d * 10,
    }
    if status != 0:
        ex["sys_status"] = "0x%08X" % sys_status
    if role == ROLE_INITIATOR:
        ex["peer_flags"] = peer_flags
        if status == 0:
            ex["timestamps"] = {"poll_tx": ts[0], "resp_rx": ts[1], "final_tx": ts[2]}
    elif status == 0:
        ex["timestamps"] = {"poll_rx": ts[0], "resp_tx": ts[1], "final_rx": ts[2],
                            "poll_tx_32": p0, "resp_rx_32": p1, "final_tx_32": p2}
        tof = tof_dtu_from_timestamps(ts[0], ts[1], ts[2], (p0, p1, p2))
        ex["tof_dtu"] = tof
        ex["tof_ns"] = tof * DTU_S * 1e9
        ex["range_m"] = tof * DTU_S * SPEED_OF_LIGHT
        ex["tof_dtu_mcu"] = tof_mcu
    return "%08X" % trial_id, role, n_cir, ex


# --------------------------------------------------------------------------------------
# Keyboard: non-blocking "press q to stop"
# --------------------------------------------------------------------------------------
class KeyPoller:
    def __enter__(self):
        self.mode = None
        try:
            if os.name == "nt":
                import msvcrt
                self.msvcrt = msvcrt
                self.mode = "nt"
            elif sys.stdin.isatty():
                import termios
                import tty
                self.termios = termios
                self.fd = sys.stdin.fileno()
                self.old = termios.tcgetattr(self.fd)
                tty.setcbreak(self.fd)
                self.mode = "posix"
        except Exception:
            self.mode = None
        return self

    def poll(self):
        if self.mode == "nt":
            if self.msvcrt.kbhit():
                return self.msvcrt.getwch()
        elif self.mode == "posix":
            import select
            if select.select([sys.stdin], [], [], 0)[0]:
                return sys.stdin.read(1)
        return None

    def __exit__(self, *exc):
        if self.mode == "posix":
            self.termios.tcsetattr(self.fd, self.termios.TCSADRAIN, self.old)


# --------------------------------------------------------------------------------------
# Running one trial
# --------------------------------------------------------------------------------------
def build_start(role, settings, trial_id):
    adv = settings["advanced"]
    flags = START_FLAG_DUMP_FAILED if adv.get("dump_failed") else 0
    head = struct.pack(
        FMT_START,
        role,
        flags,
        trial_id,
        int(settings.get("count", 0)) if role == ROLE_INITIATOR else int(settings.get("responder_count", 0)),
        int(adv["interval_ms"]),
        int(adv["cir_start"]),
        int(adv["cir_len"]),
        int(adv["resp_delay_us"]) // 10,
        int(adv["final_delay_us"]) // 10,
        int(adv["idle_timeout_s"]),
    )
    return head + radio_to_bytes(adv["radio"])


class _NoKeys:
    """Stand-in for KeyPoller when there is no keyboard to watch (the GUI)."""
    def __enter__(self):
        return self

    def poll(self):
        return None

    def __exit__(self, *exc):
        pass


def run_trial(link, role, settings, meta, stop_event=None, log=print, progress=True, on_update=None, use_keys=True):
    """Start a trial on the board and collect it. Returns the trial dict, or None if the
    responder was stopped before any trial began.

    on_update(dict) is called whenever the counts change (used by uwb_gui.py);
    use_keys=False leaves the keyboard alone."""
    prf64 = int(settings["advanced"]["radio"]["rx_code"]) >= 9
    trial_id_int = random.getrandbits(32) or 1
    trial = {
        "format": "uwb-cir-trial",
        "version": 1,
        "trial_id": "%08X" % trial_id_int if role == ROLE_INITIATOR else None,
        "role": ROLE_NAMES[role],
        "started": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "ended": None,
        "host": socket.gethostname(),
        "meta": dict(meta),
        "params": None,
        "device": None,
        "end": None,
        "link": {"port": link.port, "baud": settings["baud"], "crc_errors": 0},
        "exchanges": [],
    }

    link.flush_input()
    crc_before = link.crc_errors
    link.send(CMD_START, build_start(role, settings, trial_id_int))
    ack = link.wait_for(PKT_ACK, 4.0)
    if not ack:
        raise RuntimeError("no answer to START (board reset or unplugged?)")
    if ack[1] != 0:
        raise RuntimeError("board refused START: " + ACK_TEXT.get(ack[1], "code %d" % ack[1]))

    if role == ROLE_RESPONDER:
        log("Responder armed: waiting for the initiator.%s" % (" Press q to stop." if use_keys else ""))
    else:
        log("Initiator started.%s" % (" Press q to stop." if use_keys else ""))

    pending = {}        # (xid, kind) -> CIR record
    ranges = []
    n_ok = 0
    n_fail = 0
    stop_sent = None
    last_rx = time.monotonic()
    last_ping = 0.0
    last_print = 0.0
    interrupted = False

    def request_stop(why):
        nonlocal stop_sent
        if stop_sent is None:
            log("\n%s: stopping (the other board is told over UWB)..." % why)
            link.send(CMD_STOP)
            stop_sent = time.monotonic()

    def show(force=False):
        nonlocal last_print
        if on_update is not None:
            on_update({
                "device": trial["device"],
                "params": trial["params"],
                "trial_id": trial["trial_id"],
                "n_ok": n_ok,
                "n_fail": n_fail,
                "target": (trial["params"] or {}).get("target_count", 0),
                "last_m": ranges[-1] if ranges else None,
                "mean_m": statistics.fmean(ranges) if ranges else None,
                "sd_m": statistics.stdev(ranges) if len(ranges) > 1 else None,
                "begun": trial["params"] is not None,
            })
        if not progress:
            return
        now = time.monotonic()
        if not force and now - last_print < 0.25:
            return
        last_print = now
        target = (trial["params"] or {}).get("target_count", 0)
        text = "  %d%s ok, %d failed" % (n_ok, ("/%d" % target) if target else "", n_fail)
        if ranges:
            text += " | range %.3f m" % ranges[-1]
            if len(ranges) > 1:
                text += "  mean %.3f  sd %.3f" % (statistics.fmean(ranges), statistics.stdev(ranges))
        sys.stdout.write("\r" + text + "    ")
        sys.stdout.flush()

    with (KeyPoller() if use_keys else _NoKeys()) as keys:
        while True:
            try:
                key = keys.poll()
                if key and key.lower() == "q":
                    request_stop("q pressed")
                if stop_event is not None and stop_event.is_set():
                    request_stop("stop requested")

                pkt = link.get(0.1)
            except KeyboardInterrupt:
                if interrupted:
                    log("\nSecond Ctrl+C: giving up on a clean stop.")
                    break
                interrupted = True
                request_stop("Ctrl+C")
                continue

            now = time.monotonic()
            if pkt is None:
                if stop_sent is not None and now - stop_sent > 8.0:
                    log("\nBoard did not confirm the stop; saving what was received.")
                    break
                if now - last_rx > 3.0 and now - last_ping > 3.0:
                    last_ping = now
                    link.send(CMD_PING)  # keep-alive: shows up as PKT_INFO below
                if now - last_rx > 12.0:
                    log("\nBoard has gone silent (unplugged or reset?); saving what was received.")
                    break
                continue

            last_rx = now
            ptype, payload = pkt

            if ptype == PKT_CIR:
                c = decode_cir(payload, prf64)
                pending[(c["xid"], c["kind"])] = c["record"]

            elif ptype == PKT_EXCHANGE:
                tid, _role, n_cir, ex = decode_exchange(payload)
                for kind in ("poll", "response", "final"):
                    rec = pending.pop((ex["xid"], kind), None)
                    if rec is not None:
                        ex[kind] = rec
                pending.clear()
                if trial["trial_id"] is None:
                    trial["trial_id"] = tid
                if ex["status"] in ("peer_done", "peer_stop"):
                    pass  # bookkeeping exchange that only carried the end-of-trial flag
                else:
                    trial["exchanges"].append(ex)
                    if ex["status"] == "ok":
                        n_ok += 1
                        if "range_m" in ex:
                            ranges.append(ex["range_m"])
                    else:
                        n_fail += 1
                show()

            elif ptype == PKT_TRIAL_BEGIN:
                begin = decode_trial_begin(payload)
                trial["trial_id"] = begin["trial_id"]
                trial["device"] = begin.pop("device")
                begin.pop("role", None)
                trial["params"] = begin
                log("Trial %s: CIR samples %d..%d, reply delays %d / %d us, CIR read %d us"
                    % (begin["trial_id"], begin["cir_start"], begin["cir_start"] + begin["cir_len"] - 1,
                       begin["resp_delay_us"], begin["final_delay_us"], begin["cir_read_us"]))
                if role == ROLE_INITIATOR:
                    log("Calling the responder... (it can be started before or after this board)")
                show(force=True)

            elif ptype == PKT_TRIAL_END:
                trial["end"] = decode_trial_end(payload)
                trial["end"].pop("trial_id", None)
                break

            elif ptype == PKT_LOG:
                log("\n[board] " + payload.decode("ascii", "replace"))

            # PKT_INFO (keep-alive reply) and PKT_ACK (stop acknowledged) need no action.

    show(force=True)
    if progress:
        sys.stdout.write("\n")
    trial["ended"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    trial["link"]["crc_errors"] = link.crc_errors - crc_before

    if trial["end"] is None:
        trial["end"] = {"reason": "aborted_by_tool"}
    if role == ROLE_RESPONDER and trial["trial_id"] in (None, "00000000") and not trial["exchanges"]:
        return None
    return trial


# --------------------------------------------------------------------------------------
# Saving
# --------------------------------------------------------------------------------------
def write_trial_json(trial, path):
    """JSON with one exchange per line: still plain JSON, but the header stays readable
    and a text editor or diff can cope with it."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("{\n")
        keys = [k for k in trial if k != "exchanges"]
        for k in keys:
            f.write(" %s: %s,\n" % (json.dumps(k), json.dumps(trial[k])))
        f.write(' "exchanges": [\n')
        n = len(trial["exchanges"])
        for idx, ex in enumerate(trial["exchanges"]):
            f.write("  " + json.dumps(ex, separators=(",", ":")) + (",\n" if idx + 1 < n else "\n"))
        f.write(" ]\n}\n")
    os.replace(tmp, path)


def range_summary(trial):
    r = [e["range_m"] for e in trial["exchanges"] if e.get("status") == "ok" and "range_m" in e]
    if not r:
        return None
    s = {"n": len(r), "mean_m": statistics.fmean(r), "median_m": statistics.median(r), "min_m": min(r), "max_m": max(r),
         "std_m": statistics.stdev(r) if len(r) > 1 else None}
    real = trial["meta"].get("distance_m")
    if real is not None:
        s["bias_m"] = s["mean_m"] - real
    return s


def append_index(data_dir, trial, path):
    """One line per saved trial, so a folder of trials can be scanned without opening them."""
    index = os.path.join(data_dir, "trials_index.csv")
    s = trial.get("summary") or {}
    row = {
        "started": trial["started"],
        "trial_id": trial["trial_id"],
        "role": trial["role"],
        "file": os.path.basename(path),
        "group": trial["meta"].get("group", ""),
        "condition": trial["meta"].get("condition", ""),
        "distance_m": trial["meta"].get("distance_m", ""),
        "n_ok": sum(1 for e in trial["exchanges"] if e.get("status") == "ok"),
        "n_failed": sum(1 for e in trial["exchanges"] if e.get("status") != "ok"),
        "mean_m": "%.4f" % s["mean_m"] if s.get("mean_m") is not None else "",
        "std_m": "%.4f" % s["std_m"] if s.get("std_m") is not None else "",
        "bias_m": "%.4f" % s["bias_m"] if s.get("bias_m") is not None else "",
        "n_flagged": len((trial.get("analysis") or {}).get("flagged", [])) if trial.get("analysis") else "",
        "end": (trial.get("end") or {}).get("reason", ""),
    }
    new = not os.path.exists(index)
    with open(index, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


def finish_trial(trial, path, data_dir, log=print):
    """Summarise, analyse (if numpy is available), save, index, and merge with the other
    side's file if it is already in the same folder."""
    trial["summary"] = range_summary(trial)
    analysis = None
    try:
        import uwb_analyze
        analysis = uwb_analyze.analyze_trial(trial)
        trial["analysis"] = analysis
    except ImportError:
        uwb_analyze = None
    except Exception as exc:  # analysis must never cost us the data
        log("Analysis skipped: %s" % exc)

    write_trial_json(trial, path)
    append_index(data_dir, trial, path)

    end = trial.get("end") or {}
    n_ok = sum(1 for e in trial["exchanges"] if e.get("status") == "ok")
    log("Saved %s  (%d exchanges ok, %d failed, ended: %s)"
        % (path, n_ok, len(trial["exchanges"]) - n_ok, end.get("reason", "?")))
    if end.get("cir_verify") == "MISMATCH":
        log("WARNING: the fast CIR read did not match dwt_readcir() on this board. Do not trust the CIR data;"
            " report this.")
    if end.get("n_late_tx"):
        log("Note: %d late transmissions (reply delay was raised automatically: now %s / %s us)."
            % (end["n_late_tx"], end.get("resp_delay_us"), end.get("final_delay_us")))
    if trial["link"]["crc_errors"]:
        log("Note: %d corrupted serial packets were dropped. If this keeps happening, use a lower baud rate."
            % trial["link"]["crc_errors"])
    s = trial["summary"]
    if s:
        text = "Range: n=%d  mean %.3f m  median %.3f m" % (s["n"], s["mean_m"], s["median_m"])
        if s["std_m"] is not None:
            text += "  sd %.3f m" % s["std_m"]
        if "bias_m" in s:
            text += "  | real %.3f m, bias %+.3f m" % (trial["meta"]["distance_m"], s["bias_m"])
        off = None
        if uwb_analyze is not None:
            try:
                off = uwb_analyze.cal_offset(path, trial)
            except Exception:
                off = None
        if off is not None:
            log("Range (raw, before calibration): " + text[7:])
            cal = "Range (calibrated): mean %.3f m" % (s["mean_m"] - off)
            if "bias_m" in s:
                cal += "  | real %.3f m, difference %+.3f m" % (trial["meta"]["distance_m"], s["bias_m"] - off)
            log(cal)
        else:
            log(text)
            log("   (not calibrated yet: this still contains what is left of the boards' antenna delay)")
    if analysis and analysis.get("flagged"):
        log("Flagged %d of %d exchanges as abnormal:" % (len(analysis["flagged"]), analysis["n"]))
        for item in analysis["flagged"][:12]:
            more = len(item["reasons"]) - 2
            log("   xid %-5d %s%s" % (item["xid"], "; ".join(item["reasons"][:2]),
                                      (" (+%d more)" % more) if more > 0 else ""))
        if len(analysis["flagged"]) > 12:
            log("   ... see the 'analysis' block in the file for the rest")

    if uwb_analyze is not None:
        try:
            merged = uwb_analyze.merge_with_counterpart(path)
            if merged:
                log("Merged with the other side: %s" % merged)
        except Exception as exc:
            log("Merge skipped: %s" % exc)


# --------------------------------------------------------------------------------------
# Prompts and settings
# --------------------------------------------------------------------------------------
def deep_update(base, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = v
    return base


def load_settings():
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            deep_update(settings, json.load(f))
    except (OSError, ValueError):
        pass
    # Antenna delay is not something to change by accident: every board runs with the
    # driver's default whatever an older settings file says (--set can still override it).
    settings["advanced"]["radio"]["tx_ant_dly"] = 16385
    settings["advanced"]["radio"]["rx_ant_dly"] = 16385
    return settings


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass


def ask(label, default, cast=str):
    while True:
        shown = "" if default in (None, "") else " [%s]" % default
        text = input("%s%s: " % (label, shown)).strip()
        if not text:
            if default is None:
                continue
            return default
        try:
            return cast(text)
        except ValueError:
            print("  not understood, try again")


def choose_port(default):
    ports = list(list_ports.comports()) if list_ports else []
    if ports:
        print("Serial ports:")
        for p in ports:
            mark = "  <- ST-LINK" if "STLink" in (p.description or "") or "STMicro" in (p.manufacturer or "") else ""
            print("   %-8s %s%s" % (p.device, p.description or "", mark))
        names = [p.device for p in ports]
        if default not in names:
            stlinks = [p.device for p in ports if "STLink" in (p.description or "") or "STMicro" in (p.manufacturer or "")]
            if len(stlinks) == 1:
                default = stlinks[0]
            elif len(names) == 1:
                default = names[0]
    return ask("COM port", default or None)


def slug(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(text)).strip("_")


def default_filename(data_dir, group, role_name):
    stem = slug(group) or "trial"
    n = 1
    while True:
        name = "%s_%03d_%s.json" % (stem, n, role_name)
        if not os.path.exists(os.path.join(data_dir, name)):
            return name
        n += 1


def parse_role(text):
    t = text.strip().lower()
    if t in ("i", "init", "initiator", "tx", "t"):
        return "initiator"
    if t in ("r", "resp", "responder", "rx"):
        return "responder"
    raise ValueError(text)


def set_by_path(settings, assignment):
    """--set advanced.cir_len=300   --set advanced.radio.chan=5"""
    key, _, value = assignment.partition("=")
    node = settings
    parts = key.strip().split(".")
    for part in parts[:-1]:
        node = node[part]
    old = node[parts[-1]]
    if isinstance(old, bool):
        node[parts[-1]] = value.strip().lower() in ("1", "true", "yes", "on")
    elif isinstance(old, int):
        node[parts[-1]] = int(value, 0)
    elif isinstance(old, float):
        node[parts[-1]] = float(value)
    else:
        node[parts[-1]] = value


def estimate_rate(settings):
    """Rough exchanges per second from the serial throughput, to set expectations."""
    adv = settings["advanced"]
    n = adv["cir_len"] or 1016
    bytes_per_exchange = 2 * (n * 6 + 75) + 80  # the responder's two CIRs set the pace
    seconds = bytes_per_exchange * 10.0 / settings["baud"] + 0.03
    if adv["interval_ms"]:
        seconds = max(seconds, adv["interval_ms"] / 1000.0)
    return 1.0 / seconds


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run 3-CIR DS-TWR trials and save them as JSON.")
    ap.add_argument("--port", help="serial port, e.g. COM6")
    ap.add_argument("--baud", type=int, help="baud rate for the data link (default 1000000)")
    ap.add_argument("--role", type=parse_role, help="initiator (tx) or responder (rx)")
    ap.add_argument("--distance", type=float, help="real distance in metres")
    ap.add_argument("--group", help="comparison group label (same place and setup = same label)")
    ap.add_argument("--condition", help="LOS / NLOS / free text")
    ap.add_argument("--notes", help="free text stored in the file")
    ap.add_argument("--count", type=int, help="initiator: number of completed exchanges (0 = until stopped)")
    ap.add_argument("--file", help="output file name (.json)")
    ap.add_argument("--data-dir", help="folder for the output files")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override a setting, e.g. --set advanced.cir_start=600 --set advanced.cir_len=300")
    ap.add_argument("--yes", action="store_true", help="no questions: use the given options and saved answers")
    ap.add_argument("--repeat", action="store_true",
                    help="after each trial start the next one with the same answers (auto-numbered files)")
    args = ap.parse_args(argv)

    settings = load_settings()
    for assignment in args.set:
        set_by_path(settings, assignment)
    for name in ("port", "baud", "role", "count", "notes", "group", "condition"):
        if getattr(args, name) is not None:
            settings[name] = getattr(args, name)
    if args.distance is not None:
        settings["distance_m"] = args.distance
    if args.data_dir:
        settings["data_dir"] = args.data_dir

    interactive = not args.yes
    if interactive:
        print("=== UWB 3-CIR capture ===  (Enter keeps the value in [brackets])")
        settings["port"] = choose_port(settings["port"]) if not args.port else args.port
        if args.baud is None:
            settings["baud"] = ask("Baud rate", settings["baud"], int)
        if args.role is None:
            settings["role"] = ask("Role: (i)nitiator / (r)esponder", settings["role"], parse_role)
    if not settings["port"]:
        raise SystemExit("No serial port given.")
    role = ROLE_INITIATOR if settings["role"] == "initiator" else ROLE_RESPONDER
    save_settings(settings)

    link, info = connect(settings["port"], settings["baud"])
    print("Connected: firmware %s on %s at %d baud." % (info["fw_version"], settings["port"], settings["baud"]))

    first = True
    try:
        while True:
            ask_now = interactive and (first or not args.repeat)
            if ask_now:
                if first or args.distance is None:
                    settings["distance_m"] = ask("Real distance (m)", settings["distance_m"], float)
                settings["group"] = ask("Comparison group (same place + setup = same label)", settings["group"] or "default")
                settings["condition"] = ask("Condition (LOS / NLOS / ...)", settings["condition"])
                settings["notes"] = ask("Notes", settings["notes"] or "-")
                if role == ROLE_INITIATOR:
                    settings["count"] = ask("Number of exchanges (0 = until stopped)", settings["count"], int)
            data_dir = settings["data_dir"]
            name = default_filename(data_dir, settings["group"], settings["role"])
            if first and args.file:
                name = args.file
            elif ask_now:
                name = ask("File name", name)
            if not name.lower().endswith(".json"):
                name += ".json"
            path = name if os.path.isabs(name) or os.path.dirname(name) else os.path.join(data_dir, name)
            save_settings(settings)

            rate = estimate_rate(settings)
            print("Expect about %.1f exchanges per second at this baud rate and CIR length." % rate)

            meta = {"distance_m": settings["distance_m"], "group": settings["group"], "condition": settings["condition"],
                    "notes": "" if settings["notes"] == "-" else settings["notes"]}
            try:
                trial = run_trial(link, role, settings, meta)
            except RuntimeError as exc:
                print("Could not start: %s" % exc)
                trial = None
            if trial is not None:
                finish_trial(trial, path, os.path.dirname(os.path.abspath(path)))
            else:
                print("Nothing recorded.")

            first = False
            reason = ((trial or {}).get("end") or {}).get("reason")
            if args.repeat and reason not in ("stopped_here", "aborted_by_tool", None):
                continue
            if not interactive:
                break
            again = ask("Another trial? (y/n)", "y").lower()
            if not again.startswith("y"):
                break
    except (KeyboardInterrupt, EOFError):
        print("\nBye.")
    finally:
        try:
            link.send(CMD_STOP)
        except Exception:
            pass
        link.close()


if __name__ == "__main__":
    main()
