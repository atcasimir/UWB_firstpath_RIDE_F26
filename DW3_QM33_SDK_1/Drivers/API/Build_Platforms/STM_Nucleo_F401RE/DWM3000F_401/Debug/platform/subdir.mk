################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../platform/deca_mutex.c \
../platform/deca_probe_interface.c \
../platform/deca_sleep.c \
../platform/deca_spi.c \
../platform/port.c 

OBJS += \
./platform/deca_mutex.o \
./platform/deca_probe_interface.o \
./platform/deca_sleep.o \
./platform/deca_spi.o \
./platform/port.o 

C_DEPS += \
./platform/deca_mutex.d \
./platform/deca_probe_interface.d \
./platform/deca_sleep.d \
./platform/deca_spi.d \
./platform/port.d 


# Each subdirectory must supply rules for building sources it contributes
platform/%.o platform/%.su platform/%.cyclo: ../platform/%.c platform/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F401xE -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Build_Platforms/STM_Nucleo_F401RE/DWM3000F_401/platform" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/dw3000" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/lib/qmath/include" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/MAC_802_15_4" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/MAC_802_15_8" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/shared_data" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/examples_info" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-platform

clean-platform:
	-$(RM) ./platform/deca_mutex.cyclo ./platform/deca_mutex.d ./platform/deca_mutex.o ./platform/deca_mutex.su ./platform/deca_probe_interface.cyclo ./platform/deca_probe_interface.d ./platform/deca_probe_interface.o ./platform/deca_probe_interface.su ./platform/deca_sleep.cyclo ./platform/deca_sleep.d ./platform/deca_sleep.o ./platform/deca_sleep.su ./platform/deca_spi.cyclo ./platform/deca_spi.d ./platform/deca_spi.o ./platform/deca_spi.su ./platform/port.cyclo ./platform/port.d ./platform/port.o ./platform/port.su

.PHONY: clean-platform

