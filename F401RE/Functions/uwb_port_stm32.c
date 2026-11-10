/*
 * uwb_port_stm32.c - STM32 implementation of uwb_port.h.
 *
 * The SAME file is used in the NUCLEO-F401RE and NUCLEO-F439ZI projects; the
 * board is picked from the MCU symbol CubeIDE already defines for the project:
 *
 *   board          PC link (ST-LINK virtual COM port)   interrupt
 *   NUCLEO-F401RE  USART2 (PA2/PA3), handle huart2      USART2_IRQHandler
 *   NUCLEO-F439ZI  USART3 (PD8/PD9), handle huart3      USART3_IRQHandler
 *
 * Uses what CubeMX already set up in main.c (SPI1, the UART, SysTick) and adds:
 *   - the Cortex-M cycle counter for microsecond timing,
 *   - an interrupt-driven receive ring buffer on the UART, so commands from the
 *     PC are never lost while the firmware is busy with the radio or sending a CIR.
 *
 * NOTE: this file defines the UART interrupt handler named above. If you later
 * enable that UART's "global interrupt" in CubeMX, CubeMX will generate a second
 * one in stm32f4xx_it.c and the build will fail with a duplicate symbol. Leave
 * that box unticked.
 */
#include "uwb_port.h"

#include "deca_probe_interface.h"
#include <deca_device_api.h>
#include <main.h>
#include <port.h>

#if defined(STM32F439xx) || defined(STM32F429xx)
/* NUCLEO-F439ZI / F429ZI: ST-LINK virtual COM port is on USART3. */
extern UART_HandleTypeDef huart3;
#define UWB_HUART       huart3
#define UWB_UART_IRQn   USART3_IRQn
#define UWB_UART_IRQHandler USART3_IRQHandler
#else
/* NUCLEO-F401RE: ST-LINK virtual COM port is on USART2. */
extern UART_HandleTypeDef huart2;
#define UWB_HUART       huart2
#define UWB_UART_IRQn   USART2_IRQn
#define UWB_UART_IRQHandler USART2_IRQHandler
#endif

#define RX_RING_SIZE 256U /* power of two */

static volatile uint8_t rx_ring[RX_RING_SIZE];
static volatile uint16_t rx_head; /* written by the interrupt */
static volatile uint16_t rx_tail; /* written by the main loop */

void UWB_UART_IRQHandler(void)
{
    USART_TypeDef *u = UWB_HUART.Instance;
    uint32_t sr = u->SR;

    if (sr & (USART_SR_RXNE | USART_SR_ORE | USART_SR_NE | USART_SR_FE))
    {
        /* Reading SR then DR clears RXNE and the error flags. */
        uint8_t b = (uint8_t)u->DR;
        if (sr & USART_SR_RXNE)
        {
            uint16_t next = (uint16_t)((rx_head + 1U) & (RX_RING_SIZE - 1U));
            if (next != rx_tail)
            {
                rx_ring[rx_head] = b;
                rx_head = next;
            }
        }
    }
}

void uwb_port_init(void)
{
    /* Enable the cycle counter (works without a debugger attached). */
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;

    rx_head = 0;
    rx_tail = 0;
    uwb_port_uart_set_baud(UWB_HUART.Init.BaudRate);
}

uint32_t uwb_port_cycles(void)
{
    return DWT->CYCCNT;
}

uint32_t uwb_port_cycles_per_us(void)
{
    return SystemCoreClock / 1000000UL;
}

uint32_t uwb_port_millis(void)
{
    return HAL_GetTick();
}

void uwb_port_delay_ms(uint32_t ms)
{
    HAL_Delay(ms);
}

void uwb_port_uart_set_baud(uint32_t baud)
{
    uwb_port_uart_flush();
    HAL_NVIC_DisableIRQ(UWB_UART_IRQn);

    UWB_HUART.Init.BaudRate = baud;
    if (HAL_UART_Init(&UWB_HUART) != HAL_OK)
    {
        Error_Handler();
    }

    /* Receive by interrupt into the ring buffer. */
    (void)UWB_HUART.Instance->SR;
    (void)UWB_HUART.Instance->DR;
    UWB_HUART.Instance->CR1 |= USART_CR1_RXNEIE;
    HAL_NVIC_SetPriority(UWB_UART_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(UWB_UART_IRQn);
}

void uwb_port_uart_write(const uint8_t *data, uint32_t len)
{
    USART_TypeDef *u = UWB_HUART.Instance;
    while (len--)
    {
        while ((u->SR & USART_SR_TXE) == 0U)
        {
        }
        u->DR = *data++;
    }
}

void uwb_port_uart_flush(void)
{
    USART_TypeDef *u = UWB_HUART.Instance;
    if ((u->CR1 & USART_CR1_UE) == 0U)
    {
        return;
    }
    while ((u->SR & USART_SR_TC) == 0U)
    {
    }
}

int uwb_port_uart_getc(void)
{
    if (rx_head == rx_tail)
    {
        return -1;
    }
    uint8_t b = rx_ring[rx_tail];
    rx_tail = (uint16_t)((rx_tail + 1U) & (RX_RING_SIZE - 1U));
    return (int)b;
}

int uwb_port_radio_reset_and_probe(void)
{
    /* Same order as the Qorvo examples this project was built from. */
    port_set_dw_ic_spi_fastrate();
    reset_DWIC();
    Sleep(2); /* INIT_RC -> IDLE_RC */

    if (dwt_probe((struct dwt_probe_s *)&dw3000_probe_interf) == DWT_ERROR)
    {
        return -1;
    }
    return 0;
}
