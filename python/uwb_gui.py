#!/usr/bin/env python3
"""
uwb_gui.py - the MAIN window: runs on the PC of the responder board. Everything about a
trial is decided here (setup, number of exchanges), and all analysis is done here.

    Windows: double-click "UWB Capture.bat"        Mac: double-click "UWB Capture.command"
    (or, on either:  python uwb_gui.py   /   python3 uwb_gui.py)

The other board (the initiator) only needs "UWB Initiator.bat" on its PC: choose the
port, press Start once, and it serves every trial started from this window. Its files
(one CIR per exchange) are brought over on a USB stick and joined with the button
"Import other PC's files".

Needs: pip install pyserial numpy matplotlib      (tkinter comes with Python)
"""

import contextlib
import datetime
import io
import os
import queue
import sys
import threading
import time
import traceback

if sys.stdout is None:  # started with pythonw: there is no console to print to
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import uwb_calib as uc
import uwb_help
import uwb_platform as up
import uwb_run as ur
import uwb_setups as us
import uwb_tool as ut

ua = ur.ua
BAUDS = ["1000000", "460800", "230400", "115200"]
TITLE = "UWB capture"


def port_choices():
    """[(label, device)] with ST-LINK ports first."""
    items = []
    if ut.list_ports is None:
        return items
    for p in ut.list_ports.comports():
        if not up.is_board_port(p):
            continue                     # e.g. the Mac's own Bluetooth port
        description = p.description if (p.description and p.description != "n/a") else ""
        items.append((0 if up.is_stlink(p) else 1, "%s   %s" % (p.device, description), p.device))
    items.sort()
    return [(label, dev) for _, label, dev in items]


class BaseApp:
    """What the main window and the initiator window share: the board box, the output box,
    the message pump between the worker threads and the window, and closing."""

    role_name = "responder"

    def __init__(self, root):
        self.root = root
        self.settings = ut.load_settings()
        self.q = queue.Queue()
        self.runner = ur.TrialRunner(self.q)
        self.closing = False
        self.lock_widgets = []   # disabled while a trial runs

    # ---- pieces of the window
    def build_board_box(self, parent, title):
        box = ttk.LabelFrame(parent, text=title, padding=8)
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="COM port" if up.IS_WINDOWS else "Serial port").grid(row=0, column=0, sticky="w")
        self.v_port = tk.StringVar(value=self.settings.get("port", ""))
        self.cb_port = ttk.Combobox(box, textvariable=self.v_port, width=40)
        self.cb_port.grid(row=0, column=1, sticky="ew", padx=4)
        self.b_ports = ttk.Button(box, text="Refresh", width=8, command=self.refresh_ports)
        self.b_ports.grid(row=0, column=2)
        ttk.Label(box, text="Baud rate").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.v_baud = tk.StringVar(value=str(self.settings.get("baud", 1000000)))
        self.cb_baud = ttk.Combobox(box, textvariable=self.v_baud, values=BAUDS, width=12)
        self.cb_baud.grid(row=1, column=1, sticky="w", padx=4, pady=(4, 0))
        self.b_release = ttk.Button(box, text="Release port", command=self.release_port)
        self.b_release.grid(row=1, column=2, pady=(4, 0))
        self.v_conn = tk.StringVar(value="Not connected")
        ttk.Label(box, textvariable=self.v_conn, foreground=up.HINT).grid(row=2, column=0, columnspan=3, sticky="w",
                                                                         pady=(4, 0))
        self.lock_widgets += [self.cb_port, self.cb_baud, self.b_ports]
        return box

    def build_run_box(self, parent, title, start_text):
        box = ttk.LabelFrame(parent, text=title, padding=8)
        box.columnconfigure(2, weight=1)
        self.b_start = ttk.Button(box, text=start_text, command=self.start)
        self.b_start.grid(row=0, column=0, ipadx=10, ipady=4)
        self.b_stop = ttk.Button(box, text="Stop", command=self.stop)
        self.b_stop.grid(row=0, column=1, padx=6, ipadx=10, ipady=4)
        self.v_status = tk.StringVar(value="Idle")
        ttk.Label(box, textvariable=self.v_status, font=up.ui(0, True), wraplength=340,
                  justify="left").grid(row=0, column=2, sticky="w", padx=6)
        self.bar = ttk.Progressbar(box, mode="determinate", maximum=100)
        self.bar.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 2))
        self.v_counts = tk.StringVar(value="")
        ttk.Label(box, textvariable=self.v_counts).grid(row=2, column=0, columnspan=3, sticky="w")
        self.v_range = tk.StringVar(value="")
        ttk.Label(box, textvariable=self.v_range).grid(row=3, column=0, columnspan=3, sticky="w")
        return box

    def build_output_box(self, parent, height=18):
        box = ttk.LabelFrame(parent, text="Output", padding=4)
        box.columnconfigure(0, weight=1)
        box.rowconfigure(0, weight=1)
        self.txt = tk.Text(box, wrap="none", height=height, font=up.mono(), state="disabled")
        self.txt.grid(row=0, column=0, sticky="nsew")
        sy = ttk.Scrollbar(box, orient="vertical", command=self.txt.yview)
        sy.grid(row=0, column=1, sticky="ns")
        sx = ttk.Scrollbar(box, orient="horizontal", command=self.txt.xview)
        sx.grid(row=1, column=0, sticky="ew")
        self.txt.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        ttk.Button(box, text="Clear", command=self.clear_log).grid(row=2, column=0, sticky="e", pady=(4, 0))
        return box

    # ---- help
    help_text = None  # None = the main window's help

    def show_help(self):
        """A window with the instructions: list of sections on the left, text on the right."""
        win = tk.Toplevel(self.root)
        win.title("Help - how to use this")
        win.minsize(980, 620)
        win.columnconfigure(1, weight=1)
        win.rowconfigure(0, weight=1)
        parts = uwb_help.sections(self.help_text)
        lb = tk.Listbox(win, width=38, activestyle="none", exportselection=False)
        lb.grid(row=0, column=0, sticky="ns", padx=(8, 4), pady=8)
        frame = ttk.Frame(win)
        frame.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        txt = tk.Text(frame, wrap="none", font=up.mono(1), padx=10, pady=8)
        txt.grid(row=0, column=0, sticky="nsew")
        sy = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
        sy.grid(row=0, column=1, sticky="ns")
        txt.configure(yscrollcommand=sy.set)
        txt.tag_configure("title", font=up.ui(3, True), spacing1=14, spacing3=6)
        for k, (title, lines) in enumerate(parts):
            lb.insert("end", title)
            txt.mark_set("sec%d" % k, "end-1c")
            txt.mark_gravity("sec%d" % k, "left")
            txt.insert("end", title + "\n", "title")
            txt.insert("end", "\n".join(lines).strip("\n") + "\n\n")
        txt.configure(state="disabled")

        def jump(event=None):
            sel = lb.curselection()
            if sel:
                txt.see("end")                 # then scrolling back up leaves the section at the top
                txt.see("sec%d" % sel[0])

        lb.bind("<<ListboxSelect>>", jump)
        return win, lb, txt

    # ---- output box
    def log(self, text):
        self.q.put(("log", str(text).strip("\r\n")))

    def _append(self, text):
        self.txt.configure(state="normal")
        self.txt.insert("end", text + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def clear_log(self):
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.configure(state="disabled")

    # ---- board
    def refresh_ports(self):
        items = port_choices()
        self.cb_port.configure(values=[label for label, _ in items])
        current = self.port()
        devices = [dev for _, dev in items]
        if current in devices:
            self.v_port.set(items[devices.index(current)][0])
        elif len(items) == 1 or (items and not current):
            self.v_port.set(items[0][0])

    def port(self):
        text = self.v_port.get().strip()
        return text.split()[0] if text else ""

    def read_board_fields(self):
        """Returns an error text or None."""
        if not self.port():
            return "Choose the board's serial port (for example %s)." % up.PORT_EXAMPLE
        try:
            baud = int(self.v_baud.get())
        except ValueError:
            return "The baud rate must be a number."
        if ut.serial is None:
            return "pyserial is not installed.\nRun:  pip install pyserial"
        self.settings["port"] = self.port()
        self.settings["baud"] = baud
        self.settings["role"] = self.role_name
        return None

    def release_port(self):
        if self.runner.busy:
            return
        self.runner.release()
        self.v_conn.set("Not connected (port released)")
        self.set_state()

    # ---- running
    def begin_run(self):
        self.bar.configure(mode="indeterminate")
        self.bar.start(60)
        self.v_counts.set("")
        self.v_range.set("")
        self.v_status.set("Connecting...")

    def stop(self):
        if self.runner.busy:
            self.runner.stop()
            self.v_status.set("Stopping (the other board is told over UWB)...")

    def set_state(self):
        idle = not self.runner.busy
        for w in self.lock_widgets:
            try:
                w.configure(state="normal" if idle else "disabled")
            except tk.TclError:
                pass
        self.b_start.configure(state="normal" if idle else "disabled")
        self.b_stop.configure(state="disabled" if idle else "normal")
        self.b_release.configure(state="normal" if (idle and self.runner.link is not None) else "disabled")

    def show_progress(self, d):
        if d is None:
            self.bar.configure(mode="indeterminate")
            self.bar.start(60)
            self.v_counts.set("")
            self.v_range.set("")
            return
        done = d["n_ok"] + d["n_fail"]
        target = d.get("target") or 0
        if done == 0:
            return
        if not self.runner.stop_event.is_set():
            self.v_status.set("Ranging - trial %s" % (d.get("trial_id") or ""))
        if target:
            self.bar.stop()
            self.bar.configure(mode="determinate", maximum=target, value=min(d["n_ok"], target))
        self.v_counts.set("%d%s exchanges ok,  %d failed" % (d["n_ok"], ("/%d" % target) if target else "", d["n_fail"]))
        if d.get("last_m") is not None:
            off = self.live_offset(d)
            if off is None:
                text = "range (not calibrated): last %.3f m   mean %.3f m" % (d["last_m"], d["mean_m"])
            else:
                text = "range (calibrated): last %.3f m   mean %.3f m" % (d["last_m"] - off, d["mean_m"] - off)
            if d.get("sd_m") is not None:
                text += "   sd %.3f m" % d["sd_m"]
            self.v_range.set(text)

    def live_offset(self, d):
        """Calibration offset for the running trial, if this board has one (None otherwise)."""
        return None

    # ---- hooks for the subclasses
    def on_saved(self, path):
        pass

    def on_idle(self, last_file):
        pass

    def on_other(self, kind, value):
        pass

    # ---- message pump / closing
    def pump(self):
        try:
            while True:
                kind, value = self.q.get_nowait()
                if kind == "log":
                    self._append(value)
                elif kind == "status":
                    self.v_status.set(value)
                elif kind == "conn":
                    self.v_conn.set(value)
                elif kind == "progress":
                    self.show_progress(value)
                elif kind == "saved":
                    self.on_saved(value)
                elif kind == "error":
                    first_line = value.strip().splitlines()[0] if value.strip() else "error"
                    self.v_status.set("Error: " + first_line)
                elif kind == "idle":
                    self.bar.stop()
                    self.bar.configure(mode="determinate", value=0)
                    if not self.v_status.get().startswith("Error"):
                        self.v_status.set("Idle" if value is None else "Done: saved %s" % os.path.basename(value))
                    self.on_idle(value)
                    self.set_state()
                else:
                    self.on_other(kind, value)
        except queue.Empty:
            pass
        if not self.closing:
            self.root.after(80, self.pump)

    def save_fields(self):
        pass

    def on_close(self):
        if self.closing:
            return
        try:
            self.save_fields()
        except Exception:
            pass
        if self.runner.busy:
            if not messagebox.askyesno(TITLE, "A trial is running. Stop it and close?"):
                return
            self.stop()
            self._wait_close(time.monotonic() + 10.0)
        else:
            self._finish_close()

    def _wait_close(self, deadline):
        if self.runner.busy and time.monotonic() < deadline:
            self.root.after(100, lambda: self._wait_close(deadline))
        else:
            self._finish_close()

    def _finish_close(self):
        self.closing = True
        self.runner.release()
        self.root.destroy()


class MainApp(BaseApp):
    role_name = "responder"

    def __init__(self, root):
        super().__init__(root)
        self.analysing = False
        self.files = []
        self.print_lock = threading.Lock()
        self.current_setup = None   # setup id of the running trial
        data_dir = self.settings.get("data_dir", "data")
        if not os.path.isabs(data_dir):
            data_dir = os.path.join(HERE, data_dir)
        self.data_dir = os.path.normpath(data_dir)
        self.store = us.SetupStore(self.data_dir)

        root.title("UWB capture - main PC (responder board)")
        root.minsize(1040, 680)
        self._build()
        self.refresh_ports()
        self.refresh_setups(self.settings.get("gui_setup"))
        self.refresh_files()
        self.set_state()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        if up.IS_MAC:
            root.createcommand("tk::mac::Quit", self.on_close)   # Cmd+Q: stop the trial, release the port
        root.after(80, self.pump)
        if ua is None:
            self.log("Analysis is switched off because numpy is missing. Fix with:  pip install numpy matplotlib")
        if ut.serial is None:
            self.log("pyserial is not installed, so no board can be reached. Fix with:  pip install pyserial")
        if not self.store.all():
            self.log("Start by pressing 'New setup...' to describe what you are about to measure.")

    # ------------------------------------------------------------------ layout
    def _build(self):
        root = self.root
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)
        left = ttk.Frame(root, padding=8)
        left.grid(row=0, column=0, sticky="nsew")
        right = ttk.Frame(root, padding=(0, 8, 8, 8))
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.build_board_box(left, "1. Responder board (this PC)").grid(row=0, column=0, sticky="ew")

        # ---- setup
        box = ttk.LabelFrame(left, text="2. What is being measured", padding=8)
        box.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="Setup").grid(row=0, column=0, sticky="w")
        self.v_setup = tk.StringVar()
        self.cb_setup = ttk.Combobox(box, textvariable=self.v_setup, state="readonly", width=46)
        self.cb_setup.grid(row=0, column=1, columnspan=2, sticky="ew", padx=4)
        self.cb_setup.bind("<<ComboboxSelected>>", lambda e: self.setup_changed())
        bf = ttk.Frame(box)
        bf.grid(row=1, column=1, columnspan=2, sticky="w", padx=4, pady=(4, 0))
        self.b_new = ttk.Button(bf, text="New setup...", command=lambda: self.setup_dialog(None))
        self.b_new.grid(row=0, column=0)
        self.b_copy = ttk.Button(bf, text="New from this one...", command=lambda: self.setup_dialog("copy"))
        self.b_copy.grid(row=0, column=1, padx=4)
        self.b_edit = ttk.Button(bf, text="Edit...", command=lambda: self.setup_dialog("edit"))
        self.b_edit.grid(row=0, column=2)
        self.v_setup_info = tk.StringVar()
        ttk.Label(box, textvariable=self.v_setup_info, foreground=up.SOFT, wraplength=430, justify="left").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))
        pf = ttk.Frame(box)
        pf.grid(row=3, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self.v_place = tk.StringVar()
        ttk.Label(pf, textvariable=self.v_place).grid(row=0, column=0, sticky="w")
        self.b_moved = ttk.Button(pf, text="Boards were moved", command=self.boards_moved)
        self.b_moved.grid(row=0, column=1, padx=8)
        ttk.Label(box, text="Same setup and same placement = repeats of the same measurement.",
                  foreground=up.HINT).grid(row=4, column=0, columnspan=3, sticky="w")
        self.lock_widgets += [self.cb_setup, self.b_new, self.b_copy, self.b_edit, self.b_moved]

        # ---- trial
        box = ttk.LabelFrame(left, text="3. Trial", padding=8)
        box.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="Number of exchanges").grid(row=0, column=0, sticky="w")
        self.v_count = tk.StringVar(value=str(self.settings.get("responder_count", 100) or 100))
        e = ttk.Entry(box, textvariable=self.v_count, width=10)
        e.grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(box, text="0 = until Stop", foreground=up.HINT).grid(row=0, column=2, sticky="w")
        ttk.Label(box, text="Notes for this trial").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.v_notes = tk.StringVar()
        e2 = ttk.Entry(box, textvariable=self.v_notes)
        e2.grid(row=1, column=1, columnspan=2, sticky="ew", padx=4, pady=(4, 0))
        ttk.Label(box, text="Data folder").grid(row=2, column=0, sticky="w", pady=(4, 0))
        df = ttk.Frame(box)
        df.grid(row=2, column=1, columnspan=2, sticky="ew", padx=4, pady=(4, 0))
        df.columnconfigure(0, weight=1)
        self.v_dir = tk.StringVar(value=self.data_dir)
        ttk.Label(df, textvariable=self.v_dir, foreground=up.SOFT).grid(row=0, column=0, sticky="w")
        self.b_dir = ttk.Button(df, text="Change...", command=self.browse_dir)
        self.b_dir.grid(row=0, column=1, padx=(4, 0))
        self.lock_widgets += [e, e2, self.b_dir]

        self.build_run_box(left, "4. Run", "Start trial").grid(row=3, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(left, text="The initiator PC only needs its window started once (%s).\n" % up.LAUNCHERS[1] +
                             "It does not matter which side is started first.", foreground=up.HINT,
                  justify="left").grid(row=4, column=0, sticky="w", pady=(6, 0))
        ttk.Button(left, text="Help: how to use this, what the buttons do, how to read the output",
                   command=self.show_help).grid(row=5, column=0, sticky="ew", pady=(8, 0), ipady=3)

        # ---- files + analysis
        box = ttk.LabelFrame(right, text="Saved trials (newest first)", padding=8)
        box.grid(row=0, column=0, sticky="ew")
        box.columnconfigure(0, weight=1)
        lf = ttk.Frame(box)
        lf.grid(row=0, column=0, sticky="ew")
        lf.columnconfigure(0, weight=1)
        self.lb = tk.Listbox(lf, height=8, selectmode="extended", exportselection=False, activestyle="none")
        self.lb.grid(row=0, column=0, sticky="ew")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.lb.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.lb.configure(yscrollcommand=sb.set)
        self.analysis_buttons = []

        def button(parent, text, cmd, col):
            b = ttk.Button(parent, text=text, command=cmd)
            b.grid(row=0, column=col, padx=(0, 4))
            self.analysis_buttons.append(b)

        b1 = ttk.Frame(box)
        b1.grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(b1, text="Selected trial:", width=14).grid(row=0, column=0)
        button(b1, "View CIRs", self.do_view, 1)
        button(b1, "Analyze + report", self.do_report, 2)
        button(b1, "Suspect CIRs to PDF", self.do_plot_suspects, 3)
        button(b1, "All CIRs to PDF", self.do_plot_cirs, 4)
        b1b = ttk.Frame(box)
        b1b.grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Label(b1b, text="", width=14).grid(row=0, column=0)
        button(b1b, "Compare its setup", self.do_compare, 1)
        button(b1b, "Calibrate", self.do_calibrate, 2)
        button(b1b, "Overview picture", self.do_plot, 3)
        button(b1b, "Export CSV", self.do_csv, 4)
        ttk.Label(b1b, text="   Suspect PDF: at most").grid(row=0, column=5)
        self.v_limit = tk.StringVar(value=str(self.settings.get("gui_suspect_limit", 40)))
        ttk.Entry(b1b, textvariable=self.v_limit, width=5).grid(row=0, column=6, padx=4)
        ttk.Label(b1b, text="exchanges").grid(row=0, column=7)
        b2 = ttk.Frame(box)
        b2.grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Label(b2, text="Whole folder:", width=14).grid(row=0, column=0)
        button(b2, "Import other PC's files...", self.do_import, 1)
        button(b2, "Summary of all setups", self.do_summary, 2)
        button(b2, "Export ML dataset", self.do_dataset, 3)
        ttk.Button(b2, text="Open folder", command=self.open_folder).grid(row=0, column=4, padx=(0, 4))
        ttk.Button(b2, text="Refresh", command=self.refresh_files).grid(row=0, column=5)
        b3 = ttk.Frame(box)
        b3.grid(row=4, column=0, sticky="w", pady=(6, 0))
        ttk.Label(b3, text="Filter for summary / dataset:").grid(row=0, column=0)
        self.v_filter = tk.StringVar()
        ttk.Entry(b3, textvariable=self.v_filter, width=30).grid(row=0, column=1, padx=4)
        ttk.Label(b3, text="e.g.  site=lab condition=nlos", foreground=up.HINT).grid(row=0, column=2)
        self.v_drop = tk.BooleanVar(value=False)
        ttk.Checkbutton(box, text="Leave flagged (abnormal) exchanges out of compare / summary",
                        variable=self.v_drop).grid(row=5, column=0, sticky="w", pady=(4, 0))

        self.build_output_box(right).grid(row=1, column=0, sticky="nsew", pady=(8, 0))

    # ------------------------------------------------------------------ setups
    def setup_id(self):
        return us.SetupStore.id_from_label(self.v_setup.get())

    def refresh_setups(self, select=None):
        setups = self.store.all()
        labels = [self.store.label(s) for s in setups]
        self.cb_setup.configure(values=labels)
        ids = [s["id"] for s in setups]
        want = select if select in ids else (self.setup_id() if self.setup_id() in ids else (ids[-1] if ids else None))
        self.v_setup.set(labels[ids.index(want)] if want else "")
        self.setup_changed()

    def setup_changed(self):
        s = self.store.get(self.setup_id()) if self.setup_id() else None
        if s is None:
            self.v_setup_info.set("No setup yet: press 'New setup...'")
            self.v_place.set("")
            return
        bits = []
        for key, label, _ in us.FIELDS:
            if key in ("name",):
                continue
            v = s.get(key)
            if v not in (None, ""):
                bits.append("%s: %s" % (label, ("%g" % v) if isinstance(v, float) else v))
        ns = uc.floor_bounce_ns(s.get("distance_m"), s.get("antenna_height_m"))
        if ns is not None:
            bits.append("Floor reflection arrives %.1f ns after the direct path%s"
                        % (ns, "  - it MERGES with the direct path (under 2 ns)" if ns < 2.0 else " (separate from it)"))
        self.v_setup_info.set("\n".join(bits))
        place = self.store.next_placement(s["id"])
        n = s.get("trials_this_placement", 0) if place == s.get("placement", 1) else 0
        self.v_place.set("Placement %d   (%d trial%s so far in this placement, %d in this setup)"
                         % (place, n, "" if n == 1 else "s", s.get("trials", 0)))

    def boards_moved(self):
        sid = self.setup_id()
        if sid:
            self.store.boards_moved(sid)
            self.setup_changed()

    def setup_dialog(self, mode):
        """mode: None = new and empty, 'copy' = new, pre-filled from the current one, 'edit'."""
        current = self.store.get(self.setup_id()) if self.setup_id() else None
        if mode in ("copy", "edit") and current is None:
            mode = None
        win = tk.Toplevel(self.root)
        win.title("Edit setup %s" % current["id"] if mode == "edit" else "New setup")
        win.transient(self.root)
        frame = ttk.Frame(win, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        variables = {}
        for r, (key, label, kind) in enumerate(us.FIELDS):
            ttk.Label(frame, text=label).grid(row=r, column=0, sticky="w", pady=3)
            value = ""
            if mode in ("copy", "edit"):
                v = current.get(key)
                value = "" if v is None else (("%g" % v) if isinstance(v, float) else str(v))
                if mode == "copy" and key == "name":
                    value = ""
            var = tk.StringVar(value=value)
            variables[key] = var
            if kind == "choice":
                w = ttk.Combobox(frame, textvariable=var, values=us.CONDITIONS, width=22)
                if not value:
                    var.set(us.CONDITIONS[0])
            else:
                w = ttk.Entry(frame, textvariable=var, width=14 if kind == "float" else 44)
            w.grid(row=r, column=1, sticky="w" if kind != "text" else "ew", padx=6, pady=3)
        hint = ("Changing a setup does not change trials already saved: each file keeps its own copy of these fields."
                if mode == "edit" else
                "One setup = one thing you intend to measure. Anything different (distance, blockage, orientation,\n"
                "room) is a new setup. Orientation is free text, e.g. 'facing each other' or 'responder turned 90 deg'.")
        ttk.Label(frame, text=hint, foreground=up.HINT, justify="left").grid(row=len(us.FIELDS), column=0, columnspan=2,
                                                                         sticky="w", pady=(8, 4))
        bf = ttk.Frame(frame)
        bf.grid(row=len(us.FIELDS) + 1, column=0, columnspan=2, sticky="e", pady=(6, 0))
        ttk.Button(bf, text="Save", command=lambda: self.save_setup(win, variables, current["id"] if mode == "edit" else None)
                   ).grid(row=0, column=0, padx=4)
        ttk.Button(bf, text="Cancel", command=win.destroy).grid(row=0, column=1)
        try:
            win.grab_set()
        except tk.TclError:
            pass
        return win, variables

    def save_setup(self, win, variables, edit_id):
        fields, err = us.SetupStore.clean({k: v.get() for k, v in variables.items()})
        if err:
            messagebox.showerror(TITLE, err)
            return
        if edit_id:
            s = self.store.update(edit_id, fields)
        else:
            s = self.store.add(fields)
        win.destroy()
        self.refresh_setups(s["id"])

    # ------------------------------------------------------------------ trial
    def browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.data_dir)
        if d:
            self.data_dir = os.path.normpath(d)
            self.v_dir.set(self.data_dir)
            self.store = us.SetupStore(self.data_dir)
            self.refresh_setups()
            self.refresh_files()

    def save_fields(self):
        self.settings["data_dir"] = self.data_dir
        self.settings["gui_setup"] = self.setup_id()
        try:
            self.settings["responder_count"] = int(self.v_count.get() or 0)
        except ValueError:
            pass
        if self.port():
            self.settings["port"] = self.port()
        ut.save_settings(self.settings)

    def start(self):
        if self.runner.busy:
            return
        err = self.read_board_fields()
        sid = self.setup_id()
        if not err and not sid:
            err = "Create a setup first: press 'New setup...'."
        count = 0
        if not err:
            try:
                count = int(self.v_count.get() or 0)
                if count < 0 or count > 65535:
                    raise ValueError
            except ValueError:
                err = "Number of exchanges must be 0..65535."
        if err:
            messagebox.showerror(TITLE, err)
            return
        self.settings["responder_count"] = count
        self.save_fields()
        meta = self.store.begin_trial(sid)
        meta["notes"] = self.v_notes.get().strip()
        s = self.store.get(sid)
        stem = self.store.file_stem(s)
        data_dir = self.data_dir
        self.current_setup = sid
        self.setup_changed()
        self.begin_run()
        snapshot = ut.json.loads(ut.json.dumps(self.settings))
        self.log("-" * 60)
        self.log("Trial of %s, placement %s, %s exchanges"
                 % (us.setup_title(meta), meta["placement"], count if count else "unlimited"))
        self.runner.start(snapshot, "responder", meta, lambda trial: ur.next_free(data_dir, stem, "responder"))
        self.set_state()

    def live_offset(self, d):
        if not d.get("device") or not d.get("params"):
            return None
        try:
            cal = uc.load_cached(self.data_dir)
            return uc.offset_for(cal, {"role": "responder", "device": d["device"], "params": d["params"]})[0]
        except Exception:
            return None

    def on_saved(self, path):
        if self.current_setup:
            self.store.trial_saved(self.current_setup)
            self.current_setup = None
        self.setup_changed()
        self.refresh_files(select=path)

    def on_idle(self, last_file):
        self.current_setup = None
        self.v_notes.set("")

    def set_state(self):
        super().set_state()
        if not self.runner.busy:
            self.cb_setup.configure(state="readonly")
        ok = (ua is not None) and not self.analysing
        for b in self.analysis_buttons:
            b.configure(state="normal" if ok else "disabled")

    # ------------------------------------------------------------------ files
    def refresh_files(self, select=None):
        paths = []
        try:
            for name in os.listdir(self.data_dir):
                if name.lower().endswith(".json") and name not in ("setups.json", uc.FILE_NAME):
                    paths.append(os.path.join(self.data_dir, name))
        except OSError:
            pass

        def mtime(p):
            try:
                return os.path.getmtime(p)
            except OSError:
                return 0.0

        paths.sort(key=mtime, reverse=True)
        keep = [os.path.abspath(select)] if select else [os.path.abspath(p) for p in self.selected()]
        self.files = paths
        self.lb.delete(0, "end")
        for p in paths:
            self.lb.insert("end", os.path.basename(p))
        self.lb.selection_clear(0, "end")
        for k, p in enumerate(paths):
            if os.path.abspath(p) in keep:
                self.lb.selection_set(k)
                self.lb.see(k)

    def selected(self):
        return [self.files[k] for k in self.lb.curselection() if k < len(self.files)]

    def open_folder(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            up.open_path(self.data_dir)
        except Exception as exc:
            self.log("Could not open %s: %s" % (self.data_dir, exc))

    # ------------------------------------------------------------------ analysis
    def _run_analysis(self, title, func):
        """Run func() in a thread, capture what it prints and show it in the output box."""
        if ua is None:
            messagebox.showerror(TITLE, "Analysis needs numpy:\n  pip install numpy matplotlib")
            return
        if self.analysing:
            return
        self.analysing = True
        self.set_state()
        self.log("=" * 60)
        self.log(title)

        def work():
            buf = io.StringIO()
            result = None
            try:
                with self.print_lock, contextlib.redirect_stdout(buf):
                    result = func()
            except ImportError as exc:
                buf.write("\nMissing Python package: %s\n  Fix with:  pip install numpy matplotlib\n" % exc)
            except (ValueError, RuntimeError) as exc:
                buf.write("\n%s\n" % exc)
            except Exception:
                buf.write("\nERROR:\n" + traceback.format_exc())
            text = buf.getvalue().rstrip()
            if text:
                self.log(text)
            self.q.put(("analysed", result))

        threading.Thread(target=work, daemon=True).start()

    def on_other(self, kind, value):
        if kind == "analysed":
            self.analysing = False
            self.set_state()
            if isinstance(value, tuple) and value[0] == "calib":
                proposal, folder = value[1], value[2]
                n = len(proposal["pairs"])
                if messagebox.askyesno(TITLE, "Save this calibration (%d board pair%s)?\n\n"
                                              "Read the result in the Output box first. Saving changes no trial file "
                                              "and nothing in the boards; analysis will show calibrated values next to "
                                              "the raw ones." % (n, "" if n == 1 else "s")):
                    path, cal = uc.apply(folder, proposal)
                    self.log("Calibration saved in %s" % path)
                    self.log("\n".join(uc.describe(cal)))
                else:
                    self.log("Calibration not saved.")
            if isinstance(value, tuple) and value[0] == "open":
                for out in value[1]:
                    try:
                        up.open_path(out)  # the picture, PDF or report, in the system's own viewer
                    except Exception:
                        pass
            self.refresh_files()

    def _need_selection(self):
        files = self.selected()
        if not files:
            messagebox.showinfo(TITLE, "Select one or more trials in the list first.")
        return files

    def do_report(self):
        files = self._need_selection()
        if files:
            def work():
                outs = []
                for f in files:
                    ua.report(f)
                    out = ua.write_report(f)
                    print("\nReport file (opens in your browser, can be e-mailed as it is): %s" % out)
                    outs.append(out)
                return ("open", outs)

            self._run_analysis("Analyze: " + ", ".join(os.path.basename(f) for f in files), work)

    def do_plot(self):
        files = self._need_selection()
        if not files:
            return

        def work():
            outs = [ua.plot(f) for f in files]
            for out in outs:
                print("wrote", out)
            return ("open", outs)

        self._run_analysis("Overview plot: " + ", ".join(os.path.basename(f) for f in files), work)

    def do_plot_cirs(self):
        files = self._need_selection()
        if not files:
            return

        def work():
            outs = []
            for f in files:
                self.log("Drawing every CIR of %s (about a third of a second per exchange; \"View CIRs\" is instant)..."
                         % os.path.basename(f))
                out = ua.plot_cirs(f, progress=self.log)
                print("wrote", out, " (one page per exchange: poll, response, final)")
                outs.append(out)
            return ("open", outs)

        self._run_analysis("Plot all CIRs: " + ", ".join(os.path.basename(f) for f in files), work)

    def do_view(self):
        """Open the instant CIR viewer on the selected trial (nothing is written, no waiting)."""
        files = self._need_selection()
        if not files:
            return
        if ua is None:
            messagebox.showerror(TITLE, "The viewer needs numpy:\n  pip install numpy")
            return
        try:
            import uwb_viewer
            self.viewer = uwb_viewer.CirViewer(self.root, files[0])
        except Exception as exc:
            self.log("Could not open the viewer on %s: %s" % (os.path.basename(files[0]), exc))
            self.log(traceback.format_exc())
            return
        if len(files) > 1:
            self.log("The viewer shows one trial at a time: opened %s." % os.path.basename(files[0]))

    def do_plot_suspects(self):
        files = self._need_selection()
        if not files:
            return
        try:
            limit = max(1, int(self.v_limit.get() or 40))
        except ValueError:
            limit = 40
        self.settings["gui_suspect_limit"] = limit

        def work():
            outs = []
            for f in files:
                trial = ua.load_trial(f)
                found = ua.suspects(trial, ua.cal_offset(f, trial))
                n_ok = len(ua.ok_exchanges(trial))
                name = os.path.basename(f)
                if not found:
                    print("%s: none of the %d exchanges shows a sign of a direct-path miss." % (name, n_ok))
                    continue
                print("%s: %d of %d exchanges picked%s" % (name, len(found), n_ok,
                      (", plotting the %d most suspicious" % limit) if len(found) > limit else ""))
                for s in found[:limit]:
                    print("   %-5d score %4.1f   %s" % (s["xid"], s["score"], "; ".join(s["reasons"])))
                out = ua.plot_cirs(f, progress=self.log, only="suspect", limit=limit)
                if out:
                    print("wrote", out, " (page 1 lists them; then one page per exchange)")
                    outs.append(out)
            return ("open", outs)

        self._run_analysis("Plot suspect CIRs (where the first path may not be the direct path)", work)

    def do_csv(self):
        files = self._need_selection()
        if files:
            self._run_analysis("Export CSV", lambda: [print("wrote", ua.export_csv(f)) for f in files] and None)

    def do_calibrate(self):
        files = self.selected()
        folder = self.data_dir
        if not files:
            self.log("=" * 60)
            self.log("\n".join(uc.describe(uc.load(folder))))
            self.log("To calibrate: select line-of-sight trials taken at a known distance (merged files), then press"
                     " Calibrate.\nHelp, section 9, has the procedure.")
            return

        def work():
            proposal = ua.calibrate(files, save=False)
            return ("calib", proposal, folder) if proposal else None

        self._run_analysis("Calibrate (antenna delay) from: " + ", ".join(os.path.basename(f) for f in files), work)

    def do_compare(self):
        files = self.selected()
        key = None
        if files:
            try:
                key = us.setup_key(ua.load_trial(files[0]).get("meta"))
            except Exception:
                key = None
        if key is None and self.setup_id():
            key = self.setup_id()
        if key is None:
            messagebox.showinfo(TITLE, "Select a trial in the list (or choose a setup) first.")
            return
        drop = bool(self.v_drop.get())
        folder = self.data_dir

        def work():
            rows = ua.compare([folder], drop_flagged=drop, setup=key)
            if not rows:
                print("No completed exchanges found for this setup in this folder.")

        self._run_analysis("Compare the trials of %s%s" % (key, " without flagged exchanges" if drop else ""), work)

    def do_summary(self):
        folder, drop, flt = self.data_dir, bool(self.v_drop.get()), us.parse_filter(self.v_filter.get())
        self._run_analysis("Summary of all setups%s" % (("  [filter: %s]" % self.v_filter.get().strip()) if flt else ""),
                           lambda: ua.summary([folder], flt, drop) and None)

    def do_dataset(self):
        folder, flt = self.data_dir, us.parse_filter(self.v_filter.get())
        out = os.path.join(folder, "dataset_%s.npz" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))

        def work():
            ua.export_dataset([folder], out, flt)
            print("\nHow to load it:\n" + ua.DATASET_HELP)

        self._run_analysis("Export ML dataset from %s" % folder, work)

    def do_import(self):
        src = filedialog.askdirectory(title="Folder with the other PC's trial files (e.g. the USB stick)",
                                      initialdir=self.settings.get("gui_import_dir") or self.data_dir)
        if not src:
            return
        self.settings["gui_import_dir"] = src
        folder = self.data_dir
        self._run_analysis("Import from %s" % src, lambda: ur.import_trials(src, folder) and None)


def main():
    root = tk.Tk()
    up.use_native_theme(ttk)
    MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
