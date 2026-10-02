################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

-include ../makefile.init

RM := rm -rf

# All of the sources participating in the build are defined here
-include sources.mk
-include platform/subdir.mk
-include Src/examples/shared_data/subdir.mk
-include Src/examples/examples_info/subdir.mk
-include Src/examples/ex_22b_frame_filtering_rx/subdir.mk
-include Src/examples/ex_22a_frame_filtering_tx/subdir.mk
-include Src/examples/ex_21_linear_tx_power/subdir.mk
-include Src/examples/ex_20_simple_aes/subdir.mk
-include Src/examples/ex_19_tx_power_adjustment/subdir.mk
-include Src/examples/ex_18_timer/subdir.mk
-include Src/examples/ex_17_bw_cal/subdir.mk
-include Src/examples/ex_16_pll_cal/subdir.mk
-include Src/examples/ex_15_le_pend/subdir.mk
-include Src/examples/ex_14_otp_write/subdir.mk
-include Src/examples/ex_13a_gpio/subdir.mk
-include Src/examples/ex_11a_spi_crc/subdir.mk
-include Src/examples/ex_07b_ack_data_rx/subdir.mk
-include Src/examples/ex_07a_ack_data_tx/subdir.mk
-include Src/examples/ex_06f_AES_ss_twr_responder/subdir.mk
-include Src/examples/ex_06e_AES_ss_twr_initiator/subdir.mk
-include Src/examples/ex_06b_ss_twr_responder/subdir.mk
-include Src/examples/ex_06a_ss_twr_initiator/subdir.mk
-include Src/examples/ex_05d_ds_twr_resp_sts_sdc/subdir.mk
-include Src/examples/ex_05c_ds_twr_init_sts_sdc/subdir.mk
-include Src/examples/ex_05b_ds_twr_resp/subdir.mk
-include Src/examples/ex_05a_ds_twr_init/subdir.mk
-include Src/examples/ex_04b_cont_frame/subdir.mk
-include Src/examples/ex_04a_cont_wave/subdir.mk
-include Src/examples/ex_03d_tx_wait_resp_interrupts/subdir.mk
-include Src/examples/ex_03b_rx_send_resp/subdir.mk
-include Src/examples/ex_03a_tx_wait_resp/subdir.mk
-include Src/examples/ex_02k_simple_rx_cir/subdir.mk
-include Src/examples/ex_02j_rx_adc_capture/subdir.mk
-include Src/examples/ex_02i_simple_rx_aes/subdir.mk
-include Src/examples/ex_02h_simple_rx_pdoa/subdir.mk
-include Src/examples/ex_02g_simple_rx_sts_sdc/subdir.mk
-include Src/examples/ex_02f_rx_with_crystal_trim/subdir.mk
-include Src/examples/ex_02e_rx_dbl_buff/subdir.mk
-include Src/examples/ex_02d_rx_sniff/subdir.mk
-include Src/examples/ex_02c_rx_diagnostics/subdir.mk
-include Src/examples/ex_02a_simple_rx/subdir.mk
-include Src/examples/ex_01j_simple_tx_automotive/subdir.mk
-include Src/examples/ex_01i_simple_tx_aes/subdir.mk
-include Src/examples/ex_01h_simple_tx_pdoa/subdir.mk
-include Src/examples/ex_01g_simple_tx_sts_sdc/subdir.mk
-include Src/examples/ex_01e_tx_with_cca/subdir.mk
-include Src/examples/ex_01d_tx_timed_sleep/subdir.mk
-include Src/examples/ex_01c_tx_sleep_auto/subdir.mk
-include Src/examples/ex_01b_tx_sleep/subdir.mk
-include Src/examples/ex_01a_simple_tx/subdir.mk
-include Src/examples/ex_00a_reading_dev_id/subdir.mk
-include Src/MAC_802_15_8/subdir.mk
-include Src/MAC_802_15_4/subdir.mk
-include Src/subdir.mk
-include Shared/dwt_uwb_driver/lib/qmath/src/subdir.mk
-include Shared/dwt_uwb_driver/dw3720/subdir.mk
-include Shared/dwt_uwb_driver/dw3000/subdir.mk
-include Shared/dwt_uwb_driver/subdir.mk
-include Drivers/STM32F4xx_HAL_Driver/Src/subdir.mk
-include Core/Startup/subdir.mk
-include Core/Src/subdir.mk
-include objects.mk

ifneq ($(MAKECMDGOALS),clean)
ifneq ($(strip $(S_DEPS)),)
-include $(S_DEPS)
endif
ifneq ($(strip $(S_UPPER_DEPS)),)
-include $(S_UPPER_DEPS)
endif
ifneq ($(strip $(C_DEPS)),)
-include $(C_DEPS)
endif
endif

-include ../makefile.defs

OPTIONAL_TOOL_DEPS := \
$(wildcard ../makefile.defs) \
$(wildcard ../makefile.init) \
$(wildcard ../makefile.targets) \


BUILD_ARTIFACT_NAME := DWM3000_F401
BUILD_ARTIFACT_EXTENSION := elf
BUILD_ARTIFACT_PREFIX :=
BUILD_ARTIFACT := $(BUILD_ARTIFACT_PREFIX)$(BUILD_ARTIFACT_NAME)$(if $(BUILD_ARTIFACT_EXTENSION),.$(BUILD_ARTIFACT_EXTENSION),)

# Add inputs and outputs from these tool invocations to the build variables 
EXECUTABLES += \
DWM3000_F401.elf \

MAP_FILES += \
DWM3000_F401.map \

SIZE_OUTPUT += \
default.size.stdout \

OBJDUMP_LIST += \
DWM3000_F401.list \


# All Target
all: main-build

# Main-build Target
main-build: DWM3000_F401.elf secondary-outputs

# Tool invocations
DWM3000_F401.elf DWM3000_F401.map: $(OBJS) $(USER_OBJS) /Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Build_Platforms/STM_Nucleo_F401RE/DWM3000F_401/STM32F401RETX_FLASH.ld makefile objects.list $(OPTIONAL_TOOL_DEPS)
	arm-none-eabi-gcc -o "DWM3000_F401.elf" @"objects.list" $(USER_OBJS) $(LIBS) -mcpu=cortex-m4 -T"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Build_Platforms/STM_Nucleo_F401RE/DWM3000F_401/STM32F401RETX_FLASH.ld" --specs=nosys.specs -Wl,-Map="DWM3000_F401.map" -Wl,--gc-sections -static --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -Wl,--start-group -lc -lm -Wl,--end-group
	@echo 'Finished building target: $@'
	@echo ' '

default.size.stdout: $(EXECUTABLES) makefile objects.list $(OPTIONAL_TOOL_DEPS)
	arm-none-eabi-size  $(EXECUTABLES)
	@echo 'Finished building: $@'
	@echo ' '

DWM3000_F401.list: $(EXECUTABLES) makefile objects.list $(OPTIONAL_TOOL_DEPS)
	arm-none-eabi-objdump -h -S $(EXECUTABLES) > "DWM3000_F401.list"
	@echo 'Finished building: $@'
	@echo ' '

# Other Targets
clean:
	-$(RM) DWM3000_F401.elf DWM3000_F401.list DWM3000_F401.map default.size.stdout
	-@echo ' '

secondary-outputs: $(SIZE_OUTPUT) $(OBJDUMP_LIST)

fail-specified-linker-script-missing:
	@echo 'Error: Cannot find the specified linker script. Check the linker settings in the build configuration.'
	@exit 2

warn-no-linker-script-specified:
	@echo 'Warning: No linker script specified. Check the linker settings in the build configuration.'

.PHONY: all clean dependents main-build fail-specified-linker-script-missing warn-no-linker-script-specified

-include ../makefile.targets
