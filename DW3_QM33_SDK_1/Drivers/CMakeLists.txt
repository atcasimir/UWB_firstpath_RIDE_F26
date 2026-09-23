#
# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

cmake_minimum_required(VERSION 3.20)

# Set the the default build type
set(CMAKE_BUILD_TYPE Debug CACHE STRING "Build type for single-config generators")
message("Build type: ${CMAKE_BUILD_TYPE}")

set(UWB_DRIVER_PATH ${CMAKE_SOURCE_DIR}/API/Shared/dwt_uwb_driver)
set(BUILDING_PLATFORMS_PATH ${CMAKE_SOURCE_DIR}/API)

set(CMAKE_TOOLCHAIN_FILE cmake/arm-none-eabi-gcc.cmake CACHE STRING "Toolchain file")
project(qm33_package VERSION 0.0.1 LANGUAGES C ASM)

# Include CMake important files
include(cmake/config.cmake)
include(cmake/util.cmake)

set(TARGET qm33_fw)
set(TARGET_ELF ${TARGET}.elf)
set(TARGET_HEX ${TARGET}.hex)
set(TARGET_BIN ${TARGET}.bin)
set(TARGET_MAP ${TARGET}.map)

set(TARGET_ADDITIONAL_DEFINITIONS "")   

# Check whether we provided a different UWB config type
if(DEFINED CMAKE_UWB_CONFIG_OPTION)
message("Setting UWB config type to ${CMAKE_UWB_CONFIG_OPTION}")
set(TARGET_ADDITIONAL_DEFINITIONS ${TARGET_ADDITIONAL_DEFINITIONS} CMAKE_UWB_CONFIG_OPTION=${CMAKE_UWB_CONFIG_OPTION})
endif()

if(DEFINED CMAKE_BUILD_EXAMPLE)
message("Building example ${CMAKE_BUILD_EXAMPLE}")
set(TARGET_ADDITIONAL_DEFINITIONS ${TARGET_ADDITIONAL_DEFINITIONS} ${CMAKE_BUILD_EXAMPLE})
endif()

# Add used dw driver
if(USE_DRV_DW3000 EQUAL 1)
    set(TARGET_ADDITIONAL_DEFINITIONS ${TARGET_ADDITIONAL_DEFINITIONS} USE_DRV_DW3000)
endif()
if(USE_DRV_DW3720 EQUAL 1)
    set(TARGET_ADDITIONAL_DEFINITIONS ${TARGET_ADDITIONAL_DEFINITIONS} USE_DRV_DW3720)
endif()
if(AUTO_DW3300Q_DRIVER EQUAL 1)
    message("AUTO_DW3300Q_DRIVER enabled")
    add_definitions(-DAUTO_DW3300Q_DRIVER)
endif()
math(EXPR NB_DW_DRIVERS "${USE_DRV_DW3000} + ${USE_DRV_DW3720}")
if(NB_DW_DRIVERS EQUAL 0)
    message(FATAL_ERROR "At least one dw driver should be defined.")
else()
    MATH(EXPR NB_DW_DRIVERS "${USE_DRV_DW3000} + ${USE_DRV_DW3720}")
    set(TARGET_ADDITIONAL_DEFINITIONS ${TARGET_ADDITIONAL_DEFINITIONS} NB_DW_DRIVERS=${NB_DW_DRIVERS})
endif()

if(DGB_LOG EQUAL 0)
    add_definitions(-D_DGB_LOG)
endif()

if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        set(NRF_LOG_BACKEND_RTT_ENABLED 1)
        set(NRF_LOG_ENABLED 1)
else()
        set(NRF_LOG_BACKEND_RTT_ENABLED 0)
        set(NRF_LOG_ENABLED 0)
endif()

set(TARGET_ADDITIONAL_DEFINITIONS ${TARGET_ADDITIONAL_DEFINITIONS} NRF_LOG_BACKEND_RTT_ENABLED=${NRF_LOG_BACKEND_RTT_ENABLED} NRF_LOG_ENABLED=${NRF_LOG_ENABLED})
message("Additional target definitions: ${TARGET_ADDITIONAL_DEFINITIONS}")

set(DWT_DW3000 ${USE_DRV_DW3000})
set(DWT_DW3720 ${USE_DRV_DW3720})

add_subdirectory(${UWB_DRIVER_PATH})
add_subdirectory(${BUILDING_PLATFORMS_PATH} ${CMAKE_BINARY_DIR}/output)

add_hex_target(${TARGET_ELF} ${TARGET_HEX})
add_bin_target(${TARGET_ELF} ${TARGET_BIN})
