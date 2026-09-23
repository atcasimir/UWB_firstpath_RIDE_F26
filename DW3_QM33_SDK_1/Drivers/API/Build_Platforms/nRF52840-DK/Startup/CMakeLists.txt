#
# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

cmake_minimum_required(VERSION 3.13.1)


add_library(nrf52840_startup STATIC EXCLUDE_FROM_ALL)

target_sources(nrf52840_startup PRIVATE 
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/mdk/ses_startup_nrf52840.s
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/mdk/ses_startup_nrf_common.s
    thumb_crt0.s
)

target_compile_definitions(nrf52840_startup PRIVATE
    ${CONFIG_QM_DEVICE}
)

set_source_files_properties(${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/mdk/ses_startup_nrf52840.s PROPERTIES
	COMPILE_FLAGS "-x assembler-with-cpp")

set_source_files_properties(${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/mdk/ses_startup_nrf_common.s PROPERTIES
	COMPILE_FLAGS "-x assembler-with-cpp")

set_source_files_properties(thumb_crt0.s PROPERTIES
	COMPILE_FLAGS "-x assembler-with-cpp -DINITIALIZE_STACK=1 -DSTACK_CHECK=1")