#
# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

cmake_minimum_required(VERSION 3.20)

set(TEST_TARGET test_pll_cal)
set(TEST_TARGET_ELF ${TEST_TARGET}.elf)
set(TEST_TARGET_MAP ${TEST_TARGET}.map)
set(TEST_TARGET_HEX ${TEST_TARGET}.hex)

# Source and header files 
set(TEST_TARGET_SOURCES
    ${TESTS_PATH}/automated_tests/test_common.c
    ${TESTS_PATH}/automated_tests/test_pll_cal/test_pll_cal.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/platform/deca_mutex.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/platform/deca_probe_interface.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/platform/deca_sleep.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/platform/deca_spi.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/platform/port.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/mdk/system_nrf52840.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/integration/nrfx/legacy/nrf_drv_spi.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/drivers/src/nrfx_gpiote.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/drivers/src/prs/nrfx_prs.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/drivers/src/nrfx_spim.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/util/app_error.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/util/app_error_handler_gcc.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/util/app_error_weak.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/util/app_util_platform.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/atomic/nrf_atomic.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/balloc/nrf_balloc.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/log/src/nrf_log_frontend.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/memobj/nrf_memobj.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/strerror/nrf_strerror.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/boards/boards.c
)   

set(TEST_TARGET_HEADERS_DIR
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/toolchain/cmsis/include
    ${TESTS_PATH}/automated_tests
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/platform
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/config
    ${EXAMPLES_PATH}/examples/shared_data
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/drivers_nrf/nrf_soc_nosd
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/boards
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/balloc
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/ringbuf
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/log
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/log/src
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/memobj
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/util
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/atomic
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/delay
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/experimental_section_vars
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/strerror
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/hal
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/mdk
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/drivers/include
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/integration/nrfx
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/integration/nrfx/legacy
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/external/fprintf
    ${BUILDING_PLATFORMS_PATH}/Src
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
    uwb_driver
)

target_compile_definitions(${TEST_TARGET_ELF}
    PRIVATE
    NRF52840_XXAA
    BOARD_PCA10056
    ${TARGET_ADDITIONAL_DEFINITIONS}
)

target_link_options(${TEST_TARGET_ELF}
    PRIVATE
    -Wl,-Map=$<TARGET_FILE_DIR:${TEST_TARGET_ELF}>/${TEST_TARGET_MAP}
)

set_target_properties(${TEST_TARGET_ELF}
    PROPERTIES LINK_DEPENDS
    ${LINKER_SCRIPT_OUT}
)

get_test_hex(
    ${TEST_TARGET_ELF} 
    ${TEST_TARGET_HEX} 
    ${CMAKE_CURRENT_SOURCE_DIR}
)