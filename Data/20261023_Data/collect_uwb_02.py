"""Collect and analyze Qorvo DW3110 simple_rx_cir UART output.

Requires: pip install pyserial numpy matplotlib
The current STM32 firmware collects its own fixed number of frames; this script
only listens, records, saves and plots. Set NUM_MEASUREMENTS to match firmware.
"""

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import serial

PORT = "COM4"                  # Change to your STM32 COM port
BAUD_RATE = 115200             # Match firmware UART configuration
NUM_MEASUREMENTS = 1000          # Match STM32's measurement limit
READ_TIMEOUT = 1               # Serial read timeout in seconds
DWT_TICK_NS = 1e9 / (499.2e6 * 128)  # DW3110 device-time unit
TIMESTAMP_MODULUS = 1 << 40

# Fixed amplitude scale for EVERY image, including across separate collections.
# Increase this if your CIR peaks exceed the limit (clipped traces are warned about).
PLOT_Y_MAX = 5000
PLOT_DPI = 300

# IP_TOAST flags: DW3000 User Manual v1.1, page 180, bits [28:24].
RX_STATUS_FLAGS = {
    0: "No strong first-path rising edge (noise sensitive)",
    1: "Noise threshold artificially lowered",
    2: "CIR too weak for an estimate",
    3: "Coarse first path implausibly close to CIR end",
    4: "First path implausibly close to CIR end",
}


# Exact order used by print_rx_diag() in the uploaded C file.
DIAG_FIELDS = (
    "rx_time_0", "rx_time_1", "rx_time_2", "rx_time_3", "rx_time_4",
    "ipatovRxStatus", "ipatovPeak", "ipatovPower", "ipatovF1",
    "ipatovF2", "ipatovF3", "ipatovFpIndex",
)


def parse_diagnostics(text):
    values = [int(x) for x in re.findall(r"\d+", text)]
    if len(values) != len(DIAG_FIELDS):
        raise ValueError(f"Expected {len(DIAG_FIELDS)} diagnostics, got {len(values)}")
    record = dict(zip(DIAG_FIELDS, values))
    octets = bytes(record[f"rx_time_{i}"] for i in range(5))
    record["ipatovRxTime40"] = int.from_bytes(octets, "little")
    record["fp_index_samples"] = record["ipatovFpIndex"] / 64.0
    record["rx_timestamp_ns"] = record["ipatovRxTime40"] * DWT_TICK_NS

    # IP_TOAST: the low five bits are confidence warnings. Preserve all 8 bits.
    status = record["ipatovRxStatus"]
    record["rx_status_hex"] = f"0x{status:02X}"
    record["rx_status_warnings"] = [
        description for bit, description in RX_STATUS_FLAGS.items()
        if status & (1 << bit)
    ]
    record["rx_timestamp_reliable"] = (status & 0x1F) == 0

    # IP_DIAG_0, manual page 185: bits [20:0] peak amplitude,
    # bits [30:21] index of maximum-amplitude CIR sample; bit 31 reserved.
    peak = record["ipatovPeak"]
    # Qorvo: IP_PEAKA is a 21-bit Q*.2 amplitude (divide raw bits by 4).
    # Preserve both the extracted raw amplitude and the physical plotting scale.
    record["peak_amplitude_raw"] = peak & ((1 << 21) - 1)
    record["peak_amplitude"] = record["peak_amplitude_raw"] / 4.0
    record["peak_index_samples"] = (peak >> 21) & ((1 << 10) - 1)

    # IP_DIAG_1, page 185: channel area, not an amplitude sample.
    # Do NOT divide by four or treat this as a dBm reading.
    record["channel_area"] = record["ipatovPower"] & ((1 << 17) - 1)

    # IP_DIAG_2 through IP_DIAG_4, pages 186-187: 22-bit
    # magnitudes with 2 fractional bits (manual pages 47-48).
    # This conversion does NOT imply exact equality to np.hypot(raw_I, raw_Q).
    for name in ("ipatovF1", "ipatovF2", "ipatovF3"):
        record[name + "_magnitude"] = (record[name] & ((1 << 22) - 1)) / 4.0

    # FP location in 10.6 fixed point is an accumulator index, NOT
    # a propagation time or correction to the adjusted RX timestamp.
    return record


def parse_cir(text):
    # The firmware prints I,Q,I,Q,... with a trailing comma.
    values = [int(x) for x in re.findall(r"[-+]?\d+", text)]
    if len(values) < 2 or len(values) % 2:
        raise ValueError(f"Invalid CIR integer count: {len(values)}")
    return np.asarray(values[::2], dtype=np.float64) + 1j * np.asarray(
        values[1::2], dtype=np.float64
    )


def collect():
    records = []
    state = "waiting"
    diag_text = ""
    cir_text = ""
    range_text = ""
    pending_diag = None
    # Markers may arrive immediately adjacent to data without newlines.
    markers = ("RX DIAG BEGIN", "RX DIAG END", "CIR BEGIN", "CIR END", "RANGE BEGIN", "RANG END")
    stream = ""

    print(f"Listening on {PORT} at {BAUD_RATE} baud; target: {NUM_MEASUREMENTS}")
    print("Start/reset the STM32 if necessary. Press Ctrl+C to stop early.\n")

    with serial.Serial(PORT, BAUD_RATE, timeout=READ_TIMEOUT) as ser:
        try:
            while len(records) < NUM_MEASUREMENTS:
                chunk = ser.read(ser.in_waiting or 1).decode("ascii", errors="ignore")
                if not chunk:
                    continue
                stream += chunk

                while True:
                    if state == "waiting":
                        pos = stream.find("RX_DIAG_BEGIN")
                        if pos < 0:
                            stream = stream[-(len("RX_DIAG_BEGIN") - 1):]
                            break
                        stream = stream[pos + len("RX_DIAG_BEGIN"):]
                        state = "diagnostics"

                    elif state == "diagnostics":
                        pos = stream.find("RX_DIAG_END")
                        if pos < 0:
                            break
                        diag_text = stream[:pos]
                        stream = stream[pos + len("RX_DIAG_END"):]
                        try:
                            pending_diag = parse_diagnostics(diag_text)
                        except (ValueError, OverflowError) as exc:
                            print(f"Skipping invalid diagnostics: {exc}")
                            pending_diag = None
                        state = "await_cir"

                    elif state == "await_cir":
                        pos = stream.find("CIR BEGIN")
                        if pos < 0:
                            # Recover if a new diagnostics block arrives instead.
                            next_diag = stream.find("RX_DIAG_BEGIN")
                            if next_diag >= 0:
                                stream = stream[next_diag:]
                                state = "waiting"
                                pending_diag = None
                                continue
                            stream = stream[-(max(map(len, markers)) - 1):]
                            break
                        stream = stream[pos + len("CIR BEGIN"):]
                        state = "cir"

                    elif state == "cir":
                        pos = stream.find("CIR END")
                        if pos < 0:
                            break
                        cir_text = stream[:pos]
                        stream = stream[pos + len("CIR END"):]
                        if pending_diag is not None:
                            try:
                                cir = parse_cir(cir_text)
                                records.append((pending_diag, cir))
                                print(f"Collected {len(records)}/{NUM_MEASUREMENTS} "
                                      f"({len(cir)} CIR samples)")
                                print_measurement(pending_diag)
                            except ValueError as exc:
                                print(f"Skipping invalid CIR: {exc}")
                        pending_diag = None
                        state = "waiting"

                    elif state == "await_range":
                        pos = stream.find("RANGE BEGIN")
                        stream = stream[pos + len("RANGE BEGIN"):]
                        state = "range"

                    elif state == "range":
                        pos = stream.find("RANGE END")
                        range_text = stream[:pos]
                        stream = stream[pos + len("RANGE END"):]
                        try:
                             range = parse_diagnostics(diag_text)
                        except (ValueError, OverflowError) as exc:
                            print(f"Skipping invalid range: {exc}")
                            pending_diag = None       
                        state = "waiting"

        except KeyboardInterrupt:
            print("\nCollection interrupted; saving complete records received so far.")

    return records


def print_measurement(d):
    """Readable interpretation of every diagnostic sent by the firmware."""
    print(f"  First-path RX timestamp: {d['ipatovRxTime40']:,} ticks "
          f"= {d['rx_timestamp_ns']:,.3f} ns (device clock)")
    print(f"  RX status: {d['rx_status_hex']} | "
          + ("OK" if d['rx_timestamp_reliable'] else
             "; ".join(d['rx_status_warnings'])))
    print(f"  First-path CIR index: {d['fp_index_samples']:.4f} samples "
          f"(Q10.6 raw={d['ipatovFpIndex']})")
    print(f"  CIR peak: index={d['peak_index_samples']} "
          f"amplitude={d['peak_amplitude']} "
          f"(packed raw={d['ipatovPeak']})")
    print(f"  Channel area: {d['channel_area']} "
          f"(raw={d['ipatovPower']}; not dBm)")
    for j in (1, 2, 3):
        name = f"ipatovF{j}"
        print(f"  FP+{j} magnitude: {d[name + '_magnitude']:.2f} "
              f"(Q20.2 raw={d[name]})")


def save_and_plot(records, output_file):
    if not records:
        print("No complete measurements received.")
        return

    diagnostics = [r[0] for r in records]
    cirs = [r[1] for r in records]
    # Keep raw and interpreted scalar fields. Strings/lists are readable
    # on the console but are not stored as object arrays in the NPZ.
    fields = [k for k, v in diagnostics[0].items()
              if isinstance(v, (int, float, bool))]
    # Keep integers exact, including the 40-bit device timestamp.
    diag_arrays = {
        key: np.array([d[key] for d in diagnostics],
                      dtype=(np.bool_ if isinstance(diagnostics[0][key], bool)
                             else np.int64 if isinstance(diagnostics[0][key], int)
                             else np.float64))
        for key in fields
    }

    # Store raw complex CIRs without requiring pickle/object arrays.
    lengths = np.array([len(cir) for cir in cirs], dtype=np.int32)
    packed_cir = np.concatenate(cirs)
    np.savez_compressed(output_file, cir_data=packed_cir, cir_lengths=lengths,
                        **diag_arrays)
    print(f"\nSaved {len(records)} complete measurements to {output_file.resolve()}")

    print("\nConverted diagnostics:")
    print("  RX timestamps: 40-bit device clock, not time-of-flight")
    ticks = [int(d["ipatovRxTime40"]) for d in diagnostics]
    elapsed_ns = np.array([((t - ticks[0]) % TIMESTAMP_MODULUS) * DWT_TICK_NS
                           for t in ticks])
    print(f"  First RX timestamp: {ticks[0]:,} ticks = {ticks[0] * DWT_TICK_NS:,.3f} ns")
    print(f"  Last RX relative to first: {elapsed_ns[-1]:,.3f} ns "
          f"({elapsed_ns[-1] / 1e9:.6f} s; modulo 40-bit counter)")
    print("  Note: elapsed time assumes no more than one counter wrap during the batch.")
    print(f"  RX status flags observed: " + ", ".join(
        f"0x{int(x):02X} ({np.sum(diag_arrays['ipatovRxStatus'] == x)} frames)"
        for x in np.unique(diag_arrays["ipatovRxStatus"])))
    print("\nDiagnostic statistics (sample standard deviation):")
    print(f"{'Field':<24} {'Mean':>15} {'Std dev':>15} {'Min':>15} {'Max':>15}")
    report_fields = ["fp_index_samples", "peak_index_samples",
                     "peak_amplitude", "channel_area",
                     "ipatovF1_magnitude", "ipatovF2_magnitude",
                     "ipatovF3_magnitude"]
    for key in report_fields:
        arr = diag_arrays[key]
        std = np.std(arr, ddof=1) if len(arr) > 1 else 0.0
        print(f"{key:<24} {np.mean(arr):15.3f} {std:15.3f} "
              f"{np.min(arr):15.3f} {np.max(arr):15.3f}")
    print("  Raw packed peak, channel area, F1/F2/F3, status and timestamp")
    print("  are also preserved in the NPZ alongside the converted fields.")
    print("  dBm cannot be computed from the transmitted fields alone:")
    print("  IP_NACC, and DGC decision/configuration, are not transmitted.")
    print("  First-path index is in CIR samples, not directly in nanoseconds.")
    print("  Mean absolute timestamp is omitted because it is not a range measurement.")
    print(f"  Timestamp confidence: {sum(d['rx_timestamp_reliable'] for d in diagnostics)}"
          f"/{len(diagnostics)} frames without IP_TOAST warnings.")

    # All plots have the same y axis, even when comparing separate capture sessions.
    # The x range is identical within this batch (regardless of individual CIR lengths).
    plot_dir = output_file.parent / f"{output_file.stem}_plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    max_samples = max(len(cir) for cir in cirs)
    max_amplitude = max(float(np.max(np.abs(cir))) for cir in cirs)
    if max_amplitude > PLOT_Y_MAX:
        print(f"WARNING: max CIR magnitude {max_amplitude:.1f} exceeds "
              f"PLOT_Y_MAX={PLOT_Y_MAX}; image peaks will be clipped. "
              "Increase PLOT_Y_MAX and regenerate the plots.")

    for frame_number, (diag, cir) in enumerate(records, start=1):
        magnitude = np.abs(cir)
        fp_pos = diag["fp_index_samples"]
        peak_pos = diag["peak_index_samples"]
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(np.arange(len(magnitude)), magnitude, linewidth=1.1,
                label="Raw CIR magnitude")
        if 0 <= fp_pos <= len(magnitude) - 1:
            ax.axvline(fp_pos, linestyle="--", linewidth=0.8, alpha=0.42,
                       color="tab:red", label=f"Reported FP = {fp_pos:.3f}")
        if 0 <= peak_pos < len(magnitude):
            ax.axvline(peak_pos, linestyle=":", linewidth=0.8, alpha=0.42,
                       color="tab:orange", label=f"Peak index = {peak_pos}")
        ax.set(xlim=(0, max(1, max_samples - 1)), ylim=(0, PLOT_Y_MAX),
               xlabel="Accumulator sample index", ylabel="|I + jQ| (raw magnitude)",
               title=f"{output_file.stem} | Frame {frame_number:03d} | CIR magnitude")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="upper right")
        fig.tight_layout()
        image_file = plot_dir / f"frame_{frame_number:03d}.png"
        fig.savefig(image_file, dpi=PLOT_DPI)
        plt.close(fig)

    # Additional image: all frames overlaid in distinct colors, with transparent lines.
    fig, ax = plt.subplots(figsize=(12, 6))
    palette = plt.get_cmap("tab10")
    for frame_number, (diag, cir) in enumerate(records, start=1):
        color = palette((frame_number - 1) % 10)
        ax.plot(np.arange(len(cir)), np.abs(cir), color=color,
                alpha=0.67, linewidth=1.0, label=f"Frame {frame_number:03d}")
        fp_pos = diag["fp_index_samples"]
        if 0 <= fp_pos <= len(cir) - 1:
            # Small bottom tick instead of full-height markers to avoid visual clutter.
            ax.plot([fp_pos, fp_pos], [0, PLOT_Y_MAX * 0.025],
                    color=color, alpha=0.75, linewidth=1.1)
    ax.set(xlim=(0, max(1, max_samples - 1)), ylim=(0, PLOT_Y_MAX),
           xlabel="Accumulator sample index", ylabel="|I + jQ| (raw magnitude)",
           title=f"{output_file.stem} | All {len(records)} frames | CIR magnitude")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize="small", ncol=2)
    fig.tight_layout()
    combined_file = plot_dir / "all_frames.png"
    fig.savefig(combined_file, dpi=PLOT_DPI)
    plt.close(fig)

    print(f"Saved {len(records)} individual CIR plots to {plot_dir.resolve()}")
    print(f"Saved combined CIR plot to {combined_file.resolve()}")


def prompt_output_file():
    """Ask for a file name, defaulting to uwb_measurements.npz."""
    name = input("Enter measurement filename [uwb_measurements]: ").strip()
    if not name:
        name = "uwb_measurements"
    output_file = Path(name).expanduser().with_suffix(".npz")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    return output_file


if __name__ == "__main__":
    output_file = prompt_output_file()
    save_and_plot(collect(), output_file)
