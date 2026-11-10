#!/usr/bin/env python3
"""
uwb_viewer.py - look at the CIRs of a trial one exchange at a time, instantly.

Opened from the main window ("View CIRs") or on its own:

    python uwb_viewer.py data/S001_..._merged.json

Nothing is written to disk and there is no waiting: each exchange is drawn straight
onto the window. Left / Right arrow keys step through; "Show" narrows the list to the
exchanges where a direct-path miss is likely, or to the flagged ones.

Top row: magnitude of the whole CIR for poll, response and final.
Bottom row: I, Q and magnitude around the chip's first path.
Red dashed line = the chip's first path, green dotted line = the peak.
"""

import math
import os
import sys

import tkinter as tk
from tkinter import ttk

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import uwb_analyze as ua
import uwb_setups as us

KINDS = ua.KINDS
MODES = ["All exchanges", "Suspect only (direct path may be missed)", "Flagged only (unlike the rest of the trial)"]
BLUE, ORANGE, PURPLE, RED, GREEN, GRID, INK, QUIET = "#1b5fa8", "#e08a00", "#8a4fbf", "#c62828", "#1e7b3c", "#e3e6ec", "#1c2330", "#6b7483"
WINDOW = (-25, 90)   # samples around the first path shown in the bottom row


class TrialView:
    """Everything about one trial file that the window needs. No window code in here."""

    def __init__(self, path):
        self.path = path
        self.trial = ua.load_trial(path)
        self.meta = self.trial.get("meta") or {}
        self.real = self.meta.get("distance_m")
        self.cal = ua.cal_offset(path, self.trial)
        analysis = self.trial.get("analysis") or ua.analyze_trial(self.trial)
        self.flag_why = {f["xid"]: f["reasons"] for f in analysis["flagged"]}
        self.suspect = ua.suspects(self.trial, self.cal)
        self.suspect_why = {s["xid"]: s for s in self.suspect}
        self.by_xid = {e["xid"]: e for e in self.trial["exchanges"] if any(k in e for k in KINDS)}
        self.all_ids = sorted(self.by_xid)

    def ids(self, mode):
        if mode == 1:
            return [s["xid"] for s in self.suspect if s["xid"] in self.by_xid]   # most suspicious first
        if mode == 2:
            return [x for x in self.all_ids if x in self.flag_why]
        return self.all_ids

    def headline(self, xid):
        e = self.by_xid[xid]
        text = "Exchange %d   %s" % (xid, e.get("status"))
        if e.get("range_m") is not None:
            text += "   reported %.3f m" % e["range_m"]
            if self.real is not None:
                text += "   actual %.3f m   difference %+.1f cm" % (self.real, (e["range_m"] - self.real) * 100.0)
                if self.cal is not None:
                    text += "   (calibrated %+.1f cm)" % ((e["range_m"] - self.cal - self.real) * 100.0)
        return text

    def reasons(self, xid):
        lines = []
        s = self.suspect_why.get(xid)
        if s:
            lines.append("Suspect (score %.1f): %s" % (s["score"], "; ".join(s["reasons"])))
        if xid in self.flag_why:
            lines.append("Flagged: " + "; ".join(self.flag_why[xid]))
        return "\n".join(lines) if lines else "Nothing unusual found in this exchange."

    def panels(self, xid):
        """For each message: None, or the numbers to draw (plain lists, sample index on x)."""
        e = self.by_xid[xid]
        out = {}
        for kind in KINDS:
            rec = e.get(kind)
            if rec is None:
                out[kind] = None
                continue
            i, q = rec["cir"]["i"], rec["cir"]["q"]
            mag = [math.hypot(a, b) for a, b in zip(i, q)]
            start = rec.get("cir_start", 0)
            d = rec["diag"]
            fp, pk = d["fp_index"], d["peak_index"]
            lo = max(start, int(math.floor(fp)) + WINDOW[0])
            hi = min(start + len(mag), int(math.floor(fp)) + WINDOW[1])
            if hi <= lo:
                lo, hi = start, start + len(mag)
            out[kind] = {"start": start, "i": i, "q": q, "mag": mag, "fp": fp, "peak": pk, "lo": lo, "hi": hi,
                         "gap": pk - fp, "gap_ns": (pk - fp) * ua.SAMPLE_NS,
                         "fp_dbm": d.get("fp_power_dbm"), "rx_dbm": d.get("rx_power_dbm"),
                         "warn": ", ".join(d.get("status_flags") or [])}
        return out


def nice_ticks(lo, hi, n=5):
    span = hi - lo
    if span <= 0:
        return [lo]
    raw = span / float(n)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
    t = math.ceil(lo / step) * step
    out = []
    while t <= hi + 1e-9:
        out.append(t)
        t += step
    return out


def draw_panel(cv, box, xs, series, vlines, title, note="", xlabel=""):
    """One plot on a tkinter canvas.
    box = (x0, y0, x1, y1) in pixels; xs = x values; series = [(values, colour, width)];
    vlines = [(x, colour, dash)]."""
    x0, y0, x1, y1 = box
    left, right, top, bottom = x0 + 58, x1 - 10, y0 + 22, y1 - 30
    cv.create_text(x0 + 58, y0 + 9, text=title, anchor="w", fill=INK, font=("Segoe UI", 9, "bold"))
    if note:
        cv.create_text(right, y0 + 9, text=note, anchor="e", fill=QUIET, font=("Segoe UI", 8))
    if not xs or right - left < 20 or bottom - top < 20:
        cv.create_rectangle(left, top, right, bottom, outline=GRID)
        if not xs:
            cv.create_text((left + right) / 2, (top + bottom) / 2, text="not in this file", fill=QUIET)
        return
    xmin, xmax = xs[0], xs[-1] if xs[-1] > xs[0] else xs[0] + 1
    ymin = min(0.0, min(min(v) for v, _, _ in series))
    ymax = max(max(v) for v, _, _ in series)
    if ymax <= ymin:
        ymax = ymin + 1.0
    pad = 0.06 * (ymax - ymin)
    ymin, ymax = ymin - (pad if ymin < 0 else 0.0), ymax + pad
    sx = (right - left) / float(xmax - xmin)
    sy = (bottom - top) / float(ymax - ymin)

    def px(x):
        return left + (x - xmin) * sx

    def py(y):
        return bottom - (y - ymin) * sy

    for t in nice_ticks(ymin, ymax, 4):
        cv.create_line(left, py(t), right, py(t), fill=GRID)
        cv.create_text(left - 5, py(t), text="%g" % t, anchor="e", fill=QUIET, font=("Segoe UI", 8))
    for t in nice_ticks(xmin, xmax, 6):
        cv.create_line(px(t), top, px(t), bottom, fill=GRID)
        cv.create_text(px(t), bottom + 9, text="%g" % t, fill=QUIET, font=("Segoe UI", 8))
    cv.create_rectangle(left, top, right, bottom, outline="#b9c0cc")
    if xlabel:
        cv.create_text((left + right) / 2, bottom + 22, text=xlabel, fill=QUIET, font=("Segoe UI", 8))
    for values, colour, width in series:
        pts = []
        for x, v in zip(xs, values):
            pts.append(px(x))
            pts.append(py(v))
        if len(pts) >= 4:
            cv.create_line(*pts, fill=colour, width=width)
    for x, colour, dash in vlines:
        if xmin <= x <= xmax:
            cv.create_line(px(x), top, px(x), bottom, fill=colour, dash=dash, width=1.5)


def draw_exchange(cv, width, height, panels):
    """All six plots of one exchange."""
    cv.delete("all")
    colw = width / 3.0
    rowh = (height - 18) / 2.0
    for col, kind in enumerate(KINDS):
        p = panels.get(kind)
        who = "initiator" if kind == "response" else "responder"
        top_box = (col * colw, 0, (col + 1) * colw, rowh)
        bot_box = (col * colw, rowh, (col + 1) * colw, 2 * rowh)
        if p is None:
            draw_panel(cv, top_box, [], [], [], "%s (received by the %s)" % (kind, who))
            draw_panel(cv, bot_box, [], [], [], "around the first path")
            continue
        xs = list(range(p["start"], p["start"] + len(p["mag"])))
        lines = [(p["fp"], RED, (5, 3)), (p["peak"], GREEN, (2, 3))]
        draw_panel(cv, top_box, xs, [(p["mag"], BLUE, 1)], lines, "%s (received by the %s)" % (kind, who),
                   "first path %.2f   peak %d" % (p["fp"], p["peak"]))
        a, b = p["lo"] - p["start"], p["hi"] - p["start"]
        note = "peak - first path: %.2f samples = %.2f ns" % (p["gap"], p["gap_ns"])
        draw_panel(cv, bot_box, xs[a:b], [(p["i"][a:b], ORANGE, 1), (p["q"][a:b], PURPLE, 1), (p["mag"][a:b], BLUE, 2)],
                   lines, "around the first path", note, "accumulator sample (about 1 ns each)")
    cv.create_text(8, height - 8, anchor="w", fill=QUIET, font=("Segoe UI", 8),
                   text="blue |I + jQ|    orange I    purple Q    red dashed = chip's first path    green dotted = peak")


class CirViewer:
    def __init__(self, parent, path):
        self.view = TrialView(path)
        self.mode = 0
        self.ids = self.view.ids(0)
        self.pos = 0

        self.win = tk.Toplevel(parent) if parent is not None else tk.Tk()
        self.win.title("CIR viewer - %s" % os.path.basename(path))
        self.win.minsize(1100, 680)
        self.win.columnconfigure(0, weight=1)
        self.win.rowconfigure(2, weight=1)

        bar = ttk.Frame(self.win, padding=(8, 6))
        bar.grid(row=0, column=0, sticky="ew")
        ttk.Button(bar, text="<  Previous", command=lambda: self.step(-1)).grid(row=0, column=0)
        ttk.Button(bar, text="Next  >", command=lambda: self.step(1)).grid(row=0, column=1, padx=(4, 12))
        self.v_where = tk.StringVar()
        ttk.Label(bar, textvariable=self.v_where, width=16).grid(row=0, column=2)
        ttk.Label(bar, text="Go to exchange").grid(row=0, column=3, padx=(12, 4))
        self.v_goto = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.v_goto, width=7)
        e.grid(row=0, column=4)
        e.bind("<Return>", lambda ev: self.goto())
        ttk.Button(bar, text="Go", width=4, command=self.goto).grid(row=0, column=5, padx=(4, 12))
        ttk.Label(bar, text="Show").grid(row=0, column=6, padx=(0, 4))
        self.v_mode = tk.StringVar(value=MODES[0])
        cb = ttk.Combobox(bar, textvariable=self.v_mode, values=MODES, state="readonly", width=42)
        cb.grid(row=0, column=7)
        cb.bind("<<ComboboxSelected>>", lambda ev: self.set_mode(MODES.index(self.v_mode.get())))
        ttk.Label(bar, text="   Left / Right arrow keys also step", foreground="#555").grid(row=0, column=8)

        info = ttk.Frame(self.win, padding=(8, 0, 8, 4))
        info.grid(row=1, column=0, sticky="ew")
        self.v_head = tk.StringVar()
        ttk.Label(info, textvariable=self.v_head, font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        self.v_why = tk.StringVar()
        self.l_why = ttk.Label(info, textvariable=self.v_why, wraplength=1500, justify="left")
        self.l_why.grid(row=1, column=0, sticky="w")
        self.v_trial = tk.StringVar(value="%s   |   %d exchanges with CIRs, %d suspect, %d flagged" % (
            us.setup_title(self.view.meta), len(self.view.all_ids), len(self.view.suspect), len(self.view.flag_why)))
        ttk.Label(info, textvariable=self.v_trial, foreground="#555").grid(row=2, column=0, sticky="w")

        self.cv = tk.Canvas(self.win, background="white", highlightthickness=0)
        self.cv.grid(row=2, column=0, sticky="nsew")
        self.cv.bind("<Configure>", lambda ev: self.draw())
        self.win.bind("<Left>", lambda ev: self.step(-1))
        self.win.bind("<Right>", lambda ev: self.step(1))
        self.draw()

    # ---- navigation
    def set_mode(self, mode):
        current = self.ids[self.pos] if self.ids else None
        self.mode = mode
        self.ids = self.view.ids(mode)
        self.pos = self.ids.index(current) if current in self.ids else 0
        self.draw()

    def step(self, by):
        if self.ids:
            self.pos = max(0, min(len(self.ids) - 1, self.pos + by))
            self.draw()

    def goto(self):
        try:
            xid = int(self.v_goto.get())
        except ValueError:
            return
        if xid not in self.ids and xid in self.view.all_ids:
            self.mode = 0                     # asked for an exchange the filter hides: show everything
            self.v_mode.set(MODES[0])
            self.ids = self.view.ids(0)
        if xid in self.ids:
            self.pos = self.ids.index(xid)
            self.draw()

    # ---- drawing
    def draw(self):
        if not self.ids:
            self.cv.delete("all")
            self.v_where.set("0 of 0")
            self.v_head.set("No exchange matches this filter.")
            self.v_why.set("")
            return
        xid = self.ids[self.pos]
        self.v_where.set("%d of %d" % (self.pos + 1, len(self.ids)))
        self.v_head.set(self.view.headline(xid))
        self.v_why.set(self.view.reasons(xid))
        try:
            w = int(self.cv.winfo_width() or 0)
            h = int(self.cv.winfo_height() or 0)
        except (TypeError, ValueError):
            w = h = 0
        if w < 300 or h < 200:
            w, h = 1280, 620
        try:
            self.l_why.configure(wraplength=max(400, w - 30))
        except tk.TclError:
            pass
        draw_exchange(self.cv, w, h, self.view.panels(xid))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 1
    viewer = CirViewer(None, argv[0])
    viewer.win.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
