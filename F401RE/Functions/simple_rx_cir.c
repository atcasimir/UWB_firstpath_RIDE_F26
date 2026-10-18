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
#include <port.h>
#include <shared_defines.h>
#include <shared_functions.h>
#include <stdio.h>

// Print over UART
extern void print(unsigned char *data);

// Get the size of and clear CIR array
#define ARR_SZ(arr) (sizeof(arr)/sizeof(arr[0]))
#define CLEAR_ARRAY(array, size) for(int i = 0; i < size; i++) array[i] = 0

// Application name
#define APP_NAME "CIR and RX_DIAG v.10"

// Buffer for storing and printing CIR 
static uint8_t cir_buf[DWT_CIR_LEN_MAX * 2 * 3];  /* A complex sample takes up to 2 32-bit words */
static char str_to_print[DWT_CIR_LEN_MAX * 2 * 3]; /* Buffer mostly used to print the CIR data in print_cir*/
extern dwt_config_t config_options;
 
// Print the CIR data in a format that can be easily plotted.
static void print_cir(uint8_t *buf, int n_samples, dwt_cir_read_mode_e mode) {
    uint8_t *ptr = buf;
    CLEAR_ARRAY(str_to_print, sizeof(str_to_print));

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
        print((unsigned char *)str_to_print);   
        Sleep(1); // Delay to allow the UART to keep up with the data (was nrf_delay_ms, Nordic-only)
    }
}

static void print_rx_diag(const dwt_rxdiag_t *diag)
{
    char buffer[256];

    snprintf(buffer, sizeof(buffer),
             "RX_DIAG_BEGIN\r\n"
             "%u\r\n"
             "%u\r\n"
             "%u\r\n"
             "%u\r\n"
             "%u\r\n"
             "%u\r\n"
             "%u\r\n"
             "%u\r\n"
             "%u\r\n"
             "%u\r\n"
             "%u\r\n"
             "%u\r\n"
             "RX_DIAG_END",
             (unsigned int)diag->ipatovRxTime[0], // Least significant octet
             (unsigned int)diag->ipatovRxTime[1], 
             (unsigned int)diag->ipatovRxTime[2], // 5 octet (40 bit) timestamp. 8 bits each...
             (unsigned int)diag->ipatovRxTime[3],
             (unsigned int)diag->ipatovRxTime[4], // Most significant octet
             (unsigned int)diag->ipatovRxStatus,  // 8 bits. Sets warning flags based on quality of CIR, reported first-path.
             (unsigned int)diag->ipatovPeak,      // 32 bits. Peak amplitude and index
             (unsigned int)diag->ipatovPower,     // 32 bits. Channel area allows estimation of channel power for the Ipatov sequence
             (unsigned int)diag->ipatovF1,        // 32 bits. Magnitude of sample immediately after first path position
             (unsigned int)diag->ipatovF2,        // 32 bits. Magnitude of sample at second index after first path position
             (unsigned int)diag->ipatovF3,        // 32 bits. Magnitude of sample at third index after first path position
             (unsigned int)diag->ipatovFpIndex    // 16 bits. [10.6] fp format. First path index relative to index 0.
            );

    print((unsigned char *)buffer);
}

// RX_DIAG 
static dwt_deviceentcnts_t event_cnt;
static dwt_rxdiag_t rx_diag;
extern dwt_config_t config_options;

uint32_t measurement_count = 0;

// Entry point
int simple_rx_cir(void)
{
    
    print((unsigned char *)APP_NAME);   // Print application name
    port_set_dw_ic_spi_fastrate();      // Configure SPI rate
    reset_DWIC();                       // Reset DW IC
    Sleep(2);                           // Time needed for DW3000 to start up

    // Probe for correct driver
    if (dwt_probe((struct dwt_probe_s *)&dw3000_probe_interf) == DWT_ERROR)
    {
        print((unsigned char *)"PROBE FAILED");
        while (1) { };
    }

    while (!dwt_checkidlerc()) /* Need to make sure DW IC is in IDLE_RC before proceeding */ { };
    if (dwt_initialise(DWT_READ_OTP_ALL) == DWT_ERROR)
    {
        print((unsigned char *)"INIT FAILED");
        while (1) { };
    }

    // Flash D2 LED
    dwt_setleds(DWT_LEDS_ENABLE | DWT_LEDS_INIT_BLINK);

    int res;

    /* Configure DW IC. */
    /* if the dwt_configure returns DWT_ERROR either the PLL or RX calibration has failed the host should reset the device */
    if (dwt_configure(&config_options))
    {
        print((unsigned char *)"CONFIG FAILED     ");
        while (1) { };
    }

    // RX DIAG
    dwt_configeventcounters(1);
    dwt_configciadiag(1);

    /* Get the correct length of the Ipatov CIR*/
    uint32_t n_samples_ipatov;
    if (config_options.rxCode < PCODE_PRF64_START) {
        n_samples_ipatov = DWT_CIR_LEN_IP_PRF16;
    }
    else {
        n_samples_ipatov = DWT_CIR_LEN_IP_PRF64;
    }

    // Loop forever while receieving frames
    while (measurement_count < 10)
    {
        
        // Clear memory
        memset(&rx_diag, 0, sizeof(rx_diag));

        // Enable the Rx manually immediately
        res = dwt_rxenable(DWT_START_RX_IMMEDIATE);
      
        // Poll until data is received
        uint32_t status_reg;
        waitforsysstatus(&status_reg, NULL, (DWT_INT_RXFCG_BIT_MASK | SYS_STATUS_ALL_RX_ERR), 0);

        if (status_reg & DWT_INT_RXFCG_BIT_MASK){
            
        
            // Read diagnostics data 
            dwt_readdiagnostics(&rx_diag);
            print_rx_diag(&rx_diag);

            sprintf(str_to_print,"CIR BEGIN");
            print((unsigned char *)str_to_print);
            

            /* Start reading CIR data from Ipatov offset */
            dwt_acc_idx_e acc_idx = DWT_ACC_IDX_IP_M ;
            
            dwt_cir_read_mode_e modes = DWT_CIR_READ_FULL; 

            /* Ipatov data */
            int n_samples = n_samples_ipatov;
            dwt_readcir((uint32_t*)cir_buf, acc_idx, 0, n_samples, modes);
            print_cir(cir_buf, n_samples, modes);

            sprintf(str_to_print,"CIR END");
            print((unsigned char *)str_to_print);

            /* Clear good RX frame event in the DW IC status register. */
            dwt_writesysstatuslo(DWT_INT_RXFCG_BIT_MASK);

            measurement_count++;
        }else{
            /* Clear RX error events in the DW IC status register. */
            dwt_writesysstatuslo(SYS_STATUS_ALL_RX_ERR);
            sprintf(str_to_print,"RX error\r\n");
            print((unsigned char *)str_to_print);
        }
        dwt_readeventcounters(&event_cnt);
    }

    print((unsigned char*)"\r\nCOMPLETE\r\n");

}

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
