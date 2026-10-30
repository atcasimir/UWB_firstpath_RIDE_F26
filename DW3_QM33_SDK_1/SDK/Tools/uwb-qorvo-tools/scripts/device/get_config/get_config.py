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

    - You may use 'all' to recover all available internal values

    - The difference between -x and -b is the 'endianness':
      -x is showing integer values in 'natural' representation (MSB left)
      -b is showing the 'little-endian' byte stream as received from the DUT.
"""


def main():
    default_port = os.getenv("UQT_PORT", "/dev/ttyUSB0")
    parser = argparse.ArgumentParser(
        description="Get one or several configuration parameter value.",
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
    parser.add_argument("key", type=str, nargs="*", help="Calibration key")
    parser.add_argument(
        "-b",
        "--as-bytes",
        action="store_true",
        help="show the key value as a byte stream. (default: %(default)s)",
        default=False,
    )
    parser.add_argument(
        "-x",
        "--as-hex",
        action="store_true",
        help="show the key value in hex format. (default: %(default)s)",
        default=False,
    )
    parser.add_argument(
        "-r",
        "--as-repr",
        action="store_true",
        help="show the key value in format used to set it back. (default: %(default)s)",
        default=False,
    )

    args = parser.parse_args()

    if args.description:
        print(parser.description)
        sys.exit(0)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    log = logging.getLogger()

    if args.list:
        for k in config_params.keys():
            a = f'({config_params[k][0].__name__}, {"R" if config_params[k][1]==1 else "R/W"})'
            print(f"{k.name:<20} {a:<20} : {config_params[k][2]}")
        sys.exit(uqt_errno(0))

    if args.key is None:
        print("A Configuration parameter name is expected")
        sys.exit(uqt_errno(2))

    while True:
        try:

            client = None
            is_alone = None
            client = Client(port=args.port)

            if args.key == ["all"] or args.key == []:
                args.key = config_params.keys()
            is_alone = len(args.key) == 1

            for k in args.key:
                if type(k) is str:
                    try:
                        k = eval(f"Config.{k}")
                    except Exception:
                        print(f"{k} unknown config parameter. Quitting.")
                        rts = 2
                        break
                # Example of Format received:
                # (<Status.Ok: 0>, [(<Config.PmMinInactivityS4: 169>, 4, 0), (<Config.ChannelNumber: 160>, 1, 5),...)
                rts, ret = client.get_config(
                    [
                        (k),
                    ]
                )
                param, l, v = ret[0]
                if rts != Status.Ok:
                    v = rts.name
                else:
                    try:
                        v = config_params[param][0](v)
                    except Exception as e:
                        v = f"Error: {e}"
                    if args.as_bytes:
                        try:
                            v = v.to_bytes(length=len(v), byteorder="little").hex(".")
                        except Exception:
                            try:
                                v = v.hex(".")
                            except Exception:
                                v = repr(v)
                    elif args.as_hex:
                        try:
                            v = hex(v)
                        except Exception:
                            try:
                                v = v.as_hex()
                            except Exception:
                                v = repr(v)
                    elif args.as_repr:
                        v = repr(v)
                if is_alone:
                    print(f"{v!s}")
                else:
                    print(f"{k.name:<20} = {v!s}")

            break

        except UciComError as e:
            rts = e.n
            log.critical(f"{e}")
            break

    if client:
        client.close()
    sys.exit(uqt_errno(rts))


if __name__ == "__main__":
    main()
