/*! ---------------------------------------------------------------------------
 * @file    test_common.h
 * @brief   Test common functions for the DW3000 driver.
 * 
 * @copyright SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
 *            SPDX-License-Identifier: LicenseRef-QORVO-2
 */

#include <stdint.h>
#include <stdbool.h>
#include "deca_probe_interface.h"
#include "port.h"

bool test_init(void);

void print_test_info(void);

void arm_cyccnt_init(void);

uint32_t get_arm_timestamp(void);