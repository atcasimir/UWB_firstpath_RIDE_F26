/*! ----------------------------------------------------------------------------
 *  @file    read_dev_id.c
 *  @brief   Read the DW IC's device ID. 
 *  @author  David Hunt
 *           Adapted from Qorvo DW3_QM33_SDK_1.1.1 read_dev_id.c
 */

#include "deca_probe_interface.h"
#include <deca_device_api.h>
#include <port.h>
#include <stdio.h>

extern void print(unsigned char *data);

// Application name (for console ).
#define APP_NAME "READ DEV ID"


// Application entry point.
int read_dev_id(void)
{

    int err;
    uint32_t dev_id;

    // Print application name to the console.
    print((unsigned char *)APP_NAME);

    // Configure SPI rate.
    port_set_dw_ic_spi_fastrate();

    // Reset DW IC.
    reset_DWIC();

    // Time needed for DW3000 to start up (transition from INIT_RC to IDLE_RC, or could wait for SPIRDY event).
    Sleep(2); 

    // Probe for the correct device driver.
    if (dwt_probe((struct dwt_probe_s *)&dw3000_probe_interf) == DWT_ERROR)
    {
        print((unsigned char *)"PROBE FAILED");
        while (1) { };
    }

    dev_id = dwt_readdevid();

    /* Reads and validate device ID returns DWT_ERROR if it does not match expected else DWT_SUCCESS */
    if ((err = dwt_check_dev_id()) == DWT_SUCCESS)
    {
        print((unsigned char *)"DEV ID OK");
    }
    else
    {
        print((unsigned char *)"DEV ID FAILED");
    }

    return err;
}
