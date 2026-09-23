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
    default_port = os.getenv("UQT_PORT", "/dev/ttyUSB0")
    parser = argparse.ArgumentParser(description="Run Fira Test SS TWR.")
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
    )
    parser.add_argument(
        "-r",
        "--responder",
        action="store_true",
        help="start as responder (default initiator)",
    )
    parser.add_argument(
        "-c",
        "--channel",
        type=int,
        default=9,
        help="channel number. (default: %(default)s)",
    )
    parser.add_argument(
        "--preamble-code-index",
        type=int,
        default=9,
        help="app param. (default: %(default)s)",
    )
    parser.add_argument(
        "--sfd-id",
        type=int,
        choices=[0, 2],
        default=2,
        help="Start of frame delimiter, allowed values are 0, 2 (default: %(default)s)",
    )
    parser.add_argument(
        "--phr-data-rate",
        type=int,
        choices=[0, 1],
        default=0,
        help="Rate used to exchange PHR, 0 = 850Kbps 1 = 6.81Mbps. (default: %(default)s)",
    )
    parser.add_argument(
        "--sts-length",
        type=int,
        choices=[0, 1],
        default=1,
        help="Number of symbols in a STS segment. 0 = 32 symbols; 1 = 64 symbols (default: %(default)s)",
    )
    parser.add_argument(
        "--en-diag",
        action="store_true",
        default=False,
        help="set the Qorvo ENABLE_DIAGNOSTIC parameter to 1.",
    )
    parser.add_argument(
        "--antenna-set-id",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
        help="set the antenna set to use for the session. (default: %(default)s)",
    )

    args = parser.parse_args()

    if args.description:
        print(parser.description)
        sys.exit(0)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    log = logging.getLogger()

    notif_handlers = {
        (Gid.Test, OidTest.SsTwr): lambda x: print(TwrTestOutput(x)),
        (Gid.Qorvo, OidQorvo.TestDebug): lambda x: print(TestDebugData(x)),
        ("default", "default"): lambda gid, oid, x: print(
            f"Warning: Unexpected notification: {NotImplementedData(gid, oid, x)}"
        ),
    }

    while True:
        try:
            client = None
            client = Client(port=args.port, notif_handlers=notif_handlers)

            print("\n\n\n\n ----- TEST TEST_SS_TWR_CMD -----")
            rts, session_handle = client.session_init(
                TestModeSessionId, SessionType.DeviceTestMode
            )
            print(f'{f"init TestSession {TestModeSessionId} ...":<25}{rts.name}')
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

            time.sleep(0.5)

            rts, rtv = client.test_config_set(
                session_handle,
                [
                    (TestParam.RMarkerTxStart, 0),
                    (TestParam.RMarkerRxStart, 0),
                    (TestParam.StsIndexAutoIncr, 0),
                ],
            )
            print(f'{"TestConfigSet:":<25}{rts.name}')
            if rts != Status.Ok:
                print(rtv)
                break

            time.sleep(0.5)

            # Session app config
            app_configs = [
                (App.DeviceRole, 0 if args.responder else 1),
                (App.ChannelNumber, args.channel),
                (App.StsIndex, 0x00000000),
                (App.SlotDuration, 9600),
                (App.RframeConfig, 3),
                (App.PreambleCodeIndex, args.preamble_code_index),
                (App.DeviceMacAddress, 0x8D00 if args.responder else 0x8C00),
                (App.DstMacAddress, [0x8C00 if args.responder else 0x8D00]),
                (App.NumberOfControlees, 1),
                (App.SfdId, args.sfd_id),
                (App.BprfPhrDataRate, args.phr_data_rate),
                (App.PrfMode, 0),
                # Ensure SP3 frames support by setting NumberOfStsSegments to 1.
                (App.NumberOfStsSegments, 1),
                (App.StsLength, args.sts_length),
            ]
            if args.en_diag:
                app_configs.append((App.EnableDiagnostics, 1))
            if args.antenna_set_id:
                app_configs.append((App.TxAntennaSelection, args.antenna_set_id))
                app_configs.append((App.RxAntennaSelection, args.antenna_set_id))

            for i in app_configs:
                p = f"{i[0].name} ({hex(i[0])}):"

                try:
                    v = hex(i[1])
                except Exception:
                    try:
                        v = i[1].hex(".")
                    except Exception:
                        v = repr(i[1])
                print(f"    {p:<35} {v}")

            rts, rtv = client.session_set_app_config(session_handle, app_configs)
            print(f'{"TestSetAppConfig:":<25}{rts.name}')
            if rts != Status.Ok:
                print(f"session_set_app_config failed: {rts.name} ({rts}).")
                print(f"{rtv}")
                break

            time.sleep(0.5)

            rts = client.test_ss_twr()
            print(f'{"Start TestSsTWR test:":<25}{rts.name}')
            if rts != Status.Ok:
                print(f"test_ss_twr failed: {rts.name} ({rts}).")
                break

            if args.responder:
                time.sleep(30)
            else:
                time.sleep(5)

            rts = client.test_stop_session()
            print(f'{"Stop session:":<25}{rts.name}')

            if rts != Status.Ok:
                print(f"test_stop_session failed: {rts.name} ({rts})")
                client.session_deinit(session_handle)
                break

            time.sleep(0.5)
            break

        except UciComError as e:
            rts = e.n
            log.critical(f"{e}")
            break

    if client:
        status = client.session_deinit(session_handle)
        print(f"session_deinit: {status.name} ({status})")
        client.close()
    if rts == Status.Ok:
        print("Ok")
    sys.exit(uqt_errno(rts))


if __name__ == "__main__":
    main()
