#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

import argparse
import logging
import os

from uci import *
from uqt_utils.utils import uqt_errno

# Below hack sometimes required when operating on windows git-bash/msys2
import sys

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")


def main():
    default_port = os.getenv("UQT_PORT", "/dev/ttyUSB0")

    parser = argparse.ArgumentParser(
        description="Reset device calibration parameters to their default values."
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
        default=False,
        help="use logging.DEBUG level. (default: %(default)s)",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        default=False,
        help="by-pass prompt. (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=6,
        help="time in second until the script timeout. (default: %(default)s)",
    )

    args = parser.parse_args()

    if args.description:
        print(parser.description)
        sys.exit(0)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    log = logging.getLogger()

    if not args.yes:
        print("Warning: your default calibration and configuration will be erased")
        input("press <ENTER> to continue")

    try:

        client = None
        client = Client(port=args.port)

        rts = client.reset_calibration(args.timeout)

    except UciComError as e:
        rts = e.n
        log.critical(f"{e}")

    if client:
        client.close()
    sys.exit(uqt_errno(rts))


if __name__ == "__main__":
    main()
