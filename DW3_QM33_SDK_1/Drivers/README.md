# DW3XXX (QM33) Application Programming Interface (API)

## UWB Drivers API documentation

The latest DW3xxx/QM33xxx driver API documentation is available in the ``docs`` folder.

## Folders structure

  - API/Shared/dwt_uwb_driver

    Driver for DW3XXX UWB transceiver ICs. Details about each function can
    be found in DW3XXX API Guide.

  - API/Src/examples

    A set of individual (simple) examples showing how to achieve different
    functionalities, e.g. sending a frame, receiving a frame, putting the
    DW3XXX to sleep, two-way ranging.  The emphasis of theses examples is
    to be readable with explanatory notes to explain and show how the main
    features of the DW3XXX work and can be used.

  - API/Build_Platforms/STM_Nucleo_F429

    Hardware abstraction layer (system start-up code and peripheral
    drivers) for ARM Cortex-M and ST STM32 F1 processors. Provided by ST
    Microelectronics and platform dependant implementation of low-level 
    features (IT management, mutex, sleep, etc) for STM_Nucleo_F429.

  - API/Build_Platforms/nRF52840-DK

    Hardware abstraction layer (system start-up code and peripheral
    drivers) for ARM Cortex-M and nRF52840 processors. Provided by 
    Nordic Semiconductor and platform dependant implementation of low-level 
    features (IT management, mutex, sleep, etc) for nRF52840-DK.

Please refer to DW3XXX API Guide accompanying this package for more details
about provided API and examples.

NOTE: The DW3XXX API/driver code included in this package is an unbundled
      version of the DW3XXX API/driver. This version may be different to
      (generally by being newer than) those bundled with Decawave's other
      products. This particular release covers the DW3XXX hardware.

## Building with CMake

### Required software
1. [cmake](https://cmake.org/download/)
2. [ARM GNU Toolchain](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)
   - Select the recommended release from AArch32 bare-metal target (arm-none-eabi) architecture.
   - Currently we recommend version 12.2.rel1.
3. [Ninja](https://github.com/ninja-build/ninja/releases)

### Environment variables
1. CMAKE_MAKE_PROGRAM - path to 'ninja' executable. Set it if 'ninja' is not in PATH

### Build steps

The provided CMake build system supports building the examples and the tests. 
When all build targets are selected (default), it will build the test enabled in 
the `examples/example_selection.h` header.

The CMakePresets.json file contains various CMake configuration and build presets, 
the only development kit supported with CMake at the moment is nRF52840-DK. 
The preset is called nrf52840_flash.

To list the available presets: 
```shell
cmake --list-presets     
```

With CMake, the build system needs to be configured before the software can be built. 
When using the default generator (Ninja), issue the following to configure the build system with the default build type (Debug).

```shell
cmake --preset=nrf52840_flash_debug
```

To use the release build type (e.g., Release), use the following:

```shell
cmake --preset=nrf52840_flash_debug -DCMAKE_BUILD_TYPE=Release
```

or directly using the preset:

```shell
cmake --preset=nrf52840_flash_release
```

The following build types are supported.
- Debug - Minimal optimization, debug info included.
- Release - Maximum optimization for speed.
- RelWithDebInfo - Maximum optimization for speed, debug info included.
- MinSizeRel - Maximum optimization for size.

After the configuration step is done, the project can be built using the following command.
```shell
cmake --build --preset nrf52840_flash_debug
```

### CMake UWB optional configuration

It is possible to configure a specific UWB configuration via CMake. 
This configuration is optional and if CMake does not define it, each example will define its own.
Currently there are 41 different possible UWB configurations, from ```CONFIG_OPTION_01``` to ```CONFIG_OPTION_41```,
see file ```config_options.h``` for more info. To change to a specific option use the ```-DCMAKE_UWB_CONFIG_OPTION=n``` flag
where ```n``` specify the config option and goes from 1 to 41. For example, to select configuration option 22, 
```CONFIG_OPTION_22``` the flag will be:

```shell
cmake --preset=nrf52840_flash_debug -DCMAKE_UWB_CONFIG_OPTION=22
```

Later it is possible to build as per the step above.

### CMake option to build specific examples

All the examples available can be seen in the ```example_selection.h``` file. Usually to build an example it
is required to uncomment the specific line in the above mentioned file. e.g. to build the example ```TEST_READING_DEV_ID```
it is necessary to uncomment the line ```//#define TEST_READING_DEV_ID``` in the file ```example_selection.h```.
With CMake it is also possible to provide the correct example in the configuration phase, hence, to build the same example with CMake
you can run the command 
```shell
cmake --preset=nrf52840_flash_debug -DCMAKE_BUILD_EXAMPLE=TEST_READING_DEV_ID
```
CMake supports both ways to build examples but if the command line is used then all the lines in ```example_selection.h```  need to be commented.
Likewise, if the manual option is used then CMake should not provide any ```CMAKE_BUILD_EXAMPLE``` flag.
Only one example at a time can be built.

### Input/output configuration
By default, RTT is used for input/output (logging).


## Release Notes 

See [Changelog](Changelog.md)