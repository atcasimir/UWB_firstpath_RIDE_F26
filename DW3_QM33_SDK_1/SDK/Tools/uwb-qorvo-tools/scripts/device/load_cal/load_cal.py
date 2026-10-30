#!/usr/bin/env python3

# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

import argparse
import logging
import sys
import os

from uci import Client
from uqt_utils.load_calibration import load_calibration


def main():
    parser = argparse.ArgumentParser(
        description="Load calibration from given JSON file to device through UCI."
    )
    parser.add_argument(
        "--description",
        action="store_true",
        help="show short description of the script",
        default=False,
    )
    parser.add_argument(
        "-f",
        "--calibration",
        type=str,
        help="Path to calibration JSON file.",
        default=None,
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
        help="use logging.DEBUG level",
        default=False,
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.description:
        print(parser.description)
        sys.exit(0)

    if not args.calibration:
        logging.error("Please provide a calibration file.")
        sys.exit(0)

    client = Client(port=args.port)

    load_calibration(client=client, calibration_filename=args.calibration)

    client.close()


if __name__ == "__main__":
    main()
