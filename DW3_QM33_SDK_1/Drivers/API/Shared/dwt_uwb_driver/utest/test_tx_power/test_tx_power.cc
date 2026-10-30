/*
 * @copyright SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
 *            SPDX-License-Identifier: LicenseRef-QORVO-2
 *
 */

#include <stdio.h>
#include <gmock/gmock.h>
#include <gtest/gtest.h>

#include "platform_mocks.h"

struct TestTxPower:public::testing::Test {
    public:
	void SetUp() override
	{
		int32_t status = test_common_init();
		ASSERT_EQ(status, DWT_SUCCESS);
	}
};


TEST_F(TestTxPower, WhenExactTxPowerIsFoundInTable_Success)
{
	uint32_t channel = DWT_CH5;
	uint32_t exp_tx_power = 0xc2c2c2c2;
	uint8_t tx_power = 0xc2;
	uint8_t tx_power_idx;
	power_indexes_t p_indexes;
	tx_adj_res_t p_res;

	/* Expected returned values. */
	uint8_t exp_tx_power_idx = 5;
	uint8_t exp_pll_bias_trim = 7;

	int r = dwt_convert_tx_power_to_index(channel, tx_power, &tx_power_idx);
	ASSERT_EQ(r, DWT_SUCCESS);
	ASSERT_EQ(tx_power_idx, exp_tx_power_idx);

	for (int i = 0; i < DWT_MAX_POWER_INDEX; i++)
		p_indexes.input[i] = tx_power_idx;

	r = dwt_calculate_linear_tx_power(channel, &p_indexes, &p_res);
	ASSERT_EQ(r, DWT_SUCCESS);
	ASSERT_EQ(p_res.tx_frame_cfg.tx_power_setting, exp_tx_power);
	ASSERT_EQ(p_res.tx_frame_cfg.pll_bias, exp_pll_bias_trim);
}

/**
 * TestLLHWWithParams section
 * Parameters description in the tuple:
 * dwt_config_t [input] - DWT chip configuration.
 * struct mcps802154_hrp_uwb_params [input] - HRP UWB Params.
 * FrameDurationResult [input] - Frame Duration Result.
 */
class TestConvertTxPowerToIdx
	: public TestTxPower,
	  public testing::WithParamInterface<
		  std::tuple<int, uint8_t> > {
};

TEST_P(TestConvertTxPowerToIdx, DoTest)
{
	uint32_t channel = std::get<0>(GetParam());
	uint8_t tx_power = std::get<1>(GetParam());
	uint8_t tx_power_idx;
	power_indexes_t p_indexes;
	tx_adj_res_t p_res;

	int r = dwt_convert_tx_power_to_index(channel, tx_power, &tx_power_idx);
	ASSERT_EQ(r, DWT_SUCCESS);

	for (int i = 0; i < DWT_MAX_POWER_INDEX; i++)
		p_indexes.input[i] = tx_power_idx;

	r = dwt_calculate_linear_tx_power(channel, &p_indexes, &p_res);
	ASSERT_EQ(r, DWT_SUCCESS);
	
	printf("TxPowerIn 0x%02x Chan %d => Idx 0x%02x TxPowerOut 0x%02x Bias %d\n",
	       tx_power, channel, tx_power_idx, p_res.tx_frame_cfg.tx_power_setting,
	       p_res.tx_frame_cfg.pll_bias);
}

INSTANTIATE_TEST_SUITE_P(ch5, TestConvertTxPowerToIdx,
			 testing::Values(std::make_tuple(5, 0x5d),
					 std::make_tuple(5, 0x61),
					 std::make_tuple(5, 0x65),
					 std::make_tuple(5, 0x69),
					 std::make_tuple(5, 0x6d),
					 std::make_tuple(5, 0x71),
					 std::make_tuple(5, 0x75),
					 std::make_tuple(5, 0x79),
					 std::make_tuple(5, 0x7d),
					 std::make_tuple(5, 0x85),
					 std::make_tuple(5, 0x9d)));

INSTANTIATE_TEST_SUITE_P(ch9, TestConvertTxPowerToIdx,
			 testing::Values(std::make_tuple(9, 0x79),
					 std::make_tuple(9, 0x7d),
					 std::make_tuple(9, 0x85),
					 std::make_tuple(9, 0x91),
					 std::make_tuple(9, 0x95),
					 std::make_tuple(9, 0x99),
					 std::make_tuple(9, 0x9d),
					 std::make_tuple(9, 0xa1),
					 std::make_tuple(9, 0xa5),
					 std::make_tuple(9, 0xa9),
					 std::make_tuple(9, 0xad),
					 std::make_tuple(9, 0xb1),
					 std::make_tuple(9, 0xb5),
					 std::make_tuple(9, 0xb9),
					 std::make_tuple(9, 0xc1)));
