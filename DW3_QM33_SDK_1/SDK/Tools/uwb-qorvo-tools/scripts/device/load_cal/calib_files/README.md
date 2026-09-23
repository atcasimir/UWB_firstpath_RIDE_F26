# Calibration Files Introduction

JSON calibration files are stored in the directory `scripts/device/load_cal/calib_files`. These files enable the configuration of default calibration settings for various targets.

The calibration and configuration data are encapsulated within JSON files, which can be passed as arguments to the `load_cal` script. This script processes the JSON file and transmits the settings to the device via UCI for device configuration.

## Directory Structure

```
calib_files
├── <target_1>                          <- Default calibrations for <target_1>
│   └── <antenna_1>.json                <- JSON calibration file for <target_1> and <antenna_1>
├── <target_2>                          <- Default calibrations for <target_2>
│   ├── <antenna_1>.json                <- JSON calibration file for <target_2> and <antenna_1>
│   └── <antenna_2>.json                <- JSON calibration file for <target_2> and <antenna_2>
└── ...
```

## Customizing JSON Calibration Files

Default configuration JSON files serve as examples and can be customized to meet specific requirements. Calibration and configuration are managed through a Key/Value mechanism, reflected in the structure of these JSON files.

> **Note:** Detailed descriptions of available Calibration and Configuration keys are provided in a separate document.

Example JSON file:

```json
{
  "LUT": {
    "PDOA_LUT_0_CH5" : [
      [-2.9021, -1.5708],
      ...
      [3.0487, 1.4661],
      [3.1142, 1.5708]
    ],

    "PDOA_LUT_1_CH9" : [
      [-3.3905, -1.5708],
      ...
      [2.8451, 1.4661],
      [2.8932, 1.5708]
    ]
  },

  "calibrations": {
    "pdoa_lut0.data": "PDOA_LUT_0_CH5",
    "pdoa_lut1.data": "PDOA_LUT_1_CH9",

    "ant0.transceiver": "0x00",
    "ant0.port": "0x01",
    "ant0.lna": "0",

    ...
  }
}
```
