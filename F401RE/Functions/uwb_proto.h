/*
 * uwb_proto.h - shared definitions for the 3-CIR DS-TWR capture firmware.
 *
 * Two protocols are defined here:
 *   1. HOST LINK  : binary packets between the board and the PC (UART / ST-LINK VCP).
 *   2. AIR FRAMES : the UWB frames exchanged between initiator and responder.
 *
 * The Python tool (python/uwb_tool.py) mirrors the host-link structures.
 * If you change a structure here, change it there too and bump UWB_PROTO_VERSION.
 *
 * All multi-byte fields are little-endian. All structures are packed.
 */
#ifndef UWB_PROTO_H
#define UWB_PROTO_H

#include <stdint.h>

#define UWB_FW_VERSION    0x0103U /* 1.3 */
#define UWB_PROTO_VERSION 1U

#define UWB_PACKED __attribute__((packed))

/* ------------------------------------------------------------------------- */
/* HOST LINK                                                                 */
/* ------------------------------------------------------------------------- */
/*
 * Packet layout (both directions):
 *
 *   0xA5 0x5A | type (1) | length (2) | payload (length) | crc16 (2)
 *
 * crc16 = CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over type, length, payload.
 */
#define UWB_SYNC0 0xA5U
#define UWB_SYNC1 0x5AU

#define UWB_BOOT_BAUD 115200UL /* baud after reset; the PC can raise it with CMD_SET_BAUD */

/* Board -> PC */
#define PKT_INFO        0x01U /* uwb_info_t        : reply to CMD_PING, also sent once at boot  */
#define PKT_ACK         0x02U /* uwb_ack_t         : reply to every other command               */
#define PKT_LOG         0x03U /* ASCII text, no terminator                                      */
#define PKT_TRIAL_BEGIN 0x10U /* uwb_trial_begin_t : a trial has started on this board          */
#define PKT_TRIAL_END   0x11U /* uwb_trial_end_t   : the trial is over, board is idle again     */
#define PKT_CIR         0x20U /* uwb_cir_hdr_t + cir_len * 6 bytes of raw accumulator data      */
#define PKT_EXCHANGE    0x21U /* uwb_exchange_t    : closes one ranging exchange                */

/* PC -> board */
#define CMD_PING     0x80U /* no payload                */
#define CMD_SET_BAUD 0x81U /* uint32_t baud             */
#define CMD_START    0x82U /* uwb_cmd_start_t           */
#define CMD_STOP     0x83U /* no payload                */

/* uwb_ack_t.status */
#define ACK_OK           0U
#define ACK_BAD_PARAM    1U
#define ACK_BUSY         2U
#define ACK_RADIO_PROBE  3U /* dwt_probe failed: is the shield seated?            */
#define ACK_RADIO_INIT   4U /* dwt_initialise / IDLE_RC failed                    */
#define ACK_RADIO_CONFIG 5U /* dwt_configure failed (PLL or RX calibration)       */
#define ACK_UNKNOWN_CMD  6U

/* Board states (uwb_info_t.state) */
#define ST_IDLE      0U
#define ST_INITIATOR 1U
#define ST_RESPONDER 2U

/* Roles */
#define ROLE_INITIATOR 1U
#define ROLE_RESPONDER 2U

/* Which message a CIR belongs to (uwb_cir_hdr_t.kind) */
#define CIR_POLL     0U /* captured by the responder */
#define CIR_RESPONSE 1U /* captured by the initiator */
#define CIR_FINAL    2U /* captured by the responder */

/* uwb_cmd_start_t.flags */
#define START_FLAG_DUMP_FAILED 0x01U /* also send the CIRs of exchanges that did not complete */

/* uwb_exchange_t.status */
#define XS_OK          0U
#define XS_NO_RESPONSE 1U /* initiator: no response frame before the deadline          */
#define XS_NO_FINAL    2U /* responder: no final frame before the deadline             */
#define XS_LATE_TX     3U /* delayed TX was issued too late: reply delay is too short  */
#define XS_TX_FAIL     4U /* TX-done event never arrived                               */
#define XS_PEER_DONE   5U /* initiator: responder says the target count is reached     */
#define XS_PEER_STOP   6U /* initiator: responder asked to stop                        */
#define XS_PEER_LATE   7U /* initiator: responder could not reply in time (delay raised) */

/* uwb_trial_end_t.reason */
#define END_DONE         0U /* target count reached                           */
#define END_HOST_STOP    1U /* stopped from this board's PC                   */
#define END_PEER_STOP    2U /* stopped from the other board's PC              */
#define END_IDLE_TIMEOUT 3U /* no completed exchange for idle_timeout_s       */
#define END_RADIO_ERROR  4U

/* Radio configuration. Human-readable values; the firmware maps them to driver enums. */
typedef struct UWB_PACKED
{
    uint8_t  chan;         /* 5 or 9                                          */
    uint16_t preamble_len; /* 32, 64, 128, 256, 512, 1024, 1536, 2048, 4096   */
    uint8_t  pac;          /* 4, 8, 16, 32                                    */
    uint8_t  tx_code;      /* preamble code, 9..12 for 64 MHz PRF             */
    uint8_t  rx_code;
    uint8_t  sfd_type;     /* 0 IEEE 4a, 1 DW 8, 2 DW 16, 3 IEEE 4z           */
    uint8_t  data_rate;    /* 0 = 850 kb/s, 1 = 6.8 Mb/s                      */
    uint16_t sfd_timeout;  /* symbols, 0 = preamble_len + 1 + sfd - pac       */
    uint8_t  pg_delay;     /* 0 = 0x34                                        */
    uint32_t tx_power;     /* 0 = 0xfdfdfdfd (ch5) / 0xfefefefe (ch9)         */
    uint16_t tx_ant_dly;   /* device time units (15.65 ps)                    */
    uint16_t rx_ant_dly;
} uwb_radio_cfg_t;

typedef struct UWB_PACKED
{
    uint8_t  role;             /* ROLE_INITIATOR or ROLE_RESPONDER                             */
    uint8_t  flags;            /* START_FLAG_*                                                 */
    uint32_t trial_id;         /* initiator only: random ID chosen by the PC                   */
    uint16_t target_count;     /* initiator only: completed exchanges wanted, 0 = until stop   */
    uint16_t interval_ms;      /* initiator only: poll period, 0 = as fast as the link allows  */
    uint16_t cir_start;        /* initiator only: first accumulator sample to read             */
    uint16_t cir_len;          /* initiator only: number of samples, 0 = whole CIR             */
    uint16_t resp_delay_10us;  /* initiator only: poll RX -> response TX, 0 = automatic        */
    uint16_t final_delay_10us; /* initiator only: response RX -> final TX, 0 = automatic       */
    uint16_t idle_timeout_s;   /* end the trial after this long without a completed exchange,  */
                               /* 0 = never                                                    */
    uwb_radio_cfg_t radio;
} uwb_cmd_start_t;

typedef struct UWB_PACKED
{
    uint16_t fw_version;
    uint8_t  proto_version;
    uint8_t  state;       /* ST_*                              */
    uint32_t baud;
    uint32_t uptime_ms;
    uint16_t max_cir_len; /* samples in a full Ipatov CIR      */
} uwb_info_t;

typedef struct UWB_PACKED
{
    uint8_t cmd;
    uint8_t status; /* ACK_* */
} uwb_ack_t;

typedef struct UWB_PACKED
{
    uint8_t  role;
    uint32_t trial_id;
    uint16_t target_count;
    uint16_t interval_ms;
    uint16_t cir_start;
    uint16_t cir_len;
    uint16_t resp_delay_10us;
    uint16_t final_delay_10us;
    uint32_t cir_read_us;  /* measured time to read one CIR of cir_len samples over SPI */
    uint32_t dev_id;
    uint32_t part_id;
    uint8_t  lot_id[8];
    int16_t  temp_c_x100;  /* chip temperature at trial start */
    uint16_t vbat_mv;
    uwb_radio_cfg_t radio; /* as applied (defaults filled in) */
} uwb_trial_begin_t;

typedef struct UWB_PACKED
{
    uint8_t  role;
    uint32_t trial_id;
    uint8_t  reason;      /* END_*                                                        */
    uint32_t attempts;    /* initiator: polls sent. responder: polls received             */
    uint32_t completed;   /* exchanges completed (as counted by the responder)            */
    uint16_t n_timeout;   /* expected frame did not arrive                                */
    uint16_t n_late_tx;   /* delayed TX issued too late                                   */
    uint16_t n_rx_error;  /* PHY errors seen while listening (CRC, PHR, SFD timeout, ...) */
    uint16_t n_foreign;   /* good frames that were not part of this exchange              */
    uint8_t  cir_verify;  /* 0 not run, 1 fast read == dwt_readcir, 2 mismatch            */
    uint16_t resp_delay_10us;  /* final values (auto mode may have raised them)           */
    uint16_t final_delay_10us;
} uwb_trial_end_t;

/* One received frame: diagnostics followed by cir_len * 6 bytes (I lo,mid,hi, Q lo,mid,hi). */
typedef struct UWB_PACKED
{
    uint32_t trial_id;
    uint32_t xid;          /* exchange number inside the trial, starts at 1   */
    uint8_t  kind;         /* CIR_POLL / CIR_RESPONSE / CIR_FINAL             */
    uint8_t  acc;          /* 0 = Ipatov preamble CIR                         */
    uint16_t cir_start;
    uint16_t cir_len;
    uint32_t read_us;      /* SPI time spent reading this CIR                 */
    uint8_t  rx_stamp[5];  /* RX timestamp used for ranging (40-bit)          */
    uint8_t  ip_toa[5];    /* Ipatov time of arrival (40-bit)                 */
    uint8_t  ip_status;    /* IP_TOAST flags                                  */
    uint16_t ip_poa;
    uint32_t ip_peak;      /* IP_DIAG_0: index [30:21], amplitude [20:0]      */
    uint32_t ip_power;     /* IP_DIAG_1: channel area                         */
    uint32_t ip_f1;
    uint32_t ip_f2;
    uint32_t ip_f3;
    uint16_t ip_fp_index;  /* 10.6 fixed point                                */
    uint16_t ip_accum;     /* preamble symbols accumulated                    */
    int16_t  xtal_offset;  /* from dwt_readdiagnostics (raw)                  */
    int16_t  clock_offset; /* dwt_readclockoffset(): ppm = v / 2^26 * 1e6     */
    uint8_t  dgc_decision; /* 0..7, needed for the dBm formulas               */
    uint32_t cia_diag1;
} uwb_cir_hdr_t;

typedef struct UWB_PACKED
{
    uint32_t trial_id;
    uint32_t xid;
    uint8_t  role;
    uint8_t  status;           /* XS_*                                                        */
    uint8_t  peer_flags;       /* initiator: flags byte of the response frame                 */
    uint8_t  n_cir;            /* CIR packets sent for this exchange, just before this packet */
    uint16_t completed;        /* completed exchanges so far (responder's count)              */
    uint32_t t_ms;             /* board uptime                                                */
    uint32_t proc_us;          /* frame received -> reply scheduled (must stay below delay)   */
    uint16_t resp_delay_10us;
    uint16_t final_delay_10us;
    /* 40-bit device timestamps taken by this board.
     *   initiator: ts[0] poll TX, ts[1] response RX, ts[2] final TX
     *   responder: ts[0] poll RX, ts[1] response TX, ts[2] final RX                          */
    uint8_t  ts[3][5];
    /* responder only: the initiator's three timestamps (low 32 bits) from the final frame    */
    uint32_t peer_ts[3];
    double   tof_dtu;          /* responder only: time of flight in device time units         */
    uint32_t sys_status;       /* SYS_STATUS low word when the exchange ended                 */
} uwb_exchange_t;

/* ------------------------------------------------------------------------- */
/* AIR FRAMES                                                                */
/* ------------------------------------------------------------------------- */
/*
 * Same 802.15.4 data-frame header as the Qorvo DS-TWR examples:
 *   bytes 0-1 frame control 0x8841, byte 2 sequence number, bytes 3-4 PAN 0xDECA,
 *   bytes 5-6 destination, bytes 7-8 source, byte 9 function code.
 * The function codes differ from the Qorvo examples on purpose, so a board running
 * the stock example is ignored instead of half-understood.
 */
#define AIR_HDR_LEN 10U
#define AIR_FCS_LEN 2U

#define AIR_FN_POLL  0x31U
#define AIR_FN_RESP  0x32U
#define AIR_FN_FINAL 0x33U
#define AIR_FN_END   0x34U

typedef struct UWB_PACKED
{
    uint32_t trial_id;
    uint32_t xid;
    uint16_t target_count;
    uint8_t  flags; /* START_FLAG_* */
    uint16_t cir_start;
    uint16_t cir_len;
    uint16_t resp_delay_10us;
    uint16_t final_delay_10us;
} air_poll_t;

#define AIR_RESP_STOP 0x01U /* responder's PC asked to stop                       */
#define AIR_RESP_DONE 0x02U /* responder has completed target_count exchanges     */
#define AIR_RESP_LATE 0x04U /* responder was too late to reply to THIS poll: sent
                             * at once instead, no ranging, see need_delay_10us */

typedef struct UWB_PACKED
{
    uint32_t trial_id;
    uint32_t xid;
    uint8_t  flags;     /* AIR_RESP_* */
    uint16_t completed;
    uint16_t need_delay_10us; /* with AIR_RESP_LATE: reply delay this board needs, else 0 */
} air_resp_t;

typedef struct UWB_PACKED
{
    uint32_t trial_id;
    uint32_t xid;
    uint32_t poll_tx_ts;
    uint32_t resp_rx_ts;
    uint32_t final_tx_ts;
} air_final_t;

typedef struct UWB_PACKED
{
    uint32_t trial_id;
    uint8_t  reason; /* END_* */
} air_end_t;

#define AIR_MAX_FRAME (AIR_HDR_LEN + sizeof(air_final_t) + AIR_FCS_LEN)

/* Reply delays above this would overflow the 32-bit timestamp arithmetic (67 ms). */
#define UWB_MAX_DELAY_10US 6000U

/* The Python tool unpacks these by size: catch accidental layout changes at compile time. */
_Static_assert(sizeof(uwb_radio_cfg_t) == 19, "uwb_radio_cfg_t");
_Static_assert(sizeof(uwb_cmd_start_t) == 39, "uwb_cmd_start_t");
_Static_assert(sizeof(uwb_info_t) == 14, "uwb_info_t");
_Static_assert(sizeof(uwb_trial_begin_t) == 60, "uwb_trial_begin_t");
_Static_assert(sizeof(uwb_trial_end_t) == 27, "uwb_trial_end_t");
_Static_assert(sizeof(uwb_cir_hdr_t) == 64, "uwb_cir_hdr_t");
_Static_assert(sizeof(uwb_exchange_t) == 65, "uwb_exchange_t");

#endif /* UWB_PROTO_H */
