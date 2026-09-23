#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

import argparse
import logging
import time
import os

from uci import *
from uqt_utils.utils import (
    test_profile_keys,
    get_test_profile,
    uqt_errno,
    wait_for,
    str2bytes,
)

#  Below hack sometimes required when operating on windows git-bash/msys2
import sys

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

default_psdu = (
    "2D00003200000000090004E80300000104D00700000204C2010000"
    "0304EE02000004010005010007040000000006040000000008220E"
)

sep = "\n          "
epilog = f"""
Helper:
    - If no packets have been received for (T_gap x Num_packets) + TIMEOUT,
     the test is terminated with an error message. You can configure the parameters as arguments.
        run_fira_test_periodic_tx --num-packets 500 --t-gap 800 --timeout 4

Note : Test profile files Syntax:
    Each line is expected to be of'<key>=<value>' format with below characteristics.
    - All blanck lines and lines starting with "#" are by passed
    - Integers: may be prefixed with 0x, 0b, or 0o
    - Bytestream: The length (nbr of bytes) of provided byte stream
      should meet the expected parameter length.
      bytes may be separated with ':' or '.' .
    - Below parameters are bypassed:
        'file_format_version', 'file_description', 'test_type'
    - expected <key> may  be:
          {sep.join(test_profile_keys)}
"""


def main():
    parser = argparse.ArgumentParser(
        description="Run Fira's periodic TX test.",
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
        default=os.getenv("UQT_PORT", "/dev/ttyUSB0"),
        help="serial port used. (default: %(default)s)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="use logging.DEBUG level. (default: %(default)s)",
    )
    parser.add_argument(
        "--run-forever",
        action="store_true",
        help="Keep the script running indefinitely, the number of packets is set to 0xFFFFFFFF "
        'and you must press "enter" to stop the program.',
    )
    parser.add_argument(
        "-c",
        "--channel",
        type=int,
        choices=[5, 9],
        default=9,
        help="channel number. (default: %(default)s)",
    )
    parser.add_argument(
        "-i",
        "--input-file",
        type=str,
        help="recover test configuration from a test profile file.",
    )

    parser.add_argument(
        "--randomized-psdu",
        type=int,
        choices=[0, 1],
        default=0,
        help="Test config. (default: %(default)s)",
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
        "--psdu",
        type=str,
        default=default_psdu,
        help="':' or '.' separated list of bytes or Python List (default: %(default)s)",
    )
    parser.add_argument(
        "--num-packets",
        type=int,
        default=9000,
        help="Number of packets to transmit. (default: %(default)s)",
    )
    parser.add_argument(
        "--t-gap",
        type=int,
        default=2000,
        help="Gap between start of one packet to the next (in seconds). (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3,
        help="Timeout to receive first package (in seconds). (default: %(default)s)",
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

    if args.input_file:
        (app_config, test_config, misc_test) = get_test_profile(args.input_file)
        app_config.update(test_config)
        app_config.update(misc_test)
        for k in app_config.keys():
            if k not in args.__dict__.keys():
                logging.warning(f"{k} from {args.input_file} not used.")
        args.__dict__.update(app_config)

    action_completed = False

    def periodic_tx_test_callback(payload):
        nonlocal action_completed
        action_completed = True
        print(PeriodicTxTestOutput(payload))

    notif_handlers = {(Gid.Test, OidTest.PeriodicTx): periodic_tx_test_callback}

    while True:
        try:
            client = None
            client = Client(port=args.port, notif_handlers=notif_handlers)

            print("\n\n\n\n ----- TEST TEST_PERIODIC_TX_CMD -----")
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

            time.sleep(0.1)

            param_config = [
                (TestParam.TGap, args.t_gap),
                (TestParam.RandomizePsdu, args.randomized_psdu),
                (TestParam.RMarkerTxStart, 0),
                (TestParam.RMarkerRxStart, 0),
            ]

            if args.run_forever:
                param_config.append((TestParam.NumPackets, int(0xFFFFFFFF)))
            else:
                param_config.append((TestParam.NumPackets, args.num_packets))

            rts, rtv = client.test_config_set(session_handle, param_config)
            print(f'{"TestConfigSet:":<25}{rts.name}')
            if rts != Status.Ok:
                print(rtv)
                break
            time.sleep(0.1)

            app_configs = [
                (App.ChannelNumber, args.channel),
                (App.DeviceMacAddress, 0x008D),
                (App.DstMacAddress, [0x008C]),
                (App.MacFcsType, 0),
                (App.RframeConfig, args.rframe_config),
                (App.PreambleCodeIndex, args.preamble_code_index),
                (App.SfdId, args.sfd_id),
                (App.BprfPhrDataRate, args.phr_data_rate),
                (App.PrfMode, 0),
                (App.NumberOfStsSegments, args.nb_sts_segments),
                (App.StsLength, args.sts_length),
                (App.NumberOfControlees, 1),
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
            time.sleep(0.1)

            p_tx = str2bytes(args.psdu)

            rts = client.test_periodic_tx(p_tx)
            print(f'{"Start periodic_tx test:":<25}{rts.name}')
            if rts != Status.Ok:
                print(f"periodic_tx test failed: {rts.name} ({rts}).")
                break

            if args.run_forever:
                input("Press <RETURN> to stop\n")
                rts = client.test_stop_session()
                print(f'{"Stop session:":<25}{rts.name}')
                if rts != Status.Ok:
                    print(f"test_stop_session failed: {rts.name} ({rts})")
                    break

                rts = wait_for(
                    lambda: action_completed,
                    args.timeout,
                    0.1,
                )
                if not rts:
                    print(f"\nError: no test result after {args.timeout}. \n")
                    break

            else:
                delay = (args.num_packets * args.t_gap) / 1000000
                rts = wait_for(
                    lambda: action_completed,
                    delay + args.timeout,
                    0.1,
                )
                if not rts:
                    print(f"\nError: no test result after {delay + args.timeout}. \n")
                    break

                rts = client.test_stop_session()
                print(f'{"Stop session:":<25}{rts.name}')
                if rts != Status.Ok:
                    print(f"test_stop_session failed: {rts.name} ({rts})")
                    break

            time.sleep(0.1)
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
