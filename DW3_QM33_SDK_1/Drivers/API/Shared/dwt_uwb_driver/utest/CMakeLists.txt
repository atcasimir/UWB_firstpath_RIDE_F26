#
# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#
cmake_minimum_required(VERSION 3.13)

project(UnitTests C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

set(MOCKS_PATH ${PROJECT_SOURCE_DIR}/mocks)
set(UWB_DRV_PATH ${PROJECT_SOURCE_DIR}/..)
set(GTEST_PATH ${PROJECT_SOURCE_DIR}/googletest)

if(DWT_DW3000)
    add_compile_definitions(USE_DRV_DW3000)
endif()

if(DWT_DW3720)
    add_compile_definitions(USE_DRV_DW3720)
endif()

enable_testing()

add_subdirectory(${UWB_DRV_PATH} uwb_driver)
add_subdirectory(${GTEST_PATH})
add_subdirectory(test_rsl)
add_subdirectory(test_tx_power)
add_subdirectory(test_regs)
