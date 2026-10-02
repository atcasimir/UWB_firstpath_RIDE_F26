################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/dw3720/dw3720_device.c 

OBJS += \
./Shared/dwt_uwb_driver/dw3720/dw3720_device.o 

C_DEPS += \
./Shared/dwt_uwb_driver/dw3720/dw3720_device.d 


# Each subdirectory must supply rules for building sources it contributes
Shared/dwt_uwb_driver/dw3720/dw3720_device.o: /Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/dw3720/dw3720_device.c Shared/dwt_uwb_driver/dw3720/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F401xE -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Build_Platforms/STM_Nucleo_F401RE/DWM3000F_401/platform" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/dw3000" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/lib/qmath/include" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/MAC_802_15_4" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/MAC_802_15_8" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/shared_data" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/examples_info" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-Shared-2f-dwt_uwb_driver-2f-dw3720

clean-Shared-2f-dwt_uwb_driver-2f-dw3720:
	-$(RM) ./Shared/dwt_uwb_driver/dw3720/dw3720_device.cyclo ./Shared/dwt_uwb_driver/dw3720/dw3720_device.d ./Shared/dwt_uwb_driver/dw3720/dw3720_device.o ./Shared/dwt_uwb_driver/dw3720/dw3720_device.su

.PHONY: clean-Shared-2f-dwt_uwb_driver-2f-dw3720

