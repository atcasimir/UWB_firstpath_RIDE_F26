"""Collect CIR, RX diagnostics, and DS-TWR ranges from STM32 UART output.

Requires: pip install pyserial numpy matplotlib
The current STM32 firmware collects its own fixed number of frames; this script
only listens, records, saves and plots. Set NUM_MEASUREMENTS to match firmware.
"""

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import serial

PORT = "COM6"                  # Change to your STM32 COM port
BAUD_RATE = 115200             # Match firmware UART configuration
NUM_MEASUREMENTS = 10           # Match rx_twr_test.c measurement limit
READ_TIMEOUT = 1               # Serial read timeout in seconds

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


def parse_range(text):
    """The C firmware prints distance (meters), then ToF (seconds)."""
    values = text.strip().split()
    if len(values) != 2:
        raise ValueError(f"Expected distance and ToF, got {len(values)} values")
    return float(values[0]), float(values[1])


def collect():
    """Read complete DIAG -> CIR -> RANGE groups, one group per ranging trial."""
    records = []
    state = "waiting"
    stream = ""
    pending_diag = None
    pending_cir = None
    # Match the literal marker text emitted by rx_twr_test.c.
    diag_begin = "RX DIAG BEGIN"
    diag_end = "RX DIAG END"
    cir_begin = "CIR BEGIN"
    cir_end = "CIR END"
    range_begin = "RANGE BEGIN"
    range_end = "RANGE END"

    print(f"Listening on {PORT} ({BAUD_RATE} baud); collecting {NUM_MEASUREMENTS} measurements.")
    print("Start/reset STM32 if needed; Ctrl+C saves completed measurements.")

    with serial.Serial(PORT, BAUD_RATE, timeout=READ_TIMEOUT) as ser:
        try:
            while len(records) < NUM_MEASUREMENTS:
                chunk = ser.read(ser.in_waiting or 1).decode("ascii", errors="ignore")
                if not chunk:
                    continue
                stream += chunk

                # UART read() may return half a marker or half a measurement.
                # Wait until the complete closing marker arrives before parsing.
                while True:
                    if state == "waiting":
                        pos = stream.find(diag_begin)
                        if pos < 0:
                            stream = stream[-(len(diag_begin) - 1):]
                            break
                        stream = stream[pos + len(diag_begin):]
                        pending_diag = None
                        pending_cir = None
                        state = "diagnostics"

                    elif state == "diagnostics":
                        pos = stream.find(diag_end)
                        if pos < 0:
                            break
                        text = stream[:pos]
                        stream = stream[pos + len(diag_end):]
                        try:
                            pending_diag = parse_diagnostics(text)
                        except (ValueError, OverflowError) as exc:
                            print(f"Invalid diagnostics: {exc}")
                            pending_diag = None
                        state = "await_cir"

                    elif state == "await_cir":
                        pos = stream.find(cir_begin)
                        if pos < 0:
                            break
                        stream = stream[pos + len(cir_begin):]
                        state = "cir"

                    elif state == "cir":
                        pos = stream.find(cir_end)
                        if pos < 0:
                            break
                        text = stream[:pos]
                        stream = stream[pos + len(cir_end):]
                        try:
                            pending_cir = parse_cir(text)
                        except ValueError as exc:
                            print(f"Invalid CIR: {exc}")
                            pending_cir = None
                        state = "await_range"

                    elif state == "await_range":
                        pos = stream.find(range_begin)
                        if pos < 0:
                            break
                        stream = stream[pos + len(range_begin):]
                        state = "range"

                    elif state == "range":
                        pos = stream.find(range_end)
                        if pos < 0:
                            break
                        text = stream[:pos]
                        stream = stream[pos + len(range_end):]
                        try:
                            distance_m, tof_s = parse_range(text)
                            if pending_diag is not None and pending_cir is not None:
                                records.append((pending_diag, pending_cir, distance_m, tof_s))
                                print(f"Collected {len(records)}/{NUM_MEASUREMENTS} | "
                                      f"Range: {distance_m:.2f} m")
                        except ValueError as exc:
                            print(f"Invalid range: {exc}")
                        pending_diag = None
                        pending_cir = None
                        state = "waiting"

        except KeyboardInterrupt:
            print("\nInterrupted; saving completed measurements.")

    return records


def save_and_plot(records, output_file):
    if not records:
        print("No complete measurements received.")
        return

    diagnostics = [r[0] for r in records]
    cirs = [r[1] for r in records]
    ranges_m = np.array([r[2] for r in records], dtype=np.float64)
    tofs_s = np.array([r[3] for r in records], dtype=np.float64)
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
                        range_m=ranges_m, tof_s=tofs_s, **diag_arrays)
    print(f"\nSaved {len(records)} complete measurements to {output_file.resolve()}")

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

    for frame_number, (diag, cir, distance_m, tof_s) in enumerate(records, start=1):
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
        # Legend-only entry: does not change the plotted CIR.
        ax.plot([], [], color="none", label=f"Range = {distance_m:.2f} m")
        ax.legend(loc="upper right")
        fig.tight_layout()
        image_file = plot_dir / f"frame_{frame_number:03d}.png"
        fig.savefig(image_file, dpi=PLOT_DPI)
        plt.close(fig)

    # Additional image: all frames overlaid in distinct colors, with transparent lines.
    fig, ax = plt.subplots(figsize=(12, 6))
    palette = plt.get_cmap("tab10")
    for frame_number, (diag, cir, distance_m, tof_s) in enumerate(records, start=1):
        color = palette((frame_number - 1) % 10)
        # Overlay every frame without adding a separate legend entry.
        ax.plot(np.arange(len(cir)), np.abs(cir), color=color,
                alpha=0.67, linewidth=1.0)
        fp_pos = diag["fp_index_samples"]
        if 0 <= fp_pos <= len(cir) - 1:
            # Small bottom tick instead of full-height markers to avoid visual clutter.
            ax.plot([fp_pos, fp_pos], [0, PLOT_Y_MAX * 0.025],
                    color=color, alpha=0.75, linewidth=1.1)
    ax.set(xlim=(0, max(1, max_samples - 1)), ylim=(0, PLOT_Y_MAX),
           xlabel="Accumulator sample index", ylabel="|I + jQ| (raw magnitude)",
           title=f"{output_file.stem} | All {len(records)} frames | CIR magnitude")
    ax.grid(True, alpha=0.25)
    # Summary entries appear only in the combined graph legend.
    ax.plot([], [], color="none", label=f"Mean range = {np.mean(ranges_m):.2f} m")
    ax.plot([], [], color="none", label=f"Median range = {np.median(ranges_m):.2f} m")
    ax.plot([], [], color="none", label=(
        f"Range = {np.min(ranges_m):.2f}–{np.max(ranges_m):.2f} m "
        f"(span {np.ptp(ranges_m):.2f} m)"))
    # Sample statistics (N - 1 denominator), for comparison across trials.
    # A single measurement does not have a defined sample variance or SD.
    if len(ranges_m) > 1:
        ax.plot([], [], color="none",
                label=f"Variance = {np.var(ranges_m, ddof=1):.6f} m²")
        ax.plot([], [], color="none",
                label=f"Std. dev. = {np.std(ranges_m, ddof=1):.4f} m")
    else:
        ax.plot([], [], color="none", label="Variance = N/A (N < 2)")
        ax.plot([], [], color="none", label="Std. dev. = N/A (N < 2)")
    ax.legend(loc="upper right", fontsize="small")
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
