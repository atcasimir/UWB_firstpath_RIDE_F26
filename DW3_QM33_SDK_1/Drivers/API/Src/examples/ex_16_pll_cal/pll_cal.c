/*! ----------------------------------------------------------------------------
 *  @file    pll_cal.c
 *  @brief   PLL Calibration for temperature change example code
 *
 *           This is a simple code example that will continuously monitor the
 *           temperature of the chip. If a significant change in temperature
 *           compared to the initial temperature is detected the PLL will be
 *           re-calibrated. The current temperature is then recorded and the
 *           process is repeated.
 *
 * @author Decawave
 *
 * @copyright SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
 *            SPDX-License-Identifier: LicenseRef-QORVO-2
 *
 */

#include "deca_probe_interface.h"
#include <config_options.h>
#include <deca_device_api.h>
#include <deca_spi.h>
#include <example_selection.h>
#include <math.h>
#include <port.h>
#include <shared_defines.h>
#include <shared_functions.h>

#if defined(TEST_PLL_CAL)

extern void test_run_info(unsigned char *data);

extern dwt_config_t config_options;

/* Example application name */
#define APP_NAME "PLL CAL v1.0"

/*Magnitude change in temperature detected to re-calibrate PLL*/
#define TEMP_DIFF 10

int pll_cal(void)
{
    /* hold initial temperature of chip */
    float startingtemp;

    /* Print application name on the console. */
    test_run_info((unsigned char *)APP_NAME);

    /* Configure SPI rate, DW3000 supports up to 38 MHz */
    port_set_dw_ic_spi_fastrate();

    /* Reset DW IC */
    reset_DWIC(); /* Target specific drive of RSTn line into DW IC low for a period. */

    Sleep(2); // Time needed for DW3000 to start up (transition from INIT_RC to IDLE_RC, or could wait for SPIRDY event)

    /* Probe for the correct device driver. */
    if (dwt_probe((struct dwt_probe_s *)&dw3000_probe_interf) == DWT_ERROR)
    {
        test_run_info((unsigned char *)"PROBE FAILED");
        while (1) { };
    }

    while (!dwt_checkidlerc()) /* Need to make sure DW IC is in IDLE_RC before proceeding */ { };

    if (dwt_initialise(DWT_READ_OTP_ALL) == DWT_ERROR)
    {
        test_run_info((unsigned char *)"INIT FAILED     ");
        while (1) { };
    }

    /* Configure DW IC. See NOTE 1 below*/
    /* if the dwt_configure returns DWT_ERROR either the PLL or RX calibration has failed the host should reset the device */
    if (dwt_configure(&config_options))
    {
        test_run_info((unsigned char *)"CONFIG FAILED     ");
        while (1) { };
    }

    /*Record temperature of chip*/
    startingtemp = dwt_convertrawtemperature(dwt_readtempvbat() >> 8);

    /*Loop forever continuously monitoring temperature of chip and re-calibrate PLL if significant change in temperature is detected*/
    while (1)
    {
        /*checking to see if significant change in temperature has occurred */
        while (fabs(startingtemp - dwt_convertrawtemperature(dwt_readtempvbat() >> 8)) < TEMP_DIFF) { };

        /*Re-calibrate PLL now that a significant change in temperature has occurred*/
        /*BREAKPOINT 1*/
        if (dwt_pll_cal())
        {
            /*BREAKPOINT 2*/
            test_run_info((unsigned char *)"PLL FAILED TO CAL/LOCK     ");
            while (1) { };
        }
        /*BREAKPOINT 3*/
        /*Record new starting temperature*/
        startingtemp = dwt_convertrawtemperature(dwt_readtempvbat() >> 8);
    }
}
#endif
/*****************************************************************************************************************************************************
 * NOTES:
 *
 * 1. Desired configuration by user may be different to the current programmed configuration. dwt_configure is called to set desired
 *    configuration.
 ****************************************************************************************************************************************************/
