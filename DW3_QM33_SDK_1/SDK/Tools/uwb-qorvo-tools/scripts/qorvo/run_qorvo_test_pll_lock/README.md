# run_qorvo_test_pll_lock

Script **run_qorvo_test_pll_lock** is provided to demonstrate Qorvo PLL Lock TX Test. This test requests the UWB radio to lock the PLL (IDLE_PLL) and reports the lock status. The test sets the radio to INIT_RC state once completed.

## Parameters

Arguments with expected parameter available in this script:

| Parameter      | Values                                                          |
|----------------|-----------------------------------------------------------------|
| -p / --port    | Specify communication interface                                 |
| -c / --channel | Refer to CHANNEL_NUMBER in ``FIRA UCI Technical Specification`` |
| -v / --verbose | prints additional debug information                             |

## Application

The Qorvo PLL Lock TX Test shall be triggered by using TEST_PLL_LOCK_CMD command and UWBS shall respond by TEST_PLL_LOCK_RSP when command is accepted successfully.

**TEST_PLL_LOCK_CMD (GID = 0xB, OID = 0x1)**

| Payload Field(s) | Size (octet) | Description |
|------------------|--------------|-------------|
| N/A              | N/A          | N/A         |

**TEST_PLL_LOCK_RSP (GID = 0xB, OID = 0x2)**

| Payload Field(s) | Size (octet) | Description                        |
|------------------|--------------|------------------------------------|
| Status           | 1            | Status code as per [FIRA_UCI_SPEC] |

**TEST_PLL_LOCK_NTF (GID = 0xB, OID = 0x2)**

| Payload Field(s) | Size (octet) | Description                  |
|------------------|--------------|------------------------------|
| TLV count        | 1            | The number of TLVs following |
| TLF list         | 1            | See TLV descriptions below   |

**TLVs TEST_PLL_LOCK_NTF**

```{eval-rst}
+------+----------+------------------------------------------------------------------------------------------------------------------------------------------+
| Type | Length   | Value / Description                                                                                                                      |
+======+==========+==========================================================================================================================================+
| 0x01 | 1 octet  | Error code:                                                                                                                              |
|      |          |                                                                                                                                          |
|      |          | 0 - SUCCESS: see PLL lock status table                                                                                                   |
|      |          |                                                                                                                                          |
|      |          | 1 - PLL_LOCK_ERROR: setting the channel failed                                                                                           |
|      |          |                                                                                                                                          |
|      |          | 2 - INTERNAL_ERROR: setting the PLL state failed                                                                                         |
+------+----------+------------------------------------------------------------------------------------------------------------------------------------------+
| 0x02 | 4 octets | PLL_STATUS_CH9_BIST_FAIL_BIT_MASK (0x4000): PLL channel 9 BIST fail                                                                      |
|      |          |                                                                                                                                          |
|      |          | PLL_STATUS_CH5_BIST_FAIL_BIT_MASK (0x2000): PLL channel 5 BIST fail                                                                      |
|      |          |                                                                                                                                          |
|      |          | PLL_STATUS_LD_CODE_BIT_MASK (0x1f00): Counter-based lock-detect status indicator                                                         |
|      |          |                                                                                                                                          |
|      |          | PLL_STATUS_XTAL_AMP_SETTLED_BIT_MASK (0x0040): Status flag from the XTAL indicating that the amplitude has settled                       |
|      |          |                                                                                                                                          |
|      |          | PLL_STATUS_VCO_TUNE_UPDATE_BIT_MASK (0x0020): Flag to indicate that the COARSE_TUNE codes have been updated by cal and are ready to read |
|      |          |                                                                                                                                          |
|      |          | PLL_STATUS_PLL_OVRFLOW_BIT_MASK (0x0010): PLL calibration flag indicating all VCO_TUNE values have been cycled through                   |
|      |          |                                                                                                                                          |
|      |          | PLL_STATUS_PLL_HI_FLAG_BIT_MASK (0x0080): VCO freq too high indicator (active-high)                                                      |
|      |          |                                                                                                                                          |
|      |          | PLL_STATUS_PLL_LO_FLAG_N_BIT_MASK (0x0004): VCO freq too low indicator (active-low)                                                      |
|      |          |                                                                                                                                          |
|      |          | PLL_STATUS_PLL_LOCK_FLAG_BIT_MASK (0x0002): PLL lock flag                                                                                |
|      |          |                                                                                                                                          |
|      |          | PLL_STATUS_CPC_CAL_DONE_BIT_MASK (0x0001): PLL cal done and PLL locked                                                                   |
+------+----------+------------------------------------------------------------------------------------------------------------------------------------------+
```
