/*
 * uwb_host.c - binary packet link to the PC.
 *
 * Packet: 0xA5 0x5A | type | len (2, LE) | payload | crc16 (2, LE)
 * The CRC covers type, len and payload, so a corrupted or half-received packet
 * is dropped on both sides instead of being mis-parsed.
 */
#include "uwb_host.h"

#include "uwb_port.h"
#include "uwb_proto.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

/* CRC-16/CCITT-FALSE, four bits at a time (fast enough for 6 kB CIR packets). */
static uint16_t crc16_update(uint16_t crc, const uint8_t *data, uint32_t len)
{
    static const uint16_t tab[16] = { 0x0000U, 0x1021U, 0x2042U, 0x3063U, 0x4084U, 0x50A5U, 0x60C6U, 0x70E7U,
                                      0x8108U, 0x9129U, 0xA14AU, 0xB16BU, 0xC18CU, 0xD1ADU, 0xE1CEU, 0xF1EFU };
    while (len--)
    {
        uint8_t b = *data++;
        crc = (uint16_t)((crc << 4) ^ tab[((crc >> 12) ^ (b >> 4)) & 0x0FU]);
        crc = (uint16_t)((crc << 4) ^ tab[((crc >> 12) ^ b) & 0x0FU]);
    }
    return crc;
}

/* ----------------------------------------------------------------------- TX */

void uwb_host_send2(uint8_t type, const void *part1, uint16_t len1, const void *part2, uint16_t len2)
{
    uint16_t len = (uint16_t)(len1 + len2);
    uint8_t head[5] = { UWB_SYNC0, UWB_SYNC1, type, (uint8_t)(len & 0xFFU), (uint8_t)(len >> 8) };
    uint16_t crc = crc16_update(0xFFFFU, &head[2], 3);

    uwb_port_uart_write(head, sizeof(head));
    if (len1)
    {
        crc = crc16_update(crc, (const uint8_t *)part1, len1);
        uwb_port_uart_write((const uint8_t *)part1, len1);
    }
    if (len2)
    {
        crc = crc16_update(crc, (const uint8_t *)part2, len2);
        uwb_port_uart_write((const uint8_t *)part2, len2);
    }
    uint8_t tail[2] = { (uint8_t)(crc & 0xFFU), (uint8_t)(crc >> 8) };
    uwb_port_uart_write(tail, sizeof(tail));
}

void uwb_host_send(uint8_t type, const void *payload, uint16_t len)
{
    uwb_host_send2(type, payload, len, NULL, 0);
}

void uwb_host_log(const char *fmt, ...)
{
    char text[120];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(text, sizeof(text), fmt, ap);
    va_end(ap);
    if (n < 0)
    {
        return;
    }
    if (n >= (int)sizeof(text))
    {
        n = (int)sizeof(text) - 1;
    }
    uwb_host_send(PKT_LOG, text, (uint16_t)n);
}

/* ----------------------------------------------------------------------- RX */

enum
{
    RX_SYNC0,
    RX_SYNC1,
    RX_TYPE,
    RX_LEN0,
    RX_LEN1,
    RX_PAYLOAD,
    RX_CRC0,
    RX_CRC1
};

static uint8_t rx_state;
static uint8_t rx_type;
static uint16_t rx_len;
static uint16_t rx_pos;
static uint16_t rx_crc;
static uint8_t rx_buf[UWB_HOST_MAX_CMD];

void uwb_host_init(void)
{
    rx_state = RX_SYNC0;
}

uint8_t uwb_host_poll(const uint8_t **payload, uint16_t *len)
{
    int c;

    while ((c = uwb_port_uart_getc()) >= 0)
    {
        uint8_t b = (uint8_t)c;

        switch (rx_state)
        {
        case RX_SYNC0:
            if (b == UWB_SYNC0)
            {
                rx_state = RX_SYNC1;
            }
            break;
        case RX_SYNC1:
            rx_state = (b == UWB_SYNC1) ? RX_TYPE : ((b == UWB_SYNC0) ? RX_SYNC1 : RX_SYNC0);
            break;
        case RX_TYPE:
            rx_type = b;
            rx_state = RX_LEN0;
            break;
        case RX_LEN0:
            rx_len = b;
            rx_state = RX_LEN1;
            break;
        case RX_LEN1:
            rx_len |= (uint16_t)b << 8;
            rx_pos = 0;
            if (rx_len > UWB_HOST_MAX_CMD)
            {
                rx_state = RX_SYNC0; /* not a command we could ever accept */
            }
            else
            {
                rx_state = (rx_len == 0U) ? RX_CRC0 : RX_PAYLOAD;
            }
            break;
        case RX_PAYLOAD:
            rx_buf[rx_pos++] = b;
            if (rx_pos >= rx_len)
            {
                rx_state = RX_CRC0;
            }
            break;
        case RX_CRC0:
            rx_crc = b;
            rx_state = RX_CRC1;
            break;
        case RX_CRC1:
        {
            rx_crc |= (uint16_t)b << 8;
            rx_state = RX_SYNC0;

            uint8_t head[3] = { rx_type, (uint8_t)(rx_len & 0xFFU), (uint8_t)(rx_len >> 8) };
            uint16_t crc = crc16_update(0xFFFFU, head, 3);
            crc = crc16_update(crc, rx_buf, rx_len);
            if (crc == rx_crc)
            {
                *payload = rx_buf;
                *len = rx_len;
                return rx_type;
            }
            break;
        }
        default:
            rx_state = RX_SYNC0;
            break;
        }
    }
    return 0;
}
