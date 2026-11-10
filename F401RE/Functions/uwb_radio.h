/*
 * uwb_radio.h - DW3000 helpers shared by the initiator and the responder:
 * bring-up, frame TX/RX with deadlines, timestamps, diagnostics and CIR capture.
 */
#ifndef UWB_RADIO_H
#define UWB_RADIO_H

#include "uwb_proto.h"

#include <stdint.h>

/* Raw CIR buffer: one dummy byte (the DW3000 clocks one out before accumulator
 * data) followed by up to 1016 samples of 6 bytes. */
#define UWB_CIR_MAX_SAMPLES 1016U
#define UWB_CIR_BUF_SIZE    (1U + 6U * UWB_CIR_MAX_SAMPLES)

/* 1 microsecond in DW3000 device time units (499.2 MHz * 128 / 1e6 = 63897.6). */
#define UWB_DTU_PER_10US 638976ULL

typedef struct
{
    uwb_radio_cfg_t cfg; /* configuration as applied (defaults filled in)        */
    uint32_t dev_id;
    uint32_t part_id;
    uint8_t  lot_id[8];
    int16_t  temp_c_x100;
    uint16_t vbat_mv;
    uint16_t cir_samples; /* samples in a full Ipatov CIR for this PRF (992/1016) */
    uint16_t shr_us;      /* duration of preamble + SFD                           */
} uwb_radio_info_t;

/* Counters updated by uwb_radio_wait_frame(). */
typedef struct
{
    uint16_t n_rx_error;
    uint16_t n_foreign;
    uint32_t last_status;
} uwb_radio_stats_t;

extern uwb_radio_info_t uwb_radio;

/* Reset, probe, initialise and configure the DW3000. Returns an ACK_* code. */
uint8_t uwb_radio_start(const uwb_radio_cfg_t *requested);

/* Put the transceiver back to idle (safe to call at any time after start). */
void uwb_radio_idle(void);

/* Time on air, in microseconds, of the PHR + payload part of a frame
 * (frame_len includes the 2 FCS bytes). The part before it lasts uwb_radio.shr_us. */
uint32_t uwb_radio_data_us(uint16_t frame_len);

/* Microseconds elapsed since t0 = uwb_port_cycles(). */
uint32_t uwb_radio_elapsed_us(uint32_t t0);

/* Build the 10-byte header shared by every frame. Returns AIR_HDR_LEN. */
uint16_t uwb_radio_make_header(uint8_t *frame, uint8_t function, uint8_t from_initiator);

/* Load a frame (len excludes the FCS) and start transmitting.
 * mode is a dwt_starttx() mode. Returns 0, or -1 if a delayed TX was too late. */
int uwb_radio_tx(const uint8_t *frame, uint16_t len, uint8_t mode);

/* Wait for the TX-done event. Returns 0, or -1 after timeout_us. */
int uwb_radio_wait_tx_done(uint32_t timeout_us);

/*
 * Wait for a good frame whose function code is fn_a or fn_b (fn_b = 0: only fn_a).
 * The receiver must already be on (or about to turn on after a TX).
 * PHY errors and frames that do not match are counted and the receiver is
 * re-enabled, until window_us has passed since t0 (0 = no deadline).
 *
 * poll_host: if non-NULL it is called on every pass; a non-zero return aborts
 * the wait.
 *
 * Returns the payload length (>= 0) with the payload copied to payload[] and the
 * function code in *fn_out, -1 on deadline, -2 if poll_host aborted the wait.
 * On every return the receiver is off.
 */
int uwb_radio_wait_frame(uint8_t fn_a, uint8_t fn_b, uint8_t from_initiator, uint8_t *fn_out, uint8_t *payload,
                         uint16_t max_payload, uint32_t t0, uint32_t window_us, int (*poll_host)(void),
                         uwb_radio_stats_t *stats);

/* 40-bit timestamps of the last TX / RX. */
uint64_t uwb_radio_tx_stamp(void);
uint64_t uwb_radio_rx_stamp(void);
void uwb_radio_stamp_to_bytes(uint64_t stamp, uint8_t out[5]);

/* Read n CIR samples starting at sample 'start' into raw[] (raw[0] is a dummy
 * byte, data starts at raw[1]). Returns the time it took in microseconds. */
uint32_t uwb_radio_read_cir(uint8_t *raw, uint16_t start, uint16_t n);

/* After a good reception: fill hdr with the diagnostics and read the CIR. */
void uwb_radio_capture(uwb_cir_hdr_t *hdr, uint8_t *raw, uint16_t start, uint16_t n);

/* Re-read the CIR with the driver's dwt_readcir() and compare with raw[].
 * scratch must hold 6 * n bytes. Returns 1 if identical, 2 if not. */
uint8_t uwb_radio_verify_cir(const uint8_t *raw, uint8_t *scratch, uint16_t start, uint16_t n);

/* Send one PKT_CIR to the PC. Returns the time it took in microseconds. */
uint32_t uwb_radio_send_cir(const uwb_cir_hdr_t *hdr, const uint8_t *raw);

/* Pick a reply delay (in 10 us units) that covers reading a CIR. */
uint16_t uwb_radio_auto_delay_10us(uint32_t cir_read_us);

#endif /* UWB_RADIO_H */
