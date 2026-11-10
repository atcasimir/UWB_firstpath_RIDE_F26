#!/usr/bin/env python3
"""
uwb_calib.py - antenna delay calibration (Qorvo APS014 / DW3000 User Manual section 10.3).

Every board adds a fixed delay between its timestamp and its antenna: about 257 ns each
way. The chips are loaded with Qorvo's default for it (16385 in both registers), which
makes raw ranges close to true; what is left differs from board to board and puts every
range off by the same small amount, at every distance and in every room. Calibration
measures that leftover once, in clean line of sight at a known distance, and the
analysis removes it. Each trial records the register values it ran with, and a
calibration is only applied to trials recorded with the same values.

The correction is applied to the numbers when they are analysed, not written into the
chips: the saved trial files stay raw, and a calibration can be redone or removed at
any time. calibration.json in the data folder holds

    pairs   one entry per two boards (and channel) that were ranged against each other
    boards  one value per board, when three or more boards were ranged in all pairings
            (then any pairing of those boards is corrected, as in APS014 section 2.2)

Boards are recognised by the chip's part id and lot id, which every trial file records.
An offset is in metres: calibrated range = measured range - offset.
"""

import datetime
import json
import math
import os

SPEED_OF_LIGHT = 299702547.0
DTU_S = 1.0 / (499.2e6 * 128.0)
DEFAULT_ANT_DLY = 16385
FILE_NAME = "calibration.json"


def board_id(device):
    if not device or not device.get("part_id"):
        return None
    return "%s-%s" % (device.get("part_id"), device.get("lot_id") or "")


def trial_boards(trial):
    """(initiator board id or None, responder board id or None, channel)."""
    chan = ((trial.get("params") or {}).get("radio") or {}).get("chan")
    if trial.get("devices"):
        return board_id(trial["devices"].get("initiator")), board_id(trial["devices"].get("responder")), chan
    dev = board_id(trial.get("device"))
    if trial.get("role") == "initiator":
        return dev, None, chan
    return None, dev, chan


def own_ant_dly(trial):
    """TX + RX antenna delay (device time units) the board of a one-sided file was set to, or None."""
    radio = (trial.get("params") or {}).get("radio") or {}
    if "tx_ant_dly" not in radio:
        return None
    return int(radio.get("tx_ant_dly", 0)) + int(radio.get("rx_ant_dly", 0))


def ant_total(trial):
    """Sum of the antenna delays set in BOTH boards' chips during this trial (device time units).
    A calibration is only valid for trials run with the same total: the chip settings and the
    offset removed here add up. Files that know one board only assume the other was set alike."""
    both = trial.get("ant_dly")
    if both:
        vals = [v for v in (both.get("initiator"), both.get("responder")) if v is not None]
        if len(vals) == 2:
            return vals[0] + vals[1]
        if len(vals) == 1:
            return 2 * vals[0]
    own = own_ant_dly(trial)
    return None if own is None else 2 * own


def expected_offset_m(total_dtu):
    """Roughly what the offset should be: a DWM3000 board's TX + RX delay is about 513-515 ns
    (roughly 2 x 16385 device time units, the driver's old default); whatever the chips do not remove shows up as range."""
    typical_total = 4.0 * DEFAULT_ANT_DLY
    return (typical_total - (total_dtu or 0)) / 2.0 * DTU_S * SPEED_OF_LIGHT


def short(bid):
    """A board id people can read aloud: the last 4 hex digits of the part id."""
    if not bid:
        return "unknown board"
    return "board " + bid.split("-")[0][-4:].upper()


def floor_bounce_ns(distance_m, height_m):
    """How long after the direct path the floor reflection arrives (both antennas at height_m)."""
    if distance_m is None or height_m is None or distance_m <= 0 or height_m <= 0:
        return None
    return (math.sqrt(distance_m ** 2 + 4.0 * height_m ** 2) - distance_m) / SPEED_OF_LIGHT * 1e9


def dtu_from_m(offset_m):
    return offset_m / SPEED_OF_LIGHT / DTU_S


# ---- the file ------------------------------------------------------------------------
def load(folder):
    cal = {"format": "uwb-calibration", "pairs": [], "boards": {}}
    try:
        with open(os.path.join(folder, FILE_NAME), "r", encoding="utf-8") as f:
            d = json.load(f)
        if d.get("format") == "uwb-calibration":
            cal.update(d)
    except (OSError, ValueError):
        pass
    return cal


def save(folder, cal):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, FILE_NAME)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cal, f, indent=1)
    os.replace(tmp, path)
    return path


_cache = {}


def load_cached(folder):
    path = os.path.join(folder, FILE_NAME)
    try:
        stamp = os.path.getmtime(path)
    except OSError:
        return None
    if _cache.get(path, (None, None))[0] != stamp:
        _cache[path] = (stamp, load(folder))
    return _cache[path][1]


# ---- looking a correction up ---------------------------------------------------------
def offset_for(cal, trial):
    """(offset in metres, description) for this trial, or (None, why not)."""
    if not cal:
        return None, "no calibration saved"
    a, b, chan = trial_boards(trial)
    total = ant_total(trial)
    boards = (cal.get("boards") or {}).get(str(chan)) or {}
    if a and b and a in boards and b in boards and boards[a].get("ant_dly") is not None and \
            total == boards[a]["ant_dly"] + boards[b]["ant_dly"]:
        return (boards[a]["delay_m"] + boards[b]["delay_m"]) / 2.0, "per-board calibration"
    best = None
    wrong_setting = False
    for p in cal.get("pairs", []):
        if p.get("chan") != chan:
            continue
        if p.get("ant_dly_total", 4 * DEFAULT_ANT_DLY) != total:
            wrong_setting = wrong_setting or ({a, b} & {p.get("a"), p.get("b")} != set())
            continue
        pa, pb = p.get("a"), p.get("b")
        known = [x for x in (a, b) if x]
        if a and b:
            if {a, b} == {pa, pb}:
                return p["offset_m"], "pair calibration of %s" % p.get("date", "?")[:10]
            continue
        # This file knows only one of its two boards (not merged yet): accept a pair it is part of.
        if known and known[0] in (pa, pb):
            best = p if best is None or p.get("date", "") > best.get("date", "") else best
    if best is not None:
        return best["offset_m"], "pair calibration of %s (other board assumed to be the same one)" % best.get("date", "?")[:10]
    if wrong_setting:
        return None, ("the saved calibration was made with different antenna delay settings in the chips than this "
                      "trial used, so it does not apply; calibrate again with trials like this one")
    return None, "no calibration for these boards on channel %s" % chan


# ---- working a calibration out -------------------------------------------------------
def propose(trials):
    """trials: [(file name, trial dict, analysis dict)]. Returns (proposal, text lines).

    proposal is None when nothing usable was selected. Each trial contributes the mean of
    (measured range - real distance) over its exchanges that were not flagged."""
    lines = []
    groups = {}
    for name, trial, analysis in trials:
        meta = trial.get("meta") or {}
        real = meta.get("distance_m")
        a, b, chan = trial_boards(trial)
        bad = {f["xid"] for f in (analysis or {}).get("flagged", [])}
        r = [e["range_m"] for e in trial["exchanges"]
             if e.get("status") == "ok" and e.get("range_m") is not None and e["xid"] not in bad]
        if real is None or not r:
            lines.append("  skipped %s: %s" % (name, "no real distance in its setup" if real is None else "no usable ranges"))
            continue
        cond = str(meta.get("condition") or "")
        if cond and cond.upper() != "LOS":
            lines.append("  skipped %s: its setup says '%s'. Calibrate only in clean line of sight." % (name, cond))
            continue
        mean = sum(r) / len(r)
        sd = math.sqrt(sum((x - mean) ** 2 for x in r) / (len(r) - 1)) if len(r) > 1 else 0.0
        temps = []
        for dev in ([trial.get("device")] if trial.get("device") else list((trial.get("devices") or {}).values())):
            if dev and dev.get("temp_c") is not None:
                temps.append(dev["temp_c"])
        total = ant_total(trial)
        key = (tuple(sorted([a or "?", b or "?"])), chan, total)
        groups.setdefault(key, []).append({
            "file": name, "trial_id": trial.get("trial_id"), "distance_m": real, "n": len(r), "mean_m": mean,
            "offset_m": mean - real, "sd_m": sd, "height_m": meta.get("antenna_height_m"),
            "temp_c": sum(temps) / len(temps) if temps else None, "a": a, "b": b})

    if not groups:
        lines.append("Nothing to calibrate from. Select line-of-sight trials whose setup has the real distance.")
        return None, lines

    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    pairs = []
    for (ids, chan, total), items in sorted(groups.items(), key=lambda kv: str(kv[0])):
        a, b = items[0]["a"], items[0]["b"]
        lines.append("")
        lines.append("%s  <->  %s,  channel %s%s" % (short(a), short(b), chan,
                     "" if not total else "   (chips were set to antenna delays totalling %d)" % total))
        lines.append("  %-40s %8s %6s %10s %9s %8s" % ("trial", "real m", "n", "measured", "error", "sd"))
        for it in sorted(items, key=lambda t: t["distance_m"]):
            lines.append("  %-40s %8.3f %6d %10.4f %+9.4f %8.4f"
                         % (it["file"][:40], it["distance_m"], it["n"], it["mean_m"], it["offset_m"], it["sd_m"]))
        n = sum(it["n"] for it in items)
        offset = sum(it["offset_m"] * it["n"] for it in items) / n
        if abs(offset) >= 1.0:
            lines.append("  => offset %+.4f m  = %.3f ns of antenna delay in the two boards together, from %d ranges"
                         % (offset, 2.0 * offset / SPEED_OF_LIGHT * 1e9, n))
        else:
            lines.append("  => offset %+.4f m  (measured range is %s by %.1f cm), from %d ranges"
                         % (offset, "too long" if offset > 0 else "too short", abs(offset) * 100.0, n))

        # ---- sanity checks, in plain words
        if n < 200:
            lines.append("  NOTE: only %d ranges. The Qorvo note uses 200 to 1000 per measurement; more is steadier." % n)
        by_d = {}
        for it in items:
            by_d.setdefault(round(it["distance_m"], 3), []).append(it["offset_m"])
        if len(by_d) > 1:
            per = {d: sum(v) / len(v) for d, v in by_d.items()}
            spread = max(per.values()) - min(per.values())
            if spread > 0.03:
                lines.append("  WARNING: the error changes by %.1f cm between distances (%s)."
                             % (spread * 100.0, ", ".join("%.2f m: %+.1f cm" % (d, per[d] * 100.0) for d in sorted(per))))
                lines.append("           A pure antenna delay is the same at every distance, so something else is in"
                             " there:")
                lines.append("           a reflection merging with the direct path, a mis-measured distance, or a"
                             " signal-level effect.")
            else:
                lines.append("  Good: the error is the same within %.1f cm at %d distances, as a pure delay should be."
                             % (spread * 100.0, len(by_d)))
        else:
            lines.append("  Tip: repeat at one or two more distances (e.g. 1, 2 and 4 m). If the error stays the same,"
                         " it really is antenna delay.")
        for it in items:
            ns = floor_bounce_ns(it["distance_m"], it["height_m"])
            if ns is not None and ns < 2.0:
                lines.append("  WARNING: %s: at %.2f m with antennas %.2f m high the floor reflection arrives only %.1f ns"
                             % (it["file"][:30], it["distance_m"], it["height_m"], ns))
                lines.append("           after the direct path and merges with it. Raise the antennas or shorten the"
                             " distance for calibration.")
        if any(it["sd_m"] > 0.05 for it in items):
            lines.append("  WARNING: a trial has more than 5 cm spread between ranges: not a clean, steady link.")
        expect = expected_offset_m(total)
        if abs(offset - expect) > 1.5:
            lines.append("  WARNING: about %+.1f m was expected for these boards with these chip settings, not %+.1f m."
                         % (expect, offset))
            lines.append("           Check the real distance in the setup, and that both PCs run the same version of"
                         " this software.")
        elif not total:
            lines.append("  As expected: with the chips applying no antenna delay, the whole delay of both boards"
                         " (about 154 m) lands here.")
        each = dtu_from_m(offset) / 2.0
        now_each = (total or 0) / 4.0
        lines.append("  For reference, the same thing written into the chips: TX and RX antenna delay %d -> %d on both"
                     " boards." % (round(now_each), round(now_each + each)))
        if not a or not b:
            lines.append("  NOTE: these files are not merged, so only one of the two boards is known. Import the other"
                         " PC's files first to tie the calibration to both boards.")
        temps = [it["temp_c"] for it in items if it["temp_c"] is not None]
        pairs.append({"a": a, "b": b, "chan": chan, "ant_dly_total": total, "offset_m": offset, "n": n, "date": now,
                      "temp_c": (sum(temps) / len(temps)) if temps else None,
                      "distances_m": sorted(by_d), "trials": [it["trial_id"] for it in items]})
    return {"pairs": pairs}, lines


def solve_boards(pairs, chan):
    """Per-board delays (in metres of range) from pair offsets: offset_ab = (delay_a + delay_b) / 2.
    Possible when at least three boards were ranged so that they form a triangle. Returns {} if not."""
    use = [p for p in pairs if p.get("chan") == chan and p.get("a") and p.get("b") and p["a"] != p["b"]]
    totals = {p.get("ant_dly_total", 4 * DEFAULT_ANT_DLY) for p in use}
    if len(totals) != 1:
        return {}  # pairs measured with different chip settings cannot be combined
    per_board = totals.pop() / 2.0
    ids = sorted({p["a"] for p in use} | {p["b"] for p in use})
    if len(ids) < 3 or len(use) < len(ids):
        return {}
    try:
        import numpy as np
    except ImportError:
        return {}
    A = np.zeros((len(use), len(ids)))
    y = np.zeros(len(use))
    w = np.zeros(len(use))
    for k, p in enumerate(use):
        A[k, ids.index(p["a"])] = 0.5
        A[k, ids.index(p["b"])] = 0.5
        y[k] = p["offset_m"]
        w[k] = math.sqrt(max(1, p.get("n", 1)))
    if np.linalg.matrix_rank(A) < len(ids):
        return {}  # e.g. four boards in a square: every board in two pairs, still not solvable
    sol = np.linalg.lstsq(A * w[:, None], y * w, rcond=None)[0]
    return {bid: {"delay_m": float(v), "ant_dly": per_board} for bid, v in zip(ids, sol)}


def apply(folder, proposal):
    """Store a proposal: newer pair entries replace older ones for the same boards and channel."""
    cal = load(folder)
    for p in proposal["pairs"]:
        key = (frozenset([p["a"] or "?", p["b"] or "?"]), p["chan"], p.get("ant_dly_total"))
        cal["pairs"] = [q for q in cal["pairs"] if (frozenset([q.get("a") or "?", q.get("b") or "?"]), q.get("chan"),
                                                    q.get("ant_dly_total", 4 * DEFAULT_ANT_DLY)) != key]
        cal["pairs"].append(p)
    cal["boards"] = {}
    for chan in sorted({p["chan"] for p in cal["pairs"]}, key=str):
        solved = solve_boards(cal["pairs"], chan)
        if solved:
            cal["boards"][str(chan)] = solved
    return save(folder, cal), cal


def describe(cal):
    """Plain-text listing of what is stored."""
    if not cal or not cal.get("pairs"):
        return ["No calibration saved in this folder yet: ranges are shown as measured."]
    lines = ["Saved calibration (calibrated range = measured range - offset):"]
    for p in sorted(cal["pairs"], key=lambda q: (str(q.get("chan")), q.get("date", ""))):
        temp = (", chips at %.0f C" % p["temp_c"]) if p.get("temp_c") is not None else ""
        tot = p.get("ant_dly_total", 4 * DEFAULT_ANT_DLY)
        lines.append("  channel %s  %s <-> %s   offset %+.4f m   (%d ranges at %s m, %s%s; for trials with %s)"
                     % (p.get("chan"), short(p.get("a")), short(p.get("b")), p["offset_m"], p.get("n", 0),
                        "/".join("%g" % d for d in p.get("distances_m", [])), p.get("date", "")[:10], temp,
                        "no antenna delay in the chips" if not tot else "chip antenna delays totalling %d" % tot))
    for chan, boards in (cal.get("boards") or {}).items():
        lines.append("  channel %s, solved per board (three or more boards were ranged against each other):" % chan)
        for bid, v in sorted(boards.items()):
            each = dtu_from_m(v["delay_m"]) / 2.0
            base = (v.get("ant_dly") or 0) / 2.0
            lines.append("     %s: %+.4f m   (as antenna delay: %d -> %d for TX and RX)"
                         % (short(bid), v["delay_m"], round(base), round(base + each)))
    return lines
