/*! ----------------------------------------------------------------------------
 *  @file    simple_tx_sts_sdc.c
 *  @brief   Simple TX example code that utilises the STS with deterministic code
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
#include <string.h>

#if defined(TEST_SIMPLE_TX_STS_SDC)

extern void test_run_info(unsigned char *data);

/* Example application name */
#define APP_NAME "TX 4Z STS v1.0"

/* The frame sent in this example is a data frame encoded as per the IEEE 802.15.4-2011 standard. It is a 27-byte frame composed of the following
 * fields:
 *     - byte 0/1: frame control (0x8841 to indicate a data frame using 16-bit addressing and not requesting ACK).
 *       - bits 0-2: Frame Type: 001 - Data frame
 *       - bit 3: Security Enabled: 0 - No security enabled
 *       - bit 4: Frame Pending: 0 - No additional data for recipient
 *       - bit 5: AR: 0 - No ACK frame required from recipient device on receipt of data frame
 *       - bit 6: PAN ID Compression: 1 - PAN IDs are identical, Source PAN ID field shall be omitted from transmitted frame
 *       - bit 7: Reserved: 0
 *       - bit 8: Sequence Number Suppression: 0 - Sequence number field is present
 *       - bit 9: IE Present: 1 - IEs contained in frame
 *       - bits 10-11: Destination Addressing Mode: 10 - Address field contains short address
 *       - bits 12-13: Frame Version: 00 - Using IEEE Std 802.15.4-2003 frames
 *       - bits 14-15: Source Addressing Mode: 10 - Include source address in frame
 *     - byte 2: sequence number, incremented for each new frame.
 *     - byte 3/4: PAN ID (0xDECA) 
 *     - byte 5/6: destination address, see NOTE 8 below.
 *     - byte 7/8: source address, see NOTE 7 below.
 *     - byte 9 to 24: MAC payload, see NOTE 6 below.
 *     - byte 25/26: frame check-sum, automatically set by DW IC. */
static uint8_t tx_msg[] = { 0x41, 0x88, 0, 0xCA, 0xDE, 'X', 'R', 'X', 'T', 'D', 'A', 'T', 'A', 0, 0 };
/* Index to access the sequence number of the data frame in the tx_msg array. */
#define FRAME_SN_IDX      2
#define FRAME_PAYLOAD_IDX 9

#define FRAME_LENGTH (sizeof(tx_msg) + FCS_LEN) // The real length that is going to be transmitted

/* Inter-frame delay period, in milliseconds. */
#define TX_DELAY_MS 500

/* Values for the PG_DELAY and TX_POWER registers reflect the bandwidth and power of the spectrum at the current
 * temperature. These values can be calibrated prior to taking reference measurements. See NOTE 1 below. */
extern dwt_txconfig_t txconfig_options;
extern dwt_config_t config_options;

/**
 * Application entry point.
 */
int simple_tx_sts_sdc(void)
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

    /* Enabling LEDs here for debug so that for each TX the D1 LED will flash on DW3000 red eval-shield boards. */
    dwt_setleds(DWT_LEDS_ENABLE | DWT_LEDS_INIT_BLINK);

    /* Configure DW IC. See NOTE 8 below. */
    /* if the dwt_configure returns DWT_ERROR either the PLL or RX calibration has failed the host should reset the device */
    if (dwt_configure(&config_options))
    {
        test_run_info((unsigned char *)"CONFIG FAILED     ");
        while (1) { };
    }

    /* Configure the TX spectrum parameters (power, PG delay and PG count) */
    dwt_configuretxrf(&txconfig_options);

    /* can enable TX/RX states output on GPIOs 5 and 6 to help debug */
    dwt_setlnapamode(DWT_LNA_ENABLE | DWT_PA_ENABLE);

    /* Loop forever sending frames periodically. */
    while (1)
    {
        /* Write frame data to DW IC and prepare transmission. See NOTE 2 below.*/
        dwt_writetxdata(FRAME_LENGTH - FCS_LEN, tx_msg, 0); /* Zero offset in TX buffer. */

        /*
         * In this example, since the length of the transmitted frame does not change,
         * nor the other parameters of the dwt_writetxfctrl function, the
         * dwt_writetxfctrl call could be outside the main while(1) loop.
         */
        dwt_writetxfctrl(FRAME_LENGTH, 0, 0); /* Zero offset in TX buffer, no ranging. */

        /* Start transmission. */
        dwt_starttx(DWT_START_TX_IMMEDIATE);
        /* Poll DW IC until TX frame sent event set. See NOTE 3 below.
         * STATUS register is 4 bytes long but, as the event we are looking at is in the first byte of the register, we can use this simplest API
         * function to access it.*/
        waitforsysstatus(NULL, NULL, DWT_INT_TXFRS_BIT_MASK, 0);

        /* Clear TX frame sent event. */
        dwt_writesysstatuslo(DWT_INT_TXFRS_BIT_MASK);

        /* Execute a delay between transmissions. */
        Sleep(TX_DELAY_MS);

        /* Increment the blink frame sequence number (modulo 256). */
        tx_msg[FRAME_SN_IDX]++;
    }
}

#endif
/*****************************************************************************************************************************************************
 * NOTES:
 *
 * 1. In a real application, for optimum performance within regulatory limits, it may be necessary to set TX pulse bandwidth and TX power, (using
 *    the dwt_configuretxrf API call) to per device calibrated values saved in the target system or the DW IC OTP memory.
 * 2. dwt_writetxdata() takes the full size of tx_msg as a parameter but only copies (size - 2) bytes as the check-sum at the end of the frame is
 *    automatically appended by the DW IC. This means that our tx_msg could be two bytes shorter without losing any data (but the sizeof would not
 *    work anymore then as we would still have to indicate the full length of the frame to dwt_writetxdata()).
 * 3. We use polled mode of operation here to keep the example as simple as possible but the TXFRS status event can be used to generate an interrupt.
 *    Please refer to DW IC User Manual for more details on "interrupts".
 * 4. This example code functions in the same manner as the simple_tx.c test code, however it uses the STS that was introduced in IEEE 802.15.4z
 * 5. Since this example is using the STS, it will be using one of the newer frame formats that were introduced in IEEE 802.15.4z.
 *    It will use packet configuration 1 which looks like so:
 *    ---------------------------------------------------
 *    | Ipatov Preamble | SFD | STS | PHR | PHY Payload |
 *    ---------------------------------------------------
 *    Since this example is for test purposes only and not meant to illustrate a working use case, we will be sending unencrypted data in the PHY
 *    Payload to the receiver device. This is obviously not recommended in a real use case as it is not a very secure format of data transmission.
 *    However, it is useful to illustrate how a transmitter and receiver will work with one and other at a basic level using the STS.
 *    Also the STS will be using deterministic code thus the receiver will stay in sync with transmitter even in case of missed frames/errored frames.
 *    There are more realistic examples in the code base that utilise STS, ranging and encrypted data payloads for a more complete solution.
 * 6. The frames used here are Decawave specific ranging frames, complying with the IEEE 802.15.4 standard data frame encoding. The frames are the
 *    following:
 *     - a poll message sent by the initiator to trigger the ranging exchange.
 *     - a response message sent by the responder to complete the exchange and provide all information needed by the initiator to compute the
 *       time-of-flight (distance) estimate.
 *    The first 10 bytes of those frame are common and are composed of the following fields:
 *     - byte 0/1: frame control (0x8841 to indicate a data frame using 16-bit addressing).
 *     - byte 2: sequence number, incremented for each new frame.
 *     - byte 3/4: PAN ID (0xDECA).
 *     - byte 5/6: destination address, see NOTE 7 below.
 *     - byte 7/8: source address, see NOTE 7 below.
 *     - byte 9: function code (specific values to indicate which message it is in the ranging process).
 *    The remaining bytes are specific to each message as follows:
 *    Poll message:
 *     - no more data
 *    Response message:
 *     - byte 0 -> 13: poll message reception timestamp.
 *     - byte 4 -> 17: response message transmission timestamp.
 * 7. Source and destination addresses are hard coded constants to keep the example simple but for a real product every device should have a unique ID.
 *    For development purposes it is possible to generate a DW IC unique ID by combining the Lot ID & Part Number values programmed into the DW IC
 *    during its manufacture. However there is no guarantee this will not conflict with someone else's implementation. We recommended that customers
 *    buy a block of addresses from the IEEE Registration Authority for their production items. See "EUI" in the DW IC User Manual.
 * 8. Desired configuration by user may be different to the current programmed configuration. dwt_configure is called to set desired
 *    configuration.
 ****************************************************************************************************************************************************/
