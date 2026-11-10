#!/usr/bin/env python3
"""
uwb_gui_initiator.py - the small window for the PC of the INITIATOR board.

    Windows: double-click "UWB Initiator.bat"      Mac: double-click "UWB Initiator.command"
    (or, on either:  python uwb_gui_initiator.py   /   python3 uwb_gui_initiator.py)

Choose the COM port and press Start once. From then on the board keeps calling the
main (responder) board and serves every trial that is started there: the trial length
and what is being measured are decided on the main PC. Each trial's response CIRs are
saved in the data folder; copy that folder to a USB stick and use "Import other PC's
files" in the main window to join them with the poll and final CIRs.

Needs: pip install pyserial            (numpy optional; tkinter comes with Python)
"""

import os
import sys

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import uwb_gui as base
import uwb_help
import uwb_platform as up
import uwb_tool as ut

TITLE = "UWB initiator"


class InitiatorApp(base.BaseApp):
    role_name = "initiator"
    help_text = uwb_help.INITIATOR_HELP

    def __init__(self, root):
        super().__init__(root)
        self.saved = 0
        data_dir = self.settings.get("data_dir", "data")
        if not os.path.isabs(data_dir):
            data_dir = os.path.join(HERE, data_dir)
        self.data_dir = os.path.normpath(data_dir)

        root.title("UWB initiator board")
        root.minsize(560, 560)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main = ttk.Frame(root, padding=8)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(4, weight=1)

        self.build_board_box(main, "1. Initiator board (this PC)").grid(row=0, column=0, sticky="ew")

        adv = self.settings["advanced"]
        box = ttk.LabelFrame(main, text="CIR capture (decided here for both boards) - leave as is for the full CIR",
                             padding=8)
        box.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.v_cstart = tk.StringVar(value=str(adv.get("cir_start", 0)))
        self.v_clen = tk.StringVar(value=str(adv.get("cir_len", 0)))
        self.v_chan = tk.StringVar(value=str(adv["radio"].get("chan", 9)))
        ttk.Label(box, text="First sample").grid(row=0, column=0, sticky="w")
        e1 = ttk.Entry(box, textvariable=self.v_cstart, width=7)
        e1.grid(row=0, column=1, padx=4)
        ttk.Label(box, text="Samples (0 = all 1016)").grid(row=0, column=2, sticky="w", padx=(8, 0))
        e2 = ttk.Entry(box, textvariable=self.v_clen, width=7)
        e2.grid(row=0, column=3, padx=4)
        ttk.Label(box, text="Channel (same as main PC)").grid(row=0, column=4, sticky="w", padx=(8, 0))
        e3 = ttk.Combobox(box, textvariable=self.v_chan, values=["5", "9"], width=4)
        e3.grid(row=0, column=5, padx=4)

        box = ttk.Frame(main)
        box.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="Data folder").grid(row=0, column=0, sticky="w")
        self.v_dir = tk.StringVar(value=self.data_dir)
        ttk.Label(box, textvariable=self.v_dir, foreground=up.SOFT).grid(row=0, column=1, sticky="w", padx=6)
        self.b_dir = ttk.Button(box, text="Change...", command=self.browse_dir)
        self.b_dir.grid(row=0, column=2)
        ttk.Button(box, text="Open folder", command=self.open_folder).grid(row=0, column=3, padx=(4, 0))
        self.lock_widgets += [e1, e2, e3, self.b_dir]

        self.build_run_box(main, "2. Run", "Start").grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.build_output_box(main, height=12).grid(row=4, column=0, sticky="nsew", pady=(8, 0))
        ttk.Label(main, text="Press Start once and leave it running. Trials are started and stopped on the main PC.\n"
                             "Afterwards copy the data folder to a USB stick for the main PC.", foreground=up.HINT,
                  justify="left").grid(row=5, column=0, sticky="w", pady=(6, 0))
        ttk.Button(main, text="Help", command=self.show_help).grid(row=6, column=0, sticky="e", pady=(4, 0))

        self.refresh_ports()
        self.set_state()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        if up.IS_MAC:
            root.createcommand("tk::mac::Quit", self.on_close)   # Cmd+Q: stop, release the port
        root.after(80, self.pump)
        if ut.serial is None:
            self.log("pyserial is not installed, so no board can be reached. Fix with:  pip install pyserial")

    def browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.data_dir)
        if d:
            self.data_dir = os.path.normpath(d)
            self.v_dir.set(self.data_dir)

    def open_folder(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            up.open_path(self.data_dir)
        except Exception as exc:
            self.log("Could not open %s: %s" % (self.data_dir, exc))

    def save_fields(self):
        self.settings["data_dir"] = self.data_dir
        if self.port():
            self.settings["port"] = self.port()
        ut.save_settings(self.settings)

    def start(self):
        if self.runner.busy:
            return
        err = self.read_board_fields()
        if not err:
            try:
                cstart = int(self.v_cstart.get() or 0)
                clen = int(self.v_clen.get() or 0)
                chan = int(self.v_chan.get())
                if chan not in (5, 9) or cstart < 0 or clen < 0 or cstart + clen > 1016:
                    raise ValueError
            except ValueError:
                err = "Channel must be 5 or 9 and the CIR window must fit in samples 0..1015."
        if err:
            messagebox.showerror(TITLE, err)
            return
        adv = self.settings["advanced"]
        adv["cir_start"], adv["cir_len"] = cstart, clen
        adv["radio"]["chan"] = chan
        self.settings["count"] = 0          # the main PC decides how long a trial is
        self.save_fields()
        self.begin_run()
        snapshot = ut.json.loads(ut.json.dumps(self.settings))
        data_dir = self.data_dir

        def path_for(trial):
            stamp = (trial.get("started") or "")[:19].replace("-", "").replace(":", "").replace("T", "_")
            name = "initiator_%s_%s.json" % (stamp, trial.get("trial_id") or "trial")
            return os.path.join(data_dir, name)

        self.runner.start(snapshot, "initiator", {}, path_for, repeat=True, keep_empty=False)
        self.set_state()

    def on_saved(self, path):
        self.saved += 1
        self.log("%d trial file%s saved in this session." % (self.saved, "" if self.saved == 1 else "s"))

    def on_idle(self, last_file):
        if not self.v_status.get().startswith("Error"):
            self.v_status.set("Stopped. Press Start to serve trials again.")


def main():
    root = tk.Tk()
    up.use_native_theme(ttk)
    InitiatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
