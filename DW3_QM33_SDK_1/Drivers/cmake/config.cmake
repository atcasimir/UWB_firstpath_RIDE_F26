#
# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

message("Configuring QM33 simple-examples package!")

# Set device to use in this package
set(USE_DRV_DW3000 1)
set(USE_DRV_DW3720 1)
set(AUTO_DW3300Q_DRIVER 0)

set(DGB_LOG 0)

# At least one device need to be selected
math(EXPR NB_DW_DRIVERS "${USE_DRV_DW3000} + ${USE_DRV_DW3720}")
if(NB_DW_DRIVERS EQUAL 0)
    message(FATAL_ERROR "At least one dw driver should be defined.")
endif()

set(HEAP_SIZE 8192 CACHE STRING "Heap size")
set(STACK_SIZE 8192 CACHE STRING "Stack size")
set(STACK_PROCESS_SIZE 0 CACHE STRING "Stack process size")

# Set RAM and FLASH regions
set(FLASH_ADDR 0x00000000 CACHE STRING "Flash start address")
set(FLASH_SIZE 0x00100000 CACHE STRING "Flash size")
set(RAM_ADDR 0x20000000 CACHE STRING "Ram start address")
set(RAM_SIZE 0x00040000 CACHE STRING "Ram size")