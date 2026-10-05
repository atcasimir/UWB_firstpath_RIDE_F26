#
# SPDX-FileCopyrightText: Copyright (c) 2025 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

set(SRC
    test_rsl.cc
    ${MOCKS_PATH}/platform_mocks.cpp
    ${MOCKS_PATH}/uwb_mock_regs.cpp
    )

add_executable(test_rsl ${SRC})

target_include_directories(test_rsl PRIVATE
    ${MOCKS_PATH}
)

target_link_libraries(test_rsl PUBLIC
    gtest_main
    PRIVATE
    gtest
    uwb_driver
)

add_test(
    NAME test_rsl
    COMMAND test_rsl
)
