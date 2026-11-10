#!/usr/bin/env python3
"""
uwb_setups.py - "which measurements belong together".

A SETUP is what you intended to measure: site, real distance, LOS / blocked, what is
in the way, how the boards are turned, antenna height. It is defined once, saved in
<data folder>/setups.json and chosen from a list afterwards, so "same setup" is an
exact match and not a label typed by hand.

A PLACEMENT is one physical positioning of the boards for a setup. It is a counter that
goes up when the boards have been moved and put back (button in the window), or when a
different setup was measured in between. Trials with the same setup AND the same
placement are true repeats; the same setup over several placements shows how repeatable
the setup itself is.

Every trial file stores the setup id, a copy of the setup's fields and the placement in
its "meta" block, so a file stays self-describing even if setups.json is lost.
"""

import datetime
import json
import os
import re

CONDITIONS = ["LOS", "partial blockage", "NLOS"]

# (key, label, kind) in the order they are shown. kind: "text", "float" or "choice".
FIELDS = [
    ("name", "Name", "text"),
    ("site", "Site (room / location)", "text"),
    ("distance_m", "Real distance (m)", "float"),
    ("condition", "Condition", "choice"),
    ("obstruction", "What is in the way", "text"),
    ("orientation", "Orientation of the boards", "text"),
    ("antenna_height_m", "Antenna height (m)", "float"),
    ("notes", "Notes", "text"),
]
META_KEYS = [k for k, _, _ in FIELDS if k not in ("name", "notes")]


def slug(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(text)).strip("_")


class SetupStore:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.path = os.path.join(data_dir, "setups.json")
        self.data = {"format": "uwb-setups", "next_id": 1, "last_setup": None, "setups": []}
        self.load()

    # ---- file
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("format") == "uwb-setups":
                self.data.update(d)
        except (OSError, ValueError):
            pass

    def save(self):
        os.makedirs(self.data_dir, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=1)
        os.replace(tmp, self.path)

    # ---- access
    def all(self):
        return list(self.data["setups"])

    def get(self, setup_id):
        for s in self.data["setups"]:
            if s["id"] == setup_id:
                return s
        return None

    @staticmethod
    def label(s):
        """One line for the drop-down list."""
        parts = [s["id"], s.get("name") or ""]
        detail = []
        if s.get("site"):
            detail.append(s["site"])
        if s.get("distance_m") is not None:
            detail.append("%g m" % s["distance_m"])
        if s.get("condition"):
            detail.append(s["condition"])
        return "  ".join(p for p in parts if p) + ("   (" + ", ".join(detail) + ")" if detail else "")

    @staticmethod
    def id_from_label(label):
        return label.split()[0] if label and label.strip() else None

    # ---- editing
    @staticmethod
    def clean(fields):
        """Validate the fields of the form. Returns (dict, None) or (None, error text)."""
        out = {}
        for key, label, kind in FIELDS:
            v = fields.get(key, "")
            v = v.strip() if isinstance(v, str) else v
            if kind == "float":
                if v in ("", None):
                    v = None
                else:
                    try:
                        v = float(v)
                    except (TypeError, ValueError):
                        return None, "%s must be a number." % label
            out[key] = v
        if not out["name"]:
            return None, "Give the setup a name."
        if out["distance_m"] is None or out["distance_m"] < 0:
            return None, "The real distance is needed (metres, antenna to antenna)."
        if not out["condition"]:
            out["condition"] = CONDITIONS[0]
        return out, None

    def add(self, fields):
        s = dict(fields)
        s["id"] = "S%03d" % self.data["next_id"]
        self.data["next_id"] += 1
        s["placement"] = 1
        s["trials"] = 0
        s["created"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        self.data["setups"].append(s)
        self.save()
        return s

    def update(self, setup_id, fields):
        s = self.get(setup_id)
        if s is None:
            return None
        for key, _, _ in FIELDS:
            s[key] = fields.get(key)
        self.save()
        return s

    # ---- placements
    def boards_moved(self, setup_id):
        """The boards were moved and put back: the next trial is a new placement."""
        s = self.get(setup_id)
        if s is None:
            return None
        if s.get("trials_this_placement", 0) > 0:
            # Counts up once, however often the button is pressed before the next trial.
            s["placement"] = s.get("placement", 1) + 1
            s["trials_this_placement"] = 0
        self.save()
        return s["placement"]

    def next_placement(self, setup_id):
        """The placement the next trial of this setup will get (nothing is changed)."""
        s = self.get(setup_id)
        if s is None:
            return None
        last = self.data.get("last_setup")
        if last is not None and last != setup_id and s.get("trials_this_placement", 0) > 0:
            return s.get("placement", 1) + 1
        return s.get("placement", 1)

    def begin_trial(self, setup_id):
        """Call when a trial starts. Returns the meta block for the trial file.

        If another setup was measured since this one's last trial, the boards have been
        rearranged in between, so this is a new placement."""
        s = self.get(setup_id)
        if s is None:
            raise KeyError(setup_id)
        last = self.data.get("last_setup")
        if last is not None and last != setup_id and s.get("trials_this_placement", 0) > 0:
            s["placement"] = s.get("placement", 1) + 1
            s["trials_this_placement"] = 0
        self.data["last_setup"] = setup_id
        self.save()
        return self.meta(s)

    def trial_saved(self, setup_id):
        s = self.get(setup_id)
        if s is not None:
            s["trials"] = s.get("trials", 0) + 1
            s["trials_this_placement"] = s.get("trials_this_placement", 0) + 1
            self.save()

    @staticmethod
    def meta(s, trial_notes=""):
        m = {"setup_id": s["id"], "setup_name": s.get("name", ""), "placement": s.get("placement", 1)}
        for k in META_KEYS:
            m[k] = s.get(k)
        m["setup_notes"] = s.get("notes") or ""
        m["notes"] = trial_notes or ""
        m["group"] = "%s %s" % (s["id"], s.get("name", ""))  # for tools that still read the old label
        return m

    def file_stem(self, s):
        return "%s_%s_p%d" % (s["id"], slug(s.get("name", "")) or "setup", s.get("placement", 1))


# ---- reading the grouping back out of trial files (used by uwb_analyze) ----------------
def setup_key(meta):
    """What a trial belongs to: its setup id, or the old free-text group for older files."""
    meta = meta or {}
    if meta.get("setup_id"):
        return meta["setup_id"]
    return "group:" + str(meta.get("group", ""))


def setup_title(meta):
    meta = meta or {}
    if meta.get("setup_id"):
        bits = [b for b in (meta.get("site"), ("%g m" % meta["distance_m"]) if meta.get("distance_m") is not None else None,
                            meta.get("condition"), meta.get("obstruction"), meta.get("orientation")) if b]
        return "setup %s '%s'%s" % (meta["setup_id"], meta.get("setup_name", ""), ("  (" + ", ".join(bits) + ")") if bits else "")
    return "group '%s' (older file without a setup)" % meta.get("group", "")


def parse_filter(text):
    """'site=lab condition=nlos' -> [('site','lab'), ('condition','nlos')]; bare words match any field."""
    out = []
    for token in (text or "").split():
        key, sep, value = token.partition("=")
        out.append((key.lower(), value.lower()) if sep else (None, token.lower()))
    return out


def matches(meta, flt):
    meta = meta or {}
    alias = {"distance": "distance_m", "setup": "setup_id", "name": "setup_name", "height": "antenna_height_m"}
    for key, value in flt:
        if key is None:
            if not any(value in str(v).lower() for v in meta.values() if v is not None):
                return False
        else:
            v = meta.get(alias.get(key, key))
            if v is None:
                return False
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                try:
                    if abs(float(value) - float(v)) > 1e-9:
                        return False
                except ValueError:
                    return False
            elif value not in str(v).lower():
                return False
    return True
