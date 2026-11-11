#!/usr/bin/env python3
"""uwb_help.py - the text behind the Help buttons. Lines starting with "# " are section titles."""

HELP = r"""
# 1. What this does, in one minute

Two boards measure the distance between them by exchanging three short radio
messages: POLL, RESPONSE and FINAL. That is one "exchange", and it gives one range.

Each time a board receives a message it also records the channel impulse response
(CIR): a picture of how the signal arrived, with the direct path first and the
reflections after it. So every exchange produces three CIRs:

    poll      received by the responder board   (this PC, the main window)
    response  received by the initiator board   (the other PC, the small window)
    final     received by the responder board   (this PC)

A "trial" is a run of many exchanges with the boards left untouched.
The main window saves the poll and final CIRs. The initiator PC saves the response
CIRs. "Import other PC's files" joins them into one file with all three.


# 2. First-time setup

1. Flash both boards with the firmware from STM32CubeIDE (same firmware on both).
2. On both computers install the Python packages:
       Windows:   pip install pyserial numpy matplotlib
       Mac:       python3 -m pip install pyserial numpy matplotlib
3. Copy the whole "python" folder to the initiator's computer.
4. Start the windows:
       Windows:   double-click "UWB Capture.bat"     /  "UWB Initiator.bat"
       Mac:       double-click "UWB Capture.command" /  "UWB Initiator.command"
   The two computers do not have to be the same kind. A trial recorded on a Mac
   merges with one recorded on Windows, and the other way round.

A console window (Windows) or a Terminal window (Mac) opens next to each window.
Leave it open; if something goes wrong at start-up, the reason is printed there.
Mac users: see section 13 for the one-time steps.


# 3. A normal session, step by step

Initiator PC (once):
  1. Choose the COM port of its board.
  2. Press Start. It shows "Calling the main (responder) board..." and stays like
     that. Leave it alone for the whole session.

Main PC:
  1. Choose the COM port of the responder board.
  2. Choose a setup from the list, or press "New setup..." (see section 5).
  3. Type the number of exchanges (0 means "until I press Stop").
  4. Press "Start trial". The bar fills up and the range numbers update.
  5. When it is done the new file appears at the top of the list on the right.

It does not matter which PC is started first.

Before the next trial, ask yourself what changed:
  - nothing                          -> just press Start trial again
  - I moved or bumped a board        -> press "Boards were moved", then Start trial
  - distance / blockage / room /
    orientation is different         -> "New from this one...", change the field, save

At the end: copy the initiator PC's data folder to a USB stick and press
"Import other PC's files..." on the main PC (section 6).


# 4. The main window, button by button

Box 1 - Responder board
  COM port       The board's serial port (called "Serial port" on a Mac, where it
                 looks like /dev/cu.usbmodem1103). ST-LINK ports are listed first.
  Refresh        Re-reads the list after plugging a board in.
  Baud rate      Speed of the USB link. 1000000 is fastest. If you see serial
                 errors or it will not connect, use 460800 or 115200.
  Release port   Closes the port so another program can use the board. The port
                 otherwise stays open between trials.

Box 2 - What is being measured
  Setup                  The thing you are measuring (section 5).
  New setup...           Empty form for a new setup.
  New from this one...   Same form, pre-filled with the current setup.
  Edit...                Fix a typo. Saved trials keep the fields they were made with.
  Boards were moved      The next trial is a new "placement" (section 5).

Box 3 - Trial
  Number of exchanges    How many completed exchanges to collect. 0 = until Stop.
  Transmit power         How strongly THIS PC's board transmits. Default = full power, as
                         before. The other choices lower it by about 3 to 29 dB (typical
                         figures from the chip's manual, not a calibration). Each PC sets
                         its own board, so choose the same level in the initiator window
                         too; otherwise poll and final get weaker but the response does
                         not (or the other way round). No reflash: the level is sent to
                         the board at Start, and it stays selected until you change it.
                         The trial file and the report record the level of both boards.
                         Lower power means a weaker first path and, far enough down,
                         failed exchanges. The range also shifts by a few centimetres
                         with received level, so compare trials taken at the same power.
  Notes for this trial   Free text saved in the file. Cleared after each trial.
  Data folder            Where the files go. Each data folder has its own setups.

Box 4 - Run
  Start trial    Connects if needed, then waits for the initiator and runs the trial.
  Stop           Ends the trial early and tells the other board over the radio.
                 What was collected so far is saved.

Saved trials (right side) - "Selected trial" buttons need a file selected in the list
  Analyze + report     Readable summary in the Output box, and a report file you can
                       send to someone (section 7).
  View CIRs            Opens a viewer on the selected trial. No waiting and no file:
                       each exchange is drawn at once. Previous / Next or the Left /
                       Right arrow keys step through; "Go to exchange" jumps; "Show"
                       narrows to the suspect or the flagged exchanges (suspects come
                       most suspicious first). Use this for looking; use the PDFs
                       for sending.
  Suspect CIRs to PDF  A PDF with ONLY the exchanges where the chip's first path is most
                       likely not the direct path, most suspicious first. Page 1 lists
                       them with the reason for each. "At most N exchanges" (next row)
                       caps how many are drawn. See section 8.
  All CIRs to PDF      A PDF, one page per exchange, showing poll, response and final.
                       Takes about a third of a second per exchange.
  Overview picture     One picture: all CIRs overlaid, and range per exchange.
  Compare its setup    All trials of the same setup side by side (section 7).
  Calibrate            Antenna delay calibration from the selected trials (section 9).
                       With nothing selected it shows the calibration in use.
  Export CSV           One row per exchange, for Excel or MATLAB.

"Whole folder" buttons work on everything in the data folder
  Import other PC's files...   Brings in the initiator's files and merges (section 6).
  Summary of all setups        One line per setup and placement.
  Export ML dataset            One array file with every CIR plus a table of labels.
  Open folder                  Opens the data folder in Explorer.
  Refresh                      Re-reads the file list.

  Filter box     Limits Summary and Export ML dataset, e.g.
                     site=lab condition=nlos        distance=2        cabinet
                 A bare word matches any field of the setup.
  Leave flagged exchanges out   Compare and Summary then ignore abnormal exchanges.

Output box       Everything the buttons report is printed here. Clear empties it.


# 5. Setups and placements

A SETUP is what you intend to measure: site, real distance, condition (LOS, partial
blockage, NLOS), what is in the way, how the boards are turned, antenna height.
You fill it in once and pick it from the list afterwards. It gets an id like S003.
If anything in that list is different, it is a different setup.

  Real distance   Antenna to antenna, in metres. This is the "truth" that every
                  range is compared with, so measure it carefully.
  Condition       Your own statement of whether the direct path is clear. The
                  boards cannot know this; it is the label used later for sorting
                  and for machine learning. It does not change the measurement.

Under the setup the window shows when the floor reflection arrives after the direct
path. Below about 2 ns the two merge into one pulse and the range can shift by
centimetres, even in "line of sight". Raise the antennas or shorten the distance if
you want a clean reference.

A PLACEMENT is one physical positioning of the boards for a setup. Putting the
boards back "in the same place" is never exact, and a few centimetres change the
reflections. So:

  same setup, same placement        true repeats (boards untouched in between)
  same setup, different placement   shows how repeatable the setup is

Press "Boards were moved" after touching a board. The number also goes up by itself
when you come back to a setup after measuring a different one.

File names follow this:   S003_lab_2m_los_p2_001_responder.json
                          setup  name     placement  trial number


# 6. Getting all three CIRs into one file

1. Initiator PC: press "Open folder". Copy the files named initiator_....json
   (or the whole folder) to a USB stick.
2. Main PC: press "Import other PC's files..." and choose the stick.
3. Files ending in _merged.json appear in the list. Use those from now on.

The files are matched by a trial id that the boards exchange over the radio, not by
file name, so renaming is harmless. Importing the same stick again copies nothing.
"no counterpart yet" means the other half of that trial was not on the stick.


# 7. Reading the Output box

WHILE A TRIAL RUNS
  Trial 127BB76A: CIR samples 0..1015, reply delays 10400 / 8300 us, CIR read 8046 us
      The trial id; which part of the CIR is captured; how long each board waits
      before replying; how long reading one CIR from the chip takes.
  Saved ... (100 exchanges ok, 3 failed, ended: done)
      "ended" is one of:
        done                    the requested number was reached
        stopped_here            Stop was pressed on this PC
        stopped_by_other_side   the other board ended the trial
        idle_timeout            30 s without a completed exchange
  Note: N late transmissions (reply delay was raised automatically ...)
      Normal at the start when the two boards are different models: the slower one
      asks for more time, which costs one exchange.
  Range: n=100 mean 2.013 m median 2.012 m sd 0.021 m | real 2.000 m, bias +0.013 m
      Once the boards are calibrated this becomes two lines: the range as measured
      ("raw, before calibration") and the calibrated one.
  Flagged 4 of 100 exchanges as abnormal: ...

ANALYZE + REPORT
  Prints the summary below and writes  <trial>_report.html  next to the trial file.
  The report file opens in your browser by itself. It is one self-contained file
  (pictures included), so it can be e-mailed as it is; print it from the browser to
  get a PDF. It has everything the Output box shows, plus two charts and a table
  with every single exchange: reported range, actual distance, the difference, and
  first path, peak and the gap between them (in samples and ns) for each message.

  RANGE: reported vs actual
      actual distance        what you entered in the setup
      mean reported range    average of all ranges in the trial
      difference             mean reported minus actual. Positive = measuring too
                             long, negative = too short. Before calibration this
                             contains the boards' antenna delay (section 9).
      after calibration      the same with the antenna delay removed
      mean without the flagged ones   the same, leaving the abnormal exchanges out
      spread of single ranges (sd)    how much single ranges scatter around the mean.
                             It does not shrink when you collect more.
      how well the mean is known      95 % confidence interval of the mean. It does
                             shrink with more exchanges (sd / root n, times 1.96).

  FIRST PATH vs PEAK   one line per message (poll, response, final)
      first path      where in the CIR the chip says the signal first arrived
      peak            the strongest sample of the CIR
      peak - first    the gap between them, in samples and in nanoseconds
                      (1 sample = 1.0016 ns = 30 cm of path)
      smallest .. largest   the range of that gap over the trial
      1 to 3 samples is a clean direct path. More than 6 means the strongest arrival
      is a later one: a strong reflection, or a blocked direct path. A gap that
      jumps between two values from exchange to exchange means two arrivals are
      about equally strong and take turns being the peak. Neither flags an exchange:
      when it happens often, the report says so once, as a NOTE about the trial.

  EXCHANGES furthest from the actual distance
      the five worst single exchanges. All of them are in the report file.

  FLAGGED ...   each abnormal exchange with its reasons (section 8).

COMPARE ITS SETUP
  One line per trial of that setup:
      plc        placement number
      95% CI     compare trials by this, not by the mean alone: a 10-exchange trial
                 has a wide interval, a 100-exchange trial a narrow one
      bias       mean minus real distance
      cal bias   the same after calibration ("-" if those boards are not calibrated)
      vs the other trials   "agrees", or "DIFFERS by ..." when this trial's mean is
                 further from the others than chance explains
  "placement N pooled"   all exchanges of that placement as one data set
  "spread of the placement means"   how much the result moves when the boards are
                 set up again. If this is large compared with sd, the setup is
                 sensitive to position: a sign of reflections close to the direct path.

SUMMARY OF ALL SETUPS
  One line per setup and placement, sorted by site, condition and distance:
  trials, exchanges (n), mean, sd, bias, cal bias, flagged, failed.


# 8. Why an exchange fails or is flagged

FAILED exchanges did not complete, so they have no range:
  no_response   initiator: its poll was not answered in time
  no_final      responder: the final message never arrived
  late_tx       this board was not ready to reply in time
  peer_late     initiator: the other board said it needs a longer reply delay
  tx_fail       the chip did not confirm a transmission
A few are normal, more so with blockage. Many in clean line of sight means
something is wrong (distance too large, boards not facing, wrong channel).

FLAGGED exchanges completed but are unlike the rest of their trial.
Two things must both be true: the value is far outside what the other exchanges
of the same trial show, AND it is off by an amount that matters. Something every
exchange of a trial shares (a reflection stronger than the direct path, say) is
therefore not a flag; the report mentions it once as a NOTE about the trial.
Each message type is judged only against its own kind: a final's CIR is compared
with the other finals of the trial, never with polls or responses. The one rule
that uses the whole exchange is the range.
  range ... is +0.31 m from the trial median      at least 10 cm off
  chip first-path warning                         the chip doubted its own estimate
                                                  (the only rule with no comparison)
  first path is N samples earlier/later than usual on the rising edge
                                                  at least 1 sample (30 cm) off; this is
                                                  the sign of a first-path miss
  peak is N samples after the first path (usually M in this trial)
                                                  at least 3 samples from the usual gap
                                                  and a one-off: a gap that keeps coming
                                                  back is the peak hopping between two
                                                  arrivals, which is normal for that trial
  energy before the reported first path           at least 5 x the noise
  CIR shape unlike the rest of the trial          similarity below 0.80
  first path N dB below total power               at least 3 dB from the usual value
Flags are hints for a closer look (the viewer and the CIR PDFs show the reasons), not verdicts.
Files saved with older rules are re-judged automatically the next time they are opened.

SUSPECT exchanges (the viewer's "Suspect only", and Suspect CIRs to PDF) are picked for one question only: is the
chip's first path really the direct path? Each sign adds to a score, and the
highest scores are plotted first:
  range far from the rest of the trial   too long = a later path taken as the first;
                                         too short = something ahead of the pulse
  the messages disagree on the first path
                                         poll, response and final cross the same channel
                                         within about 20 ms, so the first path should sit
                                         at the same spot on the rising edge in all three.
                                         When they differ by more than a sample, at least
                                         one is wrong.
  energy before the reported first path  an earlier arrival the chip did not pick
  the chip itself doubted its first path
  first path off the rising edge, or peak unusually far behind it
                                         compared with the rest of the trial
  CIR shape unlike the rest of the trial
  calibrated range far from the real distance   (only once the boards are calibrated)
A high score means "look here first", not "this one is wrong".
"Unlike the rest" needs at least 15 exchanges in the trial to be judged.


# 9. Calibration (antenna delay)

WHAT IT IS
Each board delays the signal between its clock and its antenna, about 257 ns each
way. The chips are loaded with a standard value for that (16385, Qorvo's default),
so ranges are already close to true without doing anything. But the default is the
same for every board and real boards differ a little, which leaves every range off
by the same small amount, typically up to a few tens of centimetres, at every
distance and in every room. Calibration measures that leftover once for a pair of
boards, and the analysis subtracts it.

HOW OFTEN
Once per pair of boards and per channel. Not per setup, not per room.
Redo it if you change channel, swap a board or module, or the temperature is very
different (about 2 mm per degree C per board).

HOW TO DO IT
  1. Pick a clean spot: antennas high (1.2 m or more), facing each other, at least
     1 m from walls, tables and metal. Short distance: 1 to 3 m.
  2. Make a setup with condition LOS and the real distance, measured antenna to
     antenna as exactly as you can. A 1 cm tape error is a 1 cm calibration error.
  3. Run a trial of 200 to 1000 exchanges.
  4. Better: repeat at two more distances (for example 1, 2 and 4 m), each as its
     own setup.
  5. Import the initiator's files so the trials are merged (this ties the
     calibration to both boards).
  6. Select those merged trials in the list and press Calibrate.
  7. Read the result in the Output box, then answer Yes to save it.

READING THE RESULT
  => offset -0.1230 m   the ranges were 12.3 cm too short; that is corrected from now on
  Good: the error is the same within 0.6 cm at 3 distances
                        what a pure antenna delay looks like
  WARNING: the error changes by N cm between distances
                        not a pure delay: a reflection merging with the direct
                        path, a mis-measured distance, or a signal-strength effect.
                        Fix the geometry and repeat before trusting it.
  WARNING: ... floor reflection arrives only N ns after the direct path
                        raise the antennas or shorten the distance

WHAT CHANGES AFTERWARDS
Nothing in the boards and nothing in the saved files. The live range in the Run box,
Analyze, Compare, Summary and the ML dataset show the calibrated value (next to the
raw one where there is room). To remove a calibration, delete calibration.json from
the data folder.

With THREE boards: range each pair (A-B, A-C, B-C) and calibrate with all of those
trials selected. The delay of each single board is then worked out, and any pairing
of the three is corrected.


# 10. The machine-learning dataset

"Export ML dataset" writes dataset_<date>.npz and dataset_<date>_labels.csv.
    cir       N x 3 x 1016 x 2     exchange, message (poll/response/final), sample, (I, Q)
    fp_index  N x 3                the chip's own first-path position
    distance_m, range_m, error_m, setup_id, placement, condition, ...   one per exchange
The Output box prints the full list and how to load it in Python.
Use merged files, otherwise the response CIR is missing.
Split training and test data by setup or placement, never by row: rows from one
placement are nearly identical.


# 11. What is in the data folder

  S001_..._responder.json    poll + final CIRs of one trial (main PC)
  initiator_..._<id>.json    response CIRs of one trial (initiator PC)
  ..._merged.json            all three, after import
  ..._report.html            Analyze + report: the file to send to someone
  ..._cirs.pdf               Plot all CIRs
  ..._overview.png           Plot overview
  ....csv                    Export CSV
  dataset_*.npz, *_labels.csv   Export ML dataset
  setups.json                your setups and placement counters
  calibration.json           the antenna delay calibration
  trials_index.csv           one line per saved trial

Inside a trial file each CIR is two lists of whole numbers, "i" and "q", one value
per sample, next to the chip's diagnostics for that message.


# 12. When something goes wrong

Will not connect / "No reply from the board"
    Wrong COM port, the board has other firmware, or another program holds the
    port. Press the black reset button on the board and try again.
"Access is denied" / port in use
    Another window, a terminal, or a paused debug session in STM32CubeIDE has the
    port. Close it, or press Release port there.
Main window stays on "Waiting for the initiator board to call..."
    Is the initiator window started and showing "Calling..."? Same channel on
    both? Reset both boards and start again.
Many failed exchanges in clean line of sight
    Lower the baud rate; check the boards face each other; move them closer.
"Corrupted serial packets" note
    Lower the baud rate.
"The fast CIR read did not match"
    Do not trust that trial's CIRs. Report it; the SPI speed needs lowering.
A window looks broken or a button prints ERROR
    Copy the text from the Output box or the console / Terminal window and report it.


# 13. On a Mac

Everything works the same as on Windows; only starting it is different.

ONE-TIME SETUP
  1. Install Python from python.org. Do not rely on the Python that comes with macOS:
     its window toolkit is too old and shows blank windows. (With Homebrew Python,
     also run:  brew install python-tk)
  2. In Terminal:   python3 -m pip install pyserial numpy matplotlib
  3. The first time, right-click "UWB Capture.command", choose Open, and confirm.
     macOS asks this once for a file that came from another computer.

IF DOUBLE-CLICKING DOES NOT START IT
  "...cannot be opened" or it opens in a text editor: the file lost its "program"
  mark on the way over (this happens with zip files and some USB sticks).
  In Terminal:
        cd  (drag the python folder onto the Terminal window)  and press Return
        chmod +x *.command
  Or skip the launcher altogether:
        python3 uwb_gui.py              the main window
        python3 uwb_gui_initiator.py    the initiator window

THE SERIAL PORT
  It is listed as /dev/cu.usbmodem followed by digits, with the ST-LINK first. The
  digits change with the USB socket used. The Mac's own Bluetooth port is hidden.
  If no usbmodem port appears: try another cable (many are charge-only) and press
  Refresh.

SPEED
  1000000 baud is tried first. If the board does not answer after the switch, choose
  460800 or 115200.

QUITTING
  Cmd+Q, or the red button, stops a running trial and releases the port.
  "Open folder" opens Finder; reports, plots and PDFs open in the Mac's own viewers.
"""


def sections(text=None):
    """[(title, [lines])] in order."""
    out = []
    for line in (text or HELP).strip("\n").split("\n"):
        if line.startswith("# "):
            out.append((line[2:].strip(), []))
        elif out:
            out[-1][1].append(line)
    return out


INITIATOR_HELP = r"""
# The initiator window

This small window runs on the PC of the INITIATOR board. Its only job is to keep
that board calling the main (responder) board and to save the one CIR per exchange
that the initiator receives (the "response" CIR).

  1. Choose the board's COM port (Refresh re-reads the list).
  2. Press Start once. It shows "Calling the main (responder) board...".
  3. Leave it running. Every trial started on the main PC is served automatically;
     trial length and what is being measured are decided there.
  4. Stop ends it. Release port lets another program use the board.
On a Mac, start this window with "UWB Initiator.command" (first time: right-click,
Open). The port is listed as /dev/cu.usbmodem followed by digits.

After the session: press "Open folder", copy the initiator_....json files to a USB
stick, and use "Import other PC's files..." in the main window. That produces the
merged files with poll, response and final together.

CIR capture boxes
  First sample / Samples   Which part of the 1016-sample CIR both boards capture.
                           Leave 0 and 0 for the whole CIR. A smaller window (for
                           example first sample 700, 200 samples) is much faster.
  Channel                  5 or 9. Must be the same as on the main PC (which uses 9).

Baud rate: 1000000 is fastest; use 460800 or 115200 if it will not connect or
reports corrupted serial packets.

"Stopped. Press Start to serve trials again." means it is no longer calling.
Trials in which nothing was exchanged are not saved.
"""
