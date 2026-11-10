/*
 * uwb_app.h - top level of the 3-CIR DS-TWR capture firmware.
 *
 * main.c calls uwb_app_run() once; it never returns. The board then waits for
 * commands from the PC (python/uwb_tool.py) and becomes initiator or responder
 * on request, so both boards run the same firmware image.
 */
#ifndef UWB_APP_H
#define UWB_APP_H

#include "uwb_proto.h"

#include <stdint.h>

void uwb_app_run(void);

/* Called by the roles while a trial is running. Answers CMD_PING, refuses
 * commands that need an idle board, and returns 1 when CMD_STOP has arrived. */
int uwb_app_service_host(void);

/* Two raw CIR buffers of UWB_CIR_BUF_SIZE bytes (index 0 or 1). */
uint8_t *uwb_app_cir_buf(int index);

/* Clamp a requested CIR window to what the accumulator holds. */
void uwb_app_normalise_window(uint16_t *start, uint16_t *len);

/* Delay before the receiver turns on after our own frame, so that it opens
 * 2 ms before the peer's reply can start (0 if the reply comes sooner). */
uint32_t uwb_app_rx_after_tx_us(uint32_t reply_delay_us, uint16_t own_frame_len);

/* Raise a reply delay by 25 % after a late transmission (automatic mode). */
uint16_t uwb_app_bump_delay(uint16_t delay_10us);

void uwb_initiator_run(const uwb_cmd_start_t *cmd);
void uwb_responder_run(const uwb_cmd_start_t *cmd);

#endif /* UWB_APP_H */
