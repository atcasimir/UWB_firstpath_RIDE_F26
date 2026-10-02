/*! ----------------------------------------------------------------------------
 * @file    port.h
 * @brief   HW specific definitions and functions for portability
 *          Ported from the Qorvo STM_Nucleo_F429 platform to the NUCLEO-F401RE
 *          with a DWM3000EVB on the Arduino headers.
 *
 *          Pin map (labels come from CubeMX, see Core/Inc/main.h):
 *            D13 PA5  SPI1_SCK         D10 PB6  DW_NSS (GPIO, active low)
 *            D12 PA6  SPI1_MISO        D9  PC7  DW_NSS1_WAKEUP
 *            D11 PA7  SPI1_MOSI        D8  PA9  DW_IRQn (EXTI9, rising)
 *                                      D7  PA8  DW_RESET (open drain)
 *
 * @attention
 *
 * Copyright 2015-2021 (c) DecaWave Ltd, Dublin, Ireland.
 *
 * All rights reserved.
 *
 * @author DecaWave
 */

#ifndef PORT_H_
#define PORT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdint.h>
#include <string.h>
#include <sys/types.h>
#include "stm32f4xx_hal.h"
#include "main.h"

/* DW IC IRQ handler type. */
typedef void (*port_dwic_isr_t)(void);

/*! ------------------------------------------------------------------------------------------------------------------
 * @fn port_set_dwic_isr()
 *
 * @brief Install the handling function for the DW3xxx/QM33xx IRQ.
 *        The DW IC IRQ line is deactivated while the handler is installed.
 */
void port_set_dwic_isr(port_dwic_isr_t isr);

#ifndef FALSE
#define FALSE 0
#endif

#ifndef TRUE
#define TRUE 1
#endif

/****************************************************************************
 *                              MACRO
 *******************************************************************************/

/* DW_IRQn is on PA9 -> EXTI line 9 -> shared EXTI9_5 vector.
 * Note: DW_RESET (PA8) is on the same vector, but its EXTI is never enabled. */
#define DECAIRQ_EXTI_IRQn (EXTI9_5_IRQn)

#define DW_RSTn      DW_RESET_Pin
#define DW_RSTn_GPIO DW_RESET_GPIO_Port

#define DECAIRQ      DW_IRQn_Pin
#define DECAIRQ_GPIO DW_IRQn_GPIO_Port

/****************************************************************************
 *                              MACRO function
 *******************************************************************************/

#define GPIO_ResetBits(x, y)        HAL_GPIO_WritePin(x, y, RESET)
#define GPIO_SetBits(x, y)          HAL_GPIO_WritePin(x, y, SET)
#define GPIO_ReadInputDataBit(x, y) HAL_GPIO_ReadPin(x, y)

#define port_SPIx_set_chip_select()   HAL_GPIO_WritePin(DW_NSS_GPIO_Port, DW_NSS_Pin, GPIO_PIN_SET)
#define port_SPIx_clear_chip_select() HAL_GPIO_WritePin(DW_NSS_GPIO_Port, DW_NSS_Pin, GPIO_PIN_RESET)

/* Wake-up IO (D9 / PC7) */
#define SET_WAKEUP_PIN_IO_LOW  HAL_GPIO_WritePin(DW_NSS1_WAKEUP_GPIO_Port, DW_NSS1_WAKEUP_Pin, GPIO_PIN_RESET)
#define SET_WAKEUP_PIN_IO_HIGH HAL_GPIO_WritePin(DW_NSS1_WAKEUP_GPIO_Port, DW_NSS1_WAKEUP_Pin, GPIO_PIN_SET)

#define WAIT_500uSEC Sleep(1) /* should be at least 500 us; this is longer */
#define WAIT_200uSEC Sleep(1) /* should be at least 200 us; this is longer */

/* The F429 board had no LCD either; keep the stubs the examples expect. */
#define writetoLCD(x)
#define lcd_display_str(x)  ((void)0)
#define lcd_display_str2(x) ((void)0)

/****************************************************************************
 *                              port function prototypes
 *******************************************************************************/

int usleep(useconds_t usec);
void Sleep(uint32_t Delay);
unsigned long portGetTickCnt(void);

void port_set_dw_ic_spi_slowrate(void);
void port_set_dw_ic_spi_fastrate(void);

void process_deca_irq(void);

int peripherals_init(void);
void spi_peripheral_init(void);

void setup_DWICRSTnIRQ(int enable);
void reset_DWIC(void);

ITStatus EXTI_GetITEnStatus(IRQn_Type x);
uint32_t port_GetEXT_IRQStatus(void);
uint32_t port_CheckEXT_IRQ(void);
void port_DisableEXT_IRQ(void);
void port_EnableEXT_IRQ(void);

/* Some examples call change_SPI(SPI_2) when they detect a dual-SPI DW3720.
 * The DWM3000EVB has a DW3000 on one SPI, so SPI_2 is ignored on this port. */
typedef enum
{
    SPI_1 = 0,
    SPI_2
} host_using_spi_e;

void change_SPI(host_using_spi_e spi);

/*! @fn wakeup_device_with_io()
 *  @brief Wake the device by toggling the WAKEUP io with a delay. */
void wakeup_device_with_io(void);

/*! @fn make_very_short_wakeup_io()
 *  @brief Toggle the WAKEUP io very briefly (device should NOT wake up). */
void make_very_short_wakeup_io(void);

#ifdef __cplusplus
}
#endif

#endif /* PORT_H_ */
