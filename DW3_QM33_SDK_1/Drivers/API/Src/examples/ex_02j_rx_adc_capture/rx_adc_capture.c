/*! ----------------------------------------------------------------------------
 *  @file    rx_adc_capture.c
 *  @brief   This test captures the ADC samples on receiving a signal (and reads 
 *           the captured ADC buffer into a file - Only on Nordic EVB).
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
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#if defined(TEST_RX_ADC_CAPTURE)

#define NRF_PRINT_TO_FILE 0    // Only for Nordic nRF If enabled, result is saved in "simple-examples\API\Build_Platforms\nRF52840-DK"
#define COMPLEX_SAMPLES (256)  // Maximum length of buffer is 200 Bytes
#define NUM_THRESH      (4)    // Number of thresholds read

extern void test_run_info(unsigned char *data);
extern void dwt_capture_adc_samples(dwt_capture_adc_t *capture_adc);
extern void dwt_read_adc_samples(dwt_capture_adc_t *capture_adc);
extern dwt_config_t config_options;

/* Example application name and version to print to the console. */
#define APP_NAME "TEST_RX_ADC_CAPTURE"

/**
 * Application entry point.
 */
int rx_adc_capture(void)
{
    int8_t adc_results[COMPLEX_SAMPLES]; 
    dwt_capture_adc_t capture_adc;

    capture_adc.length = COMPLEX_SAMPLES;
    capture_adc.sample_start_offset = 0;
    capture_adc.test_mode_wrap = 1;
    capture_adc.buffer = adc_results;

    /* Print application name on the console. */
    test_run_info((unsigned char *)APP_NAME);

    /* DW3000 chip can run from high speed from start-up.*/
    port_set_dw_ic_spi_fastrate();

    /* Reset and initialize DW chip. */
    reset_DWIC(); /* Target specific drive of RSTn line into DW3000 low for a period. */

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
        test_run_info((unsigned char *)"INIT FAILED");
        while (TRUE) { };
    }

    /* Configure DW IC. See NOTE 1 below. */
    /* if the dwt_configure returns DWT_ERROR either the PLL or RX calibration has failed the host should reset the device */
    if (dwt_configure(&config_options))
    {
        test_run_info((unsigned char *)"CONFIG FAILED     ");
        while (1) { };
    }

    // Capture ADC samples
    dwt_capture_adc_samples(&capture_adc);
    
#if PRINT_TO_FILE
    int i = 0, j = 0;
    printf("\nThresholds: %d, %d, %d, %d\n", (int)capture_adc.thresholds[0], (int)capture_adc.thresholds[1], (int)capture_adc.thresholds[2], (int)capture_adc.thresholds[3]);
    
    FILE *fp1 = fopen("I_Q_DATA_E0.csv", "w+");

    // Reading the buffer 128 times with an offset of 96 because inside the dwt_read_adc_samples()
    // We right shift the 256 by 4 = 16 and multiply by 6 (num_bytes = 16*6 = 96) and pass the num_bytes
    // To ull_readaccdata(). From 96 bytes the format is of each 6 bytes: Ipos, Ineg, 0, Qpos, Qneg, 0
    // Ignoring the zeros, from 4 bytes of Ipos, Ineg, Qpos, Qneg we get 16 bytes of data. 
    // 8 bytes for I and 8 bytes Q in total 16 bytes. Loop over 16 times i.e 16*16 = 256 bytes of data.
    // For 256 Complex Samples we have 128 I and 128 Q results in file for post processing.
    // Total number of samples read are 128*128 = 16384 for each I and Q total 32768 samples.
    for(j = 0; j < COMPLEX_SAMPLES >> 1; j++)
    {
       // Read the captured ADC samples
       dwt_read_adc_samples(&capture_adc);
       capture_adc.sample_start_offset += 96;
       
       for(i = 0; i < COMPLEX_SAMPLES; i+=2)
       {
           fprintf(fp1, "%d, %d\n", (int)capture_adc.buffer[i], (int)capture_adc.buffer[i+1]);
       }
    }
    fclose(fp1);
#endif

    return 0;
}
#endif

/*****************************************************************************************************************************************************
 * NOTES:
 * 
 * 1. Desired configuration by user may be different to the current programmed configuration. dwt_configure is called to set desired
 *    configuration.
 * 
 * TODO: Correct and/or required notes for this example can be added later.
 ****************************************************************************************************************************************************/
