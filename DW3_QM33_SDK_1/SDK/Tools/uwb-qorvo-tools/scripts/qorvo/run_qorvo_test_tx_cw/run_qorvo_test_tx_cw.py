#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

import argparse
import logging
import time
import os
import sys

from uci import *
from uqt_utils.utils import uqt_errno

# Below hack sometimes required when operating on windows git-bash/msys2
sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run Qorvo test TX CW.")
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
        help="serial port used. (default: %(default)s)",
        default=os.getenv("UQT_PORT", "/dev/ttyUSB0"),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="use logging.DEBUG level. (default: %(default)s)",
        default=False,
    )
    parser.add_argument(
        "-c",
        "--channel",
        type=int,
        help="channel number. (default: %(default)s)",
        default=9,
    )
    parser.add_argument(
        "-t",
        "--time",
        type=int,
        help="Test time (s). -1: up to user press <ENTER>. (default: %(default)s)",
        default=3,
    )

    args = parser.parse_args()

    if args.description:
        print(parser.description)
        sys.exit(0)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    log = logging.getLogger()

    notif_handlers = {
        ("default", "default"): lambda gid, oid, x: print(
            f"Warning: Unexpected notification: {NotImplementedData(gid, oid, x)}"
        )
    }

    while True:
        try:

            client = None
            client = Client(port=args.port, notif_handlers=notif_handlers)
            print(f"Initializing session {TestModeSessionId}...")
            rts, session_handle = client.session_init(
                TestModeSessionId, SessionType.DeviceTestMode
            )
            if rts != Status.Ok:
                print(f"session_init failed: {rts.name} ({rts})")
                break

            if session_handle is None:
                print(
                    f"Using Fira 1.3 (session handle == session ID) is : {TestModeSessionId}"
                )
                session_handle = TestModeSessionId
            else:
                print(f"Using Fira 2.0 session handle is : {session_handle}")

            print("Sending session config...")
            rts, rtv = client.session_set_app_config(
                session_handle,
                [
                    (App.ChannelNumber, args.channel),
                ],
            )
            if rts != Status.Ok:
                print(f"session_set_app_config failed: {rts.name} ({rts}).")
                print(f"{rtv}")
                client.session_deinit(session_handle)
                break

            print("Starting CW...")
            rts = client.test_tx_cw(1)
            if rts != Status.Ok:
                print(f"test_start_cw failed: {rts.name} ({rts}).")
                client.session_deinit(session_handle)
                break

            if args.time == -1:
                input("Press <RETURN> to stop\n")
            else:
                time.sleep(args.time)

            print("Stopping CW")
            rts = client.test_tx_cw(0)
            if rts != Status.Ok:
                print(f"test_stop_cw failed: {rts.name} ({rts})")
                client.session_deinit(session_handle)
                break

            print("Deinitializing session...")
            rts = client.session_deinit(session_handle)
            if rts != Status.Ok:
                print(f"session_deinit failed: {rts.name} ({rts})")
                break

            break

        except UciComError as e:
            rts = e.n
            log.critical(f"{e}")
            break

    if client:
        client.close()
    if rts == Status.Ok:
        print("Ok")
    sys.exit(uqt_errno(rts))


if __name__ == "__main__":
    main()
