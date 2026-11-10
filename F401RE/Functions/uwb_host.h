/*
 * uwb_host.h - binary packet link to the PC (see uwb_proto.h for the format).
 */
#ifndef UWB_HOST_H
#define UWB_HOST_H

#include <stdint.h>

#define UWB_HOST_MAX_CMD 64U /* largest command payload accepted from the PC */

void uwb_host_init(void);

/* Send one complete packet. */
void uwb_host_send(uint8_t type, const void *payload, uint16_t len);

/* Send one packet made of two parts (header struct + bulk data) without copying. */
void uwb_host_send2(uint8_t type, const void *part1, uint16_t len1, const void *part2, uint16_t len2);

/* printf-style text to the PC (shows up in the tool's log). */
void uwb_host_log(const char *fmt, ...);

/* Non-blocking: parse whatever bytes have arrived.
 * Returns the command type when a complete, CRC-correct packet is available
 * (payload/len describe it and stay valid until the next call), otherwise 0. */
uint8_t uwb_host_poll(const uint8_t **payload, uint16_t *len);

#endif /* UWB_HOST_H */
