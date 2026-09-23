# PHY Conformance Tests (PCT)

The FiRa Consortium has established a Certification Program to verify that UWB-enabled devices conform to its requirements and test specifications. The FiRa Certification Program supports interoperability across UWB devices, focusing on secure time-of-flight (ToF) ranging measurements.

The PHY Conformance Tests (PCT) is part of the FiRa Certification Program, which ensures that specific UWB (Ultra-Wideband) devices under test (DUT) satisfy the FiRa requirements regarding the physical layer based on the IEEE 802.15.4 standard.

## Directory Structure

This directory contains the calibration and configuration file, along with a test setup diagram and README file to guide users on how to perform PHY Conformance Tests for the `QM33120WDK1` device. The directory structure is as follows:

```
.
├── README.md
├── pct_config.json
└── pct_setup_diagram.png
```

- **`README.md`**: Provides details about the PCT configuration files and the testing setup.
- **`pct_config.json`**: Configuration file for running PHY Conformance Tests for both AoA and non-AoA board type.
- **`pct_setup_diagram.png`**: Schematic diagram showing the setup used during the tests.

### PCT Configuration File

The PCT configuration file (`pct_config.json`) provided in this directory is specifically tailored for the `QM33120WDK1` setup used in PHY Conformance Testing. This file is designed to support both AoA (Angle of Arrival) and non-AoA board type. The configuration parameters are set according to the used test environment and hardware setup to ensure accurate and reliable test results.

> **Note:** In case of any changes to the hardware setup or test environment, the configuration file must be updated accordingly to reflect the new settings.

### PCT Setup

The testing setup includes hardware configurations required to perform FiRa conformance testing on the `QM33120WDK1`. A schematic of the testing setup (`pct_setup_diagram.png`) is provided to illustrate the exact connections between the key components used in the testing environment. This setup is crucial for achieving accurate and repeatable test results.

#### Setup Components

1. **QM33120WDK1**: The device under test (DUT), either AoA or non-AoA type, connected via RF and UART interfaces.
2. **PHY Conformance Test Tool (PCTT)**: A test equipment that interacts with the QM33120WDK1 to perform PHY conformance tests.
3. **Splitter Combiner**: Used to route RF signals between the QM33120WDK1 and PCTT. It manages the IN/OUT signals required for the test.
4. **PC with PCTT software**: The control system that manages the testing process using dedicated for particular PCTT software. It communicates with the PCTT and the QM33120WDK1 via UART and RF interfaces.

#### Path-Loss Adjustment

> **Warning:** Using a splitter-combiner in your test setup introduces additional signal loss. To ensure accurate test results, adjust the path-loss parameter in your PCT tool software to compensate for this loss. Refer to your PCT tool documentation for instructions on how to set this parameter.

## Running PHY Conformance Tests

1. Ensure that your hardware setup matches the schematic provided in `pct_setup_diagram.png`.
2. Reset the configuration and calibration of the DUT by running:
   ```
   reset_calibration -p <port>
   ```
3. Load the configuration and calibration from `pct_config.json` file into your DUT by running:
   ```
   load_cal -p <port> -f pct_config.json
   ```
4. Start the PHY Conformance Tests using the PCTT equipment and dedicated software.
   - Ensure the path-loss parameter in your PCT tool software is set to account for signal loss from the splitter-combiner ([see Path-Loss Adjustment](#path-loss-adjustment)).
