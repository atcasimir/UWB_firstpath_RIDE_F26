# run_fira_twr

Script **run_fira_twr** is provided to demonstrate a FiRa session ranging which can be easily modified.

## Parameters

Arguments with expected parameter available in this script:

| Parameter               | Values                                                                                                                |
|-------------------------|-----------------------------------------------------------------------------------------------------------------------|
| -t / --time             | Set the duration of the ranging session (in second); `-1` - range forever                                             |
| -p / --port             | Specify communication interface                                                                                       |
| -c / --channel          | Refer to CHANNEL_NUMBER in ``FIRA UCI Technical Specification``                                                       |
| -s / --session          | Set session ID (default: 42)                                                                                          |
| -v / --verbose          | Prints additional debug information                                                                                   |
| --controlee             | Refer to DEVICE_TYPE in ``FIRA UCI Technical Specification``                                                          |
| --round                 | Refer to RANGING_ROUND_USAGE in ``FIRA UCI Technical Specification``                                                  |
| --round-ctrl            | Refer to RANGING_ROUND_CONTROL in ``FIRA UCI Technical Specification``                                                |
| --en-key-rot            | Refer to KEY_ROTATION in ``FIRA UCI Technical Specification``                                                         |
| --key-rot-rate          | Refer to KEY_ROTATION_RATE in ``FIRA UCI Technical Specification``                                                    |
| --sts                   | Refer to STS_CONFIG in ``FIRA UCI Technical Specification``                                                           |
| --slot-span             | Refer to SLOT_DURATION in ``FIRA UCI Technical Specification``                                                        |
| --node                  | Refer to MULTI_NODE_MODE in ``FIRA UCI Technical Specification``                                                      |
| --ranging-span          | Refer to RANGING_DURATION in ``FIRA UCI Technical Specification``                                                     |
| --en-diag               | Set the Qorvo ENABLE_DIAGNOSTIC parameter to 1                                                                        |
| --diag-fields           | Set the Qorvo DIAGNOSTIC_FRAME_REPORTS_FIELD value OR <br>flags: metrics, aoa, cir, cfo. (default: 'metrics|aoa|cfo') |
| --meas-max              | Refer to MAX_NUMBER_OF_MEASUREMENTS in ``FIRA UCI Technical Specification``                                           |
| --skey SKEY             | Refer to SESSION_KEY in ``FIRA UCI Technical Specification``                                                          |
| --mac                   | Refer to DEVICE_MAC_ADDRESS in ``FIRA UCI Technical Specification``                                                   |
| --dest-mac              | Refer to DST_MAC_ADDRESS in ``FIRA UCI Technical Specification``                                                      |
| --controlees-with-sskey | Refer to SESSION_UPDATE_CONTROLLER_MULTICAST_LIST_CMD in ``FIRA UCI Technical Specification``                         |
| --frame                 | Refer to RFRAME_CONFIG in ``FIRA UCI Technical Specification``                                                        |
| --ssession              | Refer to SUB_SESSION_ID in ``FIRA UCI Technical Specification``                                                       |
| --sskey                 | Refer to SUB_SESSION_KEY in ``FIRA UCI Technical Specification``                                                      |
| --en-rssi               | Refer to RSSI_REPORTING in ``FIRA UCI Technical Specification``                                                       |
| --stats                 | Enable Statistics report at end of the run                                                                            |
| --diag_dump             | Dump the Diagnostics in the provided JSON file                                                                        |
| --n_controlees          | Refer to NUMBER_OF_CONTROLEES in ``FIRA UCI Technical Specification``                                                 |
| --block_stride_length   | Refer to BLOCK_STRIDE_LENGTH in ``FIRA UCI Technical Specification``                                                  |
| --sts-length            | Refer to STS_LENGTH in ``FIRA UCI Technical Specification``                                                           |
| --vendor-id             | Refer to VENDOR_ID in ``FIRA UCI Technical Specification``                                                            |
| --static-sts            | Refer to STATIC_STS_IV ``FIRA UCI Technical Specification``                                                           |
| --aoa-report            | Refer to AOA_RESULT_REQ ``FIRA UCI Technical Specification``                                                          |
| --preamble-idx          | Refer to PREAMBLE_CODE_INDEX ``FIRA UCI Technical Specification``                                                     |
| --sfd                   | Refer to SFD_ID ``FIRA UCI Technical Specification``                                                                  |
| --slots-per-rr          | Refer to SLOTS_PER_RR ``FIRA UCI Technical Specification``                                                            |
| --hopping-mode          | Refer to HOPPING_MODE ``FIRA UCI Technical Specification``                                                            |

> **Warning(!)**, `--diag_dump` has an effect only with the `--stats` option.

The Diagnostics parameter save the diagnostics report in a json file named
``range_data_<year>-<month>-<day>-<time>.json``. For instance: ``range_data_23-04-12-10h47m25s.json``

The report contains one entry per Fira ranging sequence, each of these entries contains one entry per frame exchanged.

## Example with Default values

Initialize a TWR FiRa session as controller on the first board.

```
run_fira_twr -p <controller port>
```

Open a second command shell in the Python script location.

Initialize a TWR FiRa session as a controlee on the second board.

```
run_fira_twr -p <controlee port> --controlee
```

Output of the script running on the controlee side with default parameter:

```
Initializing session 42...
Session 2 -> Init (StateChangeWithSessionManagementCommands)
Using Fira 2.0 session handle is : 2
Setting session 2 config ...
    DeviceType (0x0):                   0x0
    DeviceRole (0x11):                  0x0
    MultiNodeMode (0x3):                0x0
    RangingRoundUsage (0x1):            0x2
    DeviceMacAddress (0x6):             0x1
    ChannelNumber (0x4):                0x9
    ScheduleMode (0x22):                0x1
    StsConfig (0x2):                    0x0
    RframeConfig (0x12):                0x3
    ResultReportConfig (0x2e):          0xb
    VendorId (0x27):                    0x708
    StaticStsIv (0x28):                 0x60504030201
    AoaResultReq (0xd):                 0x1
    UwbInitiationTime (0x2b):           0x0
    PreambleCodeIndex (0x14):           0xa
    SfdId (0x15):                       0x2
    SlotDuration (0x8):                 0x960
    RangingInterval (0x9):              0xc8
    SlotsPerRr (0x1b):                  0x19
    MaxNumberOfMeasurements (0x32):     0x0
    HoppingMode (0x2c):                 0x0
    RssiReporting (0x13):               0x0
    BlockStrideLength (0x2d):           0x0
    NumberOfControlees (0x5):           0x1
    DstMacAddress (0x7):                [0]
    StsLength (0x35):                   0x1
Session 6 -> Idle (StateChangeWithSessionManagementCommands)
Starting ranging...
Device -> Active
Session 6 -> Active (StateChangeWithSessionManagementCommands)

[...]

# Ranging Data:
        session handle:     2
        sequence n:         8
        ranging interval:   200 ms
        measurement type:   Twr
        Mac add size:       2
        primary session id: 0x0
        n of measurement:   1
        # Measurement 1:
            status:             Ok (0x0)
            mac address:        00:00 hex
            is nlos meas:       Unsupported
            distance:           62.0 cm
            AoA azimuth:        -10.6328125 deg
            AoA az. FOM:        92.0 %
            AoA elevation:      0.0 deg
            AoA elev. FOM:      0.0
            AoA dest azimuth:   0.0 deg
            AoA dest az. FOM:   0.0 %
            AoA dest elevation: 0.0 deg
            AoA dest elev. FOM: 0.0 %
            slot in error:      0
            rssi:               -0.0 dBm

[...]

Stopping ranging...
Session 2 -> Idle (StateChangeWithSessionManagementCommands)
Device -> Ready
Deinitializing session...
Session 2 -> DeInit (StateChangeWithSessionManagementCommands)
Ok
```

## Example with Statistics, Diagnostic and RSSI

Initialize a TWR FiRa session as controller on the first board.

```
run_fira_twr -p <controller port> --stats --en-diag -en-rssi
```

Open a second command shell in the Python script location.

Initialize a TWR FiRa session as controlee on the second board (in this example, in COM40).

```
run_fira_twr -p <controlee port> --controlee
```

Output of the script running on the controller side:

```
Initializing session 42...
Session 4 -> Init (StateChangeWithSessionManagementCommands)
Using Fira 2.0 session handle is : 4
Setting session 4 config ...
    DeviceType (0x0):                   0x0
    DeviceRole (0x11):                  0x0
    MultiNodeMode (0x3):                0x0
    RangingRoundUsage (0x1):            0x2
    DeviceMacAddress (0x6):             0x1
    ChannelNumber (0x4):                0x9
    ScheduleMode (0x22):                0x1
    StsConfig (0x2):                    0x0
    RframeConfig (0x12):                0x3
    ResultReportConfig (0x2e):          0xb
    VendorId (0x27):                    0x708
    StaticStsIv (0x28):                 0x60504030201
    AoaResultReq (0xd):                 0x1
    UwbInitiationTime (0x2b):           0x0
    PreambleCodeIndex (0x14):           0xa
    SfdId (0x15):                       0x2
    SlotDuration (0x8):                 0x960
    RangingInterval (0x9):              0xc8
    SlotsPerRr (0x1b):                  0x19
    MaxNumberOfMeasurements (0x32):     0x0
    HoppingMode (0x2c):                 0x0
    RssiReporting (0x13):               0x0
    BlockStrideLength (0x2d):           0x0
    NumberOfControlees (0x5):           0x1
    DstMacAddress (0x7):                [0]
    StsLength (0x35):                   0x1
Session 4 -> Idle (StateChangeWithSessionManagementCommands)
Starting ranging...
Device -> Active
Session 4 -> Active (StateChangeWithSessionManagementCommands)

[...]

# Ranging Data:
        session handle:         2
        sequence n:         23
        ranging interval:   200 ms
        measurement type:   Twr
        Mac add size:       2
        primary session id: 0x0
        n of measurement:   1
        # Measurement 1:
            status:             Ok (0x0)
            mac address:        00:01 hex
            is nlos meas:       Unsupported
            distance:           76.0 cm
            AoA azimuth:        0.0 deg
            AoA az. FOM:        0.0 %
            AoA elevation:      0.0 deg
            AoA elev. FOM:      0.0
            AoA dest azimuth:   7.296875 deg
            AoA dest az. FOM:   92.0 %
            AoA dest elevation: 0.0 deg
            AoA dest elev. FOM: 0.0 %
            slot in error:      0
            rssi:               -60.0 dBm

# Ranging Diagnostic Data:
        Session handle:     2
        Sequence n:     23
        Nbr of reports: 6
        # Ranging Diag. Report 0:
            Message id:    Control
            Action:        Tx
            Antenna_set:   0
            Nbr of fields: 1
            # Frame Status Report:
                is processing ok  : 1
                is wifi activated : 0
        # Ranging Diag. Report 1:
            Message id:    RangingInitiation
            Action:        Tx
            Antenna_set:   0
            Nbr of fields: 1
            # Frame Status Report:
                is processing ok  : 1
                is wifi activated : 0
        # Ranging Diag. Report 2:
            Message id:    RangingResponse
            Action:        Rx
            Antenna_set:   0
            Nbr of fields: 3
            # Frame Status Report:
                is processing ok  : 1
                is wifi activated : 0
            # CFO Report:
                cfo:     -1.669 ppm
            # Segment Metrics Reports:
                Nbr of Segment Metrics: 1
                # Segment Metrics       0:
                    segment type:       1
                    primary_recv:       1
                    receiver Id:        0x0
                    noise_value:        -80
                    rsl_dBm:            -64.18359375
                    path1_rsl_dbm:      -65.88671875
                    path1_idx:          362
                    path1_snr:          14.11328125
                    path1_t:            23183
                    peak_rsl_dbm:       -64.18359375
                    peak_idx:           704
                    peak_snr:           15.81640625
                    peak_t:             45056
        # Ranging Diag. Report 3:
            Message id:    RangingFinal
            Action:        Tx
            Antenna_set:   0
            Nbr of fields: 1
            # Frame Status Report:
                is processing ok  : 1
                is wifi activated : 0
        # Ranging Diag. Report 4:
            Message id:    MeasurementReport
            Action:        Tx
            Antenna_set:   0
            Nbr of fields: 1
            # Frame Status Report:
                is processing ok  : 1
                is wifi activated : 0
        # Ranging Diag. Report 5:
            Message id:    RangingResultReport
            Action:        Rx
            Antenna_set:   0
            Nbr of fields: 3
            # Frame Status Report:
                is processing ok  : 1
                is wifi activated : 0
            # CFO Report:
                cfo:     -1.714 ppm
            # Segment Metrics Reports:
                Nbr of Segment Metrics: 1
                # Segment Metrics       0:
                    segment type:       0
                    primary_recv:       1
                    receiver Id:        0x0
                    noise_value:        -80
                    rsl_dBm:            -56.03515625
                    path1_rsl_dbm:      -57.69140625
                    path1_idx:          739
                    path1_snr:          22.30859375
                    path1_t:            47326
                    peak_rsl_dbm:       -56.03515625
                    peak_idx:           320
                    peak_snr:           23.96484375
                    peak_t:             20480

[...]

Deinitializing session...
Session 2 -> DeInit (StateChangeWithSessionManagementCommands)
Device -> Ready
Ok
Device: 00:01
                    25 Successful/ 26 Total
                    AVG Ranging: 68.80
                    STDEV Ranging: 3.75
                    AVG AoA Azimuth: 0.000
                    STDEV AoA Azimuth: 0.000
                    AVG AoA Elevation: 0.000
                    STDEV AoA Elevation: 0.000
```

Statistics of the ranging are calculated at the end of the script.

## Example for one-to-many Ranging

Initialize a One-To-Many TWR FiRa session as controller on the first board.

```
run_fira_twr -p <controller port> --node onetomany --dest-mac [0x01,0x02] --n_controlees 2
```

Open a second command shell in the Python script location.

Initialize a TWR FiRa session as controlee on the second board (in this example, in COM40).

```
run_fira_twr -p <controlee 1 port> --node onetomany --controlee --mac 1
```

Open a third command shell in the Python script location.

Initialize a TWR FiRa session as controlee on the third board (in this example, in COM18).

```
run_fira_twr -p <controlee 2 port>  --node onetomany --controlee --mac 2
```

Output of the script running on the controller side:


```
Initializing session 42...
Session 42 Init (StateChangeWithSessionManagementCommands)
Setting session 42 config ...
DeviceRole (0x11):                  0x1
DeviceType (0x0):                   0x1
MultiNodeMode (0x3):                0x1
RangingRoundUsage (0x1):            0x2
DeviceMacAddress (0x6):             0x0
ChannelNumber (0x4):                0x9
ScheduleMode (0x22):                0x1
CapSizeRange (0x20):                0x510
StsConfig (0x2):                    0x0
RframeConfig (0x12):                0x3
ResultReportConfig (0x2e):          0xf
VendorId (0x27):                    0x708
StaticStsIv (0x28):                 0x60504030201
AoaResultReq (0xd):                 0x1
UwbInitiationTime (0x2b):           0x3e8
PreambleCodeIndex (0x14):           0x9
SfdId (0x15):                       0x2
SlotDuration (0x8):                 0x960
RangingInterval (0x9):              0xc8
SlotsPerRr (0x1b):                  0x19
MaxNumberOfMeasurements (0x32):     0x0
HoppingMode (0x2c):                 0x0
RssiReporting (0x13):               0x1
NumberOfControlees (0x5):           0x2
DstMacAddress (0x7):                [1, 2]
Starting ranging...
Session 42 Idle (StateChangeWithSessionManagementCommands)
Device Active
Session 42 Active (StateChangeWithSessionManagementCommands)

[...]

# Ranging Data:
    session id:         42
    sequence n:         0
    ranging interval:   200 ms
    measurement type:   Twr
    Mac add size:       2
    primary session id: 0x0
    n of measurement:   2
    # Measurement 1:
        status:             Ok (0x0)
        mac address:        01.00
        is nlos meas:       Unsupported
        distance:           45.0 cm
        AoA azimuth:        -30.9375 deg
        AoA az. FOM:        88.0 %
        AoA elevation:      0.0 deg
        AoA elev. FOM:      0.0
        AoA dest azimuth:   10.375 deg
        AoA dest az. FOM:   92.0 %
        AoA dest elevation: 0.0 deg
        AoA dest elev. FOM: 0.0 %
        slot in error:      0
        rssi:               -63.0 dB
    # Measurement 2:
        status:             Ok (0x0)
        mac address:        02.00
        is nlos meas:       Unsupported
        distance:           22.0 cm
        AoA azimuth:        -66.578125 deg
        AoA az. FOM:        92.0 %
        AoA elevation:      0.0 deg
        AoA elev. FOM:      0.0
        AoA dest azimuth:   0.0 deg
        AoA dest az. FOM:   0.0 %
        AoA dest elevation: 0.0 deg
        AoA dest elev. FOM: 0.0 %
        slot in error:      0
        rssi:               -35.5 dB

[...]

Stopping ranging...
Deinitializing session...
Session 42 DeInit (StateChangeWithSessionManagementCommands)
Device Ready
Ok
```
## How to run FiRa TWR between 2 DUTs with Provisioned STS with Responder specific Sub-Session Key

Initialize a TWR FiRa session as controller with all required parameters on the first board:

```
run_fira_twr -p COM37 --mac 0x0A --node onetomany --sts provisioned-key
--skey "F1221354652697189900116234236422"
--controlees-with-sskey "[0x0B, 0xC, '00:01:02:03:04:05:06:07:08:09:0A:0B:0C:0D:0E:0F']"
```

Open a second command shell in the python script location.

Initialize a TWR FiRa session as controlee with all required parameters on the second board:

```
run_fira_twr -p COM40 --controlee --mac 0x0B --dest-mac 0x0A --node onetomany --sts provisioned-key
--skey "F1221354652697189900116234236422" --ssession 0xC --sskey "000102030405060708090A0B0C0D0E0F"
```

Output of the script running on controller side:

```
Initializing session 42...
Session 6 -> Init (StateChangeWithSessionManagementCommands)
Using Fira 2.0 session handle is : 6
Setting session 6 config ...
    DeviceType (0x0):                   0x1
    DeviceRole (0x11):                  0x1
    MultiNodeMode (0x3):                0x1
    RangingRoundUsage (0x1):            0x2
    DeviceMacAddress (0x6):             0xa
    ChannelNumber (0x4):                0x9
    ScheduleMode (0x22):                0x1
    StsConfig (0x2):                    0x4
    RframeConfig (0x12):                0x3
    ResultReportConfig (0x2e):          0xb
    VendorId (0x27):                    0x708
    StaticStsIv (0x28):                 0x60504030201
    AoaResultReq (0xd):                 0x1
    UwbInitiationTime (0x2b):           0x0
    PreambleCodeIndex (0x14):           0xa
    SfdId (0x15):                       0x2
    SlotDuration (0x8):                 0x960
    RangingInterval (0x9):              0xc8
    SlotsPerRr (0x1b):                  0x19
    MaxNumberOfMeasurements (0x32):     0x0
    HoppingMode (0x2c):                 0x0
    RssiReporting (0x13):               0x0
    BlockStrideLength (0x2d):           0x0
    NumberOfControlees (0x5):           0x1
    DstMacAddress (0x7):                [1]
    KeyRotationRate (0x24):             0x0
    SessionKey (0x45):                  f1.22.13.54.65.26.97.18.99.00.11.62.34.23.64.22
    StsLength (0x35):                   0x1
Session 6 -> Idle (StateChangeWithSessionManagementCommands)
Updating the multicast list of controlees...
session_update_multicast_list: Ok (0).
Starting ranging...
Device -> Active
Session 6 -> Active (StateChangeWithSessionManagementCommands)
Press <RETURN> to stop
# Ranging Data:
        session handle:         6
        sequence n:         0
        ranging interval:   200 ms
        measurement type:   Twr
        Mac add size:       2
        primary session id: 0x0
        n of measurement:   1
        # Measurement 1:
            status:             Ok (0x0)
            mac address:        00:0b hex
            is nlos meas:       Unsupported
            distance:           42.0 cm
            AoA azimuth:        0.0 deg
            AoA az. FOM:        0.0 %
            AoA elevation:      0.0 deg
            AoA elev. FOM:      0.0
            AoA dest azimuth:   0.0 deg
            AoA dest az. FOM:   0.0 %
            AoA dest elevation: 0.0 deg
            AoA dest elev. FOM: 0.0 %
            slot in error:      0
            rssi:               -0.0 dBm
```
