################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/ex_05a_ds_twr_init/ds_twr_initiator.c \
/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/ex_05a_ds_twr_init/ds_twr_initiator_sts.c 

OBJS += \
./Src/examples/ex_05a_ds_twr_init/ds_twr_initiator.o \
./Src/examples/ex_05a_ds_twr_init/ds_twr_initiator_sts.o 

C_DEPS += \
./Src/examples/ex_05a_ds_twr_init/ds_twr_initiator.d \
./Src/examples/ex_05a_ds_twr_init/ds_twr_initiator_sts.d 


# Each subdirectory must supply rules for building sources it contributes
Src/examples/ex_05a_ds_twr_init/ds_twr_initiator.o: /Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/ex_05a_ds_twr_init/ds_twr_initiator.c Src/examples/ex_05a_ds_twr_init/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F401xE -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Build_Platforms/STM_Nucleo_F401RE/DWM3000F_401/platform" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/dw3000" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/lib/qmath/include" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/MAC_802_15_4" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/MAC_802_15_8" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/shared_data" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/examples_info" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"
Src/examples/ex_05a_ds_twr_init/ds_twr_initiator_sts.o: /Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/ex_05a_ds_twr_init/ds_twr_initiator_sts.c Src/examples/ex_05a_ds_twr_init/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F401xE -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Build_Platforms/STM_Nucleo_F401RE/DWM3000F_401/platform" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/dw3000" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Shared/dwt_uwb_driver/lib/qmath/include" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/MAC_802_15_4" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/MAC_802_15_8" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/shared_data" -I"/Users/aidancasimir/dev/projects/UWB_firstpath_RIDE_F26/DW3_QM33_SDK_1/Drivers/API/Src/examples/examples_info" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-Src-2f-examples-2f-ex_05a_ds_twr_init

clean-Src-2f-examples-2f-ex_05a_ds_twr_init:
	-$(RM) ./Src/examples/ex_05a_ds_twr_init/ds_twr_initiator.cyclo ./Src/examples/ex_05a_ds_twr_init/ds_twr_initiator.d ./Src/examples/ex_05a_ds_twr_init/ds_twr_initiator.o ./Src/examples/ex_05a_ds_twr_init/ds_twr_initiator.su ./Src/examples/ex_05a_ds_twr_init/ds_twr_initiator_sts.cyclo ./Src/examples/ex_05a_ds_twr_init/ds_twr_initiator_sts.d ./Src/examples/ex_05a_ds_twr_init/ds_twr_initiator_sts.o ./Src/examples/ex_05a_ds_twr_init/ds_twr_initiator_sts.su

.PHONY: clean-Src-2f-examples-2f-ex_05a_ds_twr_init

