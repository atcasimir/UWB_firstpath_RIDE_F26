/*! ----------------------------------------------------------------------------
 *  @file    linear_tx_power_example.c
 *  @brief   This example demonstrates how the dwt_calculate_linear_tx_power API allows to calculate tx power
 *           setting with a linear output power behavior.
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
#include <shared_defines.h>
#include <shared_functions.h>

#if defined(TEST_LINEAR_TX_POWER)

extern void test_run_info(unsigned char *data);

/* Example application name and version to print to the console. */
#define APP_NAME "LINEAR_TX_POWER        v1.0 \r\n"

#define STR_SIZE 256

/* The frame sent in this example is an 802.15.4e standard blink. It is a 12-byte frame composed of the following fields:
 *     - byte 0: frame type (0xC5 for a blink).
 *     - byte 1: sequence number, incremented for each new frame.
 *     - byte 2 -> 9: device ID, see NOTE 1 below.
 */
static uint8_t tx_msg[] = { 0xC5, 0, 'D', 'E', 'C', 'A', 'W', 'A', 'V', 'E' };
/* Index to access to sequence number of the blink frame in the tx_msg array. */
#define BLINK_FRAME_SN_IDX 1

#define FRAME_LENGTH (sizeof(tx_msg) + FCS_LEN) // The real length that is going to be transmitted

#define FRAME_DURATION 178 // Frame duration for PLEN 128, 6M8, 12 bytes data

#define TX_DELAY_MS 500

/* Values for the PG_DELAY and TX_POWER registers reflect the bandwidth and power of the spectrum at the current
 * temperature. These values can be calibrated prior to taking reference measurements. See NOTE 2 below. */
extern dwt_txconfig_t txconfig_options;
extern dwt_config_t config_options;

/**
 * Application entry point.
 */
void linear_tx_power_example(void)
{
    dwt_txconfig_t tx_config;

    unsigned char str[STR_SIZE];

    /* Print application name on the console. */
    test_run_info((unsigned char *)APP_NAME);

    /* Configure SPI rate, DW3700 supports up to 38 MHz */
    port_set_dw_ic_spi_fastrate();

    /* Reset DW IC */
    /* Target specific drive of RSTn line into DW IC low for a period. */
    reset_DWIC();

    /* Time needed for DW3700 to start up
     * (transition from INIT_RC to IDLE_RC) */
    Sleep(2);

    /* Probe for the correct device driver. */
    if (dwt_probe((struct dwt_probe_s *)&dw3000_probe_interf) == DWT_ERROR)
    {
        test_run_info((unsigned char *)"PROBE FAILED");
        while (1) { };
    }

    /* Need to make sure DW IC is in IDLE_RC before proceeding */
    while (!dwt_checkidlerc()) { };

    if (dwt_initialise(DWT_READ_OTP_ALL) == DWT_ERROR)
    {
        test_run_info((unsigned char *)"INIT FAILED     ");
        while (1) { };
    }

    /* Configure DW IC. See NOTE 5 below. */
    /* if the dwt_configure returns DWT_ERROR either the PLL or RX calibration has failed the host should reset the device */
    if (dwt_configure(&config_options))
    {
        test_run_info((unsigned char *)"CONFIG FAILED     ");
        while (1) { };
    }

    /*Initial parameters for linear tx power control*/
    power_indexes_t power_indexes = {0};
    tx_adj_res_t linear_results = {0};
    int i = 0;

    /* Loop forever sending frames periodically. */
    while (1)
    {
        dwt_calculate_linear_tx_power((int) config_options.chan, &power_indexes, &linear_results);

        tx_config.power = linear_results.tx_frame_cfg.tx_power_setting;
        tx_config.PGcount = txconfig_options.PGcount;
        tx_config.PGdly = txconfig_options.PGdly;

        Sleep(1000);
        memset(str, 0, STR_SIZE);
        snprintf((char *)str, STR_SIZE, "Input Index:%d; Output Index:%d; Tx_power:%lx Pll_bias %x\r\n", power_indexes.input[0],
                        power_indexes.output[0],
                        linear_results.tx_frame_cfg.tx_power_setting,
                        linear_results.tx_frame_cfg.pll_bias);
        test_run_info(str);
        Sleep(1000);

        /* Configure the TX spectrum parameters (power PG delay and PG Count) */
        dwt_configuretxrf(&tx_config);
        dwt_setpllbiastrim(linear_results.tx_frame_cfg.pll_bias);

        /* Write frame data to DW IC and prepare transmission. See NOTE 3 below.*/
        dwt_writetxdata(FRAME_LENGTH - FCS_LEN, tx_msg, 0); /* Zero offset in TX buffer. */

        /* In this example since the length of the transmitted frame does not change,
         * nor the other parameters of the dwt_writetxfctrl function, the
         * dwt_writetxfctrl call could be outside the main while(1) loop.
         */
        dwt_writetxfctrl(FRAME_LENGTH, 0, 0); /* Zero offset in TX buffer, no ranging. */

        /* Start transmission. */
        dwt_starttx(DWT_START_TX_IMMEDIATE);
        /* Poll DW IC until TX frame sent event set. See NOTE 4 below.
         * STATUS register is 4 bytes long but, as the event we are looking
         * at is in the first byte of the register, we can use this simplest
         * API function to access it.*/
        waitforsysstatus(NULL, NULL, DWT_INT_TXFRS_BIT_MASK, 0);

        /* Clear TX frame sent event. */
        dwt_writesysstatuslo(DWT_INT_TXFRS_BIT_MASK);

        test_run_info((unsigned char *)"TX Frame Sent \r\n");

        /* Execute a delay between transmissions. */
        Sleep(TX_DELAY_MS);

        /* Increment the blink frame sequence number (modulo 256). */
        tx_msg[BLINK_FRAME_SN_IDX]++;
        i++;
        power_indexes.input[0]=i;
        power_indexes.input[1]=i;
        power_indexes.input[2]=i;
        power_indexes.input[3]=i;
    }
}
#endif // TEST_LINEAR_TX_POWER
/*****************************************************************************************************************************************************
 * NOTES:
 * 1. The device ID is a hard coded constant in the blink to keep the example simple but for a real product every device should have a unique ID.
 *    For development purposes it is possible to generate a DW IC unique ID by combining the Lot ID & Part Number values programmed into the
 *    DW IC during its manufacture. However there is no guarantee this will not conflict with someone else's implementation. We recommended that
 *    customers buy a block of addresses from the IEEE Registration Authority for their production items. See "EUI" in the DW IC User Manual.
 * 2. In a real application, for optimum performance within regulatory limits, it may be necessary to set TX pulse bandwidth and TX power, (using
 *    the dwt_configuretxrf API call) to per device calibrated values saved in the target system or the DW IC OTP memory.
 * 3. dwt_writetxdata() takes the full size of tx_msg as a parameter but only copies (size - 2) bytes as the check-sum at the end of the frame is
 *    automatically appended by the DW IC. This means that our tx_msg could be two bytes shorter without losing any data (but the sizeof would not
 *    work anymore then as we would still have to indicate the full length of the frame to dwt_writetxdata()).
 * 4. We use polled mode of operation here to keep the example as simple as possible, but the TXFRS status event can be used to generate an interrupt.
 *    Please refer to DW IC User Manual for more details on "interrupts".
 * 5. Desired configuration by user may be different to the current programmed configuration. dwt_configure is called to set desired
 *    configuration.
 *    For development purposes it is possible to generate a DW IC unique ID by combining the Lot ID & Part Number values programmed into the
 *    DW IC during its manufacture. However there is no guarantee this will not conflict with someone else's implementation. We recommended that
 *    customers buy a block of addresses from the IEEE Registration Authority for their production items. See "EUI" in the DW IC User Manual.
 *    configuration.
 ****************************************************************************************************************************************************/
