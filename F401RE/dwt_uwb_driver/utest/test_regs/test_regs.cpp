/*
	This test will check whether the basic read/write operations to the device registers mocks are working correctly.
*/
/*
 * @copyright SPDX-FileCopyrightText: Copyright (c) 2025 Qorvo US, Inc.
 *            SPDX-License-Identifier: LicenseRef-QORVO-2
 *
 */

 #include <stdio.h>
 #include <gmock/gmock.h>
 #include <gtest/gtest.h>
 #include "platform_mocks.h"
 #include "deca_device_api.h"

 #ifdef USE_DRV_DW3000
	#include "dw3000_deca_regs.h"
#elif  defined(USE_DRV_DW3720)
	#include "dw3720_deca_regs.h"
#endif
 
struct TestReadDevId:public::testing::Test {
    public:
	void SetUp() override
	{
		int32_t status = test_common_init();
		ASSERT_EQ(status, DWT_SUCCESS);
	}
};

TEST_F(TestReadDevId, GetCorrectDevID)
{
    uint32_t devId = dwt_read_reg(DEV_ID_ID);
#ifdef USE_DRV_DW3000
	EXPECT_EQ(devId, DWT_DW3000_PDOA_DEV_ID);
#elif  defined(USE_DRV_DW3720)
	EXPECT_EQ(devId, DWT_QM33120_PDOA_DEV_ID);
#endif
}

TEST_F(TestReadDevId, WriteReadTest)
{
	uint32_t expected_val = 0xAB12CD34, read_val = 0;
	dwt_write_reg(SYS_STATUS_ID, expected_val); 
	read_val = dwt_read_reg(SYS_STATUS_ID);
	EXPECT_EQ(read_val, expected_val);
}

TEST_F(TestReadDevId, AndOrReadTest)
{
	// Testing AND / OR 32-bit
	uint8_t expected_val = (uint8_t)DWT_BR_6M8;
	dwt_setdatarate((dwt_uwb_bit_rate_e)expected_val); 
	uint32_t read_val = dwt_read_reg(TX_FCTRL_ID);
	EXPECT_EQ((uint8_t)((read_val & TX_FCTRL_TXBR_BIT_MASK) >> TX_FCTRL_TXBR_BIT_OFFSET), expected_val);

	// Testing AND / OR 16-bit
	dwt_write_reg(CIA_ADJUST_ID, 0xFFFFFFFF);
	expected_val = 125;
	dwt_setpdoaoffset((uint16_t)expected_val);
	read_val = dwt_read_reg(CIA_ADJUST_ID);
	EXPECT_EQ((uint8_t)(read_val & CIA_ADJUST_PDOA_ADJ_OFFSET_BIT_MASK), expected_val);
	
	// Testing AND / OR 8-bit
	dwt_write_reg(DTUNE0_ID, 0xFFFFFFFF);
	expected_val = (uint8_t)DWT_PAC32;
	dwt_setrxpac((dwt_pac_size_e)expected_val);
	read_val = dwt_read_reg(DTUNE0_ID);
	EXPECT_EQ((uint8_t)((read_val & DTUNE0_PRE_PAC_SYM_BIT_MASK) ), expected_val);
}