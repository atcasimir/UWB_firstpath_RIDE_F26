#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

import argparse
import logging
import os
import sys

from uci import *
from uqt_utils.utils import uqt_errno

# Below hack sometimes required when operating on windows git-bash/msys2
sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

epilog = """
Note:
    - You may use 'all' or ''  to recover all available internal values
    - The difference between -x and -b is the 'endianness':
      -x is showing integer values in 'natural' representation (MSB left)
      -b is showing the 'little-endian' byte stream as received from the DUT.
    - A way to backup all calibration parameters:
      get_cal -fa all | tee my_calibration.txt
    - Recovering the calibration parameters from above file:
      set_cal -i my_calibration.txt
"""


def main():
    default_port = os.getenv("UQT_PORT", "/dev/ttyUSB0")
    parser = argparse.ArgumentParser(
        description="Get one or several calibration parameter value.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        "--description",
        action="store_true",
        help="show short description of the script",
        default=False,
    )
    parser.add_argument(
        "-p",
        "--port",
        type=str,
        default=default_port,
        help="communication port to use. (default: %(default)s)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="use logging.DEBUG level (default: %(default)s)",
        default=False,
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="list available param names and their spec (default: %(default)s)",
        default=False,
    )
    parser.add_argument(
        "key",
        type=str,
        nargs="*",
        help="blank separated calibration key (name or integer id). all: get all.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["b", "x", "r", "a", "n"],
        help="Choose param display format. Available: r(repr), x(hex), b(bytes), n(natural) or \
                            a(android param file). (default: %(default)s)",
        default="n",
    )

    args = parser.parse_args()

    if args.description:
        print(parser.description)
        sys.exit(0)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    log = logging.getLogger()

    while True:
        try:
            client = None
            is_alone = None
            client = Client(port=args.port)

            if args.list:
                print("Recovering all parameters from target...")
                rts, l, rtv = client.get_cal([])
                if rts != Status.Ok:
                    log.critical(
                        f"test_mode_calibrations_get() failed with status: {rts.name} ({rts})"
                    )
                    break
                for k, rts, l, v in rtv:
                    v = f"??? ({l} bytes)"
                    if k in cal_params.keys():
                        v = cal_params[k].__name__
                    print(f"{k:<40} : {v}")
                break

            if args.key == [
                "all"
            ]:  # ask target to output all defined cal params as  t,l,v
                args.key = []

            if args.key == []:
                print("Recovering params...")
            else:
                log.debug(f"Recovering {args.key}...")
            rts, l, rtv = client.get_cal(args.key)
            # Example of Output format:
            # (<Status.Ok: 0>, 391, [(b'wifi_coex_mode', <Status.Ok: 0>, 1, b''),
            # (b'wifi_coex_time_gap_t1', <Status.Ok: 0>, 1, b''), ...])

            is_alone = l == 1

            for k, irts, l, v in rtv:

                # Decode values:
                v_suffix = ""
                if k not in cal_params.keys():
                    v_suffix = f'(and "{k}" unknown to uqt.)'
                if irts != Status.Ok:
                    v = f"{irts.name} ({irts}) {v_suffix}"
                elif (args.format == "a") or (k not in cal_params.keys()):
                    # let's keep the bytestreams
                    pass
                else:  # decode and crosscheck Vs type
                    # print(f'{k!r} {v!r} {cal_params[k]!r}')
                    v = cal_params[k]().from_bytes(v)
                if irts == Status.Ok:
                    # encode output as requested:
                    if args.format == "a":
                        v = v.hex(":")
                    elif args.format == "b":
                        try:
                            v = v.to_bytes(length=l, byteorder="little").hex(".")
                        except Exception:
                            try:
                                v = v.hex(".")
                            except Exception:
                                v = repr(v)
                    elif args.format == "x":
                        try:
                            v = hex(v)
                        except Exception:
                            try:
                                v = v.as_hex()
                            except Exception:
                                v = repr(v)
                    elif args.format == "r":
                        v = repr(v)
                    else:  # natural number
                        pass
                # output as requested:
                if args.format == "a":
                    print(f"{k}={v}")
                elif is_alone:
                    print(v)
                else:
                    print(f"{k:<40} = {v}")

            break

        except UciComError as e:
            rts = e.n
            log.critical(f"{e}")
            break

    if (rts != Status.Ok) and (not is_alone):
        log.critical(f"{rts.name} ({rts})")
    if client:
        client.close()
    sys.exit(uqt_errno(rts))


if __name__ == "__main__":
    main()
