/*! ----------------------------------------------------------------------------
 * @file    port.c
 * @brief   HW specific definitions and functions for portability
 *          Ported from the Qorvo STM_Nucleo_F429 platform to the NUCLEO-F401RE.
 *
 *          Changes vs. the F429 port:
 *            - single SPI (SPI1); the F429's second SPI (SPI4) is not used
 *            - DW IRQ on PA9 -> EXTI9_5 (was PF12 -> EXTI15_10)
 *            - USB CDC report buffer and LCD/LED/switch helpers removed
 *              (console output goes through test_run_info() in main.c)
 *            - SPI fast rate = 84 MHz / 4 = 21 MHz (DW3000 max is 38 MHz;
 *              /2 would be 42 MHz, which is too fast)
 *            - usleep() scaled to the actual core clock
 *
 * @attention
 *
 * Copyright 2016-2021 (c) DecaWave Ltd, Dublin, Ireland.
 *
 * All rights reserved.
 *
 * @author DecaWave
 */

#include "port.h"

/****************************************************************************
 *
 *                              SPI globals (used by deca_spi.c)
 *
 *******************************************************************************/
extern SPI_HandleTypeDef hspi1; /* created by CubeMX in main.c */

SPI_HandleTypeDef *hcurrent_active_spi = &hspi1;   /* SPI used for the DW IC */
uint16_t pin_io_active_spi = DW_NSS_Pin;            /* chip-select pin (PB6) */
GPIO_PinState SPI_CS_state = GPIO_PIN_RESET;        /* CS asserted level (active low) */
host_using_spi_e host_spi = SPI_1;

/****************************************************************************
 *
 *                  Port private variables
 *
 *******************************************************************************/

/* DW IC IRQ handler definition. */
static port_dwic_isr_t port_dwic_isr = NULL;

/****************************************************************************
 *
 *                              Time section
 *
 *******************************************************************************/

/* @fn    portGetTickCnt
 * @brief SysTick count, 1 ms resolution.
 * */
unsigned long portGetTickCnt(void)
{
    return HAL_GetTick();
}

/* @fn    usleep
 * @brief Busy-wait microsecond delay.
 *        The F429 port used 12 loops/us at 144 MHz; scale that to SystemCoreClock
 *        (7 loops/us at 84 MHz). Approximate, errs on the long side.
 * */
#pragma GCC push_options
#pragma GCC optimize("O0")
int usleep(useconds_t usec)
{
    uint32_t i;
    uint32_t loops_per_us = SystemCoreClock / 12000000UL;

    if (loops_per_us == 0)
    {
        loops_per_us = 1;
    }

    usec *= loops_per_us;
    for (i = 0; i < usec; i++)
    {
        __NOP();
    }
    return 0;
}
#pragma GCC pop_options

/* @fn    Sleep
 * @brief Sleep delay in ms using SysTick timer
 * */
void Sleep(uint32_t x)
{
    HAL_Delay(x);
}

/****************************************************************************
 *
 *                              Configuration section
 *
 *******************************************************************************/

/* @fn    peripherals_init
 * */
int peripherals_init(void)
{
    /* All peripherals are initialized by the CubeMX code in main.c */
    return 0;
}

/* @fn    spi_peripheral_init
 * */
void spi_peripheral_init(void)
{
    /* SPI1 is initialized by the CubeMX code in main.c */
}

/**
 * @brief  Checks whether the specified IRQn line is enabled or not.
 * @param  IRQn: specifies the IRQn line to check.
 * @return "0" when IRQn is "not enabled" and !0 otherwise
 */
ITStatus EXTI_GetITEnStatus(IRQn_Type IRQn)
{
    return ((NVIC->ISER[(((uint32_t)(int32_t)IRQn) >> 5UL)] & (uint32_t)(1UL << (((uint32_t)(int32_t)IRQn) & 0x1FUL))) == (uint32_t)RESET) ? (RESET) : (SET);
}

/****************************************************************************
 *
 *                          DW IC port section
 *
 *******************************************************************************/

/* @fn      reset_DWIC
 * @brief   Pulse the DW IC RSTn line low.
 *          Note, the DW_RESET pin must never be driven high externally,
 *          so it is only ever used as an open-drain output.
 * */
void reset_DWIC(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = { 0 };

    GPIO_InitStruct.Pin = DW_RESET_Pin;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_OD;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(DW_RESET_GPIO_Port, &GPIO_InitStruct);

    /* drive the RSTn pin low */
    HAL_GPIO_WritePin(DW_RESET_GPIO_Port, DW_RESET_Pin, GPIO_PIN_RESET);

    usleep(1);

    /* release it (open-drain, not active) */
    setup_DWICRSTnIRQ(0);
    Sleep(2);
}

/* @fn      setup_DWICRSTnIRQ
 * @brief   Set up the DW_RESET pin mode.
 *          0  - open-drain output, released (normal state)
 *          !0 - plain input (the F429 port attached an EXTI here, but nothing
 *               in the SDK examples uses it, and on the F401 PA8 would share
 *               the EXTI9_5 vector with DW_IRQn, so no interrupt is enabled)
 * */
void setup_DWICRSTnIRQ(int enable)
{
    GPIO_InitTypeDef GPIO_InitStruct = { 0 };

    GPIO_InitStruct.Pin = DW_RESET_Pin;
    GPIO_InitStruct.Pull = GPIO_NOPULL;

    if (enable)
    {
        GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
        HAL_GPIO_Init(DW_RESET_GPIO_Port, &GPIO_InitStruct);
    }
    else
    {
        GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_OD;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
        HAL_GPIO_Init(DW_RESET_GPIO_Port, &GPIO_InitStruct);
        HAL_GPIO_WritePin(DW_RESET_GPIO_Port, DW_RESET_Pin, GPIO_PIN_SET);
    }
}

/*! ------------------------------------------------------------------------------------------------------------------
 * @fn wakeup_device_with_io()
 *
 * @brief Wake the device up by toggling the WAKEUP io with a delay.
 */
void wakeup_device_with_io(void)
{
    SET_WAKEUP_PIN_IO_HIGH;
    WAIT_200uSEC;
    SET_WAKEUP_PIN_IO_LOW;
}

/*! ------------------------------------------------------------------------------------------------------------------
 * @fn make_very_short_wakeup_io()
 *
 * @brief Toggle the WAKEUP io for a very short time. The device should not wake up.
 */
void make_very_short_wakeup_io(void)
{
    uint8_t cnt;

    SET_WAKEUP_PIN_IO_HIGH;
    for (cnt = 0; cnt < 10; cnt++)
    {
        __NOP();
    }
    SET_WAKEUP_PIN_IO_LOW;
}

/* @fn      change_SPI
 * @brief   Only SPI1 exists on this port; requests for SPI_2 are ignored.
 * */
void change_SPI(host_using_spi_e spi)
{
    (void)spi;
    hcurrent_active_spi = &hspi1;
    pin_io_active_spi = DW_NSS_Pin;
    SPI_CS_state = GPIO_PIN_RESET;
    host_spi = SPI_1;
}

/* @fn      port_set_dw_ic_spi_slowrate
 * @brief   84 MHz / 16 = 5.25 MHz (DW3000 needs <= 7 MHz before its PLL locks)
 * */
void port_set_dw_ic_spi_slowrate(void)
{
    hcurrent_active_spi->Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_16;
    HAL_SPI_Init(hcurrent_active_spi);
}

/* @fn      port_set_dw_ic_spi_fastrate
 * @brief   84 MHz / 4 = 21 MHz (DW3000 max 38 MHz)
 * */
void port_set_dw_ic_spi_fastrate(void)
{
    hcurrent_active_spi->Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_4;
    HAL_SPI_Init(hcurrent_active_spi);
}

/****************************************************************************
 *
 *                              IRQ section
 *
 *******************************************************************************/

/* @fn         HAL_GPIO_EXTI_Callback
 * @brief      EXTI line detection callback from the HAL layer.
 *             EXTI9_5_IRQHandler (stm32f4xx_it.c, generated by CubeMX) calls
 *             HAL_GPIO_EXTI_IRQHandler(DW_IRQn_Pin), which lands here.
 */
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    switch (GPIO_Pin)
    {
    case DW_IRQn_Pin:
        process_deca_irq();
        break;

    default:
        break;
    }
}

/* @fn      process_deca_irq
 * @brief   Main call-back for the DW3000 IRQ. Keeps calling the installed
 *          handler until the DW3000 releases its IRQ line.
 * */
void process_deca_irq(void)
{
    while (port_CheckEXT_IRQ() != 0)
    {
        if (port_dwic_isr)
        {
            port_dwic_isr();
        }
    }
}

/* @fn      port_DisableEXT_IRQ
 * @brief   Disable the DW_IRQ line interrupt (whole EXTI9_5 vector).
 * */
void port_DisableEXT_IRQ(void)
{
    NVIC_DisableIRQ(DECAIRQ_EXTI_IRQn);
}

/* @fn      port_EnableEXT_IRQ
 * @brief   Enable the DW_IRQ line interrupt (whole EXTI9_5 vector).
 * */
void port_EnableEXT_IRQ(void)
{
    NVIC_EnableIRQ(DECAIRQ_EXTI_IRQn);
}

/* @fn      port_GetEXT_IRQStatus
 * @brief   Is the DW_IRQ interrupt enabled in the NVIC?
 * */
uint32_t port_GetEXT_IRQStatus(void)
{
    return EXTI_GetITEnStatus(DECAIRQ_EXTI_IRQn);
}

/* @fn      port_CheckEXT_IRQ
 * @brief   Read the DW_IRQ input pin level.
 * */
uint32_t port_CheckEXT_IRQ(void)
{
    return HAL_GPIO_ReadPin(DECAIRQ_GPIO, DW_IRQn_Pin);
}

/*! ------------------------------------------------------------------------------------------------------------------
 * @fn port_set_dwic_isr()
 *
 * @brief Install the handling function for the DW IC IRQ.
 *        The DW IC IRQ is disabled while the handler is swapped in.
 *
 * @param dwic_isr function pointer to the DW IC interrupt handler to install
 */
void port_set_dwic_isr(port_dwic_isr_t dwic_isr)
{
    /* Check DW IC IRQ activation status. */
    ITStatus en = port_GetEXT_IRQStatus();

    /* If needed, deactivate DW IC IRQ during the installation of the new handler. */
    port_DisableEXT_IRQ();

    port_dwic_isr = dwic_isr;

    if (!en)
    {
        port_EnableEXT_IRQ();
    }
}
