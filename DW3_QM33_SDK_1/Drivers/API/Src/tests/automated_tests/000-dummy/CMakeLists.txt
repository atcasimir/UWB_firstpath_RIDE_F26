#
# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

cmake_minimum_required(VERSION 3.20)

set(TEST_TARGET test_dummy)
set(TEST_TARGET_ELF ${TEST_TARGET}.elf)
set(TEST_TARGET_MAP ${TEST_TARGET}.map)
set(TEST_TARGET_HEX ${TEST_TARGET}.hex)

add_hex_target(${TEST_TARGET_ELF} ${TEST_TARGET_HEX})

# Source and header files 
set(TEST_TARGET_SOURCES
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/mdk/system_nrf52840.c
    ${TESTS_PATH}/automated_tests/000-dummy/dummy.c
    ${TESTS_PATH}/automated_tests/000-dummy/main.c
)   

set(TEST_TARGET_HEADERS_DIR
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/toolchain/cmsis/include
)

# Create the target
add_executable(${TEST_TARGET_ELF})

target_sources(${TEST_TARGET_ELF} PRIVATE
	${TEST_TARGET_SOURCES}
)

target_include_directories(${TEST_TARGET_ELF}
    PRIVATE
    ${TEST_TARGET_HEADERS_DIR}
    .
)

target_link_libraries(${TEST_TARGET_ELF}
    PRIVATE
    nrf52840_startup
    c
    chelpers
    rtt_io
)

target_compile_definitions(${TEST_TARGET_ELF}
    PRIVATE
    NRF52840_XXAA
)

target_link_options(${TEST_TARGET_ELF}
    PRIVATE
    -Wl,-Map=$<TARGET_FILE_DIR:${TEST_TARGET_ELF}>/${TEST_TARGET_MAP}
)

set_target_properties(${TEST_TARGET_ELF}
    PROPERTIES LINK_DEPENDS
    ${LINKER_SCRIPT_OUT}
)