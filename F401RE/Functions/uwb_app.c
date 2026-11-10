/*
 * uwb_app.c - command loop of the 3-CIR DS-TWR capture firmware.
 *
 *   PC  --CMD_START(role, parameters)-->  board   : become initiator or responder
 *   PC  --CMD_STOP-------------------->  board   : end the trial (the other board is told over UWB)
 *   PC  <--PKT_CIR / PKT_EXCHANGE------  board   : data, see uwb_proto.h
 *
 * Files:
 *   uwb_proto.h       packet and frame formats (mirrored by python/uwb_tool.py)
 *   uwb_port_stm32.c  board-specific UART / timer / reset code
 *   uwb_host.c        packet link to the PC
 *   uwb_radio.c       DW3000 bring-up, frame TX/RX, diagnostics and CIR capture
 *   uwb_initiator.c   poll -> (response CIR) -> final
 *   uwb_responder.c   (poll CIR) -> response -> (final CIR) -> range
 */
#include "uwb_app.h"

#include "uwb_host.h"
#include "uwb_port.h"
#include "uwb_radio.h"

#include <string.h>

static uint8_t cir_buf[2][UWB_CIR_BUF_SIZE];
static uint8_t app_state = ST_IDLE;
static uint32_t app_baud = UWB_BOOT_BAUD;

uint8_t *uwb_app_cir_buf(int index)
{
    return cir_buf[index & 1];
}

void uwb_app_normalise_window(uint16_t *start, uint16_t *len)
{
    uint16_t total = uwb_radio.cir_samples;

    if (*start >= total)
    {
        *start = 0;
    }
    if ((*len == 0U) || ((uint32_t)*start + *len > total))
    {
        *len = (uint16_t)(total - *start);
    }
}

uint32_t uwb_app_rx_after_tx_us(uint32_t reply_delay_us, uint16_t own_frame_len)
{
    /* The reply's preamble starts (reply delay - preamble/SFD time) after our
     * timestamped instant; our own frame is still on air for its PHR + payload. */
    uint32_t busy = (uint32_t)uwb_radio.shr_us + uwb_radio_data_us(own_frame_len) + 2000U;
    return (reply_delay_us > busy) ? (reply_delay_us - busy) : 0U;
}

uint16_t uwb_app_bump_delay(uint16_t delay_10us)
{
    uint32_t d = (uint32_t)delay_10us + delay_10us / 4U + 20U;
    return (uint16_t)((d > UWB_MAX_DELAY_10US) ? UWB_MAX_DELAY_10US : d);
}

static void send_info(void)
{
    uwb_info_t info;

    info.fw_version = UWB_FW_VERSION;
    info.proto_version = UWB_PROTO_VERSION;
    info.state = app_state;
    info.baud = app_baud;
    info.uptime_ms = uwb_port_millis();
    info.max_cir_len = UWB_CIR_MAX_SAMPLES;
    uwb_host_send(PKT_INFO, &info, sizeof(info));
}

static void send_ack(uint8_t cmd, uint8_t status)
{
    uwb_ack_t ack = { cmd, status };
    uwb_host_send(PKT_ACK, &ack, sizeof(ack));
}

int uwb_app_service_host(void)
{
    const uint8_t *payload;
    uint16_t len;
    uint8_t cmd = uwb_host_poll(&payload, &len);

    switch (cmd)
    {
    case 0:
        return 0;
    case CMD_PING:
        send_info();
        return 0;
    case CMD_STOP:
        send_ack(CMD_STOP, ACK_OK);
        return 1;
    default:
        send_ack(cmd, ACK_BUSY); /* CMD_START / CMD_SET_BAUD need an idle board */
        return 0;
    }
}

static void handle_start(const uint8_t *payload, uint16_t len)
{
    uwb_cmd_start_t cmd;

    if (len != sizeof(cmd))
    {
        send_ack(CMD_START, ACK_BAD_PARAM);
        return;
    }
    memcpy(&cmd, payload, sizeof(cmd));

    if (((cmd.role != ROLE_INITIATOR) && (cmd.role != ROLE_RESPONDER)) || (cmd.resp_delay_10us > UWB_MAX_DELAY_10US) ||
        (cmd.final_delay_10us > UWB_MAX_DELAY_10US))
    {
        send_ack(CMD_START, ACK_BAD_PARAM);
        return;
    }

    uint8_t status = uwb_radio_start(&cmd.radio);
    send_ack(CMD_START, status);
    if (status != ACK_OK)
    {
        return;
    }

    if (cmd.role == ROLE_INITIATOR)
    {
        app_state = ST_INITIATOR;
        uwb_initiator_run(&cmd);
    }
    else
    {
        app_state = ST_RESPONDER;
        uwb_responder_run(&cmd);
    }
    uwb_radio_idle();
    app_state = ST_IDLE;
}

static void handle_set_baud(const uint8_t *payload, uint16_t len)
{
    uint32_t baud;

    if (len != sizeof(baud))
    {
        send_ack(CMD_SET_BAUD, ACK_BAD_PARAM);
        return;
    }
    memcpy(&baud, payload, sizeof(baud));
    if ((baud < 9600UL) || (baud > 2000000UL))
    {
        send_ack(CMD_SET_BAUD, ACK_BAD_PARAM);
        return;
    }

    /* Acknowledge at the old rate, let the last byte leave, then switch. */
    send_ack(CMD_SET_BAUD, ACK_OK);
    uwb_port_uart_flush();
    uwb_port_delay_ms(20);
    uwb_port_uart_set_baud(baud);
    app_baud = baud;
}

void uwb_app_run(void)
{
    uwb_port_init();
    uwb_port_uart_set_baud(UWB_BOOT_BAUD);
    uwb_host_init();
    send_info();

    for (;;)
    {
        const uint8_t *payload;
        uint16_t len;
        uint8_t cmd = uwb_host_poll(&payload, &len);

        switch (cmd)
        {
        case 0:
            break;
        case CMD_PING:
            send_info();
            break;
        case CMD_SET_BAUD:
            handle_set_baud(payload, len);
            break;
        case CMD_START:
            handle_start(payload, len);
            break;
        case CMD_STOP:
            send_ack(CMD_STOP, ACK_OK); /* already idle */
            break;
        default:
            send_ack(cmd, ACK_UNKNOWN_CMD);
            break;
        }
    }
}
