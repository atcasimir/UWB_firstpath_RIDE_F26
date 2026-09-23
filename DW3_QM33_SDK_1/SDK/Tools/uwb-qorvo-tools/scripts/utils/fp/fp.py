#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

import argparse
import sys

from uci import FP


class PrintDescription(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs):
        return super().__init__(
            option_strings, dest, nargs=0, default=argparse.SUPPRESS, **kwargs
        )

    def __call__(self, parser, namespace, values, option_string, **kwargs):
        print(parser.description)
        parser.exit()


def main():
    parser = argparse.ArgumentParser(
        description="Convert a float to fixpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="",
    )
    parser.add_argument(
        "--description",
        action=PrintDescription,
        help="show short description of the script",
    )
    parser.add_argument(
        "-r",
        "--reverse",
        action="store_true",
        help="convert a fix point to float instead (default: %(default)s)",
        default=False,
    )
    parser.add_argument(
        "v",
        metavar="V",
        type=str,
        help="Value to convert. May be an int, float, or bytearray",
    )
    parser.add_argument(
        "-s",
        "--signed",
        action="store_true",
        default=False,
        help="Presence of sign bit",
    )
    parser.add_argument(
        "i", metavar="I", type=int, help="Number of bits for the integer part"
    )
    parser.add_argument(
        "f",
        metavar="F",
        type=int,
        help="Number of bits for the fractional part",
        default=0,
    )

    args = parser.parse_args()

    try:
        if args.reverse:
            x = int(args.v, 16 if args.v[1:2] == "x" else 10)
            print(FP(x, args.signed, args.i, args.f).as_float())
        else:
            x = eval(args.v)
            if isinstance(x, int):
                x = float(x)
            print(f"{FP(x, args.signed, args.i, args.f).as_hex()}")
    except Exception as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
