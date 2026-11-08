
import serial
import numpy as np
import matplotlib.pyplot as plt

# ---------------- SERIAL SETTINGS ----------------

PORT = "COM4"       # Change this if your STM32 uses another COM port
BAUD_RATE = 115200

ser = serial.Serial(PORT, BAUD_RATE, timeout=2)

# ---------------- CIR DATA ----------------

current_measurement = None

tof_ns = None
distance_m = None

first_path_index = None
peak_index = None

I_values = []
Q_values = []

# ---------------- PLOT SETUP ----------------

plt.ion()

fig, ax = plt.subplots(figsize=(12, 6))

print("Waiting for CIR and ranging data...")


def plot_cir():

    if len(I_values) == 0:
        return

    I = np.array(I_values)
    Q = np.array(Q_values)

    # Calculate CIR magnitude
    magnitude = np.sqrt(I**2 + Q**2)

    sample_indices = np.arange(len(magnitude))

    ax.clear()

    # Plot CIR magnitude
    ax.plot(
        sample_indices,
        magnitude,
        label="CIR Magnitude"
    )

    # First path marker
    if first_path_index is not None:
        ax.axvline(
            x=first_path_index,
            linestyle="--",
            linewidth=2,
            label=f"First Path: {first_path_index:.2f}"
        )

    # Highest peak marker
    if peak_index is not None and peak_index >= 0:
        ax.axvline(
            x=peak_index,
            linestyle=":",
            linewidth=2,
            label=f"Highest Peak: {peak_index}"
        )

        ax.scatter(
            peak_index,
            magnitude[peak_index],
            marker="x",
            s=80
        )

    ax.set_xlabel("CIR Sample Index")
    ax.set_ylabel("CIR Magnitude")

    ax.set_title(
        f"Measurement {current_measurement} | "
        f"ToF = {tof_ns:.3f} ns | "
        f"Distance = {distance_m:.4f} m"
    )

    ax.grid(True)
    ax.legend()

    fig.tight_layout()
    plt.draw()
    plt.pause(0.01)


# ---------------- SERIAL READING LOOP ----------------

try:

    while True:

        raw_line = ser.readline().decode(
            "utf-8",
            errors="ignore"
        ).strip()

        if not raw_line:
            continue

        fields = raw_line.split(",")

        # Ranging result:
        # RANGE,measurement,tof_ns,distance_m

        if fields[0] == "RANGE":

            current_measurement = int(fields[1])
            tof_ns = float(fields[2])
            distance_m = float(fields[3])

            print(
                f"\nMeasurement {current_measurement}: "
                f"ToF = {tof_ns:.3f} ns, "
                f"Distance = {distance_m:.4f} m"
            )

        # Beginning of CIR data

        elif fields[0] == "CIR_BEGIN":

            I_values = []
            Q_values = []

        # CIR sample:
        # CIR,measurement,index,I,Q

        elif fields[0] == "CIR":

            measurement = int(fields[1])

            if measurement != current_measurement:
                continue

            i_value = int(fields[3])
            q_value = int(fields[4])

            I_values.append(i_value)
            Q_values.append(q_value)

        # End of CIR data

        elif fields[0] == "CIR_END":

            if int(fields[1]) == current_measurement:
                plot_cir()

        # Marker data:
        # MARKERS,measurement,first_path_index,peak_index

        elif fields[0] == "MARKERS":

            measurement = int(fields[1])

            if measurement == current_measurement:

                first_path_index = float(fields[2])
                peak_index = int(fields[3])

                print(
                    f"First path index: {first_path_index:.3f}"
                )

                print(
                    f"Highest peak index: {peak_index}"
                )

except KeyboardInterrupt:

    print("\nStopping serial capture.")

finally:

    ser.close()
    plt.ioff()
    plt.show()
