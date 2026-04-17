# V1 受控短路脈衝測試平台  
**提供給 Codex 的 FW/SW 開發背景**

## 1. 專案目標

建立一套**單通道工程驗證平台**，用於對**離散式 MOSFET DUT** 進行**受控短路脈衝測試**。

V1 **不是**完整的 AEC qualification 系統。

### V1 目標
- DUT：**離散式 MOSFET**，無內建 thermal shutdown
- Bus 電壓：**14 V nominal**
- 目標電流：**100 A**
- Pulse width：**1 ms 到 10 ms**，可調
- 第一版必須支援 **10 ms**
- 允許的 bus droop 目標：**<= 0.5 V**
- 環境：**僅室溫**
- 通道數：**單通道**
- 主要目的：**架構驗證 / 工程 bring-up**

---

## 2. V1 的非目標（Non-goals）

V1 **不要假設**需要以下功能：

- 不做 `-40°C` 低溫 qualification
- 不做多通道
- 不模擬 smart power switch 的 thermal shutdown / auto-retry
- 不做 MOS 線性限流
- 不承諾長時間 `30% duty`
- 不承諾 `1,000,000 cycles` qualification-grade robustness
- V1 不要求 FPGA
- V1 不要求 RTOS

---

## 3. 高階系統架構

## Board 1 = Power Board
目的：
- 將 4 路 PSU 輸入匯流成一個本地 14 V bus
- 提供本地儲能
- 管理 precharge / discharge / bus readiness

主要功能：
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
- 對 Board 2 輸出 status signals

## Board 2 = DUT / Driver / Protection / Control Board
目的：
- 對 DUT 施加受控脈衝應力
- 量測關鍵訊號
- 執行快速硬體保護
- 計數 pulse 並管理 sequencing

主要功能：
- DUT mount
- main current path
- gate driver
- gate resistor / gate protection
- shunt / current sensing
- short-circuit abnormal protection
- 對 oscilloscope 的 trigger I/O
- 與 Board 1 的 status interface
- MCU control

## 外部限流電阻模組
目的：
- V1 的主限流元件
- 定義受控 100 A pulse 行為

備註：
- **不要**把 DUT 視為正常工作下的主限流器
- 限流電阻模組應視為主功率路徑的一部分

---

## 4. 主電氣路徑

### 充電路徑
`4x PSU -> branch protection -> ORing -> 14 V bus / CAP BANK`

### 測試路徑
`14 V bus / CAP BANK -> current-limit resistor module -> DUT -> shunt / return`

### 重要設計原則
- **bus 是近似 DC**
- **電流是脈衝**
- pulse 由 **DUT gate switching** 形成
- bus 本身**不做 chopping**

---

## 5. Power 策略

### PSU 策略
- 4 台可程式化 PSU 並聯成一個 14 V bus
- 每台 PSU 可略微調高到 14 V 以上，以補償小壓降
- 使用 ORing 的目的：
  - 防止 backfeed
  - 降低多台 PSU 互相打架
  - 隔離故障支路
- ORing **不是** bus droop 的主要解法

### CAP BANK 策略
V1 初始目標：
- 總本地電容約為 `0.2 F to 0.4 F`

建議結構：
- bulk capacitance
- polymer / 中頻層
- film + 小 MLCC / 高頻層

### Precharge / discharge
Board 1 必須支援：
- full bus connect 前先 precharge
- stop / fault / shutdown 後的安全 discharge

---

## 5A. V1 目前已假設的硬體決策

以下 Board 1 假設目前較偏好作為 V1 的工作假設，除非後續明確更改，否則 Codex 應視為有效：

- 上游來源使用 4 台可程式化 PSU
- 每一路 PSU branch 在 Board 1 上都包含 ORing / reverse-blocking 行為
- V1 的 Board 1 **不包含獨立溫度感測器**
- V1 的 Board 1 **不包含 film capacitor layer**
- 本地 bus 上有一個 permanent small bleeder resistor
- 初始 bleeder 值約為 `1 kΩ`
- V1 不要求 Board 1 的 bus readiness 由 dedicated hardware comparator 提供
- Board 1 的 bus readiness 可由 firmware 根據以下資訊推導：
  - PSU OK 資訊
  - 本地 bus voltage ADC 量測
  - precharge completion timing / state

這些假設應保持可配置，但 Codex 不應自行假設有額外的 Board 1 analog supervision 硬體，除非後續明確加入。

## 5B. 上游 PSU 行為假設

V1 使用具有保護與狀態功能的可程式化 PSU。

重要假設：
- 上游 PSU 行為**不等同**於理想被動 DC source
- PSU 端保護可能包含 CV/CC、OVP/UVL、foldback、power-good indication、remote enable / disable
- firmware **不得假設** PSU output enable 就等於 local bus ready
- firmware **不得假設** PSU 電壓穩壓本身可取代 Board 1 的 precharge logic
- 若使用 remote sense，應只補償到 Board 1 local bus，不應補償到 DUT pulse loop
- bring-up 階段要特別注意 foldback mode，因為它可能干擾 precharge 與 bus charging 行為

Codex 應將 PSU 相關的 readiness 與 fault handling 設計成顯性邏輯，而不是隱含假設。

---

## 6. 限流策略

V1 使用：
- **外部低值、大功率、脈衝型電阻模組**

不要假設：
- 主動限流器
- MOS 線性限流運作
- V1 具有 closed-loop current control

初始電阻範圍：
- 總等效電阻約 `100 mΩ to 120 mΩ`

模組建議：
- pulse-rated
- low inductance
- high power
- mechanically replaceable

---

## 7. 機構 / 互連概念

目前較偏好的方向：
- Board 1 與 Board 2 之間以**上下疊層的正負 bus bars** 連接
- 限流電阻模組安裝在靠近 / 疊在 Board 2 的 power entry 區域
- 正端路徑先進限流模組
- 負端回流則由 DUT / shunt 區經 bus bar 回到 Board 1 return

重要 layout 意圖：
- 保持正負主路徑彼此靠近
- 最小化 loop area
- 讓電阻模組靠近 DUT
- 讓 shunt 靠近 DUT return
- 主 100 A 路徑**不要**使用 signal-style card connectors

---

## 8. 保護哲學

## 快速保護必須以硬體為先
**不要**依賴 MCU firmware 作為第一線的微秒級保護。

快速保護應以硬體實作：
- comparator OCP
- timeout protection
- fault latch

### 保護角色
- **Comparator OCP**：立即過流切斷
- **Timeout**：執行 pulse width 上限限制
- **Fault latch**：故障後鎖定系統，防止 uncontrolled retrigger
- **DUT off check**：確認 pulse 結束後電流確實回到 off 狀態

### Thermal interlock
V1 可允許 thermal interlock，但其角色是：
- 提供 pulse 間冷卻允許
- 不是用來取代 pulse 內的快速保護

---

## 9. 儀器概念

## Function generator
- 現有 `33250A` 繼續作為 DUT gate command 或 timing reference 的 pulse timing source

## Oscilloscope
預期使用方式：
- segmented memory
- 擷取 first pulse / last pulse / fault event

建議通道：
- CH1 = VDS
- CH2 = ID
- CH3 = VGS
- CH4 = trigger marker / gate command

## MCU 輸出的 trigger signals
建議：
- `START_TRIG`
- `END_TRIG`
- `FAULT_TRIG`
- optional per-pulse marker

---

## 10. MCU 角色（STM32）

假設 MCU family：**STM32**

V1 建議：
- 使用簡單的 `main loop + interrupts + state machine`
- 除非專案範圍擴大，否則避免 RTOS

## MCU 應負責
- system state machine
- 管理 precharge / ready / arm / run / fault / discharge flow
- pulse count
- 讀取 status inputs
- 記錄 fault source
- 產生 trigger markers
- 與 PC host 通訊
- 執行較高層的 sequencing

## MCU 不應作為主責的功能
- 微秒級主過流保護
- 第一線 shutdown arbitration
- 依波形做快速 fault decisions

---

## 11. 建議的 firmware state machine

建議 top-level states：

- `BOOT`
- `IDLE`
- `PRECHARGE`
- `WAIT_BUS_READY`
- `ARMED`
- `RUNNING`
- `FAULT`
- `DISCHARGE`
- `SAFE_OFF`

### 基本流程
1. `BOOT`
2. `IDLE`
3. 使用者命令 -> `PRECHARGE`
4. 等待 bus 穩定 -> `WAIT_BUS_READY`
5. 若 ready -> `ARMED`
6. 收到 run command -> `RUNNING`
7. 正常完成 -> `DISCHARGE` 或回到 `ARMED`
8. 任何 latched fault -> `FAULT`
9. 使用者 reset / 條件安全後 -> `DISCHARGE` 或 `IDLE`

---

## 12. 建議的 firmware 模組

建議 source layout：

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

### 模組意圖
- `app_state.*`  
  system state machine

- `app_io.*`  
  GPIO abstraction、輸入讀取、輸出驅動

- `app_fault.*`  
  fault collection、priority、latching、clear logic

- `app_counter.*`  
  pulse counting、run counters、timing utilities

- `app_comm.*`  
  UART / USB CDC protocol

- `app_log.*`  
  event log / fault log / status snapshots

- `app_config.*`  
  polarity、timing、thresholds、build-time config

---

## 13. 建議的 firmware I/O abstraction

以下名稱僅為 placeholder。Codex 應以可配置方式實作。

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

### Analog inputs（optional，僅慢速監控）
- `BUS_V_ADC`
- `CAP_V_ADC`
- `TEMP_BOARD1_ADC`
- `TEMP_DUT_ADC`
- `CURRENT_MON_ADC` (optional slow monitor, not fast protection path)

---

## 13A. V1 中偏好的 Board 1 status 解讀方式

在 V1 中，Board 1 status 可用最少的額外硬體來解讀。

建議輸入 / 推導訊號：
- `PS_OK_ALL_IN`
- `BUS_V_ADC`
- `CAP_V_ADC`
- `INTERLOCK_IN`
- optional `PRECHARGE_MON_IN`
- optional `DISCHARGE_MON_IN`

由 firmware 推導出的訊號：
- `BUS_READY`
- `PRECHARGE_DONE`
- `DISCHARGE_DONE`
- `BUS_UNDERVOLTAGE`
- `BUS_NOT_SAFE`

V1 範例解讀：
- `BUS_READY = (PS_OK_ALL_IN == true) AND (BUS_V_ADC >= configured_ready_threshold)`
- `PRECHARGE_DONE = (BUS_V_ADC reaches configured precharge threshold within timeout)`
- `DISCHARGE_DONE = (BUS_V_ADC <= configured safe voltage threshold)`

---

## 14. Fault handling policy

Codex 應實作清楚明確的 fault policy。

### fault source 範例
- OCP
- timeout
- thermal interlock
- bus undervoltage
- precharge failed
- discharge failed
- E-stop
- latch mismatch
- DUT off-check failed

### 必要行為
On fault：
1. disable driver request
2. assert `FAULT_TRIG`
3. latch internal fault state
4. stop pulse count progression
5. 記錄 fault code 與 timestamp / count
6. 在回到 armed state 之前，要求 explicit reset path

### Fault priority
建議 priority 範例：
1. E-stop
2. OCP
3. timeout
4. latch / off-check failure
5. thermal
6. bus readiness loss
7. communication or minor warnings

---

## 14A. 額外的 Board 1 相關 fault cases

V1 中可額外考慮的 Board 1 fault：

- PSU not OK
- precharge timeout
- bus 未達 ready threshold
- armed 或 running 時發生 bus undervoltage
- discharge timeout
- 發出 discharge command 後，bus 仍高於 safe voltage

建議處理：
- PSU 相關 fault 應與 DUT 相關快速保護 fault 分開記錄
- Board 1 power readiness faults 應阻止系統進入 `ARMED`
- discharge 相關 faults 應阻止系統進入完全安全的 maintenance state

---

## 15. Bring-up 策略

V1 的 firmware 與 hardware 應分階段驗證。

### Stage 0：dry run，無 DUT stress
- power-up
- precharge
- discharge
- state transitions
- comms
- trigger outputs
- status LEDs

### Stage 1：無高電流
- 驗證 function generator timing path
- 驗證 driver enable / disable logic
- 驗證 fault latch reset
- 驗證 oscilloscope trigger markers

### Stage 2：低能量路徑測試
- reduced bus energy
- reduced pulse count
- 驗證 shunt polarity / measurement chain
- 以安全 thresholds 驗證 OCP trip path

### Stage 3：工程脈衝 bring-up
- 逐步增加 pulse width
- 逐步增加能量
- 驗證 bus droop
- 驗證 abnormal protection

---

## 16. PC 端 software 範圍

V1 PC software 應保持簡單。

## 建議的 V1 host software 方式
- Python-based host utility
- serial protocol over UART or USB CDC
- optional CSV logging
- optional JSON config file

### Host software 職責
- connect 到 STM32
- send configuration
- start / stop / reset
- read status
- read event log
- save fault log
- optional 產生 human-readable test summary

### 建議的最小命令集
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

## 17. 建議的 command protocol 風格

V1 中保持簡單、可讀的文字型協定即可。

範例：

```text
PING
GET_STATUS
ARM
START COUNT=1000
STOP
RESET_FAULT
```

範例回應：

```text
OK
STATUS IDLE
STATUS RUNNING COUNT=123
FAULT OCP COUNT=456
DONE COUNT=1000
```

除非後續有需要，V1 不必採用 binary protocol。

---

## 18. Codex 實作指引

## Codex 不應默默假設的事項
以下項目若沒有明確設定，Codex 不應自行假設：
- active-high vs active-low polarity
- latch reset polarity
- relay timing
- comparator output polarity
- function generator pulse 是直接使用還是僅監看
- trigger outputs 是 pulse 還是 level signals
- ADC scaling constants
- exact timer frequency / pulse count relationship
- per-pulse counting 是來自 MCU-generated event 還是 external monitor input

## Coding style expectations
- readable C
- modular HAL-based implementation
- no hidden magic numbers
- centralized config
- explicit fault reasons
- simple logs
- compile cleanly with warnings enabled
- fail-safe defaults

## Firmware 設計偏好
- state machine first
- hardware abstraction second
- command interface third
- optimization later

---

## 18A. Codex 對 power hardware 的非假設項

Codex **不得默默假設**：
- V1 每一路 PSU branch 一定都有 fuse
- Board 1 一定有 dedicated analog comparator 作為 bus-ready
- V1 的 Board 1 一定有 temperature sensing
- Board 1 一定有 film capacitor layer
- PSU parallel mode configuration 對 firmware 完全透明
- PSU foldback behavior 對 startup 無影響

這些都應視為 explicit configuration / documentation items。

---

## 19. 必須保持可配置的 open items

這些項目應存在於 compile-time 或 runtime config 中：

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

## 20. 對 Codex 的最小交付要求

## Firmware
1. STM32 project skeleton
2. GPIO mapping layer
3. state machine implementation
4. fault manager
5. pulse counter
6. serial command parser
7. event logging structure
8. safe default startup behavior
9. 盡可能做成可單元測試的 pure-C logic

## PC software
1. Python CLI tool
2. serial connection handling
3. basic commands
4. status / fault display
5. CSV log export
6. optional configuration file support

---

## 21. 建議的初始開發順序

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

## 22. V1 software 驗收條件

### Firmware 可接受條件
- 開機進入 safe state
- 預設不會 enable driver
- 可正確處理 precharge / arm / run / stop / fault / discharge state transitions
- 發生 fault 時一定進入安全行為
- pulse count 對工程驗證已足夠準確
- 會記錄 fault source 與 count
- 外部 host 可下命令、可查詢狀態

### Host software 可接受條件
- 操作者可 connect、arm、start、stop、reset
- status 與 fault reason 可讀
- 可儲存基本 logs
- V1 不要求 GUI

---

## 23. 對未來擴充的備註

架構應避免阻礙未來擴充：
- multi-channel support
- channel scheduler
- 更進階的 host GUI
- data logging to database
- 更複雜的 instrument automation
- 與 oscilloscope / function generator 更緊密整合

但 V1 的實作仍應保持：
- 單通道
- 簡單
- 不過度設計

---

## 24. 給 Codex 的摘要

本專案是一套**單通道、以 STM32 為核心的受控短路脈衝測試平台**。

核心規則：
- 快速保護由硬體處理
- MCU 負責 sequencing 與 logging
- firmware 要保持簡單
- 優先 deterministic state machine
- 優先 explicit safe states
- V1 不要 over-design
- 不要自行假設缺失的硬體細節

若硬體 polarity 或行為不明，應把它暴露成 configuration，並明確記錄假設。

---

## 25. 目前 Board 1 的實作方向（資訊性）

目前 Board 1 的硬體方向包含：
- branch ORing / reverse blocking 採 controller + back-to-back MOSFET 結構
- Board 1 上有本地 bulk capacitor bank
- Board 1 支援 polymer mid-layer
- 電阻式 precharge path
- MOS-based precharge bypass path
- active discharge path
- permanent small bleeder resistor

這些內容是提供 FW/SW 背景的資訊性描述，BOM 細節後續仍可能調整。

---

## 26. 目前偏好的 Board 2 硬體工作假設（資訊性）

除非後續明確變更，V1 的 Board 2 可先採以下工作假設：

- logic / protection domain 以 **3.3V** 為主
- gate driver domain 先以 **6V nominal** 為主
- current sensing 採 **low-side shunt**
- shunt 初始值為 **2 mΩ**
- current monitor path 只作**慢速監控 / 記錄**，不作為第一線快速保護
- VDS / VGS 板上量測以 **ADC monitoring / slow observation** 為主
- 真正高速 VDS / VGS 波形仍以 oscilloscope 直接量測為主
- Board 2 應保留 **socket path** 與 **direct-solder DUT path** 的雙路徑概念，用於 bring-up / A-B comparison
- 一次只允許啟用一條 DUT path，不可同時並用

這些屬於目前偏好的硬體工作假設，目的是幫助 Codex 理解 V1 系統行為與 bring-up 流程，而不是凍結最終硬體細節。

---

## 27. V1 動態目標補充（資訊性）

除了 100A / 1ms~10ms 的 nominal 目標外，V1 目前可接受的動態目標可再補充如下：

- 不強求在極短亞微秒 / 單位微秒內到達最終電流
- V1 可接受的工程目標為：  
  **約 30 µs 左右到達目標電流 100A 附近**
- 因此，firmware / software 不應默默假設「上電後數微秒內一定到達穩態電流」
- 在資料記錄與 fault interpretation 上，應區分：
  - turn-on 前緣過渡區
  - 近穩態電流區
  - turn-off 與 fault recovery 區

這一點對後續的 log interpretation、fault review、以及 bring-up documentation 很重要。

---

## 28. 與主功率互連相關、Codex 不應誤判的事項

V1 為分板式架構：

- Board 1（power / CAP bank）
- external current-limit resistor module
- Board 2（DUT / driver / protection）

因此 Codex 不應自行假設：
- DUT 與 CAP BANK 是零距離連接
- 主功率回路寄生參數可忽略
- turn-on 電流在最前緣就必然等於穩態值
- socket path 與 direct-solder path 的寄生條件完全相同

對 FW/SW 來說，這代表：
- fault thresholds 與 blanking windows 應保持可調
- bring-up logs 應區分不同 DUT mounting path
- 若後續加入 path selection 設定，應在 log / status 中清楚記錄當前使用的是：
  - `SOCKET_PATH`
  - `DIRECT_PATH`

---

## 29. ADC scaling / monitor interpretation 建議

Codex 應將所有 monitor scaling 視為**顯性設定**，不得硬編碼為固定值。

至少應可配置：
- `BUS_V_ADC` scaling
- `CAP_V_ADC` scaling
- `CURRENT_MON_ADC` scaling
- `VDS_MON_ADC` scaling
- `VGS_MON_ADC` scaling
- `TEMP_DUT_ADC` scaling
- `TEMP_BOARD_ADC` scaling

建議：
- 將 scaling constants 集中於 config table
- 日誌中保留 raw ADC value 與 engineering unit 兩種資訊（至少於 debug 模式）
- 在 bring-up 階段允許 host 端讀取 raw + converted values，以便校正

---

## 30. Board 2 bring-up 順序補充

若 Board 2 具備 socket path 與 direct-solder path，建議 bring-up 順序如下：

### Stage A
先不接高能量 DUT，驗證：
- driver enable / disable
- fault latch
- ADC chain
- trigger output
- GPIO polarity

### Stage B
優先使用 **direct-solder DUT path** 做板級 bring-up：
- 可降低 socket / contact variability
- 有利於驗證主功率路徑、保護鏈與量測鏈本體

### Stage C
在 direct path 工作正常後，再切換到 **socket path**：
- 比較兩條 DUT path 的差異
- 記錄是否出現額外 overshoot / ringing / current rise delay / contact-related anomalies

### Stage D
若 socket path 與 direct path 表現差異顯著：
- 不應直接將其歸因於 firmware
- 應先標記為 path-dependent hardware behavior，並保留比較紀錄

這些步驟對 Codex 來說，主要影響：
- bring-up script
- log annotation
- host software test metadata
