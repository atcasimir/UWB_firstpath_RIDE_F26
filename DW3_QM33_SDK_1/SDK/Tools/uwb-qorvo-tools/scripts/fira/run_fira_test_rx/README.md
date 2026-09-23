# run_fira_test_rx

Script **run_fira_test_rx** is provided to demonstrate FiRa RX Test. This RF test can be used to report signal parameters like SNR, AOA etc. Generally, this test is used to receive a single packet by using the TEST_RX_CMD command.

## Parameters

Arguments with expected parameter available in this script:

| Parameter             | Values                                                                     |
|-----------------------|----------------------------------------------------------------------------|
| -p / --port           | Specify communication interface                                            |
| -c / --channel        | Refer to CHANNEL_NUMBER in ``FIRA UCI Technical Specification``            |
| -v / --verbose        | Print additional debug information                                         |
| --preamble-code-index | Refer to PREAMBLE_CODE_INDEX in ``FIRA UCI Technical Specification``       |
| --sfd-id              | Refer to SFD_ID in ``FIRA UCI Technical Specification``                    |
| --rframe-config       | Refer to RFRAME_CONFIG in ``FIRA UCI Technical Specification`` (default 0) |
| --phr-data-rate       | Refer to BPRF_PHR_DATA_RATE in ``FIRA UCI Technical Specification``        |
| --nb-sts-segments     | Refer to NUMBER_OF_STS_SEGMENTS in ``FIRA UCI Technical Specification`` (supported values: 0, 1) |
| --sts-length          | Refer to STS_LENGTH in ``FIRA UCI Technical Specification``                |
| --en-diag             | Set the Qorvo ENABLE_DIAGNOSTIC parameter to 1                             |
| --antenna-set-id      | Set the antenna set to use for the session. (default: 0)                   |

## Application

Refer to "Application Configuration Parameters" in ``FIRA UCI Technical Specification`` for the possible values on APP configuration parameters.

**Test configuration parameters for RX Test**

| Parameter Name        | Len (octets) | ID   | Description                                                                                              |
|-----------------------|--------------|------|----------------------------------------------------------------------------------------------------------|
| RMARKER_TX_START      | 4            | 0x06 | Start time of TX in 1/(128*499.2MHz) units                                                               |
| STS_INDEX_AUTO_INCR   | 1            | 0x08 | 0x00: STS_INDEX config value is used for all PER Rx/ Periodic TX test. (default) Commented [SV4]: CR-241 |

The RX Test shall be triggered by using the TEST_RX_CMD command and UWBS shall respond by TEST_RX_RSP when a command is accepted successfully. The Configuration Parameters defined in the tables below affect the behavior of the test.

The TEST_RX_CMD command shall be issued only after applying all required configuration parameters and the “Device Test Mode” session SHALL be in SESSION_STATE_IDLE Session State, otherwise UWBS SHALL respond TEST_RX_RSP with Status of STATUS_ERROR_SESSION_NOT_CONFIGURED, indicating that session is not configured.

UWBS shall notify TEST_RX_NTF notification after the UWB packet is received from the intended device.

**TEST_RX_CMD**


| Payload Field(s) | Size (octet) | Description   |
|------------------|--------------|---------------|
| Command          | 0 Octets     | Start RX Test |

**TEST_RX_RSP**

| Payload Field(s) | Size (octet) | Description                         |
|------------------|--------------|-------------------------------------|
| Status           | 1            | Status code as per [FIRA_UCI_SPEC]. |

**TEST_RX_NTF**

| Payload Field(s) | Size (octet)  | Description                                                                                                 |
|------------------|---------------|-------------------------------------------------------------------------------------------------------------|
| Status           | 1             | Refer to generic status codes                                                                               |
| RX_DONE_TS_INT   | 4             | Integer part of timestamp 1/124.8Mhz ticks                                                                  |
| RX_DONE_TS_FRAC  | 2             | Fractional part of timestamp in 1/(128 * 499.2Mhz) ticks                                                    |
| AoA Azimuth      | 2             | AoA Azimuth in degrees and it is a signed value in Q9.7 format. This field is zero if AOA_RESULT_REQ = 0.   |
| AoA Elevation    | 2             | AoA Elevation in degrees and it is a signed value in Q9.7 format. This field is zero if AOA_RESULT_REQ = 0. |
| ToA Gap          | 1             | ToA of main path minus ToA of first path in nanoseconds                                                     |
| PHR              | 2             | Received PHR (bits 0-12 as per IEEE spec)                                                                   |
| PSDU Data Length | 2             | Length of PSDU Data(N) to follow                                                                            |
| PSDU Data        | N Octets      | PSDU Data[0:N] bytes; <br>0 <= N <= 127 for BPRF.                                                           |

## Example

Use 2 different shells, one for each DUT. They will be called here after DUT-TX and DUT-RX.

In shell 'DUT-RX', start the device in a 'listener' test mod:

```
run_fira_test_rx -p <dut rx port>
```

In shell 'DUT-TX', request a given payload to be sent:

```
run_fira_test_rx  -p <dut tx port> --psdu '0a.0b.0c.0d.0e.0f'
```

In shell 'DUT-RX', verify the received data:
You should expect the same data to be received ...

```
RxTestOutput gid:13, oid:5, Test Result:
...
PSDU data:     0a.0b.0c.0d.0e.of
...
```
