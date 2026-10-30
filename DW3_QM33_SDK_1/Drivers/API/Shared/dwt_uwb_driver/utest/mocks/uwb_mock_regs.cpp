/* 
 * SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
 * SPDX-License-Identifier: LicenseRef-QORVO-2
 */

#include "uwb_mock_regs.h"
#include <string.h>

/* An array to keep all the mocked UWB block registers */
uint8_t uwb_mock_reg_space[UWB_REGS_SPACE_SIZE];

void uwb_mock_regs_clear(void) {
    memset(uwb_mock_reg_space, 0, UWB_REGS_SPACE_SIZE);

#ifdef USE_DRV_DW3000
	uwb_mock_reg_space[0] = 0x12;
#elif  defined(USE_DRV_DW3720)
	uwb_mock_reg_space[0] = 0x14;
#endif    
    uwb_mock_reg_space[1] = 0x03;
    uwb_mock_reg_space[2] = 0xCA;
    uwb_mock_reg_space[3] = 0xDE;
}
