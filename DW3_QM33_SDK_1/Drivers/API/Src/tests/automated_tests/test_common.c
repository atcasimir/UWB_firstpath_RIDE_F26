/*! ---------------------------------------------------------------------------
 * @file    test_common.c
 * @brief   Test common functions for the DW3000 driver.
 * 
 * @copyright SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
 *            SPDX-License-Identifier: LicenseRef-QORVO-2
 */

#include "test_common.h"

#define  ARM_CM_DEMCR      (*(uint32_t *)0xE000EDFC)
#define  ARM_CM_DWT_CTRL   (*(uint32_t *)0xE0001000)
#define  ARM_CM_DWT_CYCCNT (*(uint32_t *)0xE0001004)

bool test_init(void)
{
    /*Configure SPI rate, DW3000 supports up to 38MHz*/
    port_set_dw_ic_spi_fastrate();

    /*Reset DW IC*/
    reset_DWIC(); /* Target specific drive of RSTn line into DW IC low for a period. */

    Sleep(2); // Time needed for DW3000 to start up(transition from INIT_RC to IDLE_RC, or could wait for SPIRDY event)

    /* Probe for correct driver device */
    if(dwt_probe((struct dwt_probe_s *)&dw3000_probe_interf) == DWT_ERROR)
    {
        return false;
    }

    /* Counter for timeout check */
    int idle_rc_check_counter = 0; 

    /* Make sure DW IC is in IDLE before proceeding. If after 5 seconds we are still stuck, return false*/ 
    while (!dwt_checkidlerc()) 
    {
        idle_rc_check_counter++;
        if(idle_rc_check_counter > 50)
        {
            return false;
        }
        Sleep(100);
    };

    /* Initialise the UWB transceiver */
    if(dwt_initialise(DWT_READ_OTP_ALL) == DWT_ERROR)
    {
        return false;
    }
    return true;
}

void print_test_info(void)
{
    printf("QM33 drivers version %s\n", dwt_version_string());

    float curr_temp = dwt_convertrawtemperature(dwt_readtempvbat() >> 8);
    printf("Temperature %1.2f\n", (double)curr_temp);

    /* Retrive and print device ID information */
    uint32_t dev_id, part_id;
    uint64_t lot_id;
    dev_id = dwt_readdevid();
    part_id = dwt_getpartid();
    lot_id = dwt_getlotid();
    printf("Device ID: 0x%08X, Lot ID: 0x%08X, Part ID: 0x%08X\n", dev_id, lot_id, part_id);
}

void arm_cyccnt_init(void) 
{ 
    if (ARM_CM_DWT_CTRL != 0) 
    {   // See if DWT is available 
        ARM_CM_DEMCR |= 1 << 24; // Set bit 24 
        ARM_CM_DWT_CYCCNT = 0; 
        ARM_CM_DWT_CTRL |= 1 << 0; // Set bit 0 
    } 
} 

uint32_t get_arm_timestamp(void) 
{ 
    return ARM_CM_DWT_CYCCNT; 
} 
