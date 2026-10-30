#!/usr/bin/env python3

# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

import os
import sys
import subprocess
import argparse
import colorama
import toml


def find_pyproject_toml(start_path="."):
    current_dir = start_path
    while current_dir != "/":
        if "pyproject.toml" in os.listdir(current_dir):
            return os.path.join(current_dir, "pyproject.toml")
        current_dir = os.path.dirname(current_dir)
    return None


def main():
    parser = argparse.ArgumentParser(description="List available tools")
    parser.add_argument(
        "--description",
        action="store_true",
        help="show short description of the script",
    )
    args = parser.parse_args()

    if args.description:
        print(parser.description)
        sys.exit(0)

    colorama.init()

    this_script_dir = os.path.dirname(os.path.abspath(os.path.normpath(__file__)))
    pyproject_path = find_pyproject_toml(start_path=this_script_dir)

    if not pyproject_path:
        print("pyproject.toml not found in any parent directory.")
        sys.exit(0)

    pyproject = toml.load(pyproject_path)
    for filename in pyproject["tool"]["poetry"]["scripts"].keys():
        try:
            result = subprocess.run(
                f"{filename} --description",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
            )
            if result.returncode == 0:
                print(f"-> {filename:40s} {result.stdout.strip()}")
            else:
                print(
                    f"{colorama.Fore.RED}-> {filename:40s} Error or "
                    f"not supported.{colorama.Style.RESET_ALL}"
                )
        except Exception as e:
            print(f"Error executing {filename}: {str(e)}")

    print(
        f"{colorama.Fore.YELLOW}WARNING! Above tools are delivered by Qorvo "
        f"as UCI examples and are not optimized nor meant to be used for "
        f"final production.{colorama.Style.RESET_ALL}"
    )


if __name__ == "__main__":
    main()
