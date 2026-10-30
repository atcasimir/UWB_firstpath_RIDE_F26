#
# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

cmake_minimum_required(VERSION 3.13)

add_library(rtt_io STATIC EXCLUDE_FROM_ALL)

target_include_directories(rtt_io PUBLIC .)
target_sources(rtt_io PRIVATE 
    rtt_io.c
    common_libc_hooks.c
)

target_link_libraries(rtt_io PRIVATE c segger_rtt)