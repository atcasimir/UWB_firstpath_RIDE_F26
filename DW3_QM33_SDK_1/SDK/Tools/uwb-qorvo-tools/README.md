# UWB Qorvo Tools

Welcome to the 'UWB Qorvo Tools' (UQT) Reference Guide. This guide is designed
to help you navigate and utilize the various tools provided by Qorvo for operating
Ultra-Wideband (UWB) devices through the UCI (UWB Communication Interface).

> Warning: These tools are delivered by Qorvo as UCI examples on an as-is basis and
are not optimized nor meant to be used as an end product.

## Root Folder Organization

Here is the core structure and key components of the UQT library. Less critical files and directories have been omitted.

```
uwb-qorvo-tools
    ├── README.md                         <-- UQT Introduction
    ├── pyproject.toml                    <-- UQT Project configuration file.
    ├── lib                               <-- Library folder.
    │   |── uqt-utils                     <-- Helpers for main scripts.
    │   └── uwb-uci                       <-- UCI transport layer libraries.
    └── scripts                           <-- Script folder divided into "chapters".
        ├── <functionality_1>             <-- A "chapter" represents functionality 1.
        │   ├── <example_1>               <-- Example 1 for functionality 1.
        │   │   ├── <example_1_main.py>   <-- Entrance point for example 1 for functionality 1.
        │   │   ├── <example_1_helper.py> <-- Helper script for example 1 for functionality 1.
        │   │   ├── ...                   <-- Other scripts and assets needed for for example 1 for functionality 1.
        │   │   └── README.md             <-- Documentation for example 1 for functionality 1.
        │   ├── <example_2>               <-- Example 2 for functionality 1.
        │   ├── ...                       <-- Other examples for functionality 1.
        │   └── README.md                 <-- Generic documentation for functionality 1.
        ├── <functionality_2>             <-- A "chapter" represents functionality 2.
        └── ...                           <-- Other "chapters" represent further functionalities.
```

## Prerequisites

- Installed python 3.10
- Installed pip 21.3 or greater

### Python

You may download Python 3.10 from [official web page](https://www.python.org/downloads/) or install it using an appropriate package manager.

In Linux you may install python using apt:
```
sudo apt-get install python3.10
```

In Windows PowerShell you may install python using chocolatey:
```
choco install python310 -y
```

In macOS:
  - Download Python from: https://www.python.org/downloads/. Recommended version is 3.10.
  - Install Python pkg.

### PIP upgrade

You may upgrade pip to a required version by executing:
```
pip install pip>=21.3 --upgrade
```

## Quick Start

### Install UQT

After you have installed the prerequisites mentioned above, you can proceed with the installation of UQT. There are two types of installations: editable and non-editable. The non-editable installation is the default option and is recommended for most users. However, if you need to make modifications to the UQT codebase, you should use the editable installation.

#### Non-Editable Installation

To perform a non-editable installation of UQT, follow these steps:

##### Linux
```
cd uwb-qorvo-tools
python -m venv .venv
source .venv/bin/activate
pip install .
```

##### Windows PowerShell
```
cd uwb-qorvo-tools
python -m venv .venv
.\.venv\Scripts\activate.ps1
pip install .
```

##### macOS zsh
```
cd uwb-qorvo-tools
python -m venv .venv
source .venv/bin/activate
pip install .
```

#### Editable Installation

To perform an editable installation of UQT, follow these steps:

##### Linux
```
cd uwb-qorvo-tools
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e lib/uqt-utils/
pip install -e lib/uwb-uci/
```

##### Windows PowerShell
```
cd uwb-qorvo-tools
python -m venv .venv
.\.venv\Scripts\activate.ps1
pip install -e .
pip install -e lib/uqt-utils/
pip install -e lib/uwb-uci/
```

##### macOS zsh
```
cd uwb-qorvo-tools
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e lib/uqt-utils/
pip install -e lib/uwb-uci/
```

> **Note:** The order of package installation matters!. When performing an editable installation, it is important to install the packages in the following order: UQT, uqt-utils, and uwb-uci. This ensures that any changes made in the dependencies are properly reflected in the main project. When installing the main project in editable mode using `pip install -e .`, it is crucial to manually install the dependencies in the correct order to ensure that any changes made in the dependencies are properly reflected in the main project.

### Executing programs

If UQT is installed within a virtual environment, you must activate the virtual environment before executing scripts. If UQT is installed globally, you can skip this step.

To activate the virtual environment, follow the instructions below:

**Linux**
```
cd uwb-qorvo-tools
source .venv/bin/activate
```

**Windows PowerShell**

```
cd uwb-qorvo-tools
.\.venv\Scripts\activate.ps1
```

> **Warning** On Windows recommened to use shell is PowerShell. Other shell like cmd, Git Bash, etc. may require activation of the virtual environment with other activation scripts.

**macOS zsh**
```
cd uwb-qorvo-tools
source .venv/bin/activate
```

After the virtual environment is activated you may use Python scripts as other regular Python scripts:
```
python /path/to/script1.py <arg1> <arg2> <...>
python /path/to/script2.py <arg1> <arg2> <...>
```

The second option is using entry points. In this case, an explicit call to `python` is not needed:
```
<entry_point1> <arg1> <arg2> <...>
<entry_point2> <arg1> <arg2> <...>
```

### How to check all possible entry points

```
uqt_ls
-> <script_name_1>                          One line description of <script_name_1>
-> <script_name_2>                          One line description of <script_name_2>
-> <script_name_3>                          One line description of <script_name_3>
...
```

In order to get more information about a specific script run it with `-h` option or read `README.md` file in the appropriate subdirectory in `script` folder.

For example:
```
<script_name_1> -h
```

### How to check current environment

```
uqt_info

    # Python3 version:
        ...
    # Customization (UQT_CUSTOM):
        ....
    # Wanted Extensions (UQT_ADDINS):
        addin_name_1
        addin_name_2
        addin_name_3
        ...
    # Loaded Extensions:
        ...
    # DUT 'Default':
        unknown port ('UQT_PORT' not defined.)
```

## Manual: About communicating with a DUT

The DUT communication is done through the use of OS 'ports': `COMxx`, `/dev/ttyUSBxx`, `/dev/serial/xx`, `/dev/cu.usbmodemxx`.
The related transport protocol is UART.

### Communication Ports

To find the appropriate port for your DUT, please:

**Windows (PowerShell)**:
   - Open the Device Manager.
   - Expand `Ports (COM & LPT)`.
   - Look for your DUT port (e.g. `USB Serial Port (COM5)`).
   - Use the port number (e.g. `COM5`) to set the `UQT_PORT` variable.
   - Set a default port:
        ```
        $env:UQT_PORT="<port>"
        ```
   - Verify the proper settings:
        ```
        uqt_info
        ```

**Linux**:
   - List the available ports using `ls /dev/serial/by-id/`.
   - Look for the appropriate port (e.g. `/dev/serial/by-id/usb-Nordic_Semiconductor_nRF52_USB_Product_<XYZ>-if00`).
   - Use the port name (e.g. `/dev/serial/by-id/usb-Nordic_Semiconductor_nRF52_USB_Product_<XYZ>-if00`) to set the UQT_PORT variable.
   - Set a default port:
        ```
        export UQT_PORT="<port>"
        ```
   - Verify the proper settings:
        ```
        uqt_info
        ```

**macOS**:
   - List the available ports using `ls /dev/`.
   - Look for the appropriate port (e.g. `/dev/cu.usbmodem<XYZ>`).
   - Use the port name (e.g. `/dev/cu.usbmodem<XYZ>`) to set the UQT_PORT variable.
   - Set a default port:
        ```
        export UQT_PORT="<port>"
        ```
   - Verify the proper settings:
        ```
        uqt_info
        ```

> **Note**: For UQT scripts that require specifying a communication port, the `--port` option is available. If this option is not explicitly provided, the scripts will by default use `UQT_PORT` environment variable as the communication port with the Device Under Test (DUT). The `--port` option can always be used to manually specify the port regardless of the `UQT_PORT` setting.

## Manual: about configuring your DUT

### How to get/set Device Configuration

```
# Get the list of available parameters:
    get_config -l
# Get the value of all available parameters:
    get_config all
# Set the default channel number to 5:
    set_config ChannelNumber 5
```

### How to get/set Calibration Parameters

```
# Get the list of available parameters:
    get_cal -l
# Get the value of all cal parameters as binary stream:
    get_cal -b all
# Backup all your calibration values to a file:
    get_cal -fa all | tee my_calibration.txt
# Recover your calibration values from a file:
    set_cal -i my_calibration.txt
```

**In order to get more information about a specific script and/or use case please read the subsequent chapter or `README.md` file in the appropriate subdirectory.**
