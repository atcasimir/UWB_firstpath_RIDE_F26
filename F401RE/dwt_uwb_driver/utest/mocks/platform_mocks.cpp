/*
 * @copyright SPDX-FileCopyrightText: Copyright (c) 2025 Qorvo US, Inc.
 *            SPDX-License-Identifier: LicenseRef-QORVO-2
 *
 */
#include "platform_mocks.h"
#include "uwb_mock_regs.h"
#include <stdio.h>
#include "deca_interface.h"

#ifdef USE_DRV_DW3000
extern const struct dwt_driver_s dw3000_driver;
const struct dwt_driver_s dw3xxx_driver = dw3000_driver;
#elif  defined(USE_DRV_DW3720)
extern const struct dwt_driver_s dw3720_driver;
const struct dwt_driver_s dw3xxx_driver = dw3720_driver;
#else
const struct dwt_driver_s dw3xxx_driver;
#error "No DWT driver selected"
#endif


const struct dwt_driver_s* tmp_ptr[] = { &dw3xxx_driver };

void deca_usleep(unsigned long time_us)
{
	(void)time_us;
}

void deca_sleep(unsigned int time_ms)
{
	(void)time_ms;
}

decaIrqStatus_t decamutexon(void)
{
	return 0;
}

void decamutexoff(decaIrqStatus_t s)
{
	(void)s;
}

int32_t readfromspi(uint16_t header_length, uint8_t *header_buffer, uint16_t read_length,
			   uint8_t *read_buffer)
{
	printf("readfromspi: header_length=%d, read_length=%d\n, ", header_length, read_length);
	for(int i = 0; i < header_length; i++)
	{
		printf("header_buffer[%d]=0x%02X\n", i, header_buffer[i]);
	}

	uint16_t addr = ((header_buffer[0] & 0x3F) << 8) | (header_buffer[1] & 0xFC); // Retrive the address from the header

    printf("SPI Read: Addr: 0x%04X, Length: %d bytes\n",addr, read_length);

	if ((read_length + addr) > (UWB_REGS_SPACE_SIZE / 4))
	{
		return DWT_ERROR;
	}

	uint16_t idx = 0;

	for (int i = 0; i < read_length; i++)
	{
		idx = addr + i;
		read_buffer[i] = uwb_mock_reg_space[idx];
		printf("read_buffer[%d]=0x%02X\n", i, read_buffer[i]);
		printf("uwb_mock_reg_space[%d]=0x%02X\n", idx, uwb_mock_reg_space[idx]);
	}

	return DWT_SUCCESS;
} // end readfromspi()

int32_t writetospi(uint16_t header_length, const uint8_t *header_buffer,
			  uint16_t write_length, const uint8_t *write_buffer)
{
	printf("writetospi: header_length=%d, write_length=%d\n, ", header_length, write_length);
	for(int i = 0; i < header_length; i++)
	{
		printf("header_buffer[%d]=0x%02X\n", i, header_buffer[i]);
	}
	
	uint16_t addr = ((header_buffer[0] & 0x3F) << 8) | (header_buffer[1] & 0xFC); // Retrive the address from the header

    printf("SPI Write: Addr: 0x%04X, Length: %d bytes\n",addr, write_length);

	if ((write_length + addr) > (UWB_REGS_SPACE_SIZE / 4))
	{
		return DWT_ERROR;
	}

	uint16_t idx = 0;

	// Check if it's an AND / OR operation
	uint8_t andor = header_buffer[1] & 0x03;
	switch (andor)
	{
		case (DW3000_SPI_AND_OR_8 & 0x03): // OR operation 8-bit
			printf("OR operation 8-bit\n");
			for (int i = 0; i < 1; i++)
			{
				idx = addr + i;
				uwb_mock_reg_space[idx] &= write_buffer[i]; // AND operation
				uwb_mock_reg_space[idx] |= write_buffer[i+1]; // OR operation
				printf("write_buffer[%d]=0x%02X\n", i, write_buffer[i]);
				printf("uwb_mock_reg_space[%d]=0x%02X\n", idx, uwb_mock_reg_space[idx]);
			}
			break;
		case (DW3000_SPI_AND_OR_16 & 0x03): // OR operation 16-bit
			printf("OR operation 16-bit\n");
			for (int i = 0; i < 2; i++)
			{
				idx = addr + i;
				uwb_mock_reg_space[idx] &= write_buffer[i]; // AND operation
				uwb_mock_reg_space[idx] |= write_buffer[i+2]; // OR operation
				printf("write_buffer[%d]=0x%02X\n", i, write_buffer[i]);
				printf("uwb_mock_reg_space[%d]=0x%02X\n", idx, uwb_mock_reg_space[idx]);
			}
			break;
		case (DW3000_SPI_AND_OR_32 & 0x03): // OR operation 32-bit
			printf("OR operation 32-bit\n");
			for (int i = 0; i < 4; i++)
			{
				idx = addr + i;
				uwb_mock_reg_space[idx] &= write_buffer[i]; // AND operation
				uwb_mock_reg_space[idx] |= write_buffer[i+4]; // OR operation
				printf("write_buffer[%d]=0x%02X\n", i, write_buffer[i]);
				printf("uwb_mock_reg_space[%d]=0x%02X\n", idx, uwb_mock_reg_space[idx]);
			}
			break;
		default:
			// Normal write operation
			for (int i = 0; i < write_length; i++)
			{
				idx = addr + i;
				uwb_mock_reg_space[idx] = write_buffer[i];
				printf("write_buffer[%d]=0x%02X\n", i, write_buffer[i]);
				printf("uwb_mock_reg_space[%d]=0x%02X\n", idx, uwb_mock_reg_space[idx]);
			}
			break;
	}	

	return DWT_SUCCESS;
}
int32_t writetospiwithcrc(uint16_t header_length, const uint8_t *header_buffer,
				 uint16_t write_length, const uint8_t *write_buffer, uint8_t crc8)
{
	(void)crc8;
	writetospi(header_length, header_buffer, write_length, write_buffer);
	return DWT_SUCCESS;
}

void setslowrate(void)
{
}

void setfastrate(void)
{
}

void wakeup_device_with_io(void)
{
}

static const struct dwt_spi_s dw3xxx_spi_fct = {
    .readfromspi = readfromspi,
    .writetospi = writetospi,
    .writetospiwithcrc = writetospiwithcrc,
    .setslowrate = setslowrate,
    .setfastrate = setfastrate
};

const struct dwt_probe_s dw3xxx_probe_interf = 
{
    .dw = NULL,
    .spi = (void*)&dw3xxx_spi_fct,
    .wakeup_device_with_io = wakeup_device_with_io,
    .driver_list = (struct dwt_driver_s **)tmp_ptr,
    .dw_driver_num = 1,
};

int32_t test_common_init(void)
{
	uwb_mock_regs_clear();

	int32_t res = dwt_probe((struct dwt_probe_s *)&dw3xxx_probe_interf);

	if(res != DWT_SUCCESS)
	{
		return res;
	}
	
	return res;
}