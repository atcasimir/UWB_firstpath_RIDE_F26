#
# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

cmake_minimum_required(VERSION 3.13)

# RTT buffers size configuration
set(CONFIG_RTT_BUFFER_SIZE_UP 1024 CACHE STRING "RTT uplink buffer size")
set(CONFIG_RTT_BUFFER_SIZE_DOWN 256 CACHE STRING "RTT downlink buffer size")

# Interrupt priority to lock on SEGGER_RTT_LOCK
# Higher priority = lower priority number
set(CONFIG_SEGGER_RTT_MAX_INTERRUPT_PRIORITY 32 CACHE STRING "Interrupt priority to lock on SEGGER_RTT_LOCK")

# Blocking or non-blocking mode
set(CONFIG_SEGGER_RTT_MODE_DEFAULT SEGGER_RTT_MODE_NO_BLOCK_SKIP CACHE STRING "Blocking or non-blocking mode")
set_property(CACHE CONFIG_SEGGER_RTT_MODE_DEFAULT PROPERTY STRINGS
             "SEGGER_RTT_MODE_NO_BLOCK_SKIP" "SEGGER_RTT_MODE_NO_BLOCK_TRIM" "SEGGER_RTT_MODE_BLOCK_IF_FIFO_FULL")

add_library(segger_rtt STATIC EXCLUDE_FROM_ALL)

target_include_directories(segger_rtt 
    PUBLIC RTT Config
)

target_compile_definitions(segger_rtt PUBLIC
    BUFFER_SIZE_UP=${CONFIG_RTT_BUFFER_SIZE_UP}
    BUFFER_SIZE_DOWN=${CONFIG_RTT_BUFFER_SIZE_DOWN}
    SEGGER_RTT_MAX_INTERRUPT_PRIORITY=${CONFIG_SEGGER_RTT_MAX_INTERRUPT_PRIORITY}
    SEGGER_RTT_MODE_DEFAULT=${CONFIG_SEGGER_RTT_MODE_DEFAULT}
)

target_sources(segger_rtt PRIVATE
    RTT/SEGGER_RTT.c
    RTT/SEGGER_RTT_ASM_ARMv7M.S
)

target_link_libraries(segger_rtt PRIVATE c)
