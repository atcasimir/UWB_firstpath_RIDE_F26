
#
# SPDX-FileCopyrightText: Copyright (c) 2025 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#
# Used to build the unit tests for DW3000 and DW3720 and run them
#
set -e

# Function to run unit tests for a given driver
run_unit_test() {
    # Make the argument uppercase
    build_dir='build_'$1
    # Get the device name in capital letters
    DEVICE=$1
    DEVICE=$(echo $DEVICE | tr '[:lower:]' '[:upper:]')
    echo "Running unit tests for $DEVICE"
    # Set the device name as a cmake variable
    cmake -B $build_dir . -DDWT_$DEVICE=1
    # Build the unit tests
    cmake --build $build_dir
    # Run the unit tests
    ctest --test-dir $build_dir/ -j 4 --output-on-failure
}

# Check whether an argument is passed, if no argument is passed
# run script for both DW3000 and DW3720
# Otherwise, check for a valid argument and run the script for that driver
if [ $# -eq 0 ]; then
    run_unit_test dw3000
    run_unit_test dw3720
elif [ $# -eq 1 ]; then
    if [ $1 == "dw3000" ]; then
        run_unit_test dw3000
    elif [ $1 == "dw3720" ]; then
        run_unit_test dw3720
    else
        echo "Invalid argument. Please provide either dw3000 or dw3720"
    fi
else
    echo "Invalid number of arguments. Please provide either dw3000 or dw3720"
fi
