/*
 * uwb_responder.c - responder ("RX") side of the 3-CIR double-sided two-way ranging.
 *
 * Once started the responder listens for polls. Everything about a trial (ID,
 * exchange number, CIR window, reply delays, target count) arrives in the poll,
 * so the responder's PC only has to arm it.
 *
 * For each exchange:
 *   1. poll received      -> read diagnostics + poll CIR into buffer 0
 *   2. response sent      at poll RX time + resp_delay
 *   3. final received     -> read diagnostics + final CIR into buffer 1
 *   4. range computed, then both CIRs and one exchange record go to the PC.
 * The receiver is off during step 4, so nothing can overwrite the accumulator.
 *
 * Ending a trial:
 *   - target count reached, or the responder's PC sent CMD_STOP: the responder keeps
 *     listening briefly and answers the next poll with a DONE / STOP flag, which is
 *     how the initiator (and its PC) find out;
 *   - the initiator sends an END frame (its PC stopped the trial);
 *   - no poll for idle_timeout_s.
 */
#include "uwb_app.h"
#include "uwb_host.h"
#include "uwb_port.h"
#include "uwb_radio.h"

#include <deca_device_api.h>
#include <string.h>

#define RESP_FRAME_LEN  (AIR_HDR_LEN + sizeof(air_resp_t) + AIR_FCS_LEN)
#define FINAL_FRAME_LEN (AIR_HDR_LEN + sizeof(air_final_t) + AIR_FCS_LEN)

#define CLOSING_MAX_MS    3000U /* wait this long for a poll to carry the DONE / STOP flag */
#define CLOSING_LINGER_MS 500U  /* after answering, stay this long in case the answer was lost */

/* State the host-poll callback needs while the radio is waiting for a frame. */
static struct
{
    uint8_t trial_active;
    uint8_t closing;        /* trial is over, telling the initiator          */
    uint8_t closing_flag;   /* AIR_RESP_DONE or AIR_RESP_STOP                */
    uint8_t answered;       /* a closing response has been sent              */
    uint8_t end_reason;
    uint32_t closing_ms;
    uint32_t answered_ms;
    uint32_t last_poll_ms;
    uint16_t idle_timeout_s;
} rs;

/* Trial that was last closed on this board (kept between runs of the responder).
 * If the initiator did not hear the end of it and is still polling for it when the
 * next trial is armed here, it must be told "done" again, not adopted as a new trial. */
static uint32_t last_closed_trial;

static void start_closing(uint8_t flag, uint8_t reason)
{
    if (!rs.closing)
    {
        rs.closing = 1;
        rs.closing_flag = flag;
        rs.end_reason = reason;
        rs.closing_ms = uwb_port_millis();
        rs.answered = 0;
    }
}

/* Called continuously while listening. Returns 1 to leave the responder loop. */
static int listen_poll_host(void)
{
    if (uwb_app_service_host())
    {
        if (!rs.trial_active)
        {
            rs.end_reason = END_HOST_STOP;
            return 1; /* nothing to tell the initiator */
        }
        start_closing(AIR_RESP_STOP, END_HOST_STOP);
    }

    /* Read the clock AFTER start_closing() has stamped closing_ms: the other way
     * round, a tick in between made (now - closing_ms) wrap to a huge number and
     * the trial ended at once, without telling the initiator. */
    uint32_t now = uwb_port_millis();

    if (rs.closing)
    {
        if (rs.answered && ((now - rs.answered_ms) > CLOSING_LINGER_MS))
        {
            return 1;
        }
        if ((now - rs.closing_ms) > CLOSING_MAX_MS)
        {
            return 1;
        }
    }
    else if (rs.trial_active && (rs.idle_timeout_s != 0U) && ((now - rs.last_poll_ms) > (uint32_t)rs.idle_timeout_s * 1000U))
    {
        rs.end_reason = END_IDLE_TIMEOUT;
        return 1;
    }
    return 0;
}

void uwb_responder_run(const uwb_cmd_start_t *cmd)
{
    uint8_t *raw_poll = uwb_app_cir_buf(0);
    uint8_t *raw_final = uwb_app_cir_buf(1);
    uint8_t frame[AIR_MAX_FRAME];
    uint8_t payload[sizeof(air_final_t)];
    uwb_radio_stats_t stats;
    uwb_trial_end_t end;
    uwb_trial_begin_t begin;

    memset(&rs, 0, sizeof(rs));
    memset(&stats, 0, sizeof(stats));
    memset(&end, 0, sizeof(end));
    memset(&begin, 0, sizeof(begin));
    rs.idle_timeout_s = cmd->idle_timeout_s;
    rs.end_reason = END_HOST_STOP;

    uint32_t trial_id = 0;
    uint32_t attempts = 0;
    uint16_t completed = 0;
    uint16_t target = 0;
    uint8_t trial_flags = 0;
    uint8_t begin_pending = 0;
    uint8_t verify = 0;
    uint16_t cir_start = 0;
    uint16_t cir_len = 0;
    uint16_t resp_delay = 0;
    uint16_t final_delay = 0;

    for (;;)
    {
        /* ---- listen for a poll (no deadline; the PC is serviced meanwhile) ---- */
        uint8_t fn = 0;
        dwt_rxenable((int32_t)DWT_START_RX_IMMEDIATE);
        int n = uwb_radio_wait_frame(AIR_FN_POLL, AIR_FN_END, 1, &fn, payload, sizeof(payload), 0, 0, listen_poll_host, &stats);
        uint32_t t_rx = uwb_port_cycles();

        if (n == -2)
        {
            break; /* stopped, closing finished, or idle timeout: reason is in rs.end_reason */
        }
        if (n < 0)
        {
            continue;
        }

        if (fn == AIR_FN_END)
        {
            air_end_t e;
            if ((n >= (int)sizeof(e)) && rs.trial_active)
            {
                memcpy(&e, payload, sizeof(e));
                if (e.trial_id == trial_id)
                {
                    if (!rs.closing)
                    {
                        rs.end_reason = END_PEER_STOP;
                    }
                    break;
                }
            }
            continue;
        }

        if (n < (int)sizeof(air_poll_t))
        {
            stats.n_foreign++;
            continue;
        }
        air_poll_t poll;
        memcpy(&poll, payload, sizeof(poll));
        if ((poll.resp_delay_10us == 0U) || (poll.resp_delay_10us > UWB_MAX_DELAY_10US) || (poll.final_delay_10us == 0U) ||
            (poll.final_delay_10us > UWB_MAX_DELAY_10US))
        {
            stats.n_foreign++;
            continue;
        }

        if (!rs.trial_active && (poll.trial_id == last_closed_trial) && (last_closed_trial != 0U))
        {
            /* A leftover poll of the trial that already ended here. */
            air_resp_t done;
            done.trial_id = poll.trial_id;
            done.xid = poll.xid;
            done.flags = AIR_RESP_DONE;
            done.completed = 0;
            done.need_delay_10us = 0;
            uint16_t dlen = uwb_radio_make_header(frame, AIR_FN_RESP, 0);
            memcpy(&frame[dlen], &done, sizeof(done));
            dlen = (uint16_t)(dlen + sizeof(done));
            uint64_t stale_rx_ts = uwb_radio_rx_stamp();
            dwt_setdelayedtrxtime((uint32_t)((stale_rx_ts + (uint64_t)poll.resp_delay_10us * UWB_DTU_PER_10US) >> 8));
            if (uwb_radio_tx(frame, dlen, (uint8_t)DWT_START_TX_DELAYED) == 0)
            {
                (void)uwb_radio_wait_tx_done((uint32_t)poll.resp_delay_10us * 10U + uwb_radio_data_us(RESP_FRAME_LEN) + 5000U);
            }
            continue;
        }

        if (!rs.trial_active)
        {
            /* First poll of a new trial: adopt its parameters. */
            rs.trial_active = 1;
            trial_id = poll.trial_id;
            /* Trial length: the initiator's if it set one, otherwise the one this
             * board's PC asked for (the usual case: the main PC is on the responder
             * and the initiator just keeps calling). 0 = until stopped. */
            target = (poll.target_count != 0U) ? poll.target_count : cmd->target_count;
            trial_flags = poll.flags;
            begin_pending = 1; /* sent with the first report, not now: the reply is time-critical */
        }
        else if (poll.trial_id != trial_id)
        {
            /* The initiator has moved on to a new trial without us hearing the end
             * of this one. Close this trial; the PC re-arms and the new trial is
             * picked up from its next poll. */
            if (!rs.closing)
            {
                rs.end_reason = END_PEER_STOP;
            }
            break;
        }

        rs.last_poll_ms = uwb_port_millis();
        attempts++;

        /* Capture parameters may change from poll to poll (automatic delay tuning). */
        cir_start = poll.cir_start;
        cir_len = poll.cir_len;
        uwb_app_normalise_window(&cir_start, &cir_len);
        resp_delay = poll.resp_delay_10us;
        final_delay = poll.final_delay_10us;
        uint32_t resp_delay_us = (uint32_t)resp_delay * 10U;
        uint32_t final_delay_us = (uint32_t)final_delay * 10U;

        uint64_t poll_rx_ts = uwb_radio_rx_stamp();
        uint32_t resp_time = (uint32_t)((poll_rx_ts + (uint64_t)resp_delay * UWB_DTU_PER_10US) >> 8);

        air_resp_t resp;
        resp.trial_id = trial_id;
        resp.xid = poll.xid;
        resp.completed = completed;
        resp.flags = 0U;
        resp.need_delay_10us = 0U;

        /* ---- trial already over: answer with the DONE / STOP flag only ---- */
        if (rs.closing)
        {
            resp.flags |= rs.closing_flag;
            uint16_t len = uwb_radio_make_header(frame, AIR_FN_RESP, 0);
            memcpy(&frame[len], &resp, sizeof(resp));
            len = (uint16_t)(len + sizeof(resp));
            dwt_setdelayedtrxtime(resp_time);
            if (uwb_radio_tx(frame, len, (uint8_t)DWT_START_TX_DELAYED) == 0)
            {
                (void)uwb_radio_wait_tx_done(resp_delay_us + uwb_radio_data_us(RESP_FRAME_LEN) + 5000U);
                rs.answered = 1;
                rs.answered_ms = uwb_port_millis();
            }
            continue;
        }

        uwb_exchange_t ex;
        memset(&ex, 0, sizeof(ex));
        ex.trial_id = trial_id;
        ex.xid = poll.xid;
        ex.role = ROLE_RESPONDER;
        ex.resp_delay_10us = resp_delay;
        ex.final_delay_10us = final_delay;

        /* ---- 1. capture the poll CIR ---- */
        uwb_cir_hdr_t hdr_poll;
        uwb_cir_hdr_t hdr_final;
        memset(&hdr_poll, 0, sizeof(hdr_poll));
        memset(&hdr_final, 0, sizeof(hdr_final));
        hdr_poll.trial_id = trial_id;
        hdr_poll.xid = poll.xid;
        hdr_poll.kind = CIR_POLL;
        uwb_radio_capture(&hdr_poll, raw_poll, cir_start, cir_len);
        int have_final = 0;

        if (begin_pending)
        {
            begin.cir_read_us = hdr_poll.read_us;
        }

        /* ---- 2. response at poll RX + resp_delay; receiver reopens for the final ---- */
        uint16_t len = uwb_radio_make_header(frame, AIR_FN_RESP, 0);
        memcpy(&frame[len], &resp, sizeof(resp));
        len = (uint16_t)(len + sizeof(resp));

        dwt_setdelayedtrxtime(resp_time);
        dwt_setrxaftertxdelay(uwb_app_rx_after_tx_us(final_delay_us, RESP_FRAME_LEN));

        ex.proc_us = uwb_radio_elapsed_us(t_rx);
        uint32_t t_tx = uwb_port_cycles();
        if (uwb_radio_tx(frame, len, (uint8_t)DWT_START_TX_DELAYED | (uint8_t)DWT_RESPONSE_EXPECTED) != 0)
        {
            /* Too late: the reply delay does not cover this board's CIR read
             * (the initiator sized it from its own, and it may be the faster
             * board). Answer at once, without ranging, and say how long this
             * board needs: time from the poll's timestamp to here, plus 1/8,
             * plus the start-TX call and the preamble that precedes the
             * response's timestamp. */
            uint32_t need_us = uwb_radio_data_us((uint16_t)(AIR_HDR_LEN + sizeof(air_poll_t) + AIR_FCS_LEN)) + ex.proc_us + ex.proc_us / 8U + 700U + uwb_radio.shr_us;
            uint32_t need_10us = (need_us + 99U) / 100U * 10U;
            if (need_10us > UWB_MAX_DELAY_10US)
            {
                need_10us = UWB_MAX_DELAY_10US;
            }
            resp.flags |= AIR_RESP_LATE;
            resp.need_delay_10us = (uint16_t)need_10us;
            len = uwb_radio_make_header(frame, AIR_FN_RESP, 0);
            memcpy(&frame[len], &resp, sizeof(resp));
            len = (uint16_t)(len + sizeof(resp));
            if (uwb_radio_tx(frame, len, (uint8_t)DWT_START_TX_IMMEDIATE) == 0)
            {
                (void)uwb_radio_wait_tx_done(uwb_radio.shr_us + uwb_radio_data_us(RESP_FRAME_LEN) + 5000U);
            }
            ex.status = XS_LATE_TX;
            end.n_late_tx++;
        }
        else
        {

            /* ---- 3. final ---- */
            air_final_t fin;
            uint32_t window_us = resp_delay_us + final_delay_us + uwb_radio_data_us(FINAL_FRAME_LEN) + 3000U;
            n = uwb_radio_wait_frame(AIR_FN_FINAL, 0, 1, NULL, payload, sizeof(payload), t_tx, window_us, NULL, &stats);
            if (n >= (int)sizeof(fin))
            {
                memcpy(&fin, payload, sizeof(fin));
            }
            if ((n < (int)sizeof(fin)) || (fin.trial_id != trial_id) || (fin.xid != poll.xid))
            {
                if (n >= 0)
                {
                    stats.n_foreign++;
                }
                ex.status = XS_NO_FINAL;
                ex.sys_status = stats.last_status;
                end.n_timeout++;
            }
            else
            {
                uint64_t resp_tx_ts = uwb_radio_tx_stamp();
                uint64_t final_rx_ts = uwb_radio_rx_stamp();

                hdr_final.trial_id = trial_id;
                hdr_final.xid = poll.xid;
                hdr_final.kind = CIR_FINAL;
                uwb_radio_capture(&hdr_final, raw_final, cir_start, cir_len);
                have_final = 1;

                /* ---- 4. time of flight (asymmetric double-sided TWR) ----
                 * 32-bit differences are exact as long as each interval is below 67 ms. */
                uint32_t poll_rx_32 = (uint32_t)poll_rx_ts;
                uint32_t resp_tx_32 = (uint32_t)resp_tx_ts;
                uint32_t final_rx_32 = (uint32_t)final_rx_ts;
                double Ra = (double)(uint32_t)(fin.resp_rx_ts - fin.poll_tx_ts);
                double Rb = (double)(uint32_t)(final_rx_32 - resp_tx_32);
                double Da = (double)(uint32_t)(fin.final_tx_ts - fin.resp_rx_ts);
                double Db = (double)(uint32_t)(resp_tx_32 - poll_rx_32);
                ex.tof_dtu = (Ra * Rb - Da * Db) / (Ra + Rb + Da + Db);

                uwb_radio_stamp_to_bytes(poll_rx_ts, ex.ts[0]);
                uwb_radio_stamp_to_bytes(resp_tx_ts, ex.ts[1]);
                uwb_radio_stamp_to_bytes(final_rx_ts, ex.ts[2]);
                ex.peer_ts[0] = fin.poll_tx_ts;
                ex.peer_ts[1] = fin.resp_rx_ts;
                ex.peer_ts[2] = fin.final_tx_ts;

                ex.status = XS_OK;
                completed++;
            }
        }

        /* ---- 5. report to the PC (receiver is off, accumulator still holds the final) ---- */
        if (begin_pending)
        {
            begin_pending = 0;
            begin.role = ROLE_RESPONDER;
            begin.trial_id = trial_id;
            begin.target_count = target;
            begin.cir_start = cir_start;
            begin.cir_len = cir_len;
            begin.resp_delay_10us = resp_delay;
            begin.final_delay_10us = final_delay;
            begin.dev_id = uwb_radio.dev_id;
            begin.part_id = uwb_radio.part_id;
            memcpy(begin.lot_id, uwb_radio.lot_id, sizeof(begin.lot_id));
            begin.temp_c_x100 = uwb_radio.temp_c_x100;
            begin.vbat_mv = uwb_radio.vbat_mv;
            begin.radio = uwb_radio.cfg;
            uwb_host_send(PKT_TRIAL_BEGIN, &begin, sizeof(begin));
        }

        if ((ex.status == XS_OK) || (trial_flags & START_FLAG_DUMP_FAILED))
        {
            (void)uwb_radio_send_cir(&hdr_poll, raw_poll);
            ex.n_cir = 1;
            if (have_final)
            {
                if (verify == 0U)
                {
                    /* Once per trial: check the fast CIR read against the driver's own.
                     * The poll buffer has just been sent, so it serves as scratch space. */
                    verify = uwb_radio_verify_cir(raw_final, raw_poll, cir_start, cir_len);
                }
                (void)uwb_radio_send_cir(&hdr_final, raw_final);
                ex.n_cir = 2;
            }
        }
        ex.completed = completed;
        ex.t_ms = uwb_port_millis();
        uwb_host_send(PKT_EXCHANGE, &ex, sizeof(ex));

        if ((target != 0U) && (completed >= target))
        {
            start_closing(AIR_RESP_DONE, END_DONE);
        }
    }

    /* ---- end of trial ---- */
    uwb_radio_idle();
    if (trial_id != 0U)
    {
        last_closed_trial = trial_id;
    }

    end.role = ROLE_RESPONDER;
    end.trial_id = trial_id;
    end.reason = rs.end_reason;
    end.attempts = attempts;
    end.completed = completed;
    end.n_rx_error = stats.n_rx_error;
    end.n_foreign = stats.n_foreign;
    end.cir_verify = verify;
    end.resp_delay_10us = resp_delay;
    end.final_delay_10us = final_delay;
    uwb_host_send(PKT_TRIAL_END, &end, sizeof(end));
}
