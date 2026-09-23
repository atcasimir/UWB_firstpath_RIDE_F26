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

    Allows to recover all the capability parameters of the device
"""


def main():
    default_port = os.getenv("UQT_PORT", "/dev/ttyUSB0")
    parser = argparse.ArgumentParser(
        description="Get the capability data from the device.",
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
            client = Client(port=args.port)

            rts, ret = client.get_caps()
            print("\n# Get Device Capability Parameter \n")

            if rts != Status.Ok:
                log.critical(f"get_caps() failed with status: {rts.name} ({rts})")
                break
            print(ret)
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
