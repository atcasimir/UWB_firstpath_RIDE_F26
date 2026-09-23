#
# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

cmake_minimum_required(VERSION 3.20)

set(EXAMPLES_PATH ${CMAKE_SOURCE_DIR}/API/Src)
set(TESTS_PATH ${CMAKE_SOURCE_DIR}/API/Src/tests)

# Add drivers and building platforms
if(BUILDING_PLATFORM STREQUAL "nrf52840")
    message("Building for nRF52840-DK")
    set(PLATFORM_SPECIFIC_FILES_PATH ${BUILDING_PLATFORMS_PATH}/Build_Platforms/nRF52840-DK)
    set(LINKER_SCRIPT_OUT ${PLATFORM_SPECIFIC_FILES_PATH}/Setup/nrf52840_linker.ld)
    set(LINKER_SCRIPT_IN ${PLATFORM_SPECIFIC_FILES_PATH}/Setup/nrf52840_linker.ld.in)
# TODO: Add other building platforms
endif()

# Configure the linker script
configure_file(${LINKER_SCRIPT_IN}
    ${LINKER_SCRIPT_OUT} @ONLY)

set(CMAKE_EXE_LINKER_FLAGS
    "${CMAKE_EXE_LINKER_FLAGS} -T ${LINKER_SCRIPT_OUT} -nostartfiles")

add_subdirectory(${TESTS_PATH}/automated_tests)
add_subdirectory(${PLATFORM_SPECIFIC_FILES_PATH}) 