/**
 * @file      platform_mocks.h
 * 
 * @brief     Defines the functions required to mock the platform for unit testing.
 *
 * @copyright SPDX-FileCopyrightText: Copyright (c) 2025 Qorvo US, Inc.
 *            SPDX-License-Identifier: LicenseRef-QORVO-2
 *
 */
#ifndef __PLATFORM_MOCKS_H__
#define __PLATFORM_MOCKS_H__

#include <stdint.h>

#include "deca_interface.h"
#include "deca_device_api.h"

decaIrqStatus_t decamutexon(void);

void decamutexoff(decaIrqStatus_t s);

void deca_sleep(unsigned int time_ms);

void deca_usleep(unsigned long time_us);

void deca_usleep(unsigned long time_us);

void deca_sleep(unsigned int time_ms);

decaIrqStatus_t decamutexon(void);

void decamutexoff(decaIrqStatus_t s);

int32_t readfromspi(uint16_t header_length, uint8_t *header_buffer, uint16_t read_length,
			   uint8_t *read_buffer);
int32_t writetospi(uint16_t header_length, const uint8_t *header_buffer,
			  uint16_t write_length, const uint8_t *write_buffer);
int32_t writetospiwithcrc(uint16_t header_length, const uint8_t *header_buffer,
				 uint16_t write_length, const uint8_t *write_buffer, uint8_t crc8);

void setslowrate(void);

void setfastrate(void);

void wakeup_device_with_io(void);

int32_t test_common_init(void);

#endif // __PLATFORM_MOCKS_H__