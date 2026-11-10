/*
 * uwb_initiator.c - initiator ("TX") side of the 3-CIR double-sided two-way ranging.
 *
 *   initiator                         responder
 *   ---------                         ---------
 *   POLL  ------------------------->  capture poll CIR
 *   capture response CIR  <---------  RESPONSE   (resp_delay after the poll)
 *   FINAL ------------------------->  capture final CIR, compute the range
 *         (final_delay after the response)
 *
 * The accumulator holds only the latest reception, so the response CIR is read
 * here, between receiving the response and sending the final. That is why the
 * reply delays are milliseconds instead of the few hundred microseconds of the
 * stock Qorvo example. Asymmetric DS-TWR is insensitive to the delay length.
 *
 * Every poll carries the trial ID, the exchange number (xid) and the capture
 * parameters, so the responder needs no settings of its own and both PCs can
 * match their records afterwards.
 */
#include "uwb_app.h"
#include "uwb_host.h"
#include "uwb_port.h"
#include "uwb_radio.h"

#include <deca_device_api.h>
#include <string.h>

#define POLL_FRAME_LEN  (AIR_HDR_LEN + sizeof(air_poll_t) + AIR_FCS_LEN)
#define RESP_FRAME_LEN  (AIR_HDR_LEN + sizeof(air_resp_t) + AIR_FCS_LEN)
#define FINAL_FRAME_LEN (AIR_HDR_LEN + sizeof(air_final_t) + AIR_FCS_LEN)

/* Tell the responder the trial is over. It may be busy sending CIRs to its PC
 * with its receiver off, so repeat for a while. */
static void send_end_frames(uint32_t trial_id, uint8_t reason)
{
    uint8_t frame[AIR_MAX_FRAME];
    air_end_t end = { trial_id, reason };

    for (int i = 0; i < 4; i++)
    {
        uint16_t len = uwb_radio_make_header(frame, AIR_FN_END, 1);
        memcpy(&frame[len], &end, sizeof(end));
        len = (uint16_t)(len + sizeof(end));
        if (uwb_radio_tx(frame, len, (uint8_t)DWT_START_TX_IMMEDIATE) == 0)
        {
            (void)uwb_radio_wait_tx_done(20000U);
        }
        uwb_port_delay_ms(50);
    }
}

void uwb_initiator_run(const uwb_cmd_start_t *cmd)
{
    uint8_t *raw = uwb_app_cir_buf(0);
    uint8_t frame[AIR_MAX_FRAME];
    uwb_radio_stats_t stats;
    uwb_trial_end_t end;

    memset(&stats, 0, sizeof(stats));
    memset(&end, 0, sizeof(end));

    /* ---- parameters ---- */
    uint16_t cir_start = cmd->cir_start;
    uint16_t cir_len = cmd->cir_len;
    uwb_app_normalise_window(&cir_start, &cir_len);

    /* Time one CIR read so the reply delays can be sized to it. */
    uint32_t cir_read_us = uwb_radio_read_cir(raw, cir_start, cir_len);

    uint8_t auto_resp = (cmd->resp_delay_10us == 0U);
    uint8_t auto_final = (cmd->final_delay_10us == 0U);
    uint16_t resp_delay = auto_resp ? uwb_radio_auto_delay_10us(cir_read_us) : cmd->resp_delay_10us;
    uint16_t final_delay = auto_final ? uwb_radio_auto_delay_10us(cir_read_us) : cmd->final_delay_10us;

    uwb_trial_begin_t begin;
    memset(&begin, 0, sizeof(begin));
    begin.role = ROLE_INITIATOR;
    begin.trial_id = cmd->trial_id;
    begin.target_count = cmd->target_count;
    begin.interval_ms = cmd->interval_ms;
    begin.cir_start = cir_start;
    begin.cir_len = cir_len;
    begin.resp_delay_10us = resp_delay;
    begin.final_delay_10us = final_delay;
    begin.cir_read_us = cir_read_us;
    begin.dev_id = uwb_radio.dev_id;
    begin.part_id = uwb_radio.part_id;
    memcpy(begin.lot_id, uwb_radio.lot_id, sizeof(begin.lot_id));
    begin.temp_c_x100 = uwb_radio.temp_c_x100;
    begin.vbat_mv = uwb_radio.vbat_mv;
    begin.radio = uwb_radio.cfg;
    uwb_host_send(PKT_TRIAL_BEGIN, &begin, sizeof(begin));

    /* ---- trial loop ---- */
    uint32_t xid = 0;
    uint32_t attempts = 0;
    uint16_t completed = 0; /* as reported by the responder */
    uint32_t dump_us = 0;
    uint32_t last_ok_ms = uwb_port_millis();
    uint8_t reason = END_HOST_STOP;
    uint8_t verify = 0;
    uint8_t contact = 0; /* set once the responder has answered a poll of this trial */
    int running = 1;

    while (running)
    {
        if (uwb_app_service_host())
        {
            reason = END_HOST_STOP;
            break;
        }
        if ((cmd->idle_timeout_s != 0U) && ((uwb_port_millis() - last_ok_ms) > (uint32_t)cmd->idle_timeout_s * 1000U))
        {
            reason = END_IDLE_TIMEOUT;
            break;
        }

        uint32_t cycle_ms = uwb_port_millis();
        uint32_t resp_delay_us = (uint32_t)resp_delay * 10U;
        uint32_t final_delay_us = (uint32_t)final_delay * 10U;

        xid++;
        attempts++;

        uwb_exchange_t ex;
        memset(&ex, 0, sizeof(ex));
        ex.trial_id = cmd->trial_id;
        ex.xid = xid;
        ex.role = ROLE_INITIATOR;
        ex.resp_delay_10us = resp_delay;
        ex.final_delay_10us = final_delay;

        uwb_cir_hdr_t hdr;
        memset(&hdr, 0, sizeof(hdr));
        int have_cir = 0;

        /* ---- 1. poll ---- */
        air_poll_t poll;
        poll.trial_id = cmd->trial_id;
        poll.xid = xid;
        poll.target_count = cmd->target_count;
        poll.flags = cmd->flags;
        poll.cir_start = cir_start;
        poll.cir_len = cir_len;
        poll.resp_delay_10us = resp_delay;
        poll.final_delay_10us = final_delay;

        uint16_t len = uwb_radio_make_header(frame, AIR_FN_POLL, 1);
        memcpy(&frame[len], &poll, sizeof(poll));
        len = (uint16_t)(len + sizeof(poll));

        /* The receiver opens by itself 2 ms before the response can start. */
        dwt_setrxaftertxdelay(uwb_app_rx_after_tx_us(resp_delay_us, POLL_FRAME_LEN));

        uint32_t t_poll = uwb_port_cycles();
        (void)uwb_radio_tx(frame, len, (uint8_t)DWT_START_TX_IMMEDIATE | (uint8_t)DWT_RESPONSE_EXPECTED);

        /* ---- 2. response ---- */
        air_resp_t resp;
        uint8_t payload[sizeof(air_final_t)];
        /* 30 ms of slack: a responder that was too slow for the reply delay
         * answers late (AIR_RESP_LATE), as soon as it can, and that answer must
         * be heard however slow the other board is. Otherwise the two would
         * never make contact. The slack only costs time when nothing answers. */
        uint32_t window_us = uwb_radio.shr_us + resp_delay_us + uwb_radio_data_us(RESP_FRAME_LEN) + 30000U;
        int n = uwb_radio_wait_frame(AIR_FN_RESP, 0, 0, NULL, payload, sizeof(payload), t_poll, window_us, NULL, &stats);
        uint32_t t_rx = uwb_port_cycles();

        if (n >= (int)sizeof(resp))
        {
            memcpy(&resp, payload, sizeof(resp));
        }
        if ((n < (int)sizeof(resp)) || (resp.trial_id != cmd->trial_id) || (resp.xid != xid))
        {
            if (n >= 0)
            {
                stats.n_foreign++; /* a response, but not to this poll */
            }
            ex.status = XS_NO_RESPONSE;
            ex.sys_status = stats.last_status;
            end.n_timeout++;
        }
        else
        {
            contact = 1;
            completed = resp.completed;
            ex.peer_flags = resp.flags;

            if (resp.flags & AIR_RESP_STOP)
            {
                ex.status = XS_PEER_STOP;
            }
            else if (resp.flags & AIR_RESP_DONE)
            {
                ex.status = XS_PEER_DONE;
            }
            else if (resp.flags & AIR_RESP_LATE)
            {
                /* The responder could not keep up (it is the slower board, or
                 * the delay was set by hand too short). No ranging this time. */
                ex.status = XS_PEER_LATE;
                end.n_late_tx++;
                if (auto_resp)
                {
                    uint16_t bumped = uwb_app_bump_delay(resp_delay);
                    resp_delay = (resp.need_delay_10us > bumped) ? resp.need_delay_10us : bumped;
                    if (resp_delay > UWB_MAX_DELAY_10US)
                    {
                        resp_delay = UWB_MAX_DELAY_10US;
                    }
                }
            }
            else
            {
                /* ---- 3. capture the response CIR, then send the final ---- */
                uint64_t poll_tx_ts = uwb_radio_tx_stamp();
                uint64_t resp_rx_ts = uwb_radio_rx_stamp();

                hdr.trial_id = cmd->trial_id;
                hdr.xid = xid;
                hdr.kind = CIR_RESPONSE;
                uwb_radio_capture(&hdr, raw, cir_start, cir_len);
                have_cir = 1;

                /* Delayed TX time is the high 32 bits of the 40-bit device time, lowest bit ignored.
                 * The frame leaves the antenna one TX antenna delay later. */
                uint32_t final_time = (uint32_t)((resp_rx_ts + (uint64_t)final_delay * UWB_DTU_PER_10US) >> 8);
                uint64_t final_tx_ts = (((uint64_t)(final_time & 0xFFFFFFFEUL)) << 8) + uwb_radio.cfg.tx_ant_dly;
                dwt_setdelayedtrxtime(final_time);

                air_final_t fin;
                fin.trial_id = cmd->trial_id;
                fin.xid = xid;
                fin.poll_tx_ts = (uint32_t)poll_tx_ts;
                fin.resp_rx_ts = (uint32_t)resp_rx_ts;
                fin.final_tx_ts = (uint32_t)final_tx_ts;

                len = uwb_radio_make_header(frame, AIR_FN_FINAL, 1);
                memcpy(&frame[len], &fin, sizeof(fin));
                len = (uint16_t)(len + sizeof(fin));

                uwb_radio_stamp_to_bytes(poll_tx_ts, ex.ts[0]);
                uwb_radio_stamp_to_bytes(resp_rx_ts, ex.ts[1]);
                uwb_radio_stamp_to_bytes(final_tx_ts, ex.ts[2]);

                ex.proc_us = uwb_radio_elapsed_us(t_rx);
                if (uwb_radio_tx(frame, len, (uint8_t)DWT_START_TX_DELAYED) != 0)
                {
                    ex.status = XS_LATE_TX;
                    end.n_late_tx++;
                    if (auto_final)
                    {
                        final_delay = uwb_app_bump_delay(final_delay);
                    }
                }
                else if (uwb_radio_wait_tx_done(final_delay_us + uwb_radio_data_us(FINAL_FRAME_LEN) + 5000U) != 0)
                {
                    ex.status = XS_TX_FAIL;
                }
                else
                {
                    ex.status = XS_OK;
                    last_ok_ms = uwb_port_millis();

                    if (verify == 0U)
                    {
                        /* Once per trial: check the fast CIR read against the driver's own. */
                        verify = uwb_radio_verify_cir(raw, uwb_app_cir_buf(1), cir_start, cir_len);
                    }
                }
            }
        }

        /* ---- Responder not there yet: keep calling quietly. ----
         * Until the first answer of this trial, an unanswered poll is not an
         * exchange: it is not numbered, not reported and does not count towards
         * the idle timeout. So it does not matter which board is started first. */
        if ((contact == 0U) && (ex.status == XS_NO_RESPONSE))
        {
            xid--;
            attempts--;
            end.n_timeout--;
            last_ok_ms = uwb_port_millis();
            uint32_t retry_ms = uwb_port_millis() + 20U;
            while ((int32_t)(retry_ms - uwb_port_millis()) > 0)
            {
                if (uwb_app_service_host())
                {
                    reason = END_HOST_STOP;
                    running = 0;
                    break;
                }
            }
            continue;
        }

        /* ---- 4. report to the PC ---- */
        if (have_cir && ((ex.status == XS_OK) || (cmd->flags & START_FLAG_DUMP_FAILED)))
        {
            dump_us = uwb_radio_send_cir(&hdr, raw);
            ex.n_cir = 1;
        }
        ex.completed = completed;
        ex.t_ms = uwb_port_millis();
        uwb_host_send(PKT_EXCHANGE, &ex, sizeof(ex));

        if (ex.status == XS_PEER_DONE)
        {
            reason = END_DONE;
            break;
        }
        if (ex.status == XS_PEER_STOP)
        {
            reason = END_PEER_STOP;
            break;
        }

        /* ---- 5. wait for the next slot ---- */
        uint32_t wait_until_ms;
        if (cmd->interval_ms != 0U)
        {
            wait_until_ms = cycle_ms + cmd->interval_ms;
        }
        else if (ex.status == XS_OK)
        {
            /* The responder still has to read the final CIR and has two CIRs to
             * send where we had one: give it our own send time again, plus the
             * read time and a margin. If it is still busy the poll is simply
             * missed and repeated 10 ms later. */
            wait_until_ms = uwb_port_millis() + (dump_us + dump_us / 7U + 2U * cir_read_us) / 1000U + 5U;
        }
        else
        {
            wait_until_ms = uwb_port_millis() + 10U;
        }
        while ((int32_t)(wait_until_ms - uwb_port_millis()) > 0)
        {
            if (uwb_app_service_host())
            {
                reason = END_HOST_STOP;
                running = 0;
                break;
            }
        }
    }

    /* ---- end of trial ---- */
    if ((reason == END_HOST_STOP) || (reason == END_IDLE_TIMEOUT))
    {
        send_end_frames(cmd->trial_id, reason);
    }
    uwb_radio_idle();

    end.role = ROLE_INITIATOR;
    end.trial_id = cmd->trial_id;
    end.reason = reason;
    end.attempts = attempts;
    end.completed = completed;
    end.n_rx_error = stats.n_rx_error;
    end.n_foreign = stats.n_foreign;
    end.cir_verify = verify;
    end.resp_delay_10us = resp_delay;
    end.final_delay_10us = final_delay;
    uwb_host_send(PKT_TRIAL_END, &end, sizeof(end));
}
