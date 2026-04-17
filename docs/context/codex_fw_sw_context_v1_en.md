# V1 Controlled Short-Circuit Pulse Test Platform  
**FW/SW context for Codex**

## 1. Project goal

Build a **single-channel engineering validation platform** for a **controlled short-circuit pulse test** on a **discrete MOSFET DUT**.

This is **not** a full AEC qualification system in V1.

### V1 target
- DUT: **discrete MOSFET**, no built-in thermal shutdown
- Bus voltage: **14 V nominal**
- Target current: **100 A**
- Pulse width: **1 ms to 10 ms**, adjustable
- First version must support **10 ms**
- Allowed bus droop target: **<= 0.5 V**
- Environment: **room temperature only**
- Channel count: **single channel**
- Main purpose: **architecture validation / engineering bring-up**

---

## 2. Non-goals for V1

Do **not** assume these are required in V1:

- No `-40°C` low-temperature qualification
- No multi-channel operation
- No smart power switch thermal shutdown / auto-retry emulation
- No MOS linear current limiting
- No promise of long-term `30% duty`
- No promise of `1,000,000 cycles` qualification-grade robustness in V1
- No FPGA requirement in V1
- No RTOS requirement in V1

---

## 3. High-level system architecture

## Board 1 = Power Board
Purpose:
- Aggregate 4 PSU inputs into one local 14 V bus
- Provide local energy storage
- Manage precharge / discharge / bus readiness

Main functions:
- 4x PSU input
- branch protection
- ORing / fault isolation
- common 14 V bus
- local CAP BANK
- precharge
- bus enable / connect
- discharge
- bus voltage sensing
- CAP voltage sensing
- optional temperature sensing
- status outputs to Board 2

## Board 2 = DUT / Driver / Protection / Control Board
Purpose:
- Apply controlled pulse stress to DUT
- Measure key signals
- Perform fast hardware protection
- Count cycles and manage sequencing

Main functions:
- DUT mount
- main current path
- gate driver
- gate resistor / gate protection
- shunt / current sensing
- short-circuit abnormal protection
- trigger I/O to oscilloscope
- status interface with Board 1
- MCU control

## External current-limit resistor module
Purpose:
- Main current limiting element for V1
- Defines controlled 100 A pulse behavior

Notes:
- Do **not** treat DUT as the normal current limiter
- Current-limit resistor module should be considered part of the main power path

---

## 4. Main electrical path

### Charge path
`4x PSU -> branch protection -> ORing -> 14 V bus / CAP BANK`

### Test path
`14 V bus / CAP BANK -> current-limit resistor module -> DUT -> shunt / return`

### Important design rule
- The **bus is DC-like**
- The **current is pulsed**
- The pulse is formed by **DUT gate switching**
- The bus itself is **not** chopped

---

## 5. Power strategy

### PSU strategy
- 4 programmable PSUs are paralleled into one 14 V bus
- Each PSU may be adjusted slightly above 14 V to compensate small drops
- ORing is used to:
  - prevent backfeed
  - reduce fighting between supplies
  - isolate faulty branches
- ORing is **not** the main bus droop solution

### CAP BANK strategy
Initial V1 target:
- total local capacitance roughly `0.2 F to 0.4 F`

Recommended structure:
- bulk capacitance
- polymer / mid-frequency layer
- film + small MLCC / HF layer

### Precharge / discharge
Board 1 must support:
- precharge before full bus connect
- safe discharge after stop / fault / shutdown

---



## 5A. Current V1 hardware decisions already assumed

The following Board 1 assumptions are currently preferred for V1 and should be treated as active working assumptions unless changed later:

- 4 programmable PSUs are used as the upstream source
- Each PSU branch includes ORing / reverse-blocking behavior on Board 1
- Board 1 does not include a dedicated temperature sensor in V1
- Board 1 does not include a film capacitor layer in V1
- A permanent small bleeder resistor is present on the local bus
- Initial bleeder value is approximately `1 kΩ`
- Board 1 bus readiness is not required to come from a dedicated hardware comparator in V1
- Board 1 bus readiness may be derived in firmware from:
  - PSU OK information
  - local bus voltage ADC measurement
  - precharge completion timing / state

These assumptions should remain configurable, but Codex should not assume additional Board 1 analog supervision hardware unless explicitly added later.

## 5B. Upstream PSU behavior assumptions

V1 uses programmable PSUs with protection and status features.

Important assumptions:
- upstream PSU behavior is not equivalent to an ideal passive DC source
- PSU-side protections may include CV/CC behavior, OVP/UVL, foldback, power-good indication, and remote enable / disable
- firmware must not assume that PSU output enable automatically means local bus ready
- firmware must not assume that PSU voltage regulation alone replaces Board 1 precharge logic
- if remote sense is used, it should be applied only up to the Board 1 local bus, not to the DUT pulse loop
- foldback mode should be treated carefully during bring-up because it may interfere with precharge and bus charging behavior

Codex should expose PSU-related readiness and fault handling as explicit logic, not hidden assumptions.


## 6. Current-limit strategy

V1 uses:
- **external low-value high-power pulse resistor module**

Do not assume:
- active current limiter
- MOS linear limiting operation
- closed-loop current control in V1

Initial resistor range:
- approximately `100 mΩ to 120 mΩ` total effective resistance

Module recommendation:
- pulse-rated
- low inductance
- high power
- mechanically replaceable

---

## 7. Mechanical / interconnect concept

Current preferred direction:
- Board 1 and Board 2 connected with **stacked positive/negative bus bars**
- Current-limit resistor module mounted near / on Board 2 power entry area
- Positive path goes first into resistor module
- Negative return goes from DUT / shunt area back to Board 1 return via bus bar

Important layout intent:
- keep positive and negative main paths close together
- minimize loop area
- keep resistor module close to DUT
- keep shunt close to DUT return
- do not use signal-style card connectors for main 100 A path

---

## 8. Protection philosophy

## Fast protection must be hardware-first
Do **not** rely on MCU firmware for first-line microsecond-level protection.

Fast protection should be hardware-based:
- comparator OCP
- timeout protection
- fault latch

### Protection roles
- **Comparator OCP**: immediate overcurrent kill
- **Timeout**: pulse width upper bound enforcement
- **Fault latch**: lock system after fault, prevent uncontrolled retrigger
- **DUT off check**: confirm current actually returns to off state after pulse

### Thermal interlock
Thermal interlock is allowed in V1, but role is:
- inter-pulse cooling permission
- not substitute for fast in-pulse protection

---

## 9. Instrumentation concept

## Function generator
- Existing `33250A` remains the pulse timing source for DUT gate command or timing reference

## Oscilloscope
Expected usage:
- segmented memory
- capture first pulse / last pulse / fault event

Recommended channels:
- CH1 = VDS
- CH2 = ID
- CH3 = VGS
- CH4 = trigger marker / gate command

## Trigger outputs from MCU
Suggested signals:
- `START_TRIG`
- `END_TRIG`
- `FAULT_TRIG`
- optional per-pulse marker

---

## 10. MCU role (STM32)

Assume MCU family: **STM32**
V1 recommendation:
- use simple `main loop + interrupts + state machine`
- avoid RTOS unless project scope grows

## MCU should do
- system state machine
- manage precharge / ready / arm / run / fault / discharge flow
- count pulses
- read status inputs
- log fault source
- generate trigger markers
- communicate with PC host
- enforce higher-level sequencing

## MCU should NOT be primary for
- microsecond-class main overcurrent protection
- first-line shutdown arbitration
- waveform-based fast fault decisions

---

## 11. Suggested firmware state machine

Suggested top-level states:

- `BOOT`
- `IDLE`
- `PRECHARGE`
- `WAIT_BUS_READY`
- `ARMED`
- `RUNNING`
- `FAULT`
- `DISCHARGE`
- `SAFE_OFF`

### Basic flow
1. `BOOT`
2. `IDLE`
3. User command -> `PRECHARGE`
4. Wait for bus stable -> `WAIT_BUS_READY`
5. If ready -> `ARMED`
6. On run command -> `RUNNING`
7. On normal completion -> `DISCHARGE` or back to `ARMED`
8. On any latched fault -> `FAULT`
9. After user reset / safe condition -> `DISCHARGE` or `IDLE`

---

## 12. Suggested firmware modules

Suggested source layout:

```text
Core/
  Src/
    main.c
    app_state.c
    app_io.c
    app_fault.c
    app_counter.c
    app_comm.c
    app_log.c
    app_config.c
  Inc/
    app_state.h
    app_io.h
    app_fault.h
    app_counter.h
    app_comm.h
    app_log.h
    app_config.h
```

### Module intent
- `app_state.*`  
  system state machine

- `app_io.*`  
  GPIO abstraction, reading inputs, driving outputs

- `app_fault.*`  
  fault collection, prioritization, latching, clear logic

- `app_counter.*`  
  pulse counting, run counters, timing utilities

- `app_comm.*`  
  UART / USB CDC protocol

- `app_log.*`  
  event log / fault log / status snapshots

- `app_config.*`  
  polarity, timing, thresholds, build-time config

---

## 13. Recommended firmware I/O abstraction

Below names are placeholders. Codex should implement them in a configurable way.

### Digital outputs
- `PRECHARGE_EN`
- `BUS_MAIN_EN`
- `DISCHARGE_EN`
- `DRIVER_EN`
- `RESET_LATCH`
- `START_TRIG`
- `END_TRIG`
- `FAULT_TRIG`
- `STATUS_LED_RUN`
- `STATUS_LED_FAULT`

### Digital inputs
- `BUS_READY_IN`
- `PRECHARGE_DONE_IN`
- `OCP_FAULT_IN`
- `TIMEOUT_FAULT_IN`
- `THERMAL_FAULT_IN`
- `DUT_OFF_CHECK_IN`
- `ESTOP_IN`
- `INTERLOCK_IN`
- `FG_PULSE_MON_IN` (optional)

### Analog inputs (optional, slow monitoring only)
- `BUS_V_ADC`
- `CAP_V_ADC`
- `TEMP_BOARD1_ADC`
- `TEMP_DUT_ADC`
- `CURRENT_MON_ADC` (optional slow monitor, not fast protection path)

---



## 13A. Preferred Board 1 status interpretation in V1

In V1, Board 1 status may be interpreted with minimal extra hardware.

Suggested inputs / derived signals:
- `PS_OK_ALL_IN`
- `BUS_V_ADC`
- `CAP_V_ADC`
- `INTERLOCK_IN`
- optional `PRECHARGE_MON_IN`
- optional `DISCHARGE_MON_IN`

Derived firmware signals:
- `BUS_READY`
- `PRECHARGE_DONE`
- `DISCHARGE_DONE`
- `BUS_UNDERVOLTAGE`
- `BUS_NOT_SAFE`

Example V1 interpretation:
- `BUS_READY = (PS_OK_ALL_IN == true) AND (BUS_V_ADC >= configured_ready_threshold)`
- `PRECHARGE_DONE = (BUS_V_ADC reaches configured precharge threshold within timeout)`
- `DISCHARGE_DONE = (BUS_V_ADC <= configured safe voltage threshold)`


## 14. Fault handling policy

Codex should implement a clear fault policy.

### Example fault sources
- OCP
- timeout
- thermal interlock
- bus undervoltage
- precharge failed
- discharge failed
- E-stop
- latch mismatch
- DUT off-check failed

### Required behavior
On fault:
1. disable driver request
2. assert `FAULT_TRIG`
3. latch internal fault state
4. stop pulse count progression
5. record fault code and timestamp / count
6. require explicit reset path before returning to armed state

### Fault priority
Recommended priority example:
1. E-stop
2. OCP
3. timeout
4. latch / off-check failure
5. thermal
6. bus readiness loss
7. communication or minor warnings

---



## 14A. Additional Board 1 related fault cases

Additional V1 Board 1 related faults to consider:

- PSU not OK
- precharge timeout
- bus not reaching ready threshold
- bus undervoltage during armed or running state
- discharge timeout
- bus remains above safe voltage after discharge command

Recommended handling:
- PSU-related faults should be logged separately from DUT-related fast protection faults
- Board 1 power readiness faults should block transition to `ARMED`
- discharge-related faults should block transition to fully safe maintenance state


## 15. Bring-up strategy

V1 firmware and hardware should be validated in stages.

### Stage 0: dry run, no DUT stress
- power-up
- precharge
- discharge
- state transitions
- comms
- trigger outputs
- status LEDs

### Stage 1: no high current
- verify function generator timing path
- verify driver enable / disable logic
- verify fault latch reset
- verify oscilloscope trigger markers

### Stage 2: low-energy path test
- reduced bus energy
- reduced pulse count
- verify shunt polarity / measurement chain
- verify OCP trip path with safe thresholds

### Stage 3: engineering pulse bring-up
- increase pulse width gradually
- increase energy gradually
- verify bus droop
- verify abnormal protection

---

## 16. PC-side software scope

V1 PC software should be simple.

## Recommended V1 host software approach
- Python-based host utility
- serial protocol over UART or USB CDC
- optional CSV logging
- optional JSON config file

### Host software responsibilities
- connect to STM32
- send configuration
- start / stop / reset
- read status
- read event log
- save fault log
- optionally generate human-readable test summary

### Recommended minimal commands
- `PING`
- `GET_STATUS`
- `GET_FAULT`
- `GET_COUNT`
- `ARM`
- `START`
- `STOP`
- `RESET_FAULT`
- `PRECHARGE`
- `DISCHARGE`

---

## 17. Recommended command protocol style

Keep protocol simple and text-readable in V1.

Example:

```text
PING
GET_STATUS
ARM
START COUNT=1000
STOP
RESET_FAULT
```

Example responses:

```text
OK
STATUS IDLE
STATUS RUNNING COUNT=123
FAULT OCP COUNT=456
DONE COUNT=1000
```

Binary protocol is not necessary for V1 unless required later.

---

## 18. Codex implementation guidelines

## Important assumptions Codex must NOT make silently
Do not assume without explicit config:
- active-high vs active-low polarity
- latch reset polarity
- relay timing
- comparator output polarity
- whether function generator pulse is directly used or only monitored
- whether trigger outputs must be pulses or level signals
- ADC scaling constants
- exact timer frequency / pulse count relationship
- whether per-pulse counting comes from MCU-generated event or external monitor input

## Coding style expectations
- readable C
- modular HAL-based implementation
- no hidden magic numbers
- centralized config
- explicit fault reasons
- simple logs
- compile cleanly with warnings enabled
- fail-safe defaults

## Firmware design preference
- state machine first
- hardware abstraction second
- command interface third
- optimization later

---



## 18A. Important non-assumptions for Codex regarding power hardware

Codex must NOT silently assume:
- fuse is definitely populated on each PSU branch in V1
- Board 1 has a dedicated analog comparator for bus-ready
- Board 1 has temperature sensing in V1
- Board 1 includes a film capacitor layer in V1
- PSU parallel mode configuration is fully transparent to firmware
- PSU foldback behavior is irrelevant to startup

These items must be treated as explicit configuration / documentation items.


## 19. Open items that must remain configurable

These should exist as compile-time or runtime config items:

- pulse target count
- max pulse width timeout
- trigger pulse width
- debounce / fault input filtering
- bus ready timeout
- precharge timeout
- discharge timeout
- optional thermal thresholds
- analog scaling factors
- fault priority mapping

---

## 20. Minimum deliverables expected from Codex

## Firmware
1. STM32 project skeleton
2. GPIO mapping layer
3. state machine implementation
4. fault manager
5. pulse counter
6. serial command parser
7. event logging structure
8. safe default startup behavior
9. unit-testable pure-C logic where practical

## PC software
1. Python CLI tool
2. serial connection handling
3. basic commands
4. status / fault display
5. CSV log export
6. optional configuration file support

---

## 21. Recommended initial development order for Codex

1. define config headers and I/O abstraction
2. implement state machine
3. implement fault manager
4. implement serial command interface
5. implement logging
6. integrate timing / counting
7. integrate analog monitoring
8. add host Python CLI
9. add scripted bring-up utilities

---

## 22. Acceptance criteria for V1 software

### Firmware acceptable when:
- boots into safe state
- does not enable driver by default
- handles precharge / arm / run / stop / fault / discharge transitions cleanly
- faults always force safe behavior
- pulse count is accurate enough for engineering validation
- logs fault source and count
- external host can command and query system

### Host software acceptable when:
- operator can connect, arm, start, stop, reset
- status and fault reason are readable
- basic logs can be saved
- no GUI is required in V1

---

## 23. Notes for future expansion

Architecture should avoid blocking future:
- multi-channel support
- channel scheduler
- more advanced host GUI
- data logging to database
- more complex instrument automation
- tighter integration with oscilloscope / function generator control

However, V1 implementation should stay single-channel and simple.

---

## 24. Summary for Codex

This project is a **single-channel STM32-based controlled short-circuit pulse test platform**.

Key rules:
- hardware handles fast protection
- MCU handles sequencing and logging
- keep firmware simple
- prefer deterministic state machine
- prefer explicit safe states
- do not over-design V1
- do not assume missing hardware details

If hardware polarity or behavior is unknown, expose it as configuration and document the assumption.


---

## 25. Current Board 1 implementation direction (informational)

Current Board 1 hardware direction includes:
- branch ORing / reverse blocking using controller + back-to-back MOSFET structure
- local bulk capacitor bank on Board 1
- polymer mid-layer support on Board 1
- resistor-based precharge path
- MOS-based precharge bypass path
- active discharge path
- permanent small bleeder resistor

These details are informational for firmware / software context and may still evolve at BOM level.
