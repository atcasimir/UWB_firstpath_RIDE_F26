#
# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

cmake_minimum_required(VERSION 3.13)

add_library(chelpers STATIC EXCLUDE_FROM_ALL)

target_sources(chelpers PRIVATE 
    libc_hooks.c
)
target_link_libraries(chelpers PRIVATE qosal)
