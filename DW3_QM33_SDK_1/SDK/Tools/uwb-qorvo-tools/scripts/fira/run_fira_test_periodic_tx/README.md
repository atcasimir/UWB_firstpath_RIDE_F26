# run_fira_test_periodic_tx

Script **run_fira_test_periodic_tx** is provided to demonstrate FiRa Periodic TX Test. In the Periodic TX Test mode, the UWBS continues to send UWB packets until a configured number of packets (NUM_PACKETS) have been sent. This test mode may be used to measure characteristics like signal power, bandwidth and IEEE spectral mask of the transmitted signal.

## Parameters

Arguments with expected parameter available in this script:

| Parameter                | Values                                                                        |
|--------------------------|-------------------------------------------------------------------------------|
| -p / --port              | Specify communication interface                                               |
| -c / --channel           | Refer to CHANNEL_NUMBER in ``FIRA UCI Technical Specification``               |
| -i / --input-file        | Recover test configuration from a test profile file                           |
| -v / --verbose           | Prints additional debug information                                           |
| --randomized-psdu        | Refer to RANDOMIZE_PSDU in ``FIRA UCI Extension for Testing`` (default 0)     |
| --preamble-code-index    | Refer to PREAMBLE_CODE_INDEX in ``FIRA UCI Technical Specification``          |
| --sfd-id                 | Refer to SFD_ID in ``FIRA UCI Technical Specification``                       |
| --rframe-config          | Refer to RFRAME_CONFIG in ``FIRA UCI Technical Specification`` (default 0)    |
| --phr-data-rate          | Refer to BPRF_PHR_DATA_RATE in ``FIRA UCI Technical Specification``           |
| --nb-sts-segments        | Refer to NUMBER_OF_STS_SEGMENTS in ``FIRA UCI Technical Specification`` (supported values: 0, 1) |
| --sts-length             | Refer to STS_LENGTH in ``FIRA UCI Technical Specification``                   |
| --psdu                   | ':' or '.' separated list of bytes                                            |
| --num-packets            | Refer to NUM_PACKETS in ``FIRA UCI Extension for Testing`` (default = 1000)   |
| --t-gap                  | Refer to T_GAP in ``FIRA UCI Extension for Testing`` (default = 2000)         |
| --timeout                | Set timeout to receive the first package (in seconds). (default: 3)           |
| --en-diag                | Set the Qorvo ENABLE_DIAGNOSTIC parameter to 1                                |
| --antenna-set-id         | Set the antenna set to use for the session. (default: 0)                      |
| --run-forever            | Keep the script running indefinitely, press "enter" to stop the program.      |

## Application

Refer to "Application Configuration Parameters" in ``FIRA UCI Technical Specification`` for the possible values on APP configuration parameter.

```{eval-rst}
+----------------+-------------+------+------------------------------------------------------------------------------------------------------+---------+
| Parameter Name | Len (octet) | ID   | Description                                                                                          | Default |
+================+=============+======+======================================================================================================+=========+
| NUM_PACKETS    | 4           | 0x00 | No. of packets                                                                                       | 1000    |
+----------------+-------------+------+------------------------------------------------------------------------------------------------------+---------+
| T_GAP          | 4           | 0x01 | Gap between start of one packet to the next in us.                                                   | 2000    |
+----------------+-------------+------+------------------------------------------------------------------------------------------------------+---------+
| RANDOMIZE_PSDU | 1           | 0x04 | 0 - No randomization                                                                                 | 0       |
|                |             |      |                                                                                                      |         |
|                |             |      | 1 - Take first byte of data supplied by command and it shall be used as a seed for randomizing PSDU  |         |
+----------------+-------------+------+------------------------------------------------------------------------------------------------------+---------+
```

The periodic TX Test shall be triggered by using TEST_PERIODIC_TX_CMD command.

The TEST_PERIODIC_TX_CMD command SHALL be issued only after applying all required configuration parameters and the “Device Test Mode” session shall be in SESSION_STATE_IDLE Session State, otherwise UWBS SHALL respond TEST_PERIODIC_TX_RSP with Status of STATUS_ERROR_SESSION_NOT_CONFIGURED indicating that Test Session is not configured.

The UWBS shall respond TEST_PERIODIC_TX_RSP with the status of STATUS_OK and starts Periodic Test. The UWBS SHALL periodically starts sending UWB packets with PSDU Data as a payload. The periodicity is configured by the T_GAP Test Configuration Parameter and the number of packets to be transferred is configured by NUM_PACKETS APP Configuration Parameter.

The UWBS shall notify TEST_PERIODIC_TX_NTF notification with the status of STATUS_OK after NUM_PACKETS packets are sent over UWB to the intended destination UWB device.

**TEST_PERIODIC_TX_CMD**

| Payload Field(s) | Size (octet)    | Description                                                                    |
|------------------|-----------------|--------------------------------------------------------------------------------|
| PSDU Data        | N Octets        | PSDU Data[0:N] bytes; <br>0 <= N <= 127 for BPRF.                              |

**TEST_PERIODIC_TX_RSP**

| Payload Field(s) | Size (octet) | Description                         |
|------------------|--------------|-------------------------------------|
| Status           | 1            | Status code as per [FIRA_UCI_SPEC]. |

**TEST_PERIODIC_TX_NTF**

| Payload Field(s) | Size (octet) | Description                         |
|------------------|--------------|-------------------------------------|
| Status           | 1            | Status code as per [FIRA_UCI_SPEC]. |
