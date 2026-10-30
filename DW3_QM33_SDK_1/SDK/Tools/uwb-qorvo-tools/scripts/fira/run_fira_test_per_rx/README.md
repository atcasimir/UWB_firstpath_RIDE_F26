# run_fira_test_per_rx

Script **run_fira_test_per_rx** is provided to demonstrate the FiRa PER RX Test. In the Packet/bit Error Rate RX Test mode, the UWBS continues to look for UWB packets in a timely fashion (T_GAP) until a configured number of packets (NUM_PACKETS) have elapsed. The timing of the packet starts only after the successful reception of the first packet, otherwise UWBS looks for the first packet indefinitely. This test mode can be used to measure the receiver sensitivity of the UWB device.

## Parameters

Arguments with expected parameter available in this script:

| Parameter             | Values                                                                         |
|-----------------------|--------------------------------------------------------------------------------|
| -t / --time           | Set the duration of the ranging session (in second); `-1` - range forever      |
| -p / --port           | Set communication port                                                         |
| -c / --channel        | Refer to CHANNEL_NUMBER in ``FIRA UCI Technical Specification``                |
| -i / --input-file     | Recover test configuration from a test profile file                            |
| -v / --verbose        | Print additional debug information                                            |
| --randomized-psdu     | Refer to RANDOMIZE_PSDU in ``FIRA UCI Extension for Testing`` (default 0)      |
| --preamble-code-index | Refer to PREAMBLE_CODE_INDEX in ``FIRA UCI Technical Specification``           |
| --sfd-id              | Refer to SFD_ID in ``FIRA UCI Technical Specification``                        |
| --rframe-config       | Refer to RFRAME_CONFIG in ``FIRA UCI Technical Specification`` (default 0)     |
| --phr-data-rate       | Refer to BPRF_PHR_DATA_RATE in ``FIRA UCI Technical Specification``            |
| --sts-length          | Refer to STS_LENGTH in ``FIRA UCI Technical Specification``                    |
| --nb-sts-segments     | Refer to NUMBER_OF_STS_SEGMENTS in ``FIRA UCI Technical Specification`` (supported values: 0, 1) |
| --psdu                | ':' or '.' separated list of bytes                                             |
| --num-packets         | Refer to NUM_PACKETS in ``FIRA UCI Extension for Testing`` (default = 1000)    |
| --t-gap               | Refer to T_GAP in ``FIRA UCI Extension for Testing`` (default = 2000)          |
| --timeout             | Set timeout to receive the first package (in seconds). (default: 3)            |
| --en-diag             | Set the Qorvo ENABLE_DIAGNOSTIC parameter to 1                                 |
| --antenna-set-id      | Set the antenna set to use for the session. (default: 0)                       |

## Application

Refer to "Application Configuration Parameters" in ``FIRA UCI Technical Specification`` for the possible values on APP configuration parameters.

```{eval-rst}
+----------------+-------------+------+------------------------------------------------------------------------------------------------------+---------+
| Parameter Name | Len (octet) | ID   | Description                                                                                          | Default |
+================+=============+======+======================================================================================================+=========+
| NUM_PACKETS    | 4           | 0x00 | No. of packets                                                                                       | 1000    |
+----------------+-------------+------+------------------------------------------------------------------------------------------------------+---------+
| T_GAP          | 4           | 0x01 | Gap between start of one packet to the next in us T_GAP >> packet length                             | 2000    |
+----------------+-------------+------+------------------------------------------------------------------------------------------------------+---------+
| T_START        | 4           | 0x02 | Max. time from the start of T_GAP to SFD found state in us                                           | 450     |
+----------------+-------------+------+------------------------------------------------------------------------------------------------------+---------+
| T_WIN          | 4           | 0x03 | Max. time for which RX is looking for a packet from the start of T_GAP in us T_WIN > T_START         | 750     |
+----------------+-------------+------+------------------------------------------------------------------------------------------------------+---------+
| RANDOMIZE_PSDU | 1           | 0x04 | 0 - No randomization                                                                                 | 0       |
|                |             |      |                                                                                                      |         |
|                |             |      | 1 - Take first byte of data supplied by command and it shall be used as a seed for randomizing PSDU  |         |
+----------------+-------------+------+------------------------------------------------------------------------------------------------------+---------+
```
The PER RX Test shall be triggered by using TEST_PER_RX_CMD command.

The TEST_PER_RX_CMD command shall be issued only after applying all required Configuration parameters and the “Device Test Mode” session SHALL be in SESSION_STATE_IDLE Session State, otherwise UWBS will respond TEST_PER_RX_RSP with Status of STATUS_ERROR_SESSION_NOT_CONFIGURED indicating that session is not configured.

The UWBS shall respond TEST_PER_RX_RSP with the status of STATUS_OK and start PER Test. The number of packets to be received over UWB is configured by the NUM_PACKETS APP Configuration Parameter. UWBS shall notify TEST_PER_RX_NTF notification after completing the PER Rx test.

| Payload Field(s) | Size (octet) | Description                                                                 |
|------------------|--------------|-----------------------------------------------------------------------------|
| PSDU Data        | N Octets     | PSDU Data[0:N] bytes. 0 <= N <= 127 for BPRF.                               |

| Payload Field(s) | Size (octet) | Description                         |
|------------------|--------------|-------------------------------------|
| Status           | 1            | Status code as per [FIRA_UCI_SPEC]. |

| Payload Field(s) | Size (octet)  | Description                                                         |
|------------------|---------------|---------------------------------------------------------------------|
| Status           | 1             | Notify host after receiving NUM_PACKETS. Refer generic status codes |
| ATTEMPTS         | 4             | No. of RX attempts                                                  |
| ACQ_DETECT       | 4             | No. of times signal was detected                                    |
| ACQ_REJECT       | 4             | No. of times signal was rejected                                    |
| RX_FAIL          | 4             | No. of times RX did not go beyond ACQ stage                         |
| SYNC_CIR_READY   | 4             | No. of times sync CIR ready event was received                      |
| SFD_FAIL         | 4             | No. of time RX was stuck at either ACQ detect or sync CIR ready     |
| SFD_FOUND        | 4             | No. of times SFD was found                                          |
| PHR_DEC_ERROR    | 4             | No. of times PHR decode failed                                      |
| PHR_BIT_ERROR    | 4             | No. of times PHR bits in error                                      |
| PSDU_DEC_ERROR   | 4             | No. of times payload decode failed                                  |
| PSDU_BIT_ERROR   | 4             | No. of times payload bits in error                                  |
| STS_FOUND        | 4             | No. of times STS detection was successful                           |
| EOF              | 4             | No. of times end of frame event was triggered                       |
