# NUCLEO-F401RE + DWM3000EVB — Connection & Run Guide (Windows / macOS)

## How the pieces fit together

- **CubeIDE** compiles your C code and **flashes** it into the STM32's memory through the on-board ST-Link.
- **After flashing, the board runs on its own.** Whenever it has power, it starts the program from the beginning.
- **The USB cable also carries a serial port**:
  - **macOS:** `/dev/cu.usbmodem…`
  - **Windows:** a **COM port**, for example `COM5`
- **The terminal is only a viewer** for the text the program prints. The program runs whether or not the viewer is open.

> **Windows, one-time check:** With the board plugged in, open **Device Manager → Ports (COM & LPT)**. You should see
> **"STMicroelectronics STLink Virtual COM Port (COMx)"**. If it shows a yellow warning icon, install the
> ST-Link driver **STSW-LINK009** from st.com.

---

## The routine for any example

1. **Choose the example.** In `Src/example_selection.h`, uncomment exactly **one** `#define TEST_…` line.
2. **Build.** Click the hammer, or press **Ctrl+B** (Windows) / **⌘B** (macOS). Check for 0 errors.
3. **Flash.** Click the green **Run** button and wait for `Download verified successfully`.
   The `Shutting down... exit.` line that follows is normal.
4. **Open the viewer** (only needed if you want to see output). Commands are below.
5. **Press RESET** on the Nucleo, so you see the output from the beginning.
6. **Close the viewer** with **Ctrl+C**. To close PuTTY, close its window.

You can leave the viewer open while you flash again.

### Opening the viewer

**Windows**: run `uwbterm` in PowerShell (one-time setup is below), or use **PuTTY**:
- Connection type: **Serial**
- Serial line: **COM5** (your COM number)
- Speed: **115200**

**macOS**: run `uwbterm` (one-time setup is below), or:

```bash
(stty 115200 raw -echo; cat) < /dev/cu.usbmodem103
```

---

## Finding the board's port

**Windows (PowerShell):**

```powershell
Get-CimInstance Win32_PnPEntity | Where-Object Name -match 'STLink.*COM' | Select-Object Name
```

**macOS:**

```bash
ls /dev/cu.usbmodem*
```

With two boards plugged in, you'll get two entries. Unplug one if you need to tell them apart.

---

## Do you need the viewer for each example?

| Example | What it prints | Viewer needed? |
|---|---|---|
| `TEST_READING_DEV_ID` | `DEV ID OK` / `FAILED` | **Yes**, that's the whole result |
| `TEST_SIMPLE_TX` | Its name at startup only (or an error) | No. Once it's running, it just transmits |
| `TEST_SIMPLE_RX` | Its name at startup only | Not much use. Data is stored in memory, not printed |
| `TEST_RX_DIAG` | Its name at startup only | Not much use. Results are stored in memory, not printed |
| `TEST_SIMPLE_RX_CIR` | The full CIR for every packet | **Yes**, this is your data |

For the examples that only store results in memory, click **Debug** (the bug icon), then **Resume (F8)**, and watch the
variables in **Live Expressions**.

---

## One-time setup: the `uwbterm` shortcut

### macOS (zsh)

Paste this into Terminal once:

```bash
cat >> ~/.zshrc <<'EOF'
uwbterm() { local p=${1:-$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)}; [ -z "$p" ] && { echo "No board found"; return 1; }; echo "Listening on $p at 115200 (Ctrl-C to quit)"; (stty 115200 raw -echo; cat) < "$p"; }
EOF
source ~/.zshrc
```

### Windows (PowerShell)

Use the built-in **Windows PowerShell** (the blue icon).

**1. Allow your own profile script to run:**

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**2. Create your PowerShell profile file if it doesn't exist yet, and open it in Notepad:**

```powershell
if (!(Test-Path $PROFILE)) { New-Item -Type File -Force $PROFILE }; notepad $PROFILE
```

**3. Paste this into Notepad, save, and close it:**

```powershell
function uwbterm {
    param([string]$Port, [string]$LogFile, [int]$Baud = 115200)
    if (-not $Port) {
        $dev = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match 'STLink.*\(COM\d+\)' } | Select-Object -First 1
        if ($dev -and $dev.Name -match '\((COM\d+)\)') { $Port = $Matches[1] }
    }
    if (-not $Port) { Write-Host "No board found"; return }
    $sp = New-Object System.IO.Ports.SerialPort $Port, $Baud, 'None', 8, 'One'
    $sp.Open()
    $log = $null
    if ($LogFile) {
        $path = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($LogFile)
        $log = [System.IO.StreamWriter]::new($path, $true)
    }
    Write-Host "Listening on $Port at $Baud (Ctrl-C to quit)"
    try {
        while ($true) {
            $d = $sp.ReadExisting()
            if ($d) { [Console]::Write($d); if ($log) { $log.Write($d) } }
            else { Start-Sleep -Milliseconds 20 }
        }
    } finally {
        $sp.Close()
        if ($log) { $log.Close() }
    }
}
```

**4. Load it into the current window.** New PowerShell windows load it automatically.

```powershell
. $PROFILE
```

### Using it

| | Auto-detect the board | Choose a specific board |
|---|---|---|
| **Windows** | `uwbterm` | `uwbterm COM7` |
| **macOS** | `uwbterm` | `uwbterm /dev/cu.usbmodem1103` |

---

## Saving a CIR capture to a file

Both commands show the output on screen and save it to the file at the same time.

**Windows:**

```powershell
uwbterm -LogFile cir_capture.txt
```

**macOS:**

```bash
uwbterm | tee cir_capture.txt
```

---

## Ending a session

1. **Close the viewer** with **Ctrl+C**, or close the PuTTY window.
2. **If you used Debug**, click the red **Terminate** square in CubeIDE.
3. **Unplug the board.** There's nothing to eject on either system.

> ⚠️ Don't unplug **during flashing** (before "Download verified") or **during an ST-Link firmware upgrade**.

---

## Troubleshooting

### Nothing appears in the viewer
- **Both:** Press **RESET** on the Nucleo while the viewer is open.

### Garbage characters
- **Windows:** Check the speed is **115200** in PuTTY or `uwbterm`.
- **macOS:** Use the `(stty …; cat)` form or `uwbterm`. Don't use `stty -f`, because macOS resets the speed once `stty` finishes.

### Port busy ("Access denied" / "Resource busy")
- **Windows:** Close the other viewer (PuTTY, another PowerShell window, or CubeIDE's Terminal view).
  If you can't find it, unplug and replug the board.
- **macOS:** Find what's holding the port and kill it:
  ```bash
  lsof | grep -i usbmodem
  kill -9 <PID>
  ```
  A leftover `screen` session shows up as `SCREEN` in capitals, so `pkill screen` won't match it.

### "No ST-LINK detected!"
- **Both:** Make sure the cable carries data (some cables only charge) and quit any other ST tools.
- **Windows:** Check the driver appears correctly in Device Manager.

### No COM port / no `usbmodem` device
- **Windows:** The driver is missing (yellow icon in Device Manager). Install **STSW-LINK009**.
- **macOS:** Most likely a charge-only cable. Also check **System Settings → Privacy & Security →
  Allow accessories to connect**.
