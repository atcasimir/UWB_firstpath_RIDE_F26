/* 
 * SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
 * SPDX-License-Identifier: LicenseRef-QORVO-2
 */

#ifndef UWB_MOCK_REGS_H
#define UWB_MOCK_REGS_H

#include <stdint.h>

// Size of the UWB block registers
#define UWB_REGS_SPACE_SIZE 0x200000

extern uint8_t uwb_mock_reg_space[];
#define MOCK_UWB_ADDR_OFFSET ((uintptr_t)uwb_mock_reg_space)
void uwb_mock_regs_clear(void);

#endif // UWB_MOCK_REGS_H

