#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

import argparse
import os
import sys
import platform
import serial

import uci
from uci import *


def dut_info(name, port, env_var=None):
    if (port is None) or (port == ""):
        print(f"\n# DUT '{name}':\n    unknown port ('{env_var}' not defined.)")
        return
    try:
        # Attempt to open and immediately close the serial port to check if it's available.
        ser = serial.Serial(port)
        ser.close()
        print(f"\n# DUT '{name}' at port '{port}':")
        try:
            client = Client(port=port)
            _, rtv = client.get_device_info()
            print(f"    {rtv}")
        except Exception as e:
            print("  No response. Error: ", e)
    except serial.SerialException:
        print(f"\n# DUT '{name}':\n '{port}' not available.")


def env_info():
    try:
        python_version = platform.python_version()
    except Exception as e:
        python_version = f"unable to retreive version: got {e}"
    print(f"\n# Python3 version:\n    {python_version}")

    uqt_custom = os.environ.get("UQT_CUSTOM", "")
    uqt_addins = os.environ.get("UQT_ADDINS", "").split(":")

    print(f"\n# Customization (UQT_CUSTOM):\n    {uqt_custom}")
    print(
        f"\n# Wanted Extensions (UQT_ADDINS):\n    {(os.linesep+'    ').join(uqt_addins)}"
    )
    print(f"\n# Loaded Extensions:\n    {(os.linesep+'    ').join(uci.loaded_addins)}")


def main():
    parser = argparse.ArgumentParser(description="List current config.")
    parser.add_argument(
        "--description",
        action="store_true",
        help="show short description of the script",
    )

    args = parser.parse_args()

    if args.description:
        print(parser.description)
        sys.exit(0)

    env_info()
    dut_info("Default", os.getenv("UQT_PORT"), "UQT_PORT")


if __name__ == "__main__":
    main()
