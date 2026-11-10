#!/usr/bin/env python3
"""
uwb_analyze.py - merge, check and compare the trial files written by uwb_tool.py.

    python uwb_analyze.py merge   init.json resp.json     one file with poll + response + final per exchange
    python uwb_analyze.py merge-all data/                 pair up every initiator/responder file in a folder
    python uwb_analyze.py report  data/x_merged.json      readable analysis; also writes x_merged_report.html
    python uwb_analyze.py compare data/                   the trials of each setup side by side
    python uwb_analyze.py summary data/                   one line per setup and placement
    python uwb_analyze.py cirs    data/x_merged.json      PDF with every individual CIR (needs matplotlib)
    python uwb_analyze.py dataset data/ -o set.npz        array file for machine learning + labels .csv
    python uwb_analyze.py calibrate data/los_merged.json --save   antenna delay calibration (see uwb_calib.py)
    python uwb_analyze.py csv     data/x_merged.json      one row per exchange, for a spreadsheet
    python uwb_analyze.py plot    data/x_merged.json      overview picture (needs matplotlib)

In your own scripts:

    import uwb_analyze as ua
    trial = ua.load_trial("data/x_merged.json")
    xids, cir, fp = ua.stack_cir(trial, "poll")      # cir: complex array (exchanges x samples)
    ranges = ua.ranges(trial)                         # metres, one per completed exchange

Requires numpy.
"""

import argparse
import csv
import glob
import json
import math
import os
import re
import sys

import numpy as np

import uwb_calib as uc
import uwb_setups as us

KINDS = ("poll", "response", "final")
Z_LIMIT = 3.5           # robust z-score beyond which a value counts as abnormal
MIN_FOR_RELATIVE = 15   # relative ("unlike the rest") checks need at least this many exchanges
NLOS_GAP_SAMPLES = 6.0  # first path to peak distance treated as "likely NLOS" (Qorvo APS006 part 3)


# --------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------
def load_trial(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_trial(trial, path):
    from uwb_tool import write_trial_json
    write_trial_json(trial, path)


def ok_exchanges(trial):
    return [e for e in trial["exchanges"] if e.get("status") == "ok"]


def ranges(trial):
    """(xids, ranges in metres) of the completed exchanges that have a range."""
    ex = [e for e in ok_exchanges(trial) if e.get("range_m") is not None]
    return np.array([e["xid"] for e in ex]), np.array([e["range_m"] for e in ex], dtype=float)


def stack_cir(trial, kind):
    """All CIRs of one message type as a complex array.

    Returns (xids, cir, fp_index): cir has shape (n_exchanges, n_samples); fp_index is the
    chip's first-path index relative to the first captured sample (so it indexes cir directly).
    """
    ex = [e for e in ok_exchanges(trial) if kind in e]
    if not ex:
        return np.array([], dtype=int), np.zeros((0, 0), dtype=complex), np.array([])
    length = min(len(e[kind]["cir"]["i"]) for e in ex)
    cir = np.array([np.array(e[kind]["cir"]["i"][:length]) + 1j * np.array(e[kind]["cir"]["q"][:length]) for e in ex])
    fp = np.array([e[kind]["diag"]["fp_index"] - e[kind]["cir_start"] for e in ex])
    return np.array([e["xid"] for e in ex]), cir, fp


# --------------------------------------------------------------------------------------
# Statistics helpers
# --------------------------------------------------------------------------------------
def robust_z(x, floor=0.0):
    """(x - median) / (1.4826 * MAD): like a z-score, but a few bad values cannot hide themselves
    by inflating the spread, which is what happens with mean and standard deviation."""
    x = np.asarray(x, dtype=float)
    if not np.isfinite(x).any():
        return np.full(x.shape, np.nan), float("nan")
    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med))
    scale = max(1.4826 * mad, floor, 1e-12)
    return (x - med) / scale, med


def describe(values, real=None):
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    n = int(v.size)
    if n == 0:
        return None
    out = {"n": n, "mean_m": float(v.mean()), "median_m": float(np.median(v)), "min_m": float(v.min()),
           "max_m": float(v.max()), "std_m": None, "sem_m": None, "ci95_m": None}
    if n > 1:
        sd = float(v.std(ddof=1))
        out["std_m"] = sd
        out["sem_m"] = sd / math.sqrt(n)             # standard error of the mean
        out["ci95_m"] = 1.96 * out["sem_m"]          # mean +/- this covers the true mean 95 % of the time
    if real is not None:
        out["bias_m"] = out["mean_m"] - real
    return out


# --------------------------------------------------------------------------------------
# Per-trial analysis
# --------------------------------------------------------------------------------------
def _kind_metrics(trial, kind):
    """Per-exchange numbers describing one message's CIR and diagnostics."""
    xids, cir, fp = stack_cir(trial, kind)
    if cir.shape[0] == 0:
        return None
    ex = {e["xid"]: e for e in ok_exchanges(trial) if kind in e}
    diag = [ex[x][kind]["diag"] for x in xids]
    mag = np.abs(cir)
    n, length = mag.shape

    gap = np.array([d["peak_index"] - d["fp_index"] for d in diag], dtype=float)
    status = np.array([d["status"] for d in diag], dtype=int)
    fp_amp = np.array([max(d["f1"], d["f2"], d["f3"]) for d in diag], dtype=float)
    peak_amp = np.array([d["peak_amp"] for d in diag], dtype=float)
    power_diff = np.array([
        (d["rx_power_dbm"] - d["fp_power_dbm"]) if d.get("rx_power_dbm") is not None and d.get("fp_power_dbm") is not None
        else np.nan for d in diag])

    noise = np.full(n, np.nan)
    early = np.full(n, np.nan)
    corr = np.full(n, np.nan)
    lo, hi = 8, 40
    windows = np.full((n, lo + hi), np.nan)
    for k in range(n):
        f = int(round(fp[k]))
        if f - 30 >= 40:  # enough samples before the first path to measure the noise
            noise[k] = math.sqrt(float(np.mean(mag[k, : f - 30] ** 2)))
            if f - 16 >= 0 and noise[k] > 0:
                early[k] = float(mag[k, f - 16 : f - 3].max()) / noise[k]
        if f - lo >= 0 and f + hi <= length:
            w = mag[k, f - lo : f + hi]
            norm = np.linalg.norm(w)
            if norm > 0:
                windows[k] = w / norm
    good = np.isfinite(windows).all(axis=1)
    if good.sum() >= 3:
        template = np.median(windows[good], axis=0)
        template /= np.linalg.norm(template)
        for k in np.flatnonzero(good):
            # The first-path index is fractional but the window starts on a whole sample:
            # take the best of three one-sample shifts so alignment alone cannot lower the score.
            f = int(round(fp[k]))
            best = 0.0
            for shift in (-1, 0, 1):
                a, b = f - lo + shift, f + hi + shift
                if a >= 0 and b <= length:
                    w = mag[k, a:b]
                    norm = np.linalg.norm(w)
                    if norm > 0:
                        best = max(best, float(w @ template) / norm)
            corr[k] = best

    return {"xids": xids, "gap": gap, "status": status, "fp_amp": fp_amp, "peak_amp": peak_amp,
            "power_diff": power_diff, "noise": noise, "early": early, "corr": corr}


def analyze_trial(trial):
    """Statistics for a trial plus a list of exchanges that look abnormal, each with reasons.

    An exchange is flagged when
      - its range is far from the trial median (robust z-score),
      - the chip itself raised a first-path warning flag for one of its frames,
      - the first path is far ahead of the strongest path (likely NLOS),
      - or one of its CIRs is unlike the rest of the trial: unusual first-path-to-peak
        distance, unusual energy just before the reported first path, or an unusual shape.
    "Unlike the rest" always means compared with the other exchanges of the same trial,
    so the check adapts to the environment instead of relying on fixed thresholds.
    """
    real = trial.get("meta", {}).get("distance_m")
    xr, r = ranges(trial)
    reasons = {}

    def flag(xid, text):
        reasons.setdefault(int(xid), []).append(text)

    if r.size >= 8:
        z, med = robust_z(r, floor=0.005)
        for xid, value, zz in zip(xr, r, z):
            if abs(zz) > Z_LIMIT:
                flag(xid, "range %.3f m is %+.3f m from the trial median" % (value, value - med))

    per_kind = {}
    for kind in KINDS:
        m = _kind_metrics(trial, kind)
        if m is None:
            continue
        xids = m["xids"]
        for xid, st in zip(xids, m["status"]):
            if st & 0x1F:
                flag(xid, "%s: chip first-path warning 0x%02X" % (kind, st))
        for xid, g in zip(xids, m["gap"]):
            if g > NLOS_GAP_SAMPLES:
                flag(xid, "%s: first path %.1f samples before the peak (likely NLOS)" % (kind, g))
        if len(xids) >= MIN_FOR_RELATIVE:
            zg, medg = robust_z(m["gap"], floor=0.5)
            for xid, g, zz in zip(xids, m["gap"], zg):
                if abs(zz) > Z_LIMIT and g <= NLOS_GAP_SAMPLES:
                    flag(xid, "%s: first-path-to-peak distance %.1f samples (trial median %.1f)" % (kind, g, medg))
            ze, mede = robust_z(m["early"], floor=0.3)
            for xid, e, zz in zip(xids, m["early"], ze):
                if np.isfinite(e) and zz > Z_LIMIT and e > 3.5:
                    flag(xid, "%s: energy before the reported first path (%.1f x noise, trial median %.1f)"
                         % (kind, e, mede))
            zc, medc = robust_z(1.0 - m["corr"], floor=0.01)
            for xid, c, zz in zip(xids, m["corr"], zc):
                if np.isfinite(c) and zz > Z_LIMIT and c < 0.90:
                    flag(xid, "%s: CIR shape unlike the rest of the trial (similarity %.2f)" % (kind, c))
            zp, medp = robust_z(m["power_diff"], floor=1.0)
            for xid, p, zz in zip(xids, m["power_diff"], zp):
                if np.isfinite(p) and zz > Z_LIMIT:
                    flag(xid, "%s: first path %.1f dB below total power (trial median %.1f dB)" % (kind, p, medp))
        per_kind[kind] = {
            "n": int(len(xids)),
            "fp_to_peak_samples_median": float(np.nanmedian(m["gap"])),
            "chip_warnings": int(np.count_nonzero(m["status"] & 0x1F)),
            "noise_rms_median": None if not np.isfinite(m["noise"]).any() else float(np.nanmedian(m["noise"])),
            "shape_similarity_median": None if not np.isfinite(m["corr"]).any() else float(np.nanmedian(m["corr"])),
        }

    flagged = [{"xid": xid, "reasons": reasons[xid]} for xid in sorted(reasons)]
    flagged_ids = set(reasons)
    clean = np.array([value for xid, value in zip(xr, r) if int(xid) not in flagged_ids])
    return {
        "n": len(ok_exchanges(trial)),
        "n_failed": len(trial["exchanges"]) - len(ok_exchanges(trial)),
        "range": describe(r, real),
        "range_without_flagged": describe(clean, real),
        "per_message": per_kind,
        "flagged": flagged,
    }


# --------------------------------------------------------------------------------------
# Merging the two sides of a trial
# --------------------------------------------------------------------------------------
def merge_trials(init, resp):
    """Join an initiator file and a responder file of the same trial by exchange number."""
    if init["trial_id"] != resp["trial_id"]:
        raise ValueError("different trials: %s vs %s" % (init["trial_id"], resp["trial_id"]))
    by_xid_init = {e["xid"]: e for e in init["exchanges"]}
    exchanges = []
    for e in resp["exchanges"]:
        m = dict(e)
        i = by_xid_init.pop(e["xid"], None)
        if i is None:
            m["initiator_status"] = "missing"
        else:
            m["initiator_status"] = i["status"]
            if "response" in i:
                m["response"] = i["response"]
            if "timestamps" in i:
                m["initiator_timestamps"] = i["timestamps"]
            m["initiator_proc_us"] = i.get("proc_us")
        m["responder_proc_us"] = m.pop("proc_us", None)
        exchanges.append(m)
    for xid in sorted(by_xid_init):  # the responder never reported these (poll not heard, or still busy)
        i = dict(by_xid_init[xid])
        i["initiator_status"] = i["status"]
        i["status"] = "no_responder_record"
        exchanges.append(i)
    exchanges.sort(key=lambda e: e["xid"])

    # The responder's PC is the main one and holds the setup; the initiator's notes only fill gaps.
    meta = dict(init.get("meta") or {})
    meta.update({k: v for k, v in (resp.get("meta") or {}).items() if v not in (None, "")})
    merged = {
        "format": "uwb-cir-trial",
        "version": 1,
        "trial_id": init["trial_id"],
        "role": "merged",
        "started": min(init["started"], resp["started"]),
        "ended": max(init.get("ended") or "", resp.get("ended") or ""),
        "meta": meta,
        "meta_initiator": init.get("meta"),
        "meta_responder": resp.get("meta"),
        "params": init.get("params") or resp.get("params"),
        "ant_dly": {"initiator": uc.own_ant_dly(init), "responder": uc.own_ant_dly(resp)},
        "devices": {"initiator": init.get("device"), "responder": resp.get("device")},
        "end": {"initiator": init.get("end"), "responder": resp.get("end")},
        "link": {"initiator": init.get("link"), "responder": resp.get("link")},
        "exchanges": exchanges,
    }
    di = (init.get("meta") or {}).get("distance_m")
    dr = (resp.get("meta") or {}).get("distance_m")
    if di is not None and dr is not None and abs(di - dr) > 1e-6:
        merged["meta"]["warning"] = "the two sides recorded different real distances (%.3f vs %.3f m)" % (di, dr)
    r = ranges(merged)[1]
    merged["summary"] = describe(r, merged["meta"].get("distance_m"))
    merged["analysis"] = analyze_trial(merged)
    return merged


_HEAD_ID = re.compile(r'"trial_id":\s*"([0-9A-Fa-f]{8})"')
_HEAD_ROLE = re.compile(r'"role":\s*"(\w+)"')


def peek(path):
    """(trial_id, role) from the first lines of a trial file, without loading the CIR data."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = f.read(4096)
    except OSError:
        return None, None
    if '"uwb-cir-trial"' not in head:
        return None, None
    a, b = _HEAD_ID.search(head), _HEAD_ROLE.search(head)
    return (a.group(1).upper() if a else None), (b.group(1) if b else None)


def merged_name(path):
    stem = re.sub(r"_(initiator|responder)$", "", os.path.splitext(path)[0])
    return stem + "_merged.json"


def merge_with_counterpart(path):
    """If the other side's file of the same trial is in the same folder, write the merged file."""
    trial_id, role = peek(path)
    if not trial_id or role not in ("initiator", "responder"):
        return None
    other_role = "responder" if role == "initiator" else "initiator"
    for other in glob.glob(os.path.join(os.path.dirname(os.path.abspath(path)), "*.json")):
        if os.path.abspath(other) == os.path.abspath(path):
            continue
        if peek(other) == (trial_id, other_role):
            a, b = load_trial(path), load_trial(other)
            init, resp = (a, b) if role == "initiator" else (b, a)
            out = merged_name(path if role == "responder" else other)
            write_trial(merge_trials(init, resp), out)
            return out
    return None


def merge_all(folder):
    files = {}
    for p in sorted(glob.glob(os.path.join(folder, "*.json"))):
        trial_id, role = peek(p)
        if trial_id:
            files.setdefault(trial_id, {})[role] = p
    done = []
    for trial_id, roles in files.items():
        if "initiator" in roles and "responder" in roles and "merged" not in roles:
            out = merged_name(roles["responder"])
            write_trial(merge_trials(load_trial(roles["initiator"]), load_trial(roles["responder"])), out)
            done.append(out)
        elif "merged" not in roles and ("initiator" in roles) != ("responder" in roles):
            print("  no counterpart yet for trial %s (%s)" % (trial_id, list(roles.values())[0]))
    return done


# --------------------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------------------
def fmt(v, digits=3):
    return "-" if v is None else ("%." + str(digits) + "f") % v


def cal_offset(path, trial):
    """Antenna delay correction for this trial from calibration.json next to the file, or None."""
    cal = uc.load_cached(os.path.dirname(os.path.abspath(path)))
    return uc.offset_for(cal, trial)[0] if cal else None


SAMPLE_NS = 1e9 / (2.0 * 499.2e6)   # spacing of the accumulator samples: 1.0016 ns
CM_PER_NS = 29.9702547              # distance light covers in 1 ns


def report_data(path):
    """Everything the readable report needs, as plain numbers (used for both the text and the HTML file)."""
    trial = load_trial(path)
    a = analyze_trial(trial)
    meta = trial.get("meta") or {}
    real = meta.get("distance_m")
    cal = uc.load_cached(os.path.dirname(os.path.abspath(path)))
    off, how = uc.offset_for(cal, trial)
    why = {f["xid"]: f["reasons"] for f in a["flagged"]}

    rows = []
    for e in trial["exchanges"]:
        row = {"xid": e["xid"], "status": e.get("status"), "range_m": e.get("range_m"), "diff_m": None,
               "cal_diff_m": None, "flagged": e["xid"] in why, "reasons": why.get(e["xid"], []), "msg": {}}
        if e.get("status") == "ok" and e.get("range_m") is not None and real is not None:
            row["diff_m"] = e["range_m"] - real
            if off is not None:
                row["cal_diff_m"] = e["range_m"] - off - real
        for kind in KINDS:
            if kind in e:
                d = e[kind]["diag"]
                gap = d["peak_index"] - d["fp_index"]
                row["msg"][kind] = {"fp": d["fp_index"], "peak": d["peak_index"], "gap": gap, "gap_ns": gap * SAMPLE_NS}
        rows.append(row)

    gaps = {}
    for kind in KINDS:
        v = [(r["msg"][kind]["fp"], r["msg"][kind]["peak"], r["msg"][kind]["gap"]) for r in rows
             if kind in r["msg"] and r["status"] == "ok"]
        if v:
            g = np.array([x[2] for x in v])
            gaps[kind] = {"n": len(v), "fp": float(np.median([x[0] for x in v])), "peak": float(np.median([x[1] for x in v])),
                          "gap": float(np.median(g)), "gap_min": float(g.min()), "gap_max": float(g.max())}

    s_all, s_clean = a["range"], a["range_without_flagged"]
    return {"path": path, "trial": trial, "analysis": a, "meta": meta, "real": real, "off": off, "cal_how": how,
            "rows": rows, "gaps": gaps, "all": s_all, "clean": s_clean}


def _cm(v):
    return "%+.1f cm" % (v * 100.0)


def report(path):
    """Print the readable analysis of one trial. Returns the analysis dict."""
    d = report_data(path)
    trial, a, meta, real, off = d["trial"], d["analysis"], d["meta"], d["real"], d["off"]
    line = "=" * 78
    print(line)
    print("%s      trial %s (%s file)" % (os.path.basename(path), trial.get("trial_id"), trial.get("role")))
    print("%s%s" % (us.setup_title(meta), (", placement %s" % meta["placement"]) if meta.get("placement") is not None else ""))
    print("started %s      exchanges: %d completed, %d failed, %d flagged as abnormal"
          % (trial.get("started"), a["n"], a["n_failed"], len(a["flagged"])))

    print("")
    print("RANGE: reported vs actual")
    s = d["all"]
    if not s:
        print("   no completed exchange has a range%s" % (" (ranges are computed on the responder side)"
                                                         if trial.get("role") == "initiator" else ""))
    else:
        print("   actual distance (from the setup)   %s" % (("%.3f m" % real) if real is not None else "not given"))
        print("   mean reported range                %.3f m      %s"
              % (s["mean_m"], ("difference %+.3f m  (%s)" % (s["bias_m"], _cm(s["bias_m"]))) if "bias_m" in s else ""))
        if off is not None:
            print("   after calibration                  %.3f m      %s      [%.3f m antenna delay removed]"
                  % (s["mean_m"] - off, ("difference %+.3f m  (%s)" % (s["bias_m"] - off, _cm(s["bias_m"] - off)))
                     if "bias_m" in s else "", off))
        else:
            print("   after calibration                  -            (%s)" % d["cal_how"])
        c = d["clean"]
        if c and len(a["flagged"]):
            print("   mean without the flagged ones      %.3f m      %s"
                  % (c["mean_m"], ("difference %+.3f m  (%s)" % (c["bias_m"], _cm(c["bias_m"]))) if "bias_m" in c else ""))
        print("   spread of single ranges (sd)       %s m        smallest %.3f m, largest %.3f m"
              % (fmt(s["std_m"]), s["min_m"], s["max_m"]))
        print("   how well the mean is known         +/- %s m   (95 %% confidence, from %d ranges)" % (fmt(s["ci95_m"]), s["n"]))

    if d["gaps"]:
        print("")
        print("FIRST PATH vs PEAK   (medians over the trial; 1 sample = %.4f ns = %.1f cm of path)" % (SAMPLE_NS, SAMPLE_NS * CM_PER_NS))
        print("   %-10s %11s %11s %16s %12s %24s" % ("message", "first path", "peak", "peak - first", "in time", "smallest .. largest"))
        for kind in KINDS:
            g = d["gaps"].get(kind)
            if g:
                print("   %-10s %11.2f %11.0f %8.2f samples %9.2f ns %12.2f .. %.2f samples"
                      % (kind, g["fp"], g["peak"], g["gap"], g["gap"] * SAMPLE_NS, g["gap_min"], g["gap_max"]))
        print("   (first path = where the chip says the signal first arrived; peak = strongest sample.")
        print("    1 to 3 samples apart is a clean direct path; more than %g suggests the direct path is blocked.)" % NLOS_GAP_SAMPLES)

    ranged = [r for r in d["rows"] if r["diff_m"] is not None]
    if ranged:
        print("")
        worst = sorted(ranged, key=lambda r: -abs(r["diff_m"]))[:5]
        print("EXCHANGES furthest from the actual distance   (every exchange is in the report file)")
        print("   %-6s %10s %12s %14s  %s" % ("number", "reported", "difference", "peak - first", ""))
        for r in worst:
            g = r["msg"].get("poll") or next(iter(r["msg"].values()), None)
            print("   %-6d %8.3f m %12s %9s      %s"
                  % (r["xid"], r["range_m"], _cm(r["diff_m"]), ("%.1f smp" % g["gap"]) if g else "-",
                     ("FLAGGED: " + r["reasons"][0]) if r["flagged"] else ""))

    print("")
    if a["flagged"]:
        print("FLAGGED %d exchange%s as abnormal:" % (len(a["flagged"]), "" if len(a["flagged"]) == 1 else "s"))
        for item in a["flagged"]:
            print("   %-5d %s" % (item["xid"], "; ".join(item["reasons"])))
    else:
        print("No exchanges flagged as abnormal.")
    return a


_CSS = """
body{font-family:Segoe UI,Helvetica,Arial,sans-serif;color:#1c2330;margin:28px auto;max-width:1500px;padding:0 18px;line-height:1.45}
h1{font-size:22px;margin:0 0 2px} h2{font-size:17px;margin:30px 0 8px;border-bottom:2px solid #d9dee7;padding-bottom:4px}
.sub{color:#5b6577;font-size:13px} .cards{display:flex;flex-wrap:wrap;gap:12px;margin:14px 0}
.card{border:1px solid #d9dee7;border-radius:8px;padding:10px 16px;min-width:150px;background:#fafbfd}
.card .k{font-size:12px;color:#5b6577;text-transform:uppercase;letter-spacing:.04em} .card .v{font-size:24px;font-weight:600}
.card .n{font-size:12px;color:#5b6577} .pos{color:#b3261e} .neg{color:#1b5fa8} .zero{color:#1e7b3c}
table{border-collapse:collapse;font-size:13px;margin:6px 0} th,td{padding:4px 9px;text-align:right;border-bottom:1px solid #e6e9ef;white-space:nowrap}
td.w{white-space:normal;min-width:300px;text-align:left} .scroll{overflow-x:auto}
th{background:#f1f3f7;position:sticky;top:0} td.l,th.l{text-align:left} tr.flag td{background:#fdeeee} tr.fail td{color:#8a93a3}
th.g{border-left:2px solid #c9cfda} td.g{border-left:2px solid #e1e5ec}
.bar{display:inline-block;height:9px;vertical-align:middle;border-radius:2px} img{max-width:100%;border:1px solid #e6e9ef;border-radius:6px}
.note{font-size:13px;color:#3d4656;background:#f6f8fb;border-left:4px solid #9fb3d1;padding:8px 12px;margin:10px 0}
@media print{th{position:static} h2{page-break-after:avoid} tr{page-break-inside:avoid}}
"""


def _png(fig):
    import base64
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _report_charts(d):
    """[(caption, data-uri)] or [] when matplotlib is not installed."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    out = []
    rows = [r for r in d["rows"] if r["status"] == "ok" and r["range_m"] is not None]
    if rows:
        x = np.array([r["xid"] for r in rows])
        y = np.array([r["range_m"] for r in rows])
        fl = np.array([r["flagged"] for r in rows])
        fig, ax = plt.subplots(1, 2, figsize=(12.5, 3.9), gridspec_kw={"width_ratios": [2.2, 1]})
        ax[0].plot(x[~fl], y[~fl], "o", ms=3.5, color="#1b5fa8", label="reported range")
        if fl.any():
            ax[0].plot(x[fl], y[fl], "x", ms=7, color="#b3261e", label="flagged as abnormal")
        if d["real"] is not None:
            ax[0].axhline(d["real"], color="#1e7b3c", lw=1.6, label="actual %.3f m" % d["real"])
        ax[0].axhline(y.mean(), color="#e08a00", lw=1.3, ls="--", label="mean reported %.3f m" % y.mean())
        ax[0].set(xlabel="exchange number", ylabel="range (m)", title="Reported range of every exchange")
        ax[0].legend(fontsize=8)
        ax[0].grid(alpha=0.25)
        if d["real"] is not None:
            ax[1].hist((y - d["real"]) * 100.0, bins=min(30, max(6, len(y) // 4)), color="#7aa6d6", edgecolor="white")
            ax[1].axvline(0, color="#1e7b3c", lw=1.6)
            ax[1].axvline((y.mean() - d["real"]) * 100.0, color="#e08a00", lw=1.3, ls="--")
            ax[1].set(xlabel="reported - actual (cm)", ylabel="exchanges", title="How far off, and how often")
            ax[1].grid(alpha=0.25)
        else:
            ax[1].axis("off")
        fig.tight_layout()
        out.append(("Green line: actual distance. Dashed orange: mean of the reported ranges.", _png(fig)))
        plt.close(fig)
    if d["gaps"]:
        fig, ax = plt.subplots(figsize=(12.5, 3.2))
        colors = {"poll": "#1b5fa8", "response": "#8a4fbf", "final": "#e08a00"}
        for kind in KINDS:
            pts = [(r["xid"], r["msg"][kind]["gap"]) for r in d["rows"] if kind in r["msg"] and r["status"] == "ok"]
            if pts:
                ax.plot([p[0] for p in pts], [p[1] for p in pts], ".", ms=5, color=colors[kind], label=kind)
        ax.axhline(NLOS_GAP_SAMPLES, color="#b3261e", lw=1, ls=":", label="above this: direct path likely blocked")
        ax.set(xlabel="exchange number", ylabel="peak - first path (samples)",
               title="Distance between the first path and the peak, every exchange")
        sec = ax.secondary_yaxis("right", functions=(lambda v: v * SAMPLE_NS, lambda v: v / SAMPLE_NS))
        sec.set_ylabel("ns")
        ax.legend(fontsize=8, ncol=4)
        ax.grid(alpha=0.25)
        fig.tight_layout()
        out.append(("One dot per received message. Left axis in samples, right axis in nanoseconds.", _png(fig)))
        plt.close(fig)
    return out


def write_report(path, out=None):
    """The same analysis as report(), as one self-contained HTML file that can be e-mailed
    and opens in any browser (print it from there to get a PDF)."""
    import html

    d = report_data(path)
    trial, a, meta, real, off = d["trial"], d["analysis"], d["meta"], d["real"], d["off"]
    esc = html.escape
    out = out or os.path.splitext(path)[0] + "_report.html"

    def cls(v):
        return "zero" if abs(v) < 0.005 else ("pos" if v > 0 else "neg")

    def diff_html(v):
        return '<span class="%s">%+.3f m (%s)</span>' % (cls(v), v, _cm(v))

    h = ['<!DOCTYPE html><html><head><meta charset="utf-8"><title>%s</title><style>%s</style></head><body>'
         % (esc(os.path.basename(path)), _CSS)]
    h.append("<h1>UWB ranging trial report</h1>")
    h.append('<div class="sub">%s &nbsp;|&nbsp; trial %s &nbsp;|&nbsp; started %s</div>'
             % (esc(os.path.basename(path)), esc(str(trial.get("trial_id"))), esc(str(trial.get("started")))))
    h.append('<div class="sub">%s%s</div>' % (esc(us.setup_title(meta)),
                                               (", placement %s" % meta["placement"]) if meta.get("placement") is not None else ""))
    extra = [("Notes", meta.get("notes")), ("Setup notes", meta.get("setup_notes")), ("Antenna height",
             ("%g m" % meta["antenna_height_m"]) if meta.get("antenna_height_m") is not None else None)]
    chan = ((trial.get("params") or {}).get("radio") or {}).get("chan")
    if chan is not None:
        extra.append(("Channel", chan))
    bits = ["%s: %s" % (k, esc(str(v))) for k, v in extra if v not in (None, "")]
    if bits:
        h.append('<div class="sub">%s</div>' % " &nbsp;|&nbsp; ".join(bits))

    # ---- range
    h.append("<h2>Reported range vs actual distance</h2>")
    s = d["all"]
    if not s:
        h.append('<div class="note">No completed exchange in this file has a range. Ranges are computed on the '
                 "responder side: use the responder or merged file.</div>")
    else:
        h.append('<div class="cards">')
        h.append('<div class="card"><div class="k">Actual distance</div><div class="v">%s</div><div class="n">from the setup</div></div>'
                 % (("%.3f m" % real) if real is not None else "not given"))
        h.append('<div class="card"><div class="k">Mean reported</div><div class="v">%.3f m</div><div class="n">%d exchanges</div></div>'
                 % (s["mean_m"], s["n"]))
        if "bias_m" in s:
            h.append('<div class="card"><div class="k">Difference</div><div class="v %s">%+.3f m</div><div class="n">%s &nbsp; reported minus actual</div></div>'
                     % (cls(s["bias_m"]), s["bias_m"], _cm(s["bias_m"])))
            if off is not None:
                v = s["bias_m"] - off
                h.append('<div class="card"><div class="k">Difference, calibrated</div><div class="v %s">%+.3f m</div><div class="n">%s &nbsp; after removing %+.3f m antenna delay</div></div>'
                         % (cls(v), v, _cm(v), off))
        h.append('<div class="card"><div class="k">Spread (sd)</div><div class="v">%s m</div><div class="n">smallest %.3f, largest %.3f</div></div>'
                 % (fmt(s["std_m"]), s["min_m"], s["max_m"]))
        h.append('<div class="card"><div class="k">Mean known to</div><div class="v">&plusmn; %s m</div><div class="n">95 %% confidence</div></div>'
                 % fmt(s["ci95_m"]))
        h.append('<div class="card"><div class="k">Exchanges</div><div class="v">%d ok</div><div class="n">%d failed, %d flagged as abnormal</div></div>'
                 % (a["n"], a["n_failed"], len(a["flagged"])))
        h.append("</div>")
        c = d["clean"]
        if c and a["flagged"] and "bias_m" in c:
            h.append('<div class="note">Leaving out the %d flagged exchanges: mean %.3f m, difference %+.3f m (%s), sd %s m.</div>'
                     % (len(a["flagged"]), c["mean_m"], c["bias_m"], _cm(c["bias_m"]), fmt(c["std_m"])))
        if off is None:
            h.append('<div class="note">Not calibrated: %s. The difference above still contains the boards\' antenna delay.</div>'
                     % esc(d["cal_how"]))
    charts = _report_charts(d)
    if charts:
        h.append('<img src="%s" alt="range per exchange"><div class="sub">%s</div>' % (charts[0][1], esc(charts[0][0])))

    # ---- first path vs peak
    if d["gaps"]:
        h.append("<h2>First path vs peak</h2>")
        h.append('<div class="sub">First path: where the chip says the signal first arrived. Peak: the strongest sample. '
                 "One sample = %.4f ns = %.1f cm of path. Values are medians over the trial.</div>" % (SAMPLE_NS, SAMPLE_NS * CM_PER_NS))
        h.append('<table><tr><th class="l">Message</th><th class="l">Received by</th><th>First path index</th><th>Peak index</th>'
                 "<th>Peak &minus; first path</th><th>In time</th><th>As path length</th><th>Smallest</th><th>Largest</th><th>Messages</th></tr>")
        for kind in KINDS:
            g = d["gaps"].get(kind)
            if g:
                h.append('<tr><td class="l"><b>%s</b></td><td class="l">%s</td><td>%.2f</td><td>%.0f</td><td><b>%.2f samples</b></td>'
                         "<td><b>%.2f ns</b></td><td>%.0f cm</td><td>%.2f</td><td>%.2f</td><td>%d</td></tr>"
                         % (kind, "initiator" if kind == "response" else "responder", g["fp"], g["peak"], g["gap"],
                            g["gap"] * SAMPLE_NS, g["gap"] * SAMPLE_NS * CM_PER_NS, g["gap_min"], g["gap_max"], g["n"]))
        h.append("</table>")
        h.append('<div class="note">1 to 3 samples between first path and peak is a clean direct path. More than %g samples '
                 "means a weak early arrival ahead of a stronger later one: the direct path is probably blocked.</div>" % NLOS_GAP_SAMPLES)
        if len(charts) > 1:
            h.append('<img src="%s" alt="first path to peak"><div class="sub">%s</div>' % (charts[1][1], esc(charts[1][0])))

    # ---- every exchange
    h.append("<h2>Every exchange</h2>")
    kinds = [k for k in KINDS if k in d["gaps"]]
    has_cal = off is not None
    scale = max([abs(r["diff_m"]) for r in d["rows"] if r["diff_m"] is not None] or [1.0]) or 1.0
    head = ['<tr><th rowspan="2">No.</th><th rowspan="2" class="l">Status</th><th rowspan="2">Reported</th><th rowspan="2">Actual</th>'
            '<th rowspan="2" colspan="2">Difference</th>']
    if has_cal:
        head.append('<th rowspan="2">Calibrated<br>difference</th>')
    for k in kinds:
        head.append('<th colspan="4" class="g">%s</th>' % k)
    head.append('<th rowspan="2" class="l">Why flagged</th></tr><tr>')
    for k in kinds:
        head.append('<th class="g">first path</th><th>peak</th><th>gap (samples)</th><th>gap (ns)</th>')
    head.append("</tr>")
    h.append('<div class="scroll"><table>' + "".join(head))
    for r in d["rows"]:
        tr = "flag" if r["flagged"] else ("fail" if r["status"] != "ok" else "")
        cells = ['<td>%d</td><td class="l">%s</td>' % (r["xid"], esc(str(r["status"])))]
        cells.append("<td>%s</td><td>%s</td>" % (("%.3f m" % r["range_m"]) if r["range_m"] is not None else "-",
                                                 ("%.3f m" % real) if real is not None else "-"))
        if r["diff_m"] is not None:
            w = int(round(60 * abs(r["diff_m"]) / scale))
            color = "#b3261e" if r["diff_m"] > 0 else "#1b5fa8"
            cells.append('<td class="%s"><b>%s</b></td><td class="l"><span class="bar" style="width:%dpx;background:%s"></span></td>'
                         % (cls(r["diff_m"]), _cm(r["diff_m"]), w, color))
        else:
            cells.append("<td>-</td><td></td>")
        if has_cal:
            cells.append(('<td class="%s">%s</td>' % (cls(r["cal_diff_m"]), _cm(r["cal_diff_m"]))) if r["cal_diff_m"] is not None else "<td>-</td>")
        for k in kinds:
            m = r["msg"].get(k)
            if m:
                warn = ' style="color:#b3261e;font-weight:600"' if m["gap"] > NLOS_GAP_SAMPLES else ""
                cells.append('<td class="g">%.2f</td><td>%d</td><td%s>%.2f</td><td%s>%.2f</td>' % (m["fp"], m["peak"], warn, m["gap"], warn, m["gap_ns"]))
            else:
                cells.append('<td class="g">-</td><td>-</td><td>-</td><td>-</td>')
        cells.append('<td class="w">%s</td>' % esc("; ".join(r["reasons"])))
        h.append('<tr class="%s">%s</tr>' % (tr, "".join(cells)))
    h.append("</table></div>")
    h.append('<div class="sub">Difference = reported range minus actual distance. Red and positive: measured too long. '
             "Blue and negative: too short. Shaded rows were flagged as abnormal; grey rows did not complete.</div>")
    h.append('<div class="sub" style="margin-top:26px">Made by uwb_analyze.py from %s.</div>' % esc(os.path.basename(path)))
    h.append("</body></html>")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(h))
    return out


def collect(paths):
    """Expand folders, and keep one file per trial: merged if present, else the responder's."""
    files = []
    for p in paths:
        files += sorted(glob.glob(os.path.join(p, "*.json"))) if os.path.isdir(p) else [p]
    best = {}
    rank = {"merged": 0, "responder": 1}
    for p in files:
        trial_id, role = peek(p)
        if trial_id and role in rank and (trial_id not in best or rank[role] < rank[best[trial_id][0]]):
            best[trial_id] = (role, p)
    return [p for _, p in sorted(best.values(), key=lambda t: t[1])]


def _filtered(paths, group=None, setup=None, flt=None):
    """Trial files to compare: one per trial (merged if present), after the filters."""
    out = []
    for p in collect(paths):
        trial = load_trial(p)
        meta = trial.get("meta") or {}
        if group is not None and meta.get("group", "") != group:
            continue
        if setup is not None and us.setup_key(meta) != setup:
            continue
        if flt and not us.matches(meta, flt):
            continue
        out.append((p, trial))
    return out


def compare(paths, group=None, drop_flagged=False, setup=None, flt=None):
    """Put the trials of each setup side by side.

    Trials belong together when they have the same setup id (older files: the same group
    label). Within a setup they are listed by placement: same placement = the boards were
    not touched in between, so those trials are true repeats.

    Trials of different length are compared through the standard error of their means
    (sd / sqrt(n)): a 10-exchange trial has a wide confidence interval, a 100-exchange
    trial a narrow one, and two trials agree when their intervals overlap. The pooled
    rows treat all exchanges of a placement, or of the whole setup, as one data set.
    """
    groups = {}
    for p, trial in _filtered(paths, group, setup, flt):
        meta = trial.get("meta") or {}
        a = trial.get("analysis") or analyze_trial(trial)
        xr, r = ranges(trial)
        if drop_flagged:
            bad = {f["xid"] for f in a["flagged"]}
            r = np.array([v for x, v in zip(xr, r) if int(x) not in bad])
        groups.setdefault(us.setup_key(meta), []).append((p, trial, r, len(a["flagged"])))

    rows = []
    for g in sorted(groups):
        items = sorted(groups[g], key=lambda t: ((t[1].get("meta") or {}).get("placement") or 0, t[1].get("started") or ""))
        meta0 = items[0][1].get("meta") or {}
        print("=" * 108)
        print("%s%s" % (us.setup_title(meta0), "  (flagged exchanges left out)" if drop_flagged else ""))
        print("%-36s %4s %6s %5s %9s %9s %8s %8s %8s %8s %5s  %s"
              % ("file", "plc", "real", "n", "mean", "95% CI", "sd", "median", "bias", "cal bias", "flag",
                 "vs the other trials"))
        allr = np.concatenate([r for _, _, r, _ in items]) if items else np.array([])
        by_place = {}
        for idx, (p, trial, r, nflag) in enumerate(items):
            meta = trial.get("meta") or {}
            real = meta.get("distance_m")
            place = meta.get("placement")
            by_place.setdefault(place, []).append(r)
            s = describe(r, real)
            verdict = ""
            rest = np.concatenate([x for j, (_, _, x, _) in enumerate(items) if j != idx] or [np.array([])])
            if s and s["sem_m"] is not None and rest.size > 1:
                se = math.sqrt(s["sem_m"] ** 2 + rest.var(ddof=1) / rest.size)
                z = (s["mean_m"] - rest.mean()) / se if se > 0 else 0.0
                verdict = "agrees" if abs(z) < 2.6 else "DIFFERS by %+.3f m (%.1f standard errors)" % (
                    s["mean_m"] - rest.mean(), abs(z))
            if s:
                off = cal_offset(p, trial)
                calb = ("%+.4f" % (s["bias_m"] - off)) if (off is not None and "bias_m" in s) else "-"
                print("%-36s %4s %6s %5d %9.4f %9s %8s %8.4f %8s %8s %5d  %s"
                      % (os.path.basename(p)[:36], "-" if place is None else place, fmt(real, 2), s["n"], s["mean_m"],
                         "+/-" + fmt(s["ci95_m"], 4), fmt(s["std_m"], 4), s["median_m"],
                         ("%+.4f" % s["bias_m"]) if "bias_m" in s else "-", calb, nflag, verdict))
                rows.append({"setup": g, "setup_name": meta.get("setup_name", meta.get("group", "")), "placement": place,
                             "file": os.path.basename(p), "trial_id": trial.get("trial_id"),
                             "real_m": real, "n": s["n"], "mean_m": s["mean_m"], "ci95_m": s["ci95_m"],
                             "std_m": s["std_m"], "median_m": s["median_m"], "bias_m": s.get("bias_m"),
                             "cal_offset_m": off,
                             "cal_bias_m": (s["bias_m"] - off) if (off is not None and "bias_m" in s) else None,
                             "flagged": nflag, "vs_rest": verdict})
            else:
                print("%-36s %4s %6s %5d   (no completed exchanges with a range)"
                      % (os.path.basename(p)[:36], "-" if place is None else place, fmt(real, 2), 0))
        real0 = meta0.get("distance_m")
        if len(by_place) > 1:
            for place in sorted(by_place, key=lambda v: (v is None, v)):
                s = describe(np.concatenate(by_place[place]) if by_place[place] else np.array([]), real0)
                if s:
                    print("%-36s %4s %6s %5d %9.4f %9s %8s %8.4f %8s"
                          % ("  placement %s pooled" % place, place, "", s["n"], s["mean_m"], "+/-" + fmt(s["ci95_m"], 4),
                             fmt(s["std_m"], 4), s["median_m"], ("%+.4f" % s["bias_m"]) if "bias_m" in s else "-"))
        s = describe(allr, real0)
        if s and len(items) > 1:
            means = np.array([r.mean() for _, _, r, _ in items if r.size])
            print("%-36s %4s %6s %5d %9.4f %9s %8s %8.4f %8s"
                  % ("pooled (all exchanges)", "", "", s["n"], s["mean_m"], "+/-" + fmt(s["ci95_m"], 4),
                     fmt(s["std_m"], 4), s["median_m"], ("%+.4f" % s["bias_m"]) if "bias_m" in s else "-"))
            if means.size > 1:
                print("spread of the trial means: sd %.4f m, max - min %.4f m" % (means.std(ddof=1), np.ptp(means)))
            if len(by_place) > 1:
                pm = np.array([np.concatenate(v).mean() for v in by_place.values() if sum(x.size for x in v)])
                if pm.size > 1:
                    print("spread of the placement means (how repeatable the setup is): sd %.4f m, max - min %.4f m"
                          % (pm.std(ddof=1), np.ptp(pm)))
    return rows


def summary(paths, flt=None, drop_flagged=False):
    """One line per setup and placement, sorted by site, condition and distance: the
    whole data set at a glance, e.g. range error against distance for one site."""
    table = {}
    for p, trial in _filtered(paths, flt=flt):
        meta = trial.get("meta") or {}
        a = trial.get("analysis") or analyze_trial(trial)
        xr, r = ranges(trial)
        if drop_flagged:
            bad = {f["xid"] for f in a["flagged"]}
            r = np.array([v for x, v in zip(xr, r) if int(x) not in bad])
        key = (us.setup_key(meta), meta.get("placement"))
        t = table.setdefault(key, {"meta": meta, "trials": 0, "r": [], "rc": [], "flagged": 0, "failed": 0})
        t["trials"] += 1
        t["r"].append(r)
        off = cal_offset(p, trial)
        if off is not None:
            t["rc"].append(r - off)
        t["flagged"] += len(a["flagged"])
        t["failed"] += a["n_failed"]

    def order(item):
        m = item[1]["meta"]
        return (str(m.get("site") or ""), str(m.get("condition") or ""), m.get("distance_m") or 0.0, item[0][0],
                item[0][1] or 0)

    print("%-6s %-18s %-14s %-16s %7s %-18s %3s %6s %6s %9s %8s %8s %8s %5s %5s"
          % ("setup", "name", "site", "condition", "real m", "in the way", "plc", "trials", "n", "mean", "sd", "bias",
             "cal bias", "flag", "fail"))
    rows = []
    for (sk, place), t in sorted(table.items(), key=order):
        m = t["meta"]
        r = np.concatenate(t["r"]) if t["r"] else np.array([])
        s = describe(r, m.get("distance_m")) or {}
        calb = None
        if t["rc"] and len(t["rc"]) == len(t["r"]) and m.get("distance_m") is not None:
            rc = np.concatenate(t["rc"])
            if rc.size:
                calb = float(rc.mean()) - m["distance_m"]
        print("%-6s %-18s %-14s %-16s %7s %-18s %3s %6d %6d %9s %8s %8s %8s %5d %5d"
              % ((m.get("setup_id") or "-")[:6], str(m.get("setup_name") or m.get("group") or "")[:18],
                 str(m.get("site") or "")[:14], str(m.get("condition") or "")[:16], fmt(m.get("distance_m"), 2),
                 str(m.get("obstruction") or "")[:18], "-" if place is None else place, t["trials"], s.get("n", 0),
                 fmt(s.get("mean_m"), 4), fmt(s.get("std_m"), 4),
                 ("%+.4f" % s["bias_m"]) if s.get("bias_m") is not None else "-",
                 ("%+.4f" % calb) if calb is not None else "-", t["flagged"], t["failed"]))
        rows.append({"setup": sk, "setup_name": m.get("setup_name", m.get("group", "")), "site": m.get("site"),
                     "condition": m.get("condition"), "distance_m": m.get("distance_m"),
                     "obstruction": m.get("obstruction"), "orientation": m.get("orientation"), "placement": place,
                     "trials": t["trials"], "n": s.get("n", 0), "mean_m": s.get("mean_m"), "std_m": s.get("std_m"),
                     "bias_m": s.get("bias_m"), "cal_bias_m": calb, "flagged": t["flagged"], "failed": t["failed"]})
    if not rows:
        print("(no trials match)")
    return rows


def export_csv(path, out=None):
    trial = load_trial(path)
    a = trial.get("analysis") or analyze_trial(trial)
    why = {f["xid"]: "; ".join(f["reasons"]) for f in a["flagged"]}
    out = out or os.path.splitext(path)[0] + ".csv"
    cols = ["xid", "status", "range_m", "tof_ns", "flagged", "reasons"]
    for kind in KINDS:
        cols += ["%s_%s" % (kind, c) for c in ("fp_index", "peak_index", "peak_amp", "f1", "f2", "f3", "status",
                                               "rx_power_dbm", "fp_power_dbm", "clock_offset_ppm")]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for e in trial["exchanges"]:
            row = {"xid": e["xid"], "status": e.get("status"), "range_m": e.get("range_m"), "tof_ns": e.get("tof_ns"),
                   "flagged": int(e["xid"] in why), "reasons": why.get(e["xid"], "")}
            for kind in KINDS:
                if kind in e:
                    d = e[kind]["diag"]
                    for c in ("fp_index", "peak_index", "peak_amp", "f1", "f2", "f3", "status", "rx_power_dbm",
                              "fp_power_dbm", "clock_offset_ppm"):
                        row["%s_%s" % (kind, c)] = d.get(c)
            w.writerow(row)
    return out


def plot(path, out=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    trial = load_trial(path)
    a = trial.get("analysis") or analyze_trial(trial)
    bad = {f["xid"] for f in a["flagged"]}
    kinds = [k for k in KINDS if stack_cir(trial, k)[1].shape[0]]
    fig, axes = plt.subplots(1, len(kinds) + 1, figsize=(6 * (len(kinds) + 1), 4.8))
    for ax, kind in zip(axes, kinds):
        xids, cir, fp = stack_cir(trial, kind)
        for k in np.argsort([int(x) in bad for x in xids]):  # flagged drawn last, on top
            f = int(round(fp[k]))
            lo, hi = max(0, f - 20), min(cir.shape[1], f + 60)
            flagged = int(xids[k]) in bad
            ax.plot(np.arange(lo, hi) - f, np.abs(cir[k, lo:hi]), color="tab:red" if flagged else "tab:blue",
                    alpha=0.9 if flagged else 0.25, linewidth=1.2 if flagged else 0.7)
        ax.axvline(0, color="k", linestyle="--", linewidth=0.6)
        ax.set(title="%s CIR, aligned to the reported first path" % kind, xlabel="samples from first path (~1 ns)",
               ylabel="|I + jQ|")
        ax.grid(alpha=0.25)
    xr, r = ranges(trial)
    ax = axes[-1]
    if r.size:
        mask = np.array([int(x) in bad for x in xr])
        ax.plot(xr[~mask], r[~mask], ".", color="tab:blue", label="normal")
        ax.plot(xr[mask], r[mask], "x", color="tab:red", label="flagged")
        real = (trial.get("meta") or {}).get("distance_m")
        if real is not None:
            ax.axhline(real, color="k", linewidth=0.8, label="real %.3f m" % real)
        ax.axhline(r.mean(), color="tab:green", linestyle=":", label="mean %.3f m" % r.mean())
        ax.legend(fontsize="small")
    ax.set(title="range per exchange", xlabel="exchange number", ylabel="range (m)")
    ax.grid(alpha=0.25)
    fig.suptitle("%s  |  trial %s  |  group '%s'" % (os.path.basename(path), trial.get("trial_id"),
                                                    (trial.get("meta") or {}).get("group", "")))
    fig.tight_layout()
    out = out or os.path.splitext(path)[0] + "_overview.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def suspects(trial, cal=None):
    """Exchanges in which the chip's first path is most likely NOT the direct path, most suspicious
    first. Returns [{"xid", "score", "reasons": [text, ...]}]; an exchange with no reason is left out.

    The signs looked for, and what each adds to the score:
      - range far from the rest of the trial. Too LONG is the classic miss: a later path was taken
        as the first. Too short: noise or a sidelobe ahead of the pulse was taken as the first.
      - the three messages of one exchange disagree about where the first path sits relative to the
        peak. They cross the same channel within about 20 ms, so they should agree.
      - energy ahead of the reported first path, well above the noise: an earlier arrival exists.
      - the chip's own first-path warning flags.
      - first path far ahead of the peak: direct path blocked, weak first path, estimate fragile.
      - CIR shape near the first path unlike the rest of the trial.
    """
    real = (trial.get("meta") or {}).get("distance_m")
    found = {}

    def add(xid, points, text):
        f = found.setdefault(int(xid), {"xid": int(xid), "score": 0.0, "reasons": []})
        f["score"] += points
        f["reasons"].append(text)

    xr, r = ranges(trial)
    if r.size >= 8:
        z, med = robust_z(r, floor=0.01)
        for xid, value, zz in zip(xr, r, z):
            if abs(zz) > Z_LIMIT:
                dev = value - med
                add(xid, min(5.0, abs(zz) / Z_LIMIT) + (0.5 if dev > 0 else 0.0),
                    "range %+.2f m from the trial's median: %s" % (
                        dev, "a later path taken as the first?" if dev > 0 else "something ahead of the pulse taken as the first path?"))
    if real is not None and cal is not None:
        for xid, value in zip(xr, r):
            err = value - cal - real
            if abs(err) > 0.30:
                add(xid, min(5.0, abs(err) / 0.30), "calibrated range is %+.2f m from the real distance" % err)

    per = {}
    for kind in KINDS:
        m = _kind_metrics(trial, kind)
        if m is None:
            continue
        for k, xid in enumerate(m["xids"]):
            per.setdefault(int(xid), {})[kind] = {key: m[key][k] for key in ("gap", "status", "early", "corr")}
        med_corr = np.nanmedian(m["corr"]) if np.isfinite(m["corr"]).any() else None
        for k, xid in enumerate(m["xids"]):
            e, st, g, c = m["early"][k], int(m["status"][k]), m["gap"][k], m["corr"][k]
            if np.isfinite(e) and e >= 5.0:
                add(xid, min(4.0, e / 5.0), "%s: energy %.0f x noise just before the reported first path (an earlier arrival?)" % (kind, e))
            if st & 0x1F:
                add(xid, 1.5, "%s: the chip itself doubted its first path (warning 0x%02X)" % (kind, st))
            if g > NLOS_GAP_SAMPLES:
                add(xid, 1.0, "%s: first path %.1f samples ahead of the peak (weak first path, likely blocked)" % (kind, g))
            if med_corr is not None and np.isfinite(c) and c < 0.90 and c < med_corr - 0.05 and len(m["xids"]) >= MIN_FOR_RELATIVE:
                add(xid, 1.0, "%s: CIR shape unlike the rest of the trial (similarity %.2f)" % (kind, c))
    for xid, kinds in per.items():
        gaps = {k: v["gap"] for k, v in kinds.items()}
        if len(gaps) >= 2:
            spread = max(gaps.values()) - min(gaps.values())
            if spread > 2.0:
                add(xid, min(4.0, spread / 2.0), "the messages disagree on the first path: peak - first path is %s samples"
                    % ", ".join("%s %.1f" % (k, gaps[k]) for k in KINDS if k in gaps))
    return sorted(found.values(), key=lambda f: -f["score"])


def plot_cirs(path, out=None, window=(-25, 90), progress=None, only=None, limit=None):
    """Individual CIRs of a trial: a PDF with one page per exchange.

    only=None      every exchange
    only="suspect" only the exchanges in which a direct-path miss is likely (see suspects()),
                   most suspicious first, at most `limit` of them, with a list of them on page 1

    Top row: magnitude of the whole captured CIR for poll, response and final.
    Bottom row: I, Q and magnitude around the chip's first path, with the first path
    and the peak marked. The page title says why an exchange was picked or flagged."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    trial = load_trial(path)
    a = trial.get("analysis") or analyze_trial(trial)
    why = {f["xid"]: "; ".join(f["reasons"]) for f in a["flagged"]}
    meta = trial.get("meta") or {}
    exchanges = [e for e in trial["exchanges"] if any(k in e for k in KINDS)]
    if not exchanges:
        raise ValueError("this file holds no CIRs")
    picked = None
    n_suspect = 0
    if only == "suspect":
        picked = suspects(trial, cal_offset(path, trial))
        n_suspect = len(picked)
        if limit:
            picked = picked[:limit]
        by_xid = {e["xid"]: e for e in exchanges}
        exchanges = [by_xid[s["xid"]] for s in picked if s["xid"] in by_xid]
        why = {s["xid"]: "; ".join(s["reasons"]) for s in picked}
        out = out or os.path.splitext(path)[0] + "_suspect_cirs.pdf"
        if not exchanges:
            return None
    out = out or os.path.splitext(path)[0] + "_cirs.pdf"
    head = "%s  |  trial %s  |  %s" % (os.path.basename(path), trial.get("trial_id"), us.setup_title(meta))
    if meta.get("placement") is not None:
        head += "  |  placement %s" % meta["placement"]

    cal = cal_offset(path, trial)
    with PdfPages(out) as pdf:
        if picked is not None:
            # Page 1 and on: the list, so the reader knows what follows and why.
            rows_per_page = 30
            for start in range(0, len(picked), rows_per_page):
                fig = plt.figure(figsize=(16.5, 8.2))
                fig.text(0.03, 0.95, head, fontsize=10)
                fig.text(0.03, 0.915, "Exchanges where a direct-path miss is most likely: %d of %d in this trial%s. Most suspicious first."
                         % (n_suspect, len([e for e in trial["exchanges"] if e.get("status") == "ok"]),
                            (", the %d highest shown" % len(picked)) if len(picked) < n_suspect else ""),
                         fontsize=12, fontweight="bold")
                y = 0.875
                fig.text(0.03, y, "page   exchange   score   range     why", fontsize=9, family="monospace", fontweight="bold")
                first_cir_page = (len(picked) + rows_per_page - 1) // rows_per_page + 1
                for k, sp in enumerate(picked[start:start + rows_per_page], start):
                    y -= 0.027
                    e = by_xid.get(sp["xid"], {})
                    rng = ("%.3f m" % e["range_m"]) if e.get("range_m") is not None else "   -   "
                    text = "; ".join(sp["reasons"])
                    fig.text(0.03, y, "%4d   %8d   %5.1f   %s   %s" % (first_cir_page + k, sp["xid"], sp["score"], rng,
                                                                    text[:175] + ("..." if len(text) > 175 else "")),
                             fontsize=8.5, family="monospace")
                pdf.savefig(fig, dpi=90)
                plt.close(fig)
        for n, e in enumerate(exchanges):
            fig, axes = plt.subplots(2, 3, figsize=(16.5, 8.2))
            for col, kind in enumerate(KINDS):
                top, bot = axes[0][col], axes[1][col]
                if kind not in e:
                    for ax in (top, bot):
                        ax.text(0.5, 0.5, "no %s CIR in this file" % kind, ha="center", va="center",
                                transform=ax.transAxes, color="gray")
                        ax.set_xticks([])
                        ax.set_yticks([])
                    top.set_title(kind)
                    continue
                rec = e[kind]
                i = np.asarray(rec["cir"]["i"], dtype=float)
                q = np.asarray(rec["cir"]["q"], dtype=float)
                mag = np.hypot(i, q)
                start = rec.get("cir_start", 0)
                x = np.arange(start, start + mag.size)
                d = rec["diag"]
                fp, pk = d["fp_index"], d["peak_index"]

                top.plot(x, mag, color="tab:blue", linewidth=0.7)
                top.axvline(fp, color="tab:red", linestyle="--", linewidth=0.9, label="chip first path %.2f" % fp)
                top.axvline(pk, color="tab:green", linestyle=":", linewidth=0.9, label="peak %d" % pk)
                top.set(title="%s   (received by the %s)" % (kind, "initiator" if kind == "response" else "responder"),
                        xlabel="accumulator sample (about 1 ns each)", ylabel="|I + jQ|")
                top.legend(fontsize="x-small", loc="upper right")
                top.grid(alpha=0.25)

                lo = max(start, int(math.floor(fp)) + window[0])
                hi = min(start + mag.size, int(math.floor(fp)) + window[1])
                if hi <= lo:
                    lo, hi = start, start + mag.size
                sl = slice(lo - start, hi - start)
                bot.plot(x[sl], i[sl], color="tab:orange", linewidth=0.8, label="I")
                bot.plot(x[sl], q[sl], color="tab:purple", linewidth=0.8, label="Q")
                bot.plot(x[sl], mag[sl], color="tab:blue", linewidth=1.3, marker=".", markersize=3, label="|I + jQ|")
                bot.axvline(fp, color="tab:red", linestyle="--", linewidth=0.9)
                bot.axvline(pk, color="tab:green", linestyle=":", linewidth=0.9)
                extra = []
                if d.get("fp_power_dbm") is not None and d.get("rx_power_dbm") is not None:
                    extra.append("first path %.1f dBm, total %.1f dBm" % (d["fp_power_dbm"], d["rx_power_dbm"]))
                if d.get("status_flags"):
                    extra.append("chip: " + ", ".join(d["status_flags"]))
                bot.set(title="around the first path" + ("   " + "; ".join(extra) if extra else ""),
                        xlabel="accumulator sample", ylabel="amplitude")
                bot.title.set_fontsize(9)
                bot.legend(fontsize="x-small", loc="upper right")
                bot.grid(alpha=0.25)

            line = "exchange %d   status %s" % (e["xid"], e.get("status"))
            if e.get("range_m") is not None:
                line += "   range %.3f m" % e["range_m"]
                if meta.get("distance_m") is not None:
                    line += "  (real %.3f m, error %+.3f m" % (meta["distance_m"], e["range_m"] - meta["distance_m"])
                    line += (", calibrated %+.3f m)" % (e["range_m"] - cal - meta["distance_m"])) if cal is not None else ")"
            if e["xid"] in why:
                import textwrap
                label = "WHY IT WAS PICKED" if picked is not None else "FLAGGED"
                line += "\n" + "\n".join(textwrap.wrap("%s: %s" % (label, why[e["xid"]]), 190)[:3])
            fig.suptitle(head + "\n" + line, fontsize=10, color="tab:red" if e["xid"] in why else "black")
            fig.tight_layout(rect=(0, 0, 1, 0.93 - 0.02 * max(0, line.count("\n") - 1)))
            pdf.savefig(fig, dpi=90)
            plt.close(fig)
            if progress and (n + 1) % 20 == 0:
                progress("  %d of %d pages" % (n + 1, len(exchanges)))
    return out


DATASET_HELP = """UWB CIR data set. One row per completed ranging exchange (N rows).

cir          int32  [N, 3, 1016, 2]  channel impulse responses. axis 1: 0 = poll, 1 = response, 2 = final.
                                      axis 2: accumulator sample (about 1 ns apart). axis 3: 0 = I, 1 = Q.
                                      Samples that were not captured (windowed trials) are 0, see cir_start / cir_len.
present      bool   [N, 3]           False where that CIR is missing (e.g. file was not merged with the other side)
cir_start    int    [N, 3]           first captured sample
cir_len      int    [N, 3]           number of captured samples
accum        int    [N, 3]           preamble symbols accumulated: divide cir by this to compare amplitudes between frames
fp_index     float  [N, 3]           the chip's own first-path estimate, in samples (index into axis 2)
peak_index   int    [N, 3]           strongest sample according to the chip
fp_power_dbm, rx_power_dbm  float [N, 3]   estimated first-path and total receive power
chip_status  int    [N, 3]           chip first-path warning bits (0 = no warning)
rx_timestamp int64  [N, 3]           40-bit receive timestamps (device time units, 15.65 ps)
range_m      float  [N]              measured range with the chip's first path
distance_m   float  [N]              real distance (ground truth) from the setup
error_m      float  [N]              range_m - distance_m
cal_offset_m, range_cal_m, error_cal_m  float [N]   antenna delay correction, and range / error after removing it
                                      (NaN when the boards of that trial have not been calibrated)
flagged      bool   [N]              marked abnormal by uwb_analyze
trial_id, xid, source_file, setup_id, setup_name, placement, site, condition, obstruction, orientation,
antenna_height_m, channel
                                      per-row labels. Rows with the same setup_id and placement are true repeats;
                                      split train / test by setup or placement, never by row, to avoid leakage.

Load with:  d = numpy.load("dataset.npz", allow_pickle=False);  x = d["cir"].astype("float32") / d["accum"][..., None, None]
"""


def export_dataset(paths, out=None, flt=None, include_failed=False):
    """Collect trials into one array file for machine learning (.npz) plus a .csv of the labels."""
    L = 1016
    cirs, rows = [], []
    per = {k: [] for k in ("present", "cir_start", "cir_len", "accum", "fp_index", "peak_index", "fp_power_dbm",
                           "rx_power_dbm", "chip_status", "rx_timestamp")}
    n_files = 0
    for p, trial in _filtered(paths, flt=flt):
        meta = trial.get("meta") or {}
        a = trial.get("analysis") or analyze_trial(trial)
        bad = {f["xid"] for f in a["flagged"]}
        chan = ((trial.get("params") or {}).get("radio") or {}).get("chan")
        off = cal_offset(p, trial)
        used = 0
        for e in trial["exchanges"]:
            if not any(k in e for k in KINDS):
                continue
            if e.get("status") != "ok" and not include_failed:
                continue
            block = np.zeros((3, L, 2), dtype=np.int32)
            vals = {k: [] for k in per}
            for kind in KINDS:
                rec = e.get(kind)
                if rec is None:
                    for k in per:
                        vals[k].append(False if k == "present" else (float("nan") if k in (
                            "fp_index", "fp_power_dbm", "rx_power_dbm") else 0))
                    continue
                start = int(rec.get("cir_start", 0))
                i = np.asarray(rec["cir"]["i"], dtype=np.int32)
                q = np.asarray(rec["cir"]["q"], dtype=np.int32)
                n = min(i.size, L - start)
                block[KINDS.index(kind), start:start + n, 0] = i[:n]
                block[KINDS.index(kind), start:start + n, 1] = q[:n]
                d = rec["diag"]
                vals["present"].append(True)
                vals["cir_start"].append(start)
                vals["cir_len"].append(n)
                vals["accum"].append(d.get("accum_count") or 0)
                vals["fp_index"].append(d.get("fp_index", float("nan")))
                vals["peak_index"].append(d.get("peak_index") or 0)
                vals["fp_power_dbm"].append(d["fp_power_dbm"] if d.get("fp_power_dbm") is not None else float("nan"))
                vals["rx_power_dbm"].append(d["rx_power_dbm"] if d.get("rx_power_dbm") is not None else float("nan"))
                vals["chip_status"].append(d.get("status") or 0)
                vals["rx_timestamp"].append(rec.get("rx_timestamp") or 0)
            cirs.append(block)
            for k in per:
                per[k].append(vals[k])
            real = meta.get("distance_m")
            rng = e.get("range_m")
            rows.append({
                "row": len(rows), "file": os.path.basename(p), "trial_id": trial.get("trial_id") or "", "xid": e["xid"],
                "status": e.get("status") or "", "setup_id": meta.get("setup_id") or "",
                "setup_name": meta.get("setup_name") or meta.get("group") or "",
                "placement": meta.get("placement") if meta.get("placement") is not None else -1,
                "site": meta.get("site") or "", "condition": meta.get("condition") or "",
                "obstruction": meta.get("obstruction") or "", "orientation": meta.get("orientation") or "",
                "antenna_height_m": meta.get("antenna_height_m") if meta.get("antenna_height_m") is not None else float("nan"),
                "channel": chan if chan is not None else -1,
                "distance_m": real if real is not None else float("nan"),
                "range_m": rng if rng is not None else float("nan"),
                "error_m": (rng - real) if (rng is not None and real is not None) else float("nan"),
                "cal_offset_m": off if off is not None else float("nan"),
                "range_cal_m": (rng - off) if (rng is not None and off is not None) else float("nan"),
                "error_cal_m": (rng - off - real) if (rng is not None and off is not None and real is not None) else float("nan"),
                "flagged": e["xid"] in bad,
            })
            used += 1
        n_files += 1 if used else 0
    if not rows:
        raise ValueError("no exchanges with CIRs found (merge the initiator and responder files first)")

    out = out or "dataset.npz"
    if not out.lower().endswith(".npz"):
        out += ".npz"
    arrays = {"cir": np.stack(cirs), "description": np.array(DATASET_HELP)}
    kinds_int = {"cir_start", "cir_len", "accum", "peak_index", "chip_status"}
    for k, v in per.items():
        if k == "present":
            arrays[k] = np.array(v, dtype=bool)
        elif k == "rx_timestamp":
            arrays[k] = np.array(v, dtype=np.int64)
        elif k in kinds_int:
            arrays[k] = np.array(v, dtype=np.int32)
        else:
            arrays[k] = np.array(v, dtype=np.float64)
    for k in rows[0]:
        if k in ("row", "file", "status"):
            continue
        col = [r[k] for r in rows]
        if isinstance(col[0], bool):
            arrays[k] = np.array(col, dtype=bool)
        elif isinstance(col[0], str):
            arrays[k] = np.array(col, dtype=str)
        elif k in ("xid", "placement", "channel"):
            arrays[k] = np.array(col, dtype=np.int64)
        else:
            arrays[k] = np.array(col, dtype=np.float64)
    arrays["source_file"] = np.array([r["file"] for r in rows], dtype=str)
    np.savez_compressed(out, **arrays)

    labels = os.path.splitext(out)[0] + "_labels.csv"
    with open(labels, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    n3 = int(arrays["present"].all(axis=1).sum())
    print("%d exchanges from %d trials -> %s  (cir array %s)" % (len(rows), n_files, out, "x".join(map(str, arrays["cir"].shape))))
    print("%d of them have all three CIRs; labels also in %s" % (n3, labels))
    if n3 < len(rows):
        print("Rows without all three come from files that were not merged with the other PC's file.")
    return out


def calibrate(paths, save=False):
    """Work out the antenna delay correction from line-of-sight trials at known distances.
    Prints the result; with save=True also stores it in calibration.json next to the files.
    Returns the proposal (or None)."""
    trials = []
    for p in paths:
        trial = load_trial(p)
        trials.append((os.path.basename(p), trial, trial.get("analysis") or analyze_trial(trial)))
    proposal, lines = uc.propose(trials)
    print("\n".join(lines))
    if proposal and save:
        folder = os.path.dirname(os.path.abspath(paths[0]))
        path, cal = uc.apply(folder, proposal)
        print("\nSaved to %s" % path)
        print("\n".join(uc.describe(cal)))
    return proposal


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("merge", help="merge one initiator file and one responder file")
    p.add_argument("initiator")
    p.add_argument("responder")
    p.add_argument("-o", "--out")
    p = sub.add_parser("merge-all", help="merge every initiator/responder pair in a folder")
    p.add_argument("folder")
    p = sub.add_parser("report", help="statistics and flagged exchanges")
    p.add_argument("files", nargs="+")
    p = sub.add_parser("compare", help="compare the trials of each setup")
    p.add_argument("paths", nargs="+", help="folders and/or trial files")
    p.add_argument("--group", help="only this group label (older files)")
    p.add_argument("--setup", help="only this setup id, e.g. S003")
    p.add_argument("--filter", default="", help='e.g. "site=lab condition=nlos"')
    p.add_argument("--drop-flagged", action="store_true", help="leave flagged exchanges out of the statistics")
    p.add_argument("--csv", help="also write the table to this CSV file")
    p = sub.add_parser("summary", help="one line per setup and placement")
    p.add_argument("paths", nargs="+")
    p.add_argument("--filter", default="", help='e.g. "site=lab condition=nlos"')
    p.add_argument("--drop-flagged", action="store_true")
    p = sub.add_parser("cirs", help="PDF with every individual CIR, one page per exchange")
    p.add_argument("file")
    p.add_argument("-o", "--out")
    p = sub.add_parser("suspects", help="PDF with only the CIRs where a direct-path miss is likely")
    p.add_argument("file")
    p.add_argument("-o", "--out")
    p.add_argument("--limit", type=int, default=40, help="at most this many exchanges (default 40)")
    p = sub.add_parser("dataset", help="array file for machine learning (.npz + labels .csv)")
    p.add_argument("paths", nargs="+")
    p.add_argument("-o", "--out", default="dataset.npz")
    p.add_argument("--filter", default="")
    p = sub.add_parser("calibrate", help="antenna delay calibration from LOS trials at known distances")
    p.add_argument("files", nargs="+")
    p.add_argument("--save", action="store_true", help="store the result in calibration.json next to the files")
    p = sub.add_parser("calibration", help="show the calibration saved in a data folder")
    p.add_argument("folder")
    p = sub.add_parser("csv", help="one row per exchange")
    p.add_argument("file")
    p.add_argument("-o", "--out")
    p = sub.add_parser("plot", help="overview picture of a trial")
    p.add_argument("file")
    p.add_argument("-o", "--out")
    args = ap.parse_args(argv)

    if args.cmd == "merge":
        a, b = load_trial(args.initiator), load_trial(args.responder)
        if a.get("role") == "responder" and b.get("role") == "initiator":
            a, b = b, a
        out = args.out or merged_name(args.responder)
        write_trial(merge_trials(a, b), out)
        print("wrote", out)
    elif args.cmd == "merge-all":
        for out in merge_all(args.folder):
            print("wrote", out)
    elif args.cmd == "report":
        for f in args.files:
            report(f)
            print("\nreport file:", write_report(f))
    elif args.cmd == "compare":
        rows = compare(args.paths, args.group, args.drop_flagged, args.setup, us.parse_filter(args.filter))
        if args.csv and rows:
            with open(args.csv, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            print("wrote", args.csv)
    elif args.cmd == "summary":
        summary(args.paths, us.parse_filter(args.filter), args.drop_flagged)
    elif args.cmd == "cirs":
        print("wrote", plot_cirs(args.file, args.out, progress=print))
    elif args.cmd == "suspects":
        out = plot_cirs(args.file, args.out, progress=print, only="suspect", limit=args.limit)
        print("wrote %s" % out if out else "No exchange in this trial shows a sign of a direct-path miss.")
    elif args.cmd == "dataset":
        export_dataset(args.paths, args.out, us.parse_filter(args.filter))
    elif args.cmd == "calibrate":
        calibrate(args.files, args.save)
    elif args.cmd == "calibration":
        print("\n".join(uc.describe(uc.load(args.folder))))
    elif args.cmd == "csv":
        print("wrote", export_csv(args.file, args.out))
    elif args.cmd == "plot":
        print("wrote", plot(args.file, args.out))


if __name__ == "__main__":
    sys.exit(main())
