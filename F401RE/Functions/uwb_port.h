/*
 * uwb_port.h - the few board-specific services the capture firmware needs.
 *
 * uwb_port_stm32.c implements them for the NUCLEO-F401RE. To port the firmware to
 * another board (for example the F439ZI) only that one file has to be rewritten.
 */
#ifndef UWB_PORT_H
#define UWB_PORT_H

#include <stdint.h>

void uwb_port_init(void);

/* Free-running CPU cycle counter, used for microsecond timing.
 * Always work with differences: (uwb_port_cycles() - t0) / uwb_port_cycles_per_us(). */
uint32_t uwb_port_cycles(void);
uint32_t uwb_port_cycles_per_us(void);

uint32_t uwb_port_millis(void);
void uwb_port_delay_ms(uint32_t ms);

/* Host UART. Writes block until the bytes are in the transmitter;
 * reads come from an interrupt-filled ring buffer and never block. */
void uwb_port_uart_set_baud(uint32_t baud);
void uwb_port_uart_write(const uint8_t *data, uint32_t len);
void uwb_port_uart_flush(void);
int uwb_port_uart_getc(void); /* next received byte, or -1 if none */

/* Hardware-reset the DW3000 and run dwt_probe(). Returns 0 on success. */
int uwb_port_radio_reset_and_probe(void);

#endif /* UWB_PORT_H */
