#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

import argparse
import logging
import time
import os

from uci import (
    Client,
    App,
    Gid,
    SessionType,
    TestParam,
    Status,
    UciComError,
    TestModeSessionId,
)
from uci import OidTest, OidQorvo
from uci import TestDebugData, NotImplementedData, RxTestOutput

# Below hack sometimes required when operating on windows git-bash/msys2
import sys

from uqt_utils.utils import uqt_errno

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="run Fira's Test RX.")
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
        choices=[5, 9],
        help="Channel number. (default: %(default)s)",
        default=9,
    )
    parser.add_argument(
        "--preamble-code-index",
        type=int,
        default=9,
        help="This value configures the preamble code index 9 to 24 are allowed for BPRF. (default: %(default)s)",
    )
    parser.add_argument(
        "--sfd-id",
        type=int,
        choices=[0, 2],
        default=2,
        help="Start of frame delimiter, allowed values are 0, 2 (default: %(default)s)",
    )
    parser.add_argument(
        "--rframe-config",
        type=int,
        choices=[0, 1, 3],
        default=0,
        help="rframe configuration used to transmit/receive ranging messages."
        " 0 = SP0, 1 = SP1, 3 = SP3 (default: %(default)s)",
    )
    parser.add_argument(
        "--phr-data-rate",
        type=int,
        choices=[0, 1],
        default=0,
        help="Rate used to exchange PHR, 0 = 850Kbps 1 = 6.81Mbps. (default: %(default)s)",
    )
    parser.add_argument(
        "--nb-sts-segments",
        type=int,
        choices=[0, 1],
        default=0,
        help="Number of STS segments in the frame. (default: %(default)s)",
    )
    parser.add_argument(
        "--sts-length",
        type=int,
        choices=[0, 1],
        default=1,
        help="Number of symbols in a STS segment. 0 = 32 symbols; 1 = 64 symbols. (default: %(default)s)",
    )
    parser.add_argument(
        "--en-diag",
        action="store_true",
        default=False,
        help="Set the Qorvo ENABLE_DIAGNOSTIC parameter to 1.",
    )
    parser.add_argument(
        "--antenna-set-id",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
        help="Set the antenna set to use for the session. (default: %(default)s)",
    )

    args = parser.parse_args()

    if args.description:
        print(parser.description)
        sys.exit(0)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    log = logging.getLogger()

    notif_handlers = {
        (Gid.Test, OidTest.Rx): lambda x: print(RxTestOutput(x)),
        (Gid.Qorvo, OidQorvo.TestDebug): lambda x: print(TestDebugData(x)),
        ("default", "default"): lambda gid, oid, x: print(
            f"Warning: Unexpected notification: {NotImplementedData(gid, oid, x)}"
        ),
    }

    while True:
        try:
            client = None
            client = Client(port=args.port, notif_handlers=notif_handlers)

            print("\n\n\n\n -----  TEST_RX -----")
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
                    (TestParam.RMarkerRxStart, 0),
                    (TestParam.RMarkerTxStart, 0),
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
                (App.DeviceMacAddress, 0x008C),
                (App.DstMacAddress, [0x008D]),
                (App.NumberOfControlees, 1),
                (App.ChannelNumber, args.channel),
                (App.MacFcsType, 0),
                (App.RframeConfig, args.rframe_config),
                (App.PreambleCodeIndex, args.preamble_code_index),
                (App.SfdId, args.sfd_id),
                (App.BprfPhrDataRate, args.phr_data_rate),
                (App.PrfMode, 0),
                (App.NumberOfStsSegments, args.nb_sts_segments),
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

            rts = client.test_rx()
            print(f'{"Start Rx test:":<25}{rts.name}')
            if rts != Status.Ok:
                print(f"test_rx failed: {rts.name} ({rts}).")
                break

            time.sleep(2)
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
