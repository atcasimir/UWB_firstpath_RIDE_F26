/*! ----------------------------------------------------------------------------
 *  @file    simple_rx_cir.c
 *  @brief   Simple RX CIR example code
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

#if defined(TEST_SIMPLE_RX_CIR)

extern void test_run_info(unsigned char *data);

#define ARR_SZ(arr) (sizeof(arr)/sizeof(arr[0]))
#define CLEAR_ARRAY(array, size) for(int i = 0; i < size; i++) array[i] = 0

/* Example application name */
#define APP_NAME "SIMPLE RX CIR v1.0"

static uint8_t cir_buf[DWT_CIR_LEN_MAX * 2 * 3];  /* A complex sample takes up to 2 32-bit words */
static char str_to_print[DWT_CIR_LEN_MAX * 2 * 3]; /* Buffer mostly used to print the CIR data in print_cir*/
extern dwt_config_t config_options;

/* 
    Print the CIR data in a format that can be easily plotted.
*/
static void print_cir(uint8_t *buf, int n_samples, dwt_cir_read_mode_e mode) {
    uint8_t *ptr = buf;
    test_run_info((unsigned char *)"\n_________________________________\r\n");
    CLEAR_ARRAY(str_to_print, sizeof(str_to_print));

    if (mode == DWT_CIR_READ_FULL) {
        uint8_t lo_re, mid_re, hi_re, lo_img, mid_img, hi_img;
        uint8_t sign_re, sign_img;
        while(n_samples--){
            lo_re = *ptr++;
            mid_re = *ptr++;
            hi_re = *ptr++;
            sign_re = ((hi_re&0x80) == 0x80) ? 0xFF : 0;
            lo_img = *ptr++;
            mid_img = *ptr++;
            hi_img = *ptr++;
            sign_img = ((hi_img&0x80) == 0x80) ? 0xFF : 0;
            sprintf(str_to_print, "%ld,%ld,", (int32_t)((uint32_t)sign_re<<24 | (uint32_t)hi_re<<16 | (uint32_t)mid_re<<8 | lo_re), (int32_t)((uint32_t)sign_img<<24 | (uint32_t)hi_img<<16 | (uint32_t)mid_img<<8 | lo_img));
            test_run_info((unsigned char *)str_to_print);   
            nrf_delay_ms(1); // Delay to allow the UART to keep up with the data
        }
    }
    else {
        uint8_t lo_re, hi_re, lo_img, hi_img;
        while(n_samples--){
            lo_re = *ptr++;
            hi_re = *ptr++;
            lo_img = *ptr++;
            hi_img = *ptr++;
            sprintf(str_to_print, "%ld,%ld,", "%d,%d,", (int16_t)(hi_re<<8 | lo_re), (int16_t)(hi_img<<8 | lo_img));
            test_run_info((unsigned char *)str_to_print);
            nrf_delay_ms(1); // Delay to allow the UART to keep up with the data
        }
    }
    test_run_info((unsigned char *)"\n_________________________________\r\n");
}

/**
 * Application entry point.
 */
int simple_rx_cir(void)
{
    /* Print application name on the console. */
    test_run_info((unsigned char *)APP_NAME);

    /* Configure SPI rate, DW IC supports up to 38 MHz */
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
        test_run_info((unsigned char *)"INIT FAILED");
        while (1) { };
    }

    /* Enabling LEDs here for debug so that for each RX-enable the D2 LED will flash on DW3000 red eval-shield boards. */
    dwt_setleds(DWT_LEDS_ENABLE | DWT_LEDS_INIT_BLINK);

    int res;

    /* Configure DW IC. */
    /* if the dwt_configure returns DWT_ERROR either the PLL or RX calibration has failed the host should reset the device */
    if (dwt_configure(&config_options))
    {
        test_run_info((unsigned char *)"CONFIG FAILED     ");
        while (1) { };
    }

    /* Get the correct length of the Ipatov CIR*/
    uint32_t n_samples_ipatov;
    if (config_options.rxCode < PCODE_PRF64_START) {
        n_samples_ipatov = DWT_CIR_LEN_IP_PRF16;
    }
    else {
        n_samples_ipatov = DWT_CIR_LEN_IP_PRF64;
    }

    /* Loop forever receiving frames. */
    while (TRUE)
    {
        /* Enable the RX manually immediately. See Note 2. */
        res = dwt_rxenable(DWT_START_RX_IMMEDIATE);
        sprintf(str_to_print, "dwt_rxenable status 0x%x\r\n", res);
        test_run_info((unsigned char *)str_to_print);

        sprintf(str_to_print,"Waiting for a packet ...\r\n");
        test_run_info((unsigned char *)str_to_print);

        /* Poll until data received. See Note 3. */
        uint32_t status_reg;
        waitforsysstatus(&status_reg, NULL, (DWT_INT_RXFCG_BIT_MASK | SYS_STATUS_ALL_RX_ERR), 0);

        if (status_reg & DWT_INT_RXFCG_BIT_MASK){
            uint16_t frame_len;
            uint8_t ranging;

            /* A frame has been received, show its length. */
            frame_len = dwt_getframelength(&ranging); /* Also can check if the ranging bit was set */
            sprintf(str_to_print,"Frame Received len %d\r\n", frame_len);
            test_run_info((unsigned char *)str_to_print);

            sprintf(str_to_print,"Printing Ipatov CIR\r\n");
            test_run_info((unsigned char *)str_to_print);
            
            /* Start reading CIR data from Ipatov offset */
            dwt_acc_idx_e acc_idx = DWT_ACC_IDX_IP_M ;
            
            /*
                Choose the mode you want to print the data:
                    - DWT_CIR_READ_FULL
                    - DWT_CIR_READ_LO
                    - DWT_CIR_READ_MID
                    - DWT_CIR_READ_HI
            */
            dwt_cir_read_mode_e modes = DWT_CIR_READ_FULL; 

            /* Ipatov data */
            int n_samples = n_samples_ipatov;
            dwt_readcir((uint32_t*)cir_buf, acc_idx, 0, n_samples, modes);
            print_cir(cir_buf, n_samples, modes);
            
            /* STS0 data, not always available, it depends on the STS and PDOA mode. */
            CLEAR_ARRAY(cir_buf,sizeof(cir_buf));
            sprintf(str_to_print,"\r\nPrinting STS0 CIR\r\n");
            test_run_info((unsigned char *)str_to_print);
            acc_idx = DWT_ACC_IDX_STS0_M;
            n_samples = DWT_CIR_LEN_STS;
            dwt_readcir((uint32_t*)cir_buf, acc_idx, 0, n_samples, modes);
            print_cir(cir_buf, n_samples, modes);
            
            ///* STS1 data, not always available, it depends on the STS and PDOA mode. */
            CLEAR_ARRAY(cir_buf,sizeof(cir_buf));
            sprintf(str_to_print,"\r\nPrinting STS1 CIR\r\n");
            test_run_info((unsigned char *)str_to_print);
            acc_idx = DWT_ACC_IDX_STS1_M;
            dwt_readcir((uint32_t*)cir_buf, acc_idx, 0, n_samples, modes);
            print_cir(cir_buf, n_samples, modes);

            /* Clear good RX frame event in the DW IC status register. */
            dwt_writesysstatuslo(DWT_INT_RXFCG_BIT_MASK);
        }else{
            /* Clear RX error events in the DW IC status register. */
            dwt_writesysstatuslo(SYS_STATUS_ALL_RX_ERR);
            sprintf(str_to_print,"RX error\r\n");
            test_run_info((unsigned char *)str_to_print);
        }
    }

}
#endif
/*****************************************************************************************************************************************************
 * NOTES:
 *
 * 1. In this example, maximum frame length is set to 127 bytes which is 802.15.4 UWB standard maximum frame length. DW IC supports an extended
 *    frame length (up to 1023 bytes long) mode which is not used in this example.
 * 2. Manual reception activation is performed here but DW IC offers several features that can be used to handle more complex scenarios or to
 *    optimise system's overall performance (e.g. timeout after a given time, automatic re-enabling of reception in case of errors, etc.).
 * 3. We use polled mode of operation here to keep the example as simple as possible, but RXFCG and error/timeout status events can be used to generate
 *    interrupts. Please refer to DW IC User Manual for more details on "interrupts".
 ****************************************************************************************************************************************************/
