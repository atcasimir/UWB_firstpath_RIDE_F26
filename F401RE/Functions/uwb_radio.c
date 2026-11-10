/*
 * uwb_radio.c - DW3000 helpers shared by the initiator and the responder.
 */
#include "uwb_radio.h"

#include "uwb_host.h"
#include "uwb_port.h"

#include <deca_device_api.h>
#include <string.h>

uwb_radio_info_t uwb_radio;

/* ------------------------------------------------------------------ helpers */

uint32_t uwb_radio_elapsed_us(uint32_t t0)
{
    return (uwb_port_cycles() - t0) / uwb_port_cycles_per_us();
}

static int valid_preamble_len(uint16_t n)
{
    switch (n)
    {
    case 32: case 64: case 72: case 128: case 256: case 512: case 1024: case 1536: case 2048: case 4096:
        return 1;
    default:
        return 0;
    }
}

static int pac_to_enum(uint8_t pac, dwt_pac_size_e *out)
{
    switch (pac)
    {
    case 4:  *out = DWT_PAC4;  return 1;
    case 8:  *out = DWT_PAC8;  return 1;
    case 16: *out = DWT_PAC16; return 1;
    case 32: *out = DWT_PAC32; return 1;
    default: return 0;
    }
}

uint32_t uwb_radio_data_us(uint16_t frame_len)
{
    /* PHR (19 bits at 850 kb/s) is about 22 us. The payload carries 48 Reed-Solomon
     * parity bits for every 330 data bits (or part thereof). */
    uint32_t bits = (uint32_t)frame_len * 8U;
    bits += 48U * ((bits + 329U) / 330U);
    uint32_t ns_per_bit = (uwb_radio.cfg.data_rate == 0U) ? 1026U : 129U;
    return 22U + (bits * ns_per_bit + 999U) / 1000U;
}

uint16_t uwb_radio_auto_delay_10us(uint32_t cir_read_us)
{
    /* CIR read (+30 %), the other SPI traffic between RX and TX (about 1 ms on an
     * unoptimised F401 build, 2 ms allowed), and the preamble that has to go out
     * before the timestamped instant. Rounded up to 100 us. */
    uint32_t us = cir_read_us + (cir_read_us * 3U) / 10U + 2000U + uwb_radio.shr_us;
    uint32_t d = (us + 99U) / 100U * 10U;
    if (d > UWB_MAX_DELAY_10US)
    {
        d = UWB_MAX_DELAY_10US;
    }
    return (uint16_t)d;
}

/* -------------------------------------------------------------------- start */

uint8_t uwb_radio_start(const uwb_radio_cfg_t *requested)
{
    uwb_radio_cfg_t c = *requested;
    dwt_pac_size_e pac;

    if (((c.chan != 5U) && (c.chan != 9U)) || !valid_preamble_len(c.preamble_len) || !pac_to_enum(c.pac, &pac) ||
        (c.tx_code < 1U) || (c.tx_code > 29U) || (c.rx_code < 1U) || (c.rx_code > 29U) || (c.sfd_type > 3U) ||
        (c.data_rate > 1U))
    {
        return ACK_BAD_PARAM;
    }

    uint16_t sfd_len = (c.sfd_type == (uint8_t)DWT_SFD_DW_16) ? 16U : 8U;
    if (c.sfd_timeout == 0U)
    {
        c.sfd_timeout = (uint16_t)(c.preamble_len + 1U + sfd_len - c.pac);
    }
    if (c.pg_delay == 0U)
    {
        c.pg_delay = 0x34U;
    }
    if (c.tx_power == 0UL)
    {
        c.tx_power = (c.chan == 5U) ? 0xfdfdfdfdUL : 0xfefefefeUL;
    }

    memset(&uwb_radio, 0, sizeof(uwb_radio));
    uwb_radio.cfg = c;
    uwb_radio.cir_samples = (c.rx_code >= PCODE_PRF64_START) ? DWT_CIR_LEN_IP_PRF64 : DWT_CIR_LEN_IP_PRF16;
    /* One preamble symbol is 1017.6 ns at 64 MHz PRF (993.6 ns at 16 MHz). */
    uwb_radio.shr_us = (uint16_t)(((uint32_t)(c.preamble_len + sfd_len) * 1018U) / 1000U + 1U);

    if (uwb_port_radio_reset_and_probe() != 0)
    {
        return ACK_RADIO_PROBE;
    }

    uint32_t t0 = uwb_port_millis();
    while (!dwt_checkidlerc())
    {
        if ((uwb_port_millis() - t0) > 200U)
        {
            return ACK_RADIO_INIT;
        }
    }

    if (dwt_initialise(DWT_READ_OTP_ALL) == (int32_t)DWT_ERROR)
    {
        return ACK_RADIO_INIT;
    }

    dwt_config_t config = {
        .chan = c.chan,
        .txPreambLength = c.preamble_len,
        .rxPAC = pac,
        .txCode = c.tx_code,
        .rxCode = c.rx_code,
        .sfdType = (dwt_sfd_type_e)c.sfd_type,
        .dataRate = (c.data_rate == 0U) ? DWT_BR_850K : DWT_BR_6M8,
        .phrMode = DWT_PHRMODE_STD,
        .phrRate = DWT_PHRRATE_STD,
        .sfdTO = c.sfd_timeout,
        .stsMode = DWT_STS_MODE_OFF,
        .stsLength = DWT_STS_LEN_64,
        .pdoaMode = DWT_PDOA_M0,
    };
    if (dwt_configure(&config) != (int32_t)DWT_SUCCESS)
    {
        return ACK_RADIO_CONFIG;
    }

    dwt_txconfig_t txconfig = { .PGdly = c.pg_delay, .power = c.tx_power, .PGcount = 0 };
    dwt_configuretxrf(&txconfig);

    dwt_setrxantennadelay(c.rx_ant_dly);
    dwt_settxantennadelay(c.tx_ant_dly);

    /* TX/RX state outputs on GPIO5/6, as in the Qorvo examples. */
    dwt_setlnapamode((int32_t)DWT_LNA_ENABLE | (int32_t)DWT_PA_ENABLE);

    /* Full CIA diagnostics (first path, peak, F1..F3, power, symbol count). */
    dwt_configciadiag((uint8_t)DW_CIA_DIAG_LOG_ALL);

    /* All deadlines are kept by the MCU, so the chip's own RX timeouts stay off. */
    dwt_setrxtimeout(0);
    dwt_setpreambledetecttimeout(0);

    uwb_radio.dev_id = dwt_readdevid();
    uwb_radio.part_id = dwt_getpartid();
    uint64_t lot = dwt_getlotid();
    memcpy(uwb_radio.lot_id, &lot, sizeof(uwb_radio.lot_id));

    uint16_t tv = dwt_readtempvbat(); /* high byte temperature, low byte supply voltage */
    uwb_radio.temp_c_x100 = (int16_t)(dwt_convertrawtemperature((uint8_t)(tv >> 8)) * 100.0f);
    uwb_radio.vbat_mv = (uint16_t)(dwt_convertrawvoltage((uint8_t)(tv & 0xFFU)) * 1000.0f);

    return ACK_OK;
}

void uwb_radio_idle(void)
{
    dwt_forcetrxoff();
}

/* ------------------------------------------------------------------- frames */

uint16_t uwb_radio_make_header(uint8_t *frame, uint8_t function, uint8_t from_initiator)
{
    static uint8_t seq;

    frame[0] = 0x41U; /* frame control: data frame, 16-bit addresses */
    frame[1] = 0x88U;
    frame[2] = seq++;
    frame[3] = 0xCAU; /* PAN ID 0xDECA */
    frame[4] = 0xDEU;
    if (from_initiator)
    {
        frame[5] = 'W'; frame[6] = 'A'; /* destination: responder */
        frame[7] = 'V'; frame[8] = 'E'; /* source: initiator      */
    }
    else
    {
        frame[5] = 'V'; frame[6] = 'E';
        frame[7] = 'W'; frame[8] = 'A';
    }
    frame[9] = function;
    return AIR_HDR_LEN;
}

static int header_matches(const uint8_t *frame, uint8_t from_initiator)
{
    if ((frame[0] != 0x41U) || (frame[1] != 0x88U) || (frame[3] != 0xCAU) || (frame[4] != 0xDEU))
    {
        return 0;
    }
    if (from_initiator)
    {
        return (frame[5] == 'W') && (frame[6] == 'A') && (frame[7] == 'V') && (frame[8] == 'E');
    }
    return (frame[5] == 'V') && (frame[6] == 'E') && (frame[7] == 'W') && (frame[8] == 'A');
}

int uwb_radio_tx(const uint8_t *frame, uint16_t len, uint8_t mode)
{
    dwt_writetxdata(len, (uint8_t *)frame, 0);
    dwt_writetxfctrl((uint16_t)(len + AIR_FCS_LEN), 0, 1); /* ranging bit set */
    return (dwt_starttx(mode) == (int32_t)DWT_SUCCESS) ? 0 : -1;
}

int uwb_radio_wait_tx_done(uint32_t timeout_us)
{
    uint32_t t0 = uwb_port_cycles();

    while ((dwt_readsysstatuslo() & (uint32_t)DWT_INT_TXFRS_BIT_MASK) == 0UL)
    {
        if (uwb_radio_elapsed_us(t0) > timeout_us)
        {
            dwt_forcetrxoff();
            return -1;
        }
    }
    dwt_writesysstatuslo((uint32_t)DWT_INT_TXFRS_BIT_MASK);
    return 0;
}

int uwb_radio_wait_frame(uint8_t fn_a, uint8_t fn_b, uint8_t from_initiator, uint8_t *fn_out, uint8_t *payload,
                         uint16_t max_payload, uint32_t t0, uint32_t window_us, int (*poll_host)(void),
                         uwb_radio_stats_t *stats)
{
    uint8_t frame[AIR_MAX_FRAME];

    for (;;)
    {
        uint32_t status = dwt_readsysstatuslo();

        if (status & (uint32_t)DWT_INT_RXFCG_BIT_MASK)
        {
            uint8_t rng = 0;
            dwt_writesysstatuslo((uint32_t)DWT_INT_RXFCG_BIT_MASK | (uint32_t)DWT_INT_TXFRS_BIT_MASK);

            uint16_t frame_len = dwt_getframelength(&rng);
            if ((frame_len >= (AIR_HDR_LEN + AIR_FCS_LEN)) && (frame_len <= sizeof(frame)))
            {
                dwt_readrxdata(frame, (uint16_t)(frame_len - AIR_FCS_LEN), 0);
                uint16_t payload_len = (uint16_t)(frame_len - AIR_HDR_LEN - AIR_FCS_LEN);

                if (header_matches(frame, from_initiator) && ((frame[9] == fn_a) || ((fn_b != 0U) && (frame[9] == fn_b))) &&
                    (payload_len <= max_payload))
                {
                    memcpy(payload, &frame[AIR_HDR_LEN], payload_len);
                    if (fn_out != NULL)
                    {
                        *fn_out = frame[9];
                    }
                    return (int)payload_len; /* receiver is off; accumulator and diagnostics are valid */
                }
            }
            stats->n_foreign++;
        }
        else if (status & (SYS_STATUS_ALL_RX_ERR | SYS_STATUS_ALL_RX_TO))
        {
            dwt_writesysstatuslo(SYS_STATUS_ALL_RX_ERR | SYS_STATUS_ALL_RX_TO);
            stats->n_rx_error++;
        }
        else
        {
            /* Nothing yet. */
            if ((window_us != 0U) && (uwb_radio_elapsed_us(t0) > window_us))
            {
                stats->last_status = status;
                dwt_forcetrxoff();
                return -1;
            }
            if ((poll_host != NULL) && (poll_host() != 0))
            {
                dwt_forcetrxoff();
                return -2;
            }
            continue;
        }

        /* A frame we do not want, or a PHY error: listen again if there is time left. */
        if ((window_us != 0U) && (uwb_radio_elapsed_us(t0) > window_us))
        {
            stats->last_status = status;
            dwt_forcetrxoff();
            return -1;
        }
        dwt_rxenable((int32_t)DWT_START_RX_IMMEDIATE);
    }
}

/* --------------------------------------------------------------- timestamps */

static uint64_t bytes_to_stamp(const uint8_t b[5])
{
    uint64_t v = 0;
    for (int i = 4; i >= 0; i--)
    {
        v = (v << 8) | b[i];
    }
    return v;
}

void uwb_radio_stamp_to_bytes(uint64_t stamp, uint8_t out[5])
{
    for (int i = 0; i < 5; i++)
    {
        out[i] = (uint8_t)(stamp >> (8 * i));
    }
}

uint64_t uwb_radio_tx_stamp(void)
{
    uint8_t b[5];
    dwt_readtxtimestamp(b);
    return bytes_to_stamp(b);
}

uint64_t uwb_radio_rx_stamp(void)
{
    uint8_t b[5];
    dwt_readrxtimestamp(b, DWT_COMPAT_NONE);
    return bytes_to_stamp(b);
}

/* ---------------------------------------------------------------------- CIR */

uint32_t uwb_radio_read_cir(uint8_t *raw, uint16_t start, uint16_t n)
{
    uint32_t t0 = uwb_port_cycles();

    /* One SPI transaction for the whole window. The driver's dwt_readcir() does the
     * same job in 16-sample chunks with two extra register writes per chunk, which
     * takes about twice as long. raw[0] receives the DW3000's dummy byte. */
    dwt_readaccdata(raw, (uint16_t)(1U + 6U * n), start);

    return uwb_radio_elapsed_us(t0);
}

void uwb_radio_capture(uwb_cir_hdr_t *hdr, uint8_t *raw, uint16_t start, uint16_t n)
{
    dwt_rxdiag_t diag;

    memset(&diag, 0, sizeof(diag));
    dwt_readdiagnostics(&diag);

    hdr->acc = 0;
    hdr->cir_start = start;
    hdr->cir_len = n;
    dwt_readrxtimestamp(hdr->rx_stamp, DWT_COMPAT_NONE);
    memcpy(hdr->ip_toa, diag.ipatovRxTime, 5);
    hdr->ip_status = diag.ipatovRxStatus;
    hdr->ip_poa = diag.ipatovPOA;
    hdr->ip_peak = diag.ipatovPeak;
    hdr->ip_power = diag.ipatovPower;
    hdr->ip_f1 = diag.ipatovF1;
    hdr->ip_f2 = diag.ipatovF2;
    hdr->ip_f3 = diag.ipatovF3;
    hdr->ip_fp_index = diag.ipatovFpIndex;
    hdr->ip_accum = diag.ipatovAccumCount;
    hdr->xtal_offset = diag.xtalOffset;
    hdr->cia_diag1 = diag.ciaDiag1;
    hdr->clock_offset = dwt_readclockoffset();
    hdr->dgc_decision = dwt_get_dgcdecision();

    hdr->read_us = uwb_radio_read_cir(raw, start, n);
}

uint8_t uwb_radio_verify_cir(const uint8_t *raw, uint8_t *scratch, uint16_t start, uint16_t n)
{
    if (dwt_readcir((uint32_t *)(void *)scratch, DWT_ACC_IDX_IP_M, start, n, DWT_CIR_READ_FULL) != (int)DWT_SUCCESS)
    {
        return 2;
    }
    return (memcmp(&raw[1], scratch, 6U * (uint32_t)n) == 0) ? 1U : 2U;
}

uint32_t uwb_radio_send_cir(const uwb_cir_hdr_t *hdr, const uint8_t *raw)
{
    uint32_t t0 = uwb_port_cycles();
    uwb_host_send2(PKT_CIR, hdr, sizeof(*hdr), &raw[1], (uint16_t)(6U * hdr->cir_len));
    return uwb_radio_elapsed_us(t0);
}
