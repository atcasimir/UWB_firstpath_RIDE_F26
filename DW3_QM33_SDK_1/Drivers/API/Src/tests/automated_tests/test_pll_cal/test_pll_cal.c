/*! ----------------------------------------------------------------------------
 *  @file    test_pll_cal.c
 *  @brief   PLL Calibration test code
 *
 *           This code performs a PLL calibration test on the DW3000 device.
 *           It initializes all necessary peripherals and configurations and 
 *           repeatedly change between channel 5 and 9 to test the PLL 
 *           calibration. The test prints the execution time, total number of
 *           iterations, any failures that occur during the calibration test
 *           and a pass or fail message.
 * 
 *           If AUTO_DW3300Q_DRIVER is defined, the test will use the AUTO PLL
 *           calibration mode.
 *
 * @author Decawave
 *
 * @copyright SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
 *            SPDX-License-Identifier: LicenseRef-QORVO-2
 *
 */

#include "test_common.h"

/* Test name */
#define APP_NAME "PLL CAL TEST v1.1"

/* Default communication configuration. We use default non-STS DW mode. */
static dwt_config_t config = {
    5,                /* Channel number. */
    DWT_PLEN_128,     /* Preamble length. Used in TX only. */
    DWT_PAC8,         /* Preamble acquisition chunk size. Used in RX only. */
    9,                /* TX preamble code. Used in TX only. */
    9,                /* RX preamble code. Used in RX only. */
    1,                /* 0 to use standard 8 symbol SFD, 1 to use non-standard 8 symbol, 2 for non-standard 16 symbol SFD and 3 for 4z 8 symbol SDF type */
    DWT_BR_6M8,       /* Data rate. */
    DWT_PHRMODE_STD,  /* PHY header mode. */
    DWT_PHRRATE_STD,  /* PHY header rate. */
    (129 + 8 - 8),    /* SFD timeout (preamble length + 1 + SFD length - PAC size). Used in RX only. */
    DWT_STS_MODE_OFF, /* STS disabled */
    DWT_STS_LEN_64,   /* STS length see allowed values in Enum dwt_sts_lengths_e */
    DWT_PDOA_M0       /* PDOA mode off */
};


bool test_pll_cal(void) {

    /* Initialize all configured peripherals */
    bsp_board_init(BSP_INIT_LEDS | BSP_INIT_BUTTONS);

    /* Initialise nRF52840-DK GPIOs */
    gpio_init();

    /* Initialise the SPI for nRF52840-DK */
    nrf52840_dk_spi_init();

    /* Small pause before startup */
    nrf_delay_ms(2);
    
    if(test_init() == false) {
        printf("Initialization failed\n");
        return false;
    }

    /* if the dwt_configure returns DWT_ERROR either the PLL or RX calibration has failed the host should reset the device */
    if (dwt_configure(&config))
    {
        printf("Config Failed\n");
        return false;
    }

    print_test_info();

    #ifdef AUTO_DW3300Q_DRIVER
        printf("Testing AUTO PLL cal\n");
    #else
        printf("Testing standard PLL cal\n");
    #endif

    uint32_t t1 = get_arm_timestamp();
    uint32_t n_pll_itr_max = 2000, ch5_itr = 0, ch9_itr = 0, ch5_fails = 0, ch9_fails = 0;
    uint8_t current_channel = 5;
    int32_t pll_cal_status = DWT_SUCCESS;

    while(n_pll_itr_max-- > 0)
    {
        /* Alternate between channel 5 and 9 */
        if(current_channel == 5)
        {
            current_channel = 9;
            ch9_itr++;
        }
        else
        {
            current_channel = 5;
            ch5_itr++;
        }

        /* Set the current channel and test the PLL calibration */
        pll_cal_status = dwt_setchannel(current_channel);
        if(pll_cal_status != DWT_SUCCESS)
        {
            if(current_channel == 5)
            {
                ch5_fails++;
            }
            else
            {
                ch9_fails++;
            }
        }
    }

    printf("Execution time in ticks: %d\n", get_arm_timestamp() - t1);
    printf("Total number of PLL calibration iterations: %d\n", ch5_itr + ch9_itr);
    printf("PLL Calibration done. Channel 5: %d fails, Channel 9: %d fails\n", ch5_fails, ch9_fails);

    if ((ch5_fails > 0) || (ch9_fails > 0))
    {
        printf("PLL Calibration failed\n");
        return false;
    }

    return true;
}

int main(void) {

    printf("%s\n", APP_NAME);
    bool test_result = test_pll_cal();

    if(test_result == false) 
    {
        printf("--- FAIL ---\n");
    }
    else
    {
        printf("--- PASS ---\n"); 
    }
    return 0;
}