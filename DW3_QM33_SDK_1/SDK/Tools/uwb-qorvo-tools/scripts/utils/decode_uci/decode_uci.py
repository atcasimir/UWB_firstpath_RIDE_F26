#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

import argparse
import sys

from uci import UciMessage
from uqt_utils.utils import uqt_errno

# Below hack sometimes required when operating on windows git-bash/msys2
sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")


epilog = """
Note:
    Bytes stream is expected to be a series of bytes numbered 1, 2, ...3
    each bytes may be separated by nothing, a blank (' '), a dot ('.') or a colon (':')
    Watchout: blank separated bytes should be enclosed between ' '.

Example:
    decode_uci 20.02.00.00
    decode_uci '20 02 00 00'
    decode_uci 410300020000 41.00.00.01.00  61.02.00.06.2a.00.00.00.00.00
"""


def main():
    parser = argparse.ArgumentParser(
        description="Decode a byte stream into human-readable UCI fields.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        "--description",
        action="store_true",
        help="show short description of the script",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="./tmp.csv",
        help="output file path. (default: %(default)s)",
    )
    parser.add_argument(
        "bytes",
        nargs="*",
        type=str,
        help="byte stream. See the note for syntax supported.",
    )

    args = parser.parse_args()

    if args.description:
        print(parser.description)
        sys.exit(0)

    # Build the parameter type arguments:
    for v in args.bytes:
        v2 = v.replace(":", "").replace(".", "").replace(" ", "")
        if len(v2) % 2 != 0:
            print(
                f'Error while parsing "{v}":\n    Expecting an even number of half-hex.'
                "\n    Unable to convert to a bytestream  "
            )
            sys.exit(uqt_errno(2))
        try:
            b = bytes.fromhex(v2)
        except ValueError:
            print(
                f'Error while parsing "{v}":\n    Unable to convert to a bytestream  '
            )
            sys.exit(uqt_errno(2))
        try:
            print(UciMessage(b))
        except Exception as e:
            print(f"Error: decoding failed. {e}")


if __name__ == "__main__":
    main()
