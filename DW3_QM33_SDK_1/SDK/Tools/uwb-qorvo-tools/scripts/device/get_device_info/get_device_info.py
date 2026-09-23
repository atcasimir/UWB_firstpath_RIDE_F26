#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

import argparse
import logging
import sys
import os

from uci import *
from uqt_utils.utils import uqt_errno

# Below hack sometimes required when operating on windows git-bash/msys2
sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Get information from device.")
    parser.add_argument(
        "--description",
        action="store_true",
        help="show short description of the script",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=str,
        help="serial port used. (default: %(default)s)",
        default=os.getenv("UQT_PORT", "/dev/ttyUSB0"),
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

    print(f"Pinging device at {args.port}:")
    try:
        client = None
        client = Client(port=args.port)
        rts, rtv = client.get_device_info()
        print(rtv)
    except UciComError as e:
        rts = e.n
        print(f"{e}")

    if client:
        client.close()
    sys.exit(uqt_errno(rts))


if __name__ == "__main__":
    main()
