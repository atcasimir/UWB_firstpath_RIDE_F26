################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/config_options.c \
/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/utils.c 

OBJS += \
./Src/config_options.o \
./Src/utils.o 

C_DEPS += \
./Src/config_options.d \
./Src/utils.d 


# Each subdirectory must supply rules for building sources it contributes
Src/config_options.o: /Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/config_options.c Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F401xE -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Build_Platforms/STM_Nucleo_F401RE/DWM3000F_401/platform" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/dw3000" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/lib/qmath/include" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/MAC_802_15_4" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/MAC_802_15_8" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/shared_data" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/examples_info" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"
Src/utils.o: /Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/utils.c Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F401xE -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Build_Platforms/STM_Nucleo_F401RE/DWM3000F_401/platform" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/dw3000" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/lib/qmath/include" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/MAC_802_15_4" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/MAC_802_15_8" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/shared_data" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/examples_info" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-Src

clean-Src:
	-$(RM) ./Src/config_options.cyclo ./Src/config_options.d ./Src/config_options.o ./Src/config_options.su ./Src/utils.cyclo ./Src/utils.d ./Src/utils.o ./Src/utils.su

.PHONY: clean-Src

