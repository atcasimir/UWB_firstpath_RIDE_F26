#
# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

cmake_minimum_required(VERSION 3.20)

add_subdirectory(lib/chelpers)
add_subdirectory(lib/rtt)
add_subdirectory(lib/qio)
add_subdirectory(lib/qosal)
add_subdirectory(Startup)

# Source and header files 
set(TARGET_SOURCES
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/platform/deca_mutex.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/platform/deca_probe_interface.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/platform/deca_sleep.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/platform/deca_spi.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/platform/port.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/mdk/system_nrf52840.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/boards/boards.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/integration/nrfx/legacy/nrf_drv_clock.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/integration/nrfx/legacy/nrf_drv_spi.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/drivers/src/nrfx_clock.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/drivers/src/nrfx_gpiote.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/drivers/src/prs/nrfx_prs.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/drivers/src/nrfx_spi.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/drivers/src/nrfx_spim.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/util/app_error.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/util/app_error_handler_gcc.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/util/app_error_weak.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/util/app_util_platform.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/atomic/nrf_atomic.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/balloc/nrf_balloc.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/log/src/nrf_log_frontend.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/memobj/nrf_memobj.c
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/strerror/nrf_strerror.c
)   

set(TARGET_HEADERS_DIR
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/config
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/platform
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/drivers_nrf/nrf_soc_nosd
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/boards
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/toolchain/cmsis/include
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/balloc
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/ringbuf
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/log
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/log/src
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/memobj
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/util
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/atomic
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/delay
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/experimental_section_vars
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/components/libraries/strerror
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/hal
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/mdk
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/drivers/include
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/integration/nrfx
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/integration/nrfx/legacy
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/external/fprintf
    ${PLATFORM_SPECIFIC_FILES_PATH}/sdk/modules/nrfx/mdk
)

list(APPEND TARGET_SOURCES
    ${PLATFORM_SPECIFIC_FILES_PATH}/Source/main.c
    ${EXAMPLES_PATH}/MAC_802_15_4/mac_802_15_4.c
    ${EXAMPLES_PATH}/MAC_802_15_8/mac_802_15_8.c
    ${EXAMPLES_PATH}/examples/ex_00a_reading_dev_id/read_dev_id.c
    ${EXAMPLES_PATH}/examples/ex_01a_simple_tx/simple_tx.c
    ${EXAMPLES_PATH}/examples/ex_01b_tx_sleep/tx_sleep.c
    ${EXAMPLES_PATH}/examples/ex_01b_tx_sleep/tx_sleep_idleRC.c
    ${EXAMPLES_PATH}/examples/ex_01c_tx_sleep_auto/tx_sleep_auto.c
    ${EXAMPLES_PATH}/examples/ex_01d_tx_timed_sleep/tx_timed_sleep.c
    ${EXAMPLES_PATH}/examples/ex_01e_tx_with_cca/tx_with_cca.c
    ${EXAMPLES_PATH}/examples/ex_01g_simple_tx_sts_sdc/simple_tx_sts_sdc.c
    ${EXAMPLES_PATH}/examples/ex_01h_simple_tx_pdoa/simple_tx_pdoa.c
    ${EXAMPLES_PATH}/examples/ex_01i_simple_tx_aes/simple_tx_aes.c
    ${EXAMPLES_PATH}/examples/ex_01j_simple_tx_automotive/simple_tx_automotive.c
    ${EXAMPLES_PATH}/examples/ex_02a_simple_rx/simple_rx.c
    ${EXAMPLES_PATH}/examples/ex_02a_simple_rx/simple_rx_nlos.c
    ${EXAMPLES_PATH}/examples/ex_02c_rx_diagnostics/rx_diagnostics.c
    ${EXAMPLES_PATH}/examples/ex_02d_rx_sniff/rx_sniff.c
    ${EXAMPLES_PATH}/examples/ex_02e_rx_dbl_buff/double_buffer_rx.c
    ${EXAMPLES_PATH}/examples/ex_02f_rx_with_crystal_trim/rx_with_xtal_trim.c
    ${EXAMPLES_PATH}/examples/ex_02g_simple_rx_sts_sdc/simple_rx_sts_sdc.c
    ${EXAMPLES_PATH}/examples/ex_02h_simple_rx_pdoa/simple_rx_pdoa.c
    ${EXAMPLES_PATH}/examples/ex_02i_simple_rx_aes/simple_rx_aes.c
    ${EXAMPLES_PATH}/examples/ex_02j_rx_adc_capture/rx_adc_capture.c
    ${EXAMPLES_PATH}/examples/ex_02k_simple_rx_cir/simple_rx_cir.c
    ${EXAMPLES_PATH}/examples/ex_03a_tx_wait_resp/tx_wait_resp.c
    ${EXAMPLES_PATH}/examples/ex_03b_rx_send_resp/rx_send_resp.c
    ${EXAMPLES_PATH}/examples/ex_03d_tx_wait_resp_interrupts/tx_wait_resp_int.c
    ${EXAMPLES_PATH}/examples/ex_04a_cont_wave/continuous_wave.c
    ${EXAMPLES_PATH}/examples/ex_04b_cont_frame/continuous_frame.c
    ${EXAMPLES_PATH}/examples/ex_05a_ds_twr_init/ds_twr_initiator.c
    ${EXAMPLES_PATH}/examples/ex_05a_ds_twr_init/ds_twr_initiator_sts.c
    ${EXAMPLES_PATH}/examples/ex_05b_ds_twr_resp/ds_twr_responder.c
    ${EXAMPLES_PATH}/examples/ex_05b_ds_twr_resp/ds_twr_responder_sts.c
    ${EXAMPLES_PATH}/examples/ex_05c_ds_twr_init_sts_sdc/ds_twr_sts_sdc_initiator.c
    ${EXAMPLES_PATH}/examples/ex_05d_ds_twr_resp_sts_sdc/ds_twr_sts_sdc_responder.c
    ${EXAMPLES_PATH}/examples/ex_06a_ss_twr_initiator/ss_twr_initiator.c
    ${EXAMPLES_PATH}/examples/ex_06a_ss_twr_initiator/ss_twr_initiator_sts.c
    ${EXAMPLES_PATH}/examples/ex_06a_ss_twr_initiator/ss_twr_initiator_sts_no_data.c
    ${EXAMPLES_PATH}/examples/ex_06b_ss_twr_responder/ss_twr_responder.c
    ${EXAMPLES_PATH}/examples/ex_06b_ss_twr_responder/ss_twr_responder_sts.c
    ${EXAMPLES_PATH}/examples/ex_06b_ss_twr_responder/ss_twr_responder_sts_no_data.c
    ${EXAMPLES_PATH}/examples/ex_06e_AES_ss_twr_initiator/ss_aes_twr_initiator.c
    ${EXAMPLES_PATH}/examples/ex_06f_AES_ss_twr_responder/ss_aes_twr_responder.c
    ${EXAMPLES_PATH}/examples/ex_07a_ack_data_tx/ack_data_tx.c
    ${EXAMPLES_PATH}/examples/ex_07b_ack_data_rx/ack_data_rx.c
    ${EXAMPLES_PATH}/examples/ex_11a_spi_crc/spi_crc.c
    ${EXAMPLES_PATH}/examples/ex_13a_gpio/gpio_example.c
    ${EXAMPLES_PATH}/examples/ex_14_otp_write/otp_write.c
    ${EXAMPLES_PATH}/examples/ex_15_le_pend/le_pend_rx.c
    ${EXAMPLES_PATH}/examples/ex_15_le_pend/le_pend_tx.c
    ${EXAMPLES_PATH}/examples/ex_16_pll_cal/pll_cal.c
    ${EXAMPLES_PATH}/examples/ex_17_bw_cal/bandwidth_calibration.c
    ${EXAMPLES_PATH}/examples/ex_18_timer/timer_example.c
    ${EXAMPLES_PATH}/examples/ex_19_tx_power_adjustment/tx_power_adjustment_example.c
    ${EXAMPLES_PATH}/examples/ex_20_simple_aes/simple_aes.c
    ${EXAMPLES_PATH}/examples/ex_21_linear_tx_power/linear_tx_power_example.c
    ${EXAMPLES_PATH}/examples/ex_22b_frame_filtering_rx/frame_filtering_rx.c
    ${EXAMPLES_PATH}/examples/ex_22a_frame_filtering_tx/frame_filtering_tx.c
    ${EXAMPLES_PATH}/examples/examples_info/example_info.c
    ${EXAMPLES_PATH}/examples/shared_data/shared_functions.c
    ${EXAMPLES_PATH}/config_options.c
)   

list(APPEND TARGET_HEADERS_DIR
    ${EXAMPLES_PATH}/
    ${EXAMPLES_PATH}/MAC_802_15_4/
    ${EXAMPLES_PATH}/MAC_802_15_8/
    ${EXAMPLES_PATH}/examples/examples_info/
    ${EXAMPLES_PATH}/examples/shared_data/
    ${EXAMPLES_PATH}/MAC_802_15_4
    ${EXAMPLES_PATH}/MAC_802_15_8
    ${EXAMPLES_PATH}/examples/examples_info
    ${EXAMPLES_PATH}/examples/shared_data
)

# Create the target
add_executable(${TARGET_ELF})

target_sources(${TARGET_ELF} PRIVATE
		${TARGET_SOURCES}
)

target_include_directories(${TARGET_ELF}
    PRIVATE
    ${TARGET_HEADERS_DIR}
)

target_link_libraries(${TARGET_ELF}
    PRIVATE
    uwb_driver
    nrf52840_startup
    c
    chelpers
    rtt_io
    m
)

target_compile_definitions(${TARGET_ELF}
    PRIVATE
    BOARD_PCA10056
    CONFIG_GPIO_AS_PINRESET
    FLOAT_ABI_HARD
    INITIALIZE_USER_SECTIONS
    NO_VTOR_CONFIG
    NRF52840_XXAA
    ${TARGET_ADDITIONAL_DEFINITIONS}
)

target_link_options(${TARGET_ELF}
    PRIVATE
    -Wl,-Map=$<TARGET_FILE_DIR:${TARGET_ELF}>/${TARGET_MAP}
)

set_target_properties(${TARGET_ELF}
    PROPERTIES LINK_DEPENDS
    ${LINKER_SCRIPT_OUT}
)