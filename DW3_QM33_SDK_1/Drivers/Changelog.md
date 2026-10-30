# QM33 Simple-Examples Release Notes

## Package v17 / Driver v08.19.02  ( 23 Apr 2025)

### Changes to ``dwt_uwb_drivers``

1. Bug fixes:
   * Fixed ``dwt_get_reg_names`` API, now correctly returning the registers and their values. Note that to use it, ``DGB_LOG`` needs to be defined.
   * Added ISR check to prevent call to error callback for SP1 0-length frame.
   * Added different lower bound threshold when selecting PRF16 configuration.
2. Added APIs:
   * Added ``dwt_getgpiodir `` API to get the GPIO direction.
3. Reworked APIs:
   * Improved PLL calibration speed time for both devices.
      * On standard releases, we run hardware calibration for PLL and only run software calibration if hardware fails. This fixes issue for some parts where PLL wouldn't lock at T <= -30C, but the lock times are higher at these temperature.
      * For Automotive releases, by default we run software PLL calibration on only run hardware ones if the first fail.
   * The ``dwt_read_rx_scratch_data`` was renamed ``dwt_read_scratch_data``.
   * The ``dwt_write_rx_scratch_data`` was renamed ``dwt_write_scratch_data``. 
   * Refactored ``dwt_initialise`` API to accept the same parameters as QM35xx.
   * Reworked the error value returned by ``dwt_configure`` to be more error-specific.
4. Documentation:
   * General fixes to the API documentation.
5. Others
   * MISRA fixes.
   * Added support for GoogleTest and the ability to run unit tests internally.
   * Improved ISR execution time.

### Changes to ``simple-examples``

1. Bug fixes:
   * Changed ``dwt_initialise`` API calls to provide the correct argument.
2. General improvements:
   * Added ``DGB_LOG`` in CMake to enable register dump.
   * Updated examples to use new APIs ``dwt_read_scratch_data`` and ``dwt_write_scratch_data``.
   * Added ``frame_filtering_rx`` and ``frame_filtering_tx`` examples.
   * Added automated test capability.

## Package v16 / Driver v08.13.05  ( 25 Feb 2025)

### Changes to ``dwt_uwb_drivers``

1. Bug fixes:
   * Fixed ``dwt_readpgdelay`` API to return correct mask.
   * Speed-up ISR execution by reading frame length only if necessary.
   * Reworked internal ADC calibration routine for DW3720.
   * Fixed TX control port settings to enable correct RF port.
   * Set default value for ``STS_NTM`` = 10 to deliver the best performance detecting
     first path in reflective environment while limiting occurrence of false first path detection.
   * Updated default value of ``DWT_DGC_CFG1`` to increase success of RX in high receive signal level.
   * Fixed a bug in ``dwt_config`` that was wrongly configuring the DGC. Also, 
      the DGC will now be enabled for both PRF64 and PRF16.
   * Enforcing check on RX and TX state before setting device into IDLE state.
   * Fixed crash when calling private structure ``dwt_local_data_t priv`` before ``dwt_initialise``.
   * Fixed crash when calling ``dwt_isr`` DW structure is assigned to correct pointer. 
2. Added APIs:
   * Added ``dwt_restore_common`` to be called after wake-up from sleep.
   * Added ``dwt_restore_txrx`` to be called after ``dwt_restore_common`` when TX/RX are required.
   * Added ``dwt_setpllrxprebufen`` API to enable/disable the PLL RX prebuffer.
3. Deprecated APIs:
   * Deprecated ``dwt_restoreconfig`` and split into two APIs ``dwt_restore_common`` and ``dwt_restore_txrx``.
4. Reworked APIs:
   * Renamed ``dwt_getpllcalibrationtemperature`` to ``dwt_getpllcaltemperature``.
   * Modified ``dwt_readcir`` and ``dwt_readcir_48b`` to return ``DWT_SUCCESS`` or ``DWT_ERROR``. 
5. Documentation:
   * Fixed Doxygen style documentation.
   * Now using Sphinx to to auto-generate the drivers API documentation.

### Changes to ``simple-examples``

1. Bug fixes:
   * Added missing read dev ID from ``TEST_DS_TWR_INITIATOR`` example.
   * Added error check after ``dwt_probe`` is called in each example.
   * Outdated comments clean-up.
   * Fixed "Release" build option for both CMake and SES IDE, for nRF52840-DK.

2. General improvements:
   * Added CMake as build system option for nRF52840-DK.
   * Update simple-examples to demonstrate the new ``dwt_restore_txrx`` and ``dwt_restore_common``APIs.
   * Updated ``README.md`` with latest changes and latest auto-generated Sphinx doc.

## Package v15 / Driver v08.09.05  ( 06 Dec 2024)

1. Bug fixes:
   * Fixed bug in ``dwt_readdiagnostics_acc`` that was reading incorrect peak path position and potentially affecting applications availing of LOS/NLOS algorithm.
   * Fixed a bug that was impacting a small number of DW3000 parts after wake-up. This bug was impacting ranging performance when sleep was enabled.
   * Updating DGC configuration when swapping PRF. When swapping PRF configuration without going through ``dwt_configure`` API, i.e. using ``dwt_setrxcode`` the DGC configuration wasn't updated. With this fix, the DGC will be updated based on the PRF used in both ``dwt_configure`` and ``dwt_setrxcode``.
   * Fix the ISR when RX has FCS check disabled (FCE bit is set). The RX OK callback will be called, host needs to do own CRC check on the data.

2. Reworked to existing APIs:
   * Reworked ``dwt_restoreconfig`` to return an error in case PGF cal or ADC cal fails. ADC cal might fail in case a frame is received during calibration.
   * Improved the way  ``dwt_restoreconfig`` handles different wake-up states (IDLE and IDLE_RC) for DW3000 and DW3720.
   * Improved reliability of ADC calibration routine for DW3720.
   * ``dwt_configtxrxfcs`` now receives a ``uint8_t`` rather than ``dwt_fcs_mode_e``.
   * Reworked ``dwt_configcwmode`` and ``dwt_configcontinuousframemode`` to give user more control to turn on the TX LDOs for back to back frames and disable the RF sequencing if the frame repetition rate is zero.

3. General documentation fix and improvements.

## Package v14 / Driver v08.07.04  ( 22 Oct 2024)

1. Bug fixes:
   * Fixed ``dwt_setplenfine`` to properly set ``DWT_PLEN_4096``.
   * Disabled hardware PGF calibration on wake-up as it was introducing a 3-5 cm error/offset in the DS TWR with auto-sleep enabled.
   * Fixed ``dwt_writesysstatushi`` and ``dwt_readsysstatushi`` on DW3720, we were 
   reading / writing only 16 out 20 bit in ``SYS_STATUS_HI`` register.

2. Added APIs:
   * ``dwt_settxcode`` - Added this API to allow to change TX code without
   calling ``dwt_configure``.
   * ``dwt_setrxcode`` - Added this API to allow to change RX code without
   calling ``dwt_configure``.

3. Reworked to existing APIs:
   * Reworked ``dwt_setplenfine``, now the preamble length codes constants
   match with the actual length, so DWT_PLEN_32 = 32, etc.
   * Added ``DWT_STS_LEN_16`` in ``dwt_sts_lengths_e`` and changed to enums values
   to match qsoc_drv.
   * Reworked ``dwt_restoreconfig`` to allow to force or restore ADC calibration
   values.
   * ``dwt_calculate_linear_tx_setting`` renamed ``dwt_calculate_linear_tx_power``.
   * ``dwt_set_pll_config`` renamed ``dwt_setpllbiastrim``.
   * Reworked ``dwt_isr`` to speed up the interrupt handling function.

4. General documentation fix and improvements.

## Package v13.1 / Driver v08.02.02  ( 19 June 2024)

1. Bug fixes:
    * Fixed temperature reading for DW3000 devices.

2. Updated license to new standard.

## Package v13 / Driver v08.02.00  ( 7 June 2024)

The following updates are included in this release.

1. Bug fixes: 
    * Fixed ``dwt_getlotid`` function, now it returns the correct  lot ID.
    * Fixed ``dwt_readcir`` function in compressed mode.
    * Fixed compilation error when using NO_HEAP_BUILD flag, now the
    drivers do not have any dynamic allocated memory. 
    * Improved ``dwt_setplenfine`` API to accept any preamble length from 
    16 to 4096 and aligned with QM35 counterpart.
    * Fixed build error with SES IDE version higher than 5.5.
    * Fixed build error with System Workbench for STM32 IDE.
    * Fixed a bug in the isr which was treating packets with 
    zero length as error, this would cause FiRa SS TWR to fail.
    * Fixed PLL lock issue at -30C for DW31x0 C0 devices.

2. Added APIs:
    * ``dwt_convert_tx_power_to_index`` - API used to convert a TX power value 
                                into its corresponding TX power index.
    * ``dwt_configureisr`` - Configure "isrFlags" to accept or reject 
                    zero-length packages.
    * ``dwt_setpdoamode`` - Used to configure the PDOA mode.

3. Rework to existing APIs:
   * ``dwt_xtal_temperature_compensation`` - changed to allow to read temperature from CLI.
   * ``dwt_configure_rf_port`` - reworked this API to allign with the chip capabilities.  
   * ``ull_restoreconfig`` - added `full_restore` flag that allows to perform a full restore 
   or restore without DGC update, PGC and ADC offset calibration. 

4. Updated README and Changelog to MarkDown file extension.

## Package v12.1 / Driver v08.00.23  (15th February 2024)

The following updates are included in this release.

1. Bug fixes: 
    * Updated temperature sensor conversion equation +3 degree correction.
    * Fixed a bug in dwt_readclockoffset to return correct clock offset

2. Minor updates:
    * Updated license header
      
## Package v12.0 / Driver v08.00.22  (31st January 2024)

The following updates are included in this release.

1. Bug fixes: 
    * Fixed bug with dwt_getframelength() which was occasionally corrupting the stack.
    * Fixed bug with dwt_getlotid() which always returned 0.
    * Fixed bug with dwt_configure() and dwt_setchannel() which weren't properly setting 
    the channel and returning to IDLE_PLL state.
    * Fixed simple-examples' CI bug which wasn't building examples as expected

2. Major changes to the drivers:
    * Added MISRA compliance to dwt_uwb_driver
    * Added initial CI pipeline on Gitlab to build dwt_uwb_driver 
    using CMake tool
    * Aligning several APIs / structures to match qsoc_drv

3. API guide update and release.

5. Added APIs:
    * dwt_getwslotid
    * dwt_settxpower
    * dwt_readpllstatus
    * dwt_calculate_rssi
    * dwt_calculate_first_path_power
    * dwt_readcir48
    * dwt_readdiagnostics_acc

6. Deprecated APIs:
    * dwt_readaccdata

## Package v11.0 / Driver v08.00.11  (13th October 2023)

The following updates are included in this release.


1. Bug fixes: 
    * Minimised carrier feedthough in TX spectrum. 
    * Updated LUT for TX power linearization and LO leakage. 
    * Compensation of ToA variation which occurs when reading VBAT.
    * Fixed disable of fine grain TX sequencing, updated dwt_setfinegraintxseq() API.
    * DW3720: fix for PGF calibration / RX performance when sleep enabled.
    * Fixed an issue with PLL calibration routine when auto calibration is used.

2. Changes to the driver architecture:
    * Removed requirement for linker definition of device driver symbol.
    * Added modern CMake to drivers.
    * New header file naming per chip variant, example: dw3720_deca_regs.h.
    * Removed DW3700 drivers, the DW3700 device is no longer supported.
    * Added the -Werror for "Shared" folder which has dwt_uwb_driver.

3. API guide update and release.

4. Added features for automotive:
    * Use custom vdddig value (To address ToA issues observed at cold temperatures (-40 3., the device now allows for a custom VDDDIG value to be set.).
    * Adding init_no_chan functionality allowing to initialise device without reconfiguring channel.

5. Added APIs:
    * dwt_readcir - CIR API allowing user to read the CIR.
    * dwt_configtxrxfcs - FCS/FCE management (allow to enable/disabled FCS).

6. Deprecated APIs:
    * dwt_softreset_fcmd.
    * dwt_softreset_no_sema_fcmd.

7. Other improvements:
    * Improved algorithm for ADC offset calibration.
    * Rework softreset (Added workaround for softreset issue seen at cold temp).
    * PLL cal optimization.
    * Adding an API to configure PLL_COMMON register for use in TX power adjustment.

8. Added examples:
    * Simple RX CIR.
    * Linear TX power.

## Package v10.0 / Driver v07.10.01  (20th December 2022)

The following updates are included in this release.

1. Add support for QM33110 part

2. Refine LDO configuration for channel 5 for improved ranging performance

3. Update existing APIs to align with QM35 API. Required to reduce the
customization of host software to support Qorvo UWB chips.
Updated APIs:
    * dwt_readrxtimestamp
    * dwt_readrxtimestamplo32
    * dwt_readstsquality
    * dwt_getframelength

4. Adding new APIs to align with QM35 API. Required to reduce the
customization of host software to support Qorvo UWB chips.
New APIs:
    * dwt_read_tdoa_pdoa
    * dwt_disablecontinuouswavemode
    * dwt_setchannel
    * dwt_setstslength
    * dwt_setphr
    * dwt_setdatarate
    * dwt_setrxpac
    * dwt_setsfdtimeout

5. Disable AGC (automatic gain control) by default for optimized
receiver performance

6. Update ADC offset calibration function to prevent false packet
detection. 

7. Adding two APIs allowing to capture and read ADC samples:
    * dwt_capture_adc_samples
    * dwt_read_adc_samples

8. Adding AUTO_PLL_CAL define. It enables a hardened PLL calibration
at higher temperature for automotive application.
 AUTO_PLL_CAL is defined in deca_api_device.h and is commented by default.

9. Adding example 02j demonstrating capture and reading of ADC samples

10. Adding example 01j demonstrating the automotive build

## Package v9.3 / Driver v06.00.13  (15th May 2022)

The following updates are included in this release.

1. Updates to driver to support QM33120 parts

2. Clearing RXFR event bit in ISR for RXERR case

3. Fix Issue when writing the STS Length into the register

4. Correction in the uwb driver (BIAS_CTRL and STS_CFG – register bitfields to match User Manual)

5. Disabling PGR as well as ACD/SS count checks (needs further Systems work/threshold tuning before these STS checks can be used)

6. Enable equaliser for all modes (improves range bias)

7. Always running PGF_CAL during configuration

## Package v9.2 / Driver v06.00.06  (1st Oct 2021)

The following updates are included in this release.

1. Updated the SFD holdoff configuration to be restored to default
   if preamble length <= 64, this will make sure correct configuration is applied
   when dwt_configure() is called multiple times without device reset.

## Package v9.1 / Driver v06.00.05  (16th Sept 2021)

The following updates are included in this release.

1. Updated PLL lock wait time to 1ms, this is the max time application/host
   should wait to allow PLL to lock. In general the lock time is < 100 us, 
   however on some slow-corner parts the time may take up to 900 us!

## Package v9.0 / Driver v06.00.04  (17th August 2021)

The following updates are included in this release.

1. Various API calls have been updated to be compatible with latest versions of
   the driver APIs.

2. NLOS (Non Line-Of-Sight) example has been added to project.

3. TX Power adjustment example has been added to project.

4. AES-CCM* example added to illustrate how to use AES-CCM* correctly. The
   example uses the test vectors defined in the IEEE 802.15-4-2020 standard.

5. Design of dwt_probe() API changed since last release. The Simple Examples
   have been updated accordingly to cater for this.

6. Various coding style changes made throughout to give code a singular coding
   style.

7. Fix for SP3 packets RX events handling on DW3720 devices in dwt_isr() API.

8. Refactoring done to unify the different driver versions into one.

9. dwt_ds_sema_request() function now no longer returns a value.

10. ADC threshold has been reverted back to ADC_TH_TIE default.

11. For longer Ipatov preamble of > 64, the dwt_configure() now correctly sets
   the number of symbols of accumulation to wait before checking for an SFD
   pattern.

12. The following new APIs have been added to the driver:

    * dwt_set_alternative_pulse_shape() - Set alternate pulse shape according to ARIB.
    * dwt_entersleepafter() - Auto enter sleep / deep-sleep after TX.
    * dwt_ds_sema_status_hi() - Read semaphore status high byte.
    * dwt_ds_setinterrupt_SPIxavailable() - Enable/disable events on SPI1MAVAIL or SPI2MAVAIL events.
    * dwt_update_dw() - Update device pointer used by interrupt.
    * dwt_nlos_alldiag() - Determine if received signals (Ipatov/STS1/STS2) is LOS (Line-Of-Sight) or NLOS (Non-Line-Of-Sight).
    * dwt_nlos_ipdiag() - Determine if received Ipatov signal is LOS (Line-Of-Sight) or NLOS (Non-Line-Of-Sight).
    * dwt_adjust_tx_power() - calculate TX power setting by applying boost.
        NOTE: The following additional APIs are for debug use only. They are only
            used by DecaRanging.

    * dwt_getrxantennadelay() - Get current 16-bit RX antenna delay value.
    * dwt_gettxantennadelay() - Get current 16-bit TX antenna delay value.
    * dwt_readctrdbg() - Get low 32-bits of STS IV counter.
    * dwt_readdgcdbg() - Get 32-bit value of DGC debug register.
    * dwt_readCIAversion() - Get CIA image version written to chip.
    * dwt_getcirregaddress() - Get CIR base address.
    * dwt_get_reg_names() - return list of regsiter name/value pairs for
            debug.

13. Handling of uncorrectable errors in PHR has been added. This stops frame
   lengths being reported as zero in some cases.

14. A compilation flag (_DGB_LOG) has been added to allow for debug strings to
   be enabled/disabled as a project needs them.

15. Fixes added for dwt_isr() when STS No Data packets are used. There was a
   potential for regular frames to be treated as STS No Data packets.

16. WIN32 compilation of driver has been cleaned up to be more streamlined.

17. dwt_setcallbacks() has an additional input argument for a pointer to a
   callback function for Dual SPI events.

18. dwt_softreset() now has an input parameter. It resets the semaphore. This
   change is only valid for DW3720 devices.

19. Fix added for dwt_readdiagnostics() API. Some values in API were not being
   read correctly from registers.

20. dwt_setgpiomode() API has been refactored to make is easier to use. Input
   parameters have changed.

21. Improvements made for large, varying range values on Channel 9.

## Package v8.1 / Driver v05.05.04  (02nd June 2021)

In addition to the existing updated driver layout for ER2.1 release. Following
updates are included in this release changed from ER2.1 release.

1. Added an API to set “Fixed STS” - the same STS will be sent in each packet.

2. Disable ADC count warning check in DW3xxx, flag was raised in error.

## Package v8.0 / Driver v02.01.00  (06th May 2021)

In addition to the existing updated driver layout for ER2.0 release. Following
updates are included in this release changed from ER1 release.

1. Enabling the second SPI support on ST Micro and the Nordic nRF52840-DK.
   Changes in main.c() for STM32 to initialise second SPI and changes in file
   “deca_spi.c” for the initialisation of second SPI in
   “Build_Platforms\nRF52840-DK\Source\platform”.

2. Disable Pre-buffer-enable for Ch9 PLL calibration for E0.

3. Bug in deca_compat.c where dwt_read_reg() was returning 0.

4. Fixing function that write the PDoA Offset in deca_compat.c under
   case: “DWT_SETPDOAOFFSET”. The value to be written is ANDed with the
   inverse of CIA_ADJUST_PDOA_ADJ_OFFSET_BIT_MASK.

5. Simple Examples updated are same as ER2.0 except:
    * Double Buffer RX example:
        Second SPI support enabled for both ST Micro and the Nordic nRF52840-DK.
    * Read Dev ID:
        Second SPI support enabled for both ST Micro and the Nordic nRF52840-DK.
    * Simple TX:
        Second SPI support enabled for both ST Micro and the Nordic nRF52840-DK.
    * Double Sided Two Way Ranging with STS example:
        Failure monitored on nRF is now fixed.


## Package v7.0 / Driver v02.00.00  (13th April 2021)

In addition to the existing updated driver layout for CR5 release. Following
updates are included in this release changed from ER1 release.

1. Update in the function dwt_setgpiomode():
   This function will now // clear GPIO which has been specified by the mode
   (Each mode takes up 3 bits) and set GPIO mask as specified to enable it for
   individual GPIO or multiple GPIOs.

2. Update in the dwt_isr() function:
   Clear SPI RDY events after the callback - this lets the host read the
   SYS_STATUS register inside the callback "after" calling the corresponding
   callback if present.

3. Fixes for PLL re-calibration. PLL_CAL_EN_BIT needs to be set when PLL is
   calibrated. Updated dwt_setdwstate().

4. Wakeup (from sleep) times have been shortened from 500us to 200us.

5. Updated STS_CONFIG_HI_RES – the STS threshold to >=60%, so that only if
   STS qual is < 60%, the STS_CQ_EN bit will be set in the STS_TOAST register.

6. New DGC LUTs, change in the OTP values, the dwt_initialise() has been
   updated to check the OTP contains the new LUTs, and only if it does the
   driver will load/kick them from OTP, otherwise the values in the driver
   (refer API guide for more information) be loaded/written into the device.

7. Added new dwt_adcoffsetscalibration() API which is called at the end of
   dwt_configure to optimize receiver / configure optimal ADC thresholds.

8. _dwt_adjust_delaytime() – this has been updated for the delayed TX w.r.t
   RX timestamp. As TX/RX antenna delay is automatically added to the TX/RX
   timestamp, the antenna delay is subtracted from the delayed TX time.

9. Only disable STS CMF when PDOA mode 1 is used.

10. Fix for channel power parameter in the diagnostic structure, the parameter
   has been changed to 32 bits as the corresponding bitfield has been
   increased to 20-bits.

11. Simple Examples updated are same as CR5 except:
    * Double Buffer RX example:
        This example has a check for device ID. If the device ID is not from E0
        samples. The test will go into a forever while loop.

    * Timer example:
        This example has a check for device ID. If the device ID is not from E0
        samples. The test will go into a forever while loop.

    * GPIO example:
        This example has a check for device ID to select the GPIO mask for C0
        and E0. If the device ID is not from E0 samples. User will be required
        to select the single GPIO (1,2,3 ..) or multiple GPIOs (GPIO_ALL) from
        enum that needs to be enabled.


## Package v6.0 / Driver v05.00.00  (10th October 2019)

1. New driver layout has been added as part of this release. A "compatibility
   layer" is now in use. Each example now requires a dwt_probe() API call
   before dwt_initialise() API call. In previous releases, dwt_initialise()
   was always the first API to be called. This is no longer the case. Please
   see API Guide for more information.

2. Issues with XTAL trim values have been fixed.

3. Simple Examples with STS enabled will now check STS status and STS quality.
   STS status checking will not work if the Ipatov preamble length is 64 or
   less. In this case, the user should only check for STS quality.

4. Various fixes to SS-TWR and DS-TWR examples to use a single delay value
   between RX/TX rather than different values for different supported
   platforms.

5. Simple Examples will no longer reference deca_regs.h directly. Various new
   APIs have been created to accommodate for this. Please see API Guide for
   more information.

6. Simple Examples release has removed some unnecessary files and changed the
   layout of the code. Each supported build platform (STM & Nordic) now has
   its own directory.

7. The “DWT_PGFCAL” argument has been added to all dwt_configuresleep() API
   calls in the example code. This allows for the receiver to be re-enabled
   after sleep (on-wake).

8. Wakeup (from sleep) times have been shortened from 500us to 200us.

9. Interrupt flag names have changed slightly from previous release. For
   example, “SYS_ENABLE_LO_TXFRS_ENABLE_BIT_MASK” is now
   “DWT_INT_TXFRS_BIT_MASK”.

10. New Simple Examples added:
    * PLL calibration example:
        This example will monitor the temperature of the device. If there is a
        significant change in temperature, the PLL is re-calibrated.
    * Bandwidth calibration example:
        This example will record the initial PG count (emulating what should be
        done in factory). The example will recalibrate the bandwidth given this
        reference PG count value in a loop over time. The example should be run
        in a temperature chamber over a range of operating temperatures. The
        device will output a continuous frame for bandwidth monitoring on a
        spectrum analyser.

11. Simple Example changes:
    * Continuous frame example:
        The continuous frame example will now disable the transmission of the
        frame before resetting. Users can add a breakpoint in to monitor this on
        a spectrum analyser.


## Package v5.0 / Driver v01.03.12  (10th October 2019)


1. Fix for gearing table selection and SCP coding threshold, VCM and TX power
values have been increased by 3dB to improve performance.

2. Wakeup pin functionality tested. Wake up pin is configured as FORCE_ON by
default. It needs to be reconfigured to WAKE_UP before wake-up functionality
can be tested.

3. Fixed dwt_entersleepaftertx - which was setting a wrong bit.

4. PLEN 32 was configuring the device to transmit 40 symbols. This has been
fixed.

5. Added multi-config IEEE 802.15.4 (BPRF) example that can use 32 different
configurations.

## Package v4.0 / Driver v01.03.0b  (31st May 2019)

1. Updated CIA configurations, this improved timestamping accuracy.

2. Updated PLL cal, a manual cal is necessary to ensure proper PLL
calibration/locking before device can switch to IDLE_PLL state.

3. Added example TX_SLEEP with auto PLL cal – this can be used to show how
device may stay in IDLE_RC after wakeup and then automatically calibrate PLL
just before TX.

4. Added IEEE 802.15.4 (BPRF) examples (simple TX and RX with new cipher
configuration, 1g and 2g).

5. Added SS TWR with IEEE 802.15.4 (BPRF) configuration example.

6. Added RX Sniff mode example.

## Package v3.0 / Driver v01.03.07  (15th May 2019)

This has new and updated examples, and updated APIs – API version is 1.03.07:

1. When operating in mode 2 cipher PRF was incorrectly set. It needs to match
Ipatov PRF of 64 MHz.

2. Fix LFSR advance API (dwt_cplfsradvance).

3. Updated dwt_configure() and dwt_enable_rf_tx() APIs – correct PDOA switch
configuration for AOA devices.

4. Added example 1d: TX timed SLEEP.

5. Added example 13a: GPIO example.

## Package v2.0 / Driver v01.03.04  (12th April 2019)

This has new and updated examples, and updated APIs – API version is 1.03.04:

1. Fix for PLL calibration procedure for channel 9.

2. Updated AES APIs.

3. Updated CF and CW APIs.

4. SS-TWR examples have optimised response times.

5. Added example 5a/5b: DS-TWR.

6. Added example 2f: RX with XTAL trim.

7. Added example 7a/7b: TX and auto-ACK.

8. Added example 1e: TX with CCA example.

## Package v1.0 / Driver v01.03.00  (29th March 2019)

1. Initial release of DW3000 Driver and API, with some simple example
projects.
