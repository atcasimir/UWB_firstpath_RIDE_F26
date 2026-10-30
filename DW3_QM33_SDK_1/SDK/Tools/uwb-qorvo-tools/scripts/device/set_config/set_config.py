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

    - You may verify your parameter type and Write availability before setting
      using: get_config -l

    - You may verify the set operation through  read-back
      using get_config <cal param>

    - Int8, Int16, or Int64 cal parameters values may be
      entered using one of below format:
        - full descriptive  : set_config <parameter> 'Int16(5)'
        - decimal value     : set_config <parameter> 255
        - hexadecimal value : set_config <parameter> 0x28
        - octal             : set_config <parameter> 0o120
        - binary            : set_config <parameter> 0b101011


    - Fixed Point parameters value may be
      entered using one of below format:
        - full descriptive  : set_config <parameter> 'S4_11(5.23568)'
        - float value       : set_config <parameter> 3.5
        - integer value     : set_config <parameter> 4

    -Fixed Point WARNING if using the short format:
      integers and floats are treated differently (2 != 2.0) :
      - integers are expected to be already coded in fixed point
      - float will be translated to the related fixed-point value.
      Thus:
           - set_config XXX 2;   get_config -r -> S4_11(0.0009765625)
           - set_config XXX 2.0; get_config -r -> S4_11(2.0)

    -Configure WifiCoexFeature:
        set_config WifiCoexFeature enable=1 min_guard=5 max_guard=6 advanced_grant=1
            0 Disable (default)
            1 Enable CoEx Interface without Debug and without Warning Verbose
            2 Enable CoEx Interface with Debug Verbose only
            3 Enable CoEx Interface with Warnings Verbose only
            4 Enable CoEx Interface with both Debug and Warning Verbose
            Param min_guard_dur: Time from when UWB_WLAN_IND is LOW to the next HIGH in ms
            Param max_grant_dur: Max duration of Ranging Round in ms
            Param adv_grant_dur: Time before starting Ranging Round in ms

"""


def main():
    default_port = os.getenv("UQT_PORT", "/dev/ttyUSB0")
    parser = argparse.ArgumentParser(
        description="Set a configuration parameter value.",
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
        help="use logging.DEBUG level. (default: %(default)s)",
        default=False,
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="list available param names and their spec",
        default=False,
    )
    parser.add_argument(
        "key",
        type=str,
        nargs="?",
        default="key",
        help="Calibration key. (default: %(default)s)",
    )
    parser.add_argument(
        "value",
        type=str,
        nargs="*",
        help="Calibration value. See below notes for value format. (default: %(default)s)",
        default="value",
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
            a = f'({config_params[k][0].__name__}, {"R" if config_params[k][1] == 1 else "R/W"})'
            print(f"{k.name:<20} {a:<20} : {config_params[k][2]}")
        sys.exit(uqt_errno(0))

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    while True:
        try:

            client = None
            client = Client(port=args.port)

            # Check param:
            try:
                k = eval(f"Config.{args.key}")
            except Exception:
                print(f"{args.key} unknown config parameter. Quitting.")
                rts = 2
                break
            if config_params[k][1] == 1:
                print(f"{k.name} is Read Only. Quitting.")
                rts = 2
                break

            # Build the parameter type arguments:
            if (len(args.value) == 1) and args.value[0].startswith(
                config_params[k][0].__name__
            ):
                # We are in a descriptive syntax format
                v_str = args.value[0]
            else:
                # let's try to guess...
                v_str = ""
                for v in args.value:
                    try:
                        # convert Hex, octal, ...
                        v = eval(v)
                        v = str(v)
                    except Exception:
                        if v.find("=") != -1:
                            # keep the option
                            pass
                        else:
                            # We do have a string:
                            v = "'" + v + "'"
                    v_str = v_str + ", " + v
                v_str = v_str[1:]

            # print("""config_params[k][0]("""+v_str+""")""")
            # print(config_params[k][0])
            value = eval("""config_params[k][0](""" + v_str + """)""")

            rts, dummy = client.set_config(
                [
                    (k, value),
                ]
            )
            print(f"{rts.name} ({rts})")

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
