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

Note 1: Android parameter files Syntax
    - The length (nbr of bytes) of the byte stream provided should meet
        the expected parameter length.
    - All blanck lines and lines starting with "#" are by passed
    - Below parameters are bypassed:
        'file_format_version', 'file_description'


Note 2: parameter value syntax

    - You may verify your parameter type before setting using:
      set_cal -l | grep <cal param>

    - You may verify the set operation through  read-back using:
      get_cal <cal param>

    - In below specific syntax examples, watch-out for the use of '
      (single quote).

    - Uint8, Uint16, or Uint64 values are set using one of below syntax:
        - natural/decamal format    : set_cal <param> 255
        - hexadecimal value         : set_cal <param> 0x28
        - octal                     : set_cal <param> 0o120
        - binary                    : set_cal <param> 0b101011
        - full descriptive          : using 'Uint16(255)', 'Uint32(0x28)', ...

    - Int8, Int16, or Int64 values are set using one of below syntax:
        - natural/decimal format    : set_cal <param> -2
        - hexadecimal value         : set_cal <param> 0x254
        - octal                     : set_cal <param> 0o120
        - binary                    : set_cal <param> 0b101011
        - full descriptive          : using 'Int16(255)', 'Int32("0x28")', ...
        WARNING:
          - the (stupid) negative hex Python convention is not used (ie hex(-2) = '-0x2).
            refer to below note.
          - decimal (so called 'Natural integer') and 2nd complement 'byte-like' integers
            are handled differently. For example:
            for Uint8,  254 == 0xFe.
            for Int8,   254 != 0xFe. (0xFe == -2)

    - S4_11, .. are fixed point values. They are set using one of below syntax:
        - float value       : set_cal <param> 3.5
        - integer value     : set_cal <param> 4
        - full descriptive  : 'S4_11(3.5589)', 'S4_11(4)', ...
        WARNING:
          - Integers and floats are handled differently (2 != 2.0) :
            - integers are expected to be already coded in fixed point
            - float will be translated to the related fixed-point value.
          - Thus:
            - set_cal <param> 2   ; get_cal -r -> S4_11(0.0009765625)
            - set_cal <param> 2.0 ; get_cal -r -> S4_11(2.0)

    - AoaTable values are set using one of below syntax:
        - using a list of (aoa, pdoa) values in natural format:
            ex: set_cal  <param>  '[ (-3.14, -1.6) , ... , (3.14, 1.6) ]'
        - using a theoretical  pdoa to aoa lut:
            ex: set_cal  <param>  theory channel=9 antenna_dist_mm=20.8
        - without aoa computation (pass-through):
            ex: set_cal  <param>  identity
        - from a csv:
            ex: set_cal  <param>  /tmp/lut.csv
        - A full descriptive format may be used:
            ex:
                set_cal pdoa_lut0.data 'AoATable("theory", channel=9, antenna_dist_mm=20.8)'
                set_cal pdoa_lut0.data 'AoATable("identity")

    - AntConf values are set using one of below syntax:
        - Using aan int:
            set_cal <param> <uint8>
            ex: set_cal ant0.config 0x14
        - Using a descriptive format:
            set_cal <param> <ext_switch> <ant_port>
            with;
                <ext_switch>:   ext_switch.on  or ext_switch.off
                <ant_port>:     ant_port.n1 .. ant_port.n4
            ex: set_cal ant0.config ext_switch.on ant_port.n2
        - A full descriptive format may be used:
            ex: set_cal ant0.config 'AntConf(ext_switch.on, ant_port.n2)'

    - PhyFrame values are set using one of below syntax:
        - a standard pre-defined frame:
            set_cal <param> <frame_name>
            with <frame_name>:  std_frame.bprf3 or std_frame.hprf16
            ex: set_cal ref_frame0.phy_cfg std_frame.bprf3
        - Using a descriptive format:
            set_cal <param> <prf.b> <sfd> <psr> <data> <phr> <sts_n> <sts_len>
            with;
                <prf>:
                    prf.b  prf.h
                <sfd>:
                    sfd.ieee4a     sfd.ieee4z4   sfd.ieee4z8   sfd.ieee4z16
                    sfd.ieee4z32   sfd.rfu       sfd.dw8       sfd.dw16
                <psr>:
                    psr.n16     psr.n24     psr.n32    psr.n48    psr.n64
                    psr.n96     psr.n128    psr.n256   psr.n512   psr.n1024
                    psr.n2048   psr.n4096
                <data>:
                    data.r850k          data.r6m8          data.nodata
                    data.rfu            data.r6m8_128      data.r27m_256
                    data.r6m8_187_k7    data.r27m_256_k7   data.r54m_256
                    data.r108m_256
                <phr>:
                    phr.std   phr.as_data
                <sts_n>:
                    sts_n.n0    sts_n.n1   sts_n.n2
                    sts_n.n3    sts_n.n4
                <sts_len>:
                    sts_len.n0     sts_len.n16     sts_len.n32
                    sts_len.n64    sts_len.n128    sts_len.n256
                    sts_len.n512   sts_len.n1024   sts_len.n2048
            ex1, reconstructing the std_frame.bprf3 frame:
                set_cal ref_frame0.phy_cfg prf.b sfd.ieee4z8  psr.n64 \\
                    data.r6m8 phr.std sts_n.n1 sts_len.n64
            ex2, reconstructing the std_frame.hprf16 frame:
                set_cal ref_frame1.phy_cfg  prf.h sfd.ieee4z8 psr.n32 \\
                    data.r27m_256 phr.std sts_n.n1 sts_len.n32
        - A full descriptive format may be used:
            ex: set_cal ref_frame0.phy_cfg 'PhyFrame(prf.b, sfd.ieee4z8, \\
                    psr.n64, data.r6m8, phr.std, sts_n.n1, sts_len.n64)'
"""


def main():
    default_port = os.getenv("UQT_PORT", "/dev/ttyUSB0")
    parser = argparse.ArgumentParser(
        description="Set a calibration parameter value.",
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
        "-i",
        "--input-file",
        type=str,
        help="recover the list of (key, value) from the provided input file encoded as an android param file.",
    )
    parser.add_argument(
        "key",
        type=str,
        nargs="?",
        default="key",
        help="calibration key. (default: %(default)s)",
    )
    parser.add_argument(
        "value",
        type=str,
        nargs="*",
        default="value",
        help="Calibration value. See below notes for value format. (default: %(default)s)",
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
            rts = Status.Ok

            client = Client(port=args.port)

            if args.list:
                log.info("Recovering all parameters from target...")
                rts, l, rtv = client.test_mode_calibrations_get([])
                if rts != Status.Ok:
                    log.error(
                        f"Getting parameter list failed with status: {rts.name} ({rts})"
                    )
                for k, irts, l, v in rtv:
                    # Decode value:
                    k = k.decode()
                    v = f"??? ({l} bytes)"
                    if k in cal_params.keys():
                        v = cal_params[k].__name__
                    print(f"{k:<40} : {v}")
                break

            """
                Warning: there is no real specifications for this 'Qorvo Middleware Android format'.
                Also below is a tentative-one which is in line with current script parsing.
                2 type of Android files format exists:
                - one dealing with calibration parameters (handled here)
                - one dealing with calibration + other UCI command parameters (handled elsewhere).
                Spec:
                - serie for <key>=<val> (with possible spaces around the '='), with:
                    <key> one of: Middleware params (file_format_version, file_description)
                                or UCI calibration parameter name
                    <val> one of:
                        - bytestream as a comma separated list of bytes: <aa>:<bb>:<cc>:...
                        - only 1 'half-hex' figure
                        - 8-16-32-64 bits integer value in hexadecimal and prefixed with 0x
                    NB:
                        - no other format (decimal, binary, ...) are expected
                        - the number of half hex bytes gives the parameter length.
                - comments are starting with '#'
                - blank lines may exists

                Hack added to reuse Android conf files as Android cal files:
                - comment may be available at end of files
                - files starting with [ should be disregarded
            """

            if args.input_file:
                line_nr = 0
                try:
                    for line in open(args.input_file):
                        line_nr = line_nr + 1
                        line = line.strip()
                        if line == "":
                            continue
                        if line.startswith("#"):
                            continue
                        if line.startswith("["):
                            continue
                        line = line.split(sep="#")[0]
                        k, v = line.split("=")
                        k = k.strip()
                        v = v.strip()
                        if k in ("file_format_version", "file_description"):
                            continue
                        if v.lower().startswith("0x"):
                            vl = len(v) // 2 - 1
                            if 2 * vl + 2 != len(v):
                                log.critical(
                                    f'Bad file format at line {line_nr}: "{k}" not expressed in a even number of half \
                                             hex figures. Got "{v}".'
                                )
                                rts = 2
                                break
                            v = int(v, 16).to_bytes(vl, "little")
                        else:
                            if len(v) == 1:
                                v = f"0{v}"
                            v = bytes.fromhex(v.replace(":", ""))
                        try:
                            irts, dummy = client.test_mode_calibrations_set(
                                [
                                    (k, v),
                                ]
                            )
                            print(f"setting {k:<40} : {irts.name} ({irts})")
                            if irts != Status.Ok:
                                rts = irts
                        except UciComError as e:
                            rts = e.n
                            print(f"setting {k:<40} : {e}")
                    print(f"{rts.name} ({rts.value})")
                    break
                except ValueError as e:
                    log.critical(f"Bad file format at line {l}: {e}")
                    rts = 2
                    break

            # Build the parameter type arguments:
            if args.key not in cal_params.keys():
                log.critical("Unknown parameter (no request done). Quitting")
                rts = 2
                break

            if (len(args.value) == 1) and args.value[0].startswith(
                cal_params[args.key].__name__
            ):
                # We are in a descriptive syntax format.
                v_str = args.value[0]
            else:
                # We are in a short syntax format: let's try to guess...
                v_str = ""
                for v in args.value:
                    try:
                        # convert from  Hex, octal, enum, ...
                        ve = eval(v)
                        if isinstance(ve, int):
                            # convert Ok from  Hex, octal, binary ...
                            v = str(v)
                        else:
                            # An object has been handed over (enum, ...)
                            # let's keep it.
                            pass
                    except Exception:
                        if v.find("=") != -1:
                            # keep the option
                            pass
                        else:
                            # We do have a string:
                            v = "'" + v + "'"
                    v_str = v_str + ", " + v
                v_str = v_str[1:]  # remove initial comma
                v_str = f"{cal_params[args.key].__name__}({v_str})"
            log.debug(f"Using value defined as: {v_str}")

            try:
                value = eval(v_str)
            except SyntaxError:
                log.critical(f'Error in setting {args.key}. Syntax error: "{v_str}"')
                rts = 2
                break
            print(f"setting {args.key} = {value!r} = {value}...")

            rts, dummy = client.test_mode_calibrations_set(
                [
                    (args.key, value),
                ]
            )
            print(f"{rts.name} ({rts.value})")
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
