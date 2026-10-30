#
# SPDX-FileCopyrightText: Copyright (c) 2025 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

set(SRC
    test_regs.cpp
    ${MOCKS_PATH}/platform_mocks.cpp
    ${MOCKS_PATH}/uwb_mock_regs.cpp
    )

add_executable(test_regs ${SRC})

target_include_directories(test_regs PRIVATE
    ${MOCKS_PATH}
    ${UWB_DRV_PATH}/dw3000
    ${UWB_DRV_PATH}/dw3720
)

target_link_libraries(test_regs PUBLIC
    gtest_main
    PRIVATE
    gtest
    uwb_driver
    gmock_main
)

add_test(
    NAME test_regs
    COMMAND test_regs
)

