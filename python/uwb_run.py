#!/usr/bin/env python3
"""
uwb_run.py - the part of the windows that talks to a board: keeps the serial port open
between trials, runs trials in a background thread and reports through a queue.
No window code in here, so it can be tested without a display.

Events put on the queue, as (kind, value):
    ("log", text)  ("status", text)  ("conn", text)  ("progress", dict or None)
    ("saved", path)  ("error", text)  ("idle", last saved path or None)
"""

import os
import shutil
import threading
import time
import traceback

import uwb_tool as ut

try:
    import uwb_analyze as ua
except Exception:  # numpy missing: capture still works, analysis does not
    ua = None


def next_free(data_dir, stem, role_name):
    n = 1
    while True:
        name = "%s_%03d_%s.json" % (stem, n, role_name)
        if not os.path.exists(os.path.join(data_dir, name)):
            return os.path.join(data_dir, name)
        n += 1


class TrialRunner:
    def __init__(self, q):
        self.q = q
        self.link = None
        self.link_key = None
        self.busy = False
        self.stop_event = threading.Event()
        self.stop_all = False

    def log(self, text):
        self.q.put(("log", str(text).strip("\r\n")))

    # ---- port
    def release(self):
        if self.link is not None:
            try:
                self.link.close()
            except Exception:
                pass
        self.link = None
        self.link_key = None

    def _ensure_link(self, s):
        key = (s["port"], s["baud"])
        if self.link is not None and self.link_key == key:
            if self.link.ping(timeout=0.5, tries=2):
                return
            self.log("Board did not answer on the open port: reconnecting...")
        self.release()
        try:
            link, info = ut.connect(s["port"], s["baud"], log=self.log)
        except SystemExit as exc:  # uwb_tool reports connection problems this way
            raise RuntimeError(str(exc))
        except Exception as exc:
            text = str(exc)
            if "denied" in text.lower() or "PermissionError" in text:
                text += ("\n  Another program has this port open: a second copy of this window, uwb_tool.py in a "
                         "terminal, a serial monitor, or a debug session in STM32CubeIDE. Close it and try again.")
            raise RuntimeError(text)
        self.link, self.link_key = link, key
        self.q.put(("conn", "Connected: %s at %d baud, firmware %s" % (s["port"], s["baud"], info["fw_version"])))

    # ---- trials
    def start(self, settings, role_name, meta, path_fn, repeat=False, keep_empty=True):
        """settings: a private copy of the uwb_tool settings. path_fn(trial) -> file to write.
        repeat: start the next trial by itself until stop() (used by the initiator window).
        keep_empty: also save a trial in which no exchange was recorded."""
        if self.busy:
            return False
        self.busy = True
        self.stop_all = False
        self.stop_event = threading.Event()
        threading.Thread(target=self._thread, args=(settings, role_name, dict(meta), path_fn, repeat, keep_empty),
                         daemon=True).start()
        return True

    def stop(self):
        if self.busy:
            self.stop_all = True
            self.stop_event.set()

    def _thread(self, s, role_name, meta, path_fn, repeat, keep_empty):
        role = ut.ROLE_INITIATOR if role_name == "initiator" else ut.ROLE_RESPONDER
        waiting = ("Waiting for the initiator board to call..." if role == ut.ROLE_RESPONDER
                   else "Calling the main (responder) board... start a trial there")
        last_file = None
        try:
            self._ensure_link(s)
            while True:
                self.q.put(("status", waiting))
                self.q.put(("progress", None))
                trial = ut.run_trial(self.link, role, s, meta, stop_event=self.stop_event, log=self.log,
                                     progress=False, on_update=lambda d: self.q.put(("progress", d)), use_keys=False)
                if trial is None or (not trial["exchanges"] and not keep_empty):
                    if not repeat:
                        self.log("Nothing recorded.")
                else:
                    self.q.put(("status", "Saving and analysing..."))
                    path = path_fn(trial)
                    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                    ut.finish_trial(trial, path, os.path.dirname(os.path.abspath(path)), log=self.log)
                    last_file = path
                    merged = ua.merged_name(path) if ua is not None else None
                    self.q.put(("saved", merged if (merged and os.path.exists(merged)) else path))
                if self.stop_all or not repeat:
                    break
                self.stop_event.clear()
                time.sleep(0.3)
        except (RuntimeError, IOError, OSError) as exc:
            self.log("ERROR: %s" % exc)
            self.q.put(("error", str(exc)))
            self.release()
            self.q.put(("conn", "Not connected"))
        except Exception:
            self.log("ERROR (please report this):\n" + traceback.format_exc())
            self.q.put(("error", "unexpected error, see the output box"))
            self.release()
            self.q.put(("conn", "Not connected"))
        finally:
            self.busy = False
            self.q.put(("idle", last_file))


def import_trials(src, data_dir, log=print):
    """Copy the trial files found in src (e.g. the USB stick, sub-folders included) into
    data_dir, skipping trials that are already there, then merge every trial that now has
    both sides. Returns (number copied, list of merged files written)."""
    if ua is None:
        raise RuntimeError("numpy is needed for merging:  pip install numpy")
    os.makedirs(data_dir, exist_ok=True)
    have = set()
    for name in os.listdir(data_dir):
        if name.lower().endswith(".json"):
            have.add(ua.peek(os.path.join(data_dir, name)))
    copied = 0
    seen = 0
    base_depth = os.path.abspath(src).rstrip(os.sep).count(os.sep)
    for folder, dirs, files in os.walk(src):
        if os.path.abspath(folder).count(os.sep) - base_depth >= 3:
            dirs[:] = []
        if os.path.abspath(folder) == os.path.abspath(data_dir):
            continue
        for name in sorted(files):
            if not name.lower().endswith(".json"):
                continue
            path = os.path.join(folder, name)
            key = ua.peek(path)
            if not key[0] or key[1] not in ("initiator", "responder"):
                continue
            seen += 1
            if key in have:
                continue
            dest = os.path.join(data_dir, name)
            k = 2
            while os.path.exists(dest):
                dest = os.path.join(data_dir, "%s_%d.json" % (os.path.splitext(name)[0], k))
                k += 1
            shutil.copy2(path, dest)
            have.add(key)
            copied += 1
            log("copied %s" % name)
    merged = ua.merge_all(data_dir)
    for out in merged:
        log("merged -> %s" % os.path.basename(out))
    log("%d trial files found, %d new ones copied, %d trials merged." % (seen, copied, len(merged)))
    if seen == 0:
        log("No initiator or responder trial files in %s." % src)
    return copied, merged
