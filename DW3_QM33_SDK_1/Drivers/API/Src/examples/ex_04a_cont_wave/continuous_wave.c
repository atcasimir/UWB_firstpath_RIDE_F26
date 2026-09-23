/*! ----------------------------------------------------------------------------
 *  @file    continuous_wave.c
 *  @brief   Continuous wave mode example code
 *
 *           This example code activates continuous wave mode on channel 5 for 2 minutes before stopping operation.
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
#include <port.h>

#if defined(TEST_CONTINUOUS_WAVE)

extern void test_run_info(unsigned char *data);

/* Example application name and version to print to the console. */
#define APP_NAME "CONT WAVE v1.0"

/* Continuous wave duration, in milliseconds. */
#define CONT_WAVE_DURATION_MS 120000

/* Recommended TX power and Pulse Generator delay values for the mode defined above. */
/* Power configuration has been specifically set for DW3000 B0 rev devices. See NOTE 1 below.  */
extern dwt_txconfig_t txconfig_options;
extern dwt_txconfig_t txconfig_options_ch9;
extern dwt_config_t config_options;

/**
 * Application entry point.
 */
int continuous_wave_example(void)
{
    /* Print application name on the console. */
    test_run_info((unsigned char *)APP_NAME);

    /* Configure SPI rate, DW3000 supports up to 38 MHz */
    port_set_dw_ic_spi_fastrate();

    /* Reset DW IC */
    reset_DWIC(); /* Target specific drive of RSTn line into DW IC low for a period. */

    Sleep(2); // Time needed for DW3000 to start up (transition from INIT_RC to IDLE_RC

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

    /* Configure DW IC. See NOTE 2 below. */
    /* if the dwt_configure returns DWT_ERROR either the PLL or RX calibration has failed the host should reset the device */
    if (dwt_configure(&config_options))
    {
        test_run_info((unsigned char *)"CONFIG FAILED     ");
        while (1) { };
    }
    
    if(config_options.chan == 9)
    {
      dwt_configuretxrf(&txconfig_options_ch9);
    }
    else
    {
      dwt_configuretxrf(&txconfig_options);
    }

    /* Activate continuous wave mode. */
    dwt_configcwmode();

    /* Wait for the wanted duration of the continuous wave transmission. */
    Sleep(CONT_WAVE_DURATION_MS);

    /* Software reset of the DW IC to deactivate continuous wave mode and go back to default state. Initialisation and configuration should be run
     * again if one wants to get the DW IC back to normal operation. */
    dwt_softreset(1);

    /* End here. */
    while (1) { };
}
#endif
/*****************************************************************************************************************************************************
 * NOTES:
 *
 * 1. In a real application, for optimum performance within regulatory limits, it may be necessary to set TX pulse bandwidth and TX power, (using
 *    the dwt_configuretxrf API call) to per device calibrated values saved in the target system or the DW IC OTP memory.
 * 2. Desired configuration by user may be different to the current programmed configuration. dwt_configure is called to set desired
 *    configuration.
 ****************************************************************************************************************************************************/
