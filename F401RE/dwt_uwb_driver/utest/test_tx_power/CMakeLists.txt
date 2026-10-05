#
# SPDX-FileCopyrightText: Copyright (c) 2025 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

set(SRC
    test_tx_power.cc
    ${MOCKS_PATH}/platform_mocks.cpp
    ${MOCKS_PATH}/uwb_mock_regs.cpp
    )

add_executable(test_tx_power ${SRC})

target_include_directories(test_tx_power PRIVATE
    ${MOCKS_PATH}
)

target_link_libraries(test_tx_power PUBLIC
    gtest_main
    PRIVATE
    gtest
    uwb_driver
    gmock_main
)

add_test(
    NAME test_tx_power
    COMMAND test_tx_power
)
