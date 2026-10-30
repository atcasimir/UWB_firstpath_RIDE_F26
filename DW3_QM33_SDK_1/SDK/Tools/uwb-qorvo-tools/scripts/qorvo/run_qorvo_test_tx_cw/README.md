# run_qorvo_test_tx_cw

Script **run_qorvo_test_tx_cw** is provided to demonstrate Qorvo Continuous Wave TX Test. This test configures the device to transmit a Continuous Wave (CW) at a specified channel of Qorvo UWB radio to transmit a Continuous Wave (CW) at a specified channel frequency. This may be of use as part of the crystal trimming procedure.

## Parameters

Arguments with expected parameter available in this script:

| Parameter      | Values                                                                       |
|----------------|------------------------------------------------------------------------------|
| -p / --port    | Specify communication interface                                              |
| -c / --channel | Refer to CHANNEL_NUMBER in ``FIRA UCI Technical Specification``              |
| -t / --time    | set the duration of the ranging session (in second); `-1` - range forever    |
| -v / --verbose | prints additional debug information                                          |

## Application

**APP configuration parameters for Continuous Wave TX Test**

| Parameter Name | Tag  | Length   | Description                                 |
|----------------|------|----------|---------------------------------------------|
| CHANNEL_NUMBER | 0x04 | 1        | 0x05 for channel 5; <br>>0x09 for channel 9 |

**Test configuration parameters for Continuous Wave TX Test**

| Parameter Name       | Tag  | Length | Description                |
|----------------------|------|--------|----------------------------|
| TX_ANTENNA_SELECTION | 0xE7 | 1      | ID of the TX antenna group |


The Qorvo Continuous Wave TX Test shall be triggered by using TEST_TX_CW_CMD command and UWBS SHALL respond by TEST_TX_CW_CMD when a command is accepted successfully.

**TEST_TX_CW_CMD (GID = 0xB, OID = 0x1)**

| Payload Field(s) | Size (octet) | Description         |
|------------------|--------------|---------------------|
| Enable           | 1            | 1 = start, 0 = stop |

**TEST_TX_CW_RSP (GID = 0xB, OID = 0x1)**

| Payload Field(s) | Size (octet) | Description                        |
|------------------|--------------|------------------------------------|
| Status           | 1            | Status code as per [FIRA_UCI_SPEC] |
