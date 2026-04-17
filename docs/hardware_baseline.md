# Hardware Baseline (V1)

## 中文說明

這份文件記錄目前已經確認的硬體基線，目的是讓韌體、軟體與儀器控制都建立在同一組已知條件上，而不是各自假設。

This file captures hardware facts confirmed during bring-up.

## Instruments

### 中文說明

目前已確認的主要儀器是 DSO-X 4024G。V1 階段可以先把它當成量測與觸發觀察的主工具。

- Oscilloscope: Keysight InfiniiVision `DSO-X 4024G`
  - 4 channels available for VDS / ID / VGS / trigger marker mapping.
  - Suggested use: segmented acquisition for first/last/fault pulse capture.

## MCU

### 中文說明

目前 MCU 基線是 STM32F401xB/C，並且已知 Flash 容量是 128 KB。這會直接影響韌體複雜度與記錄策略。

- Target MCU line: `STM32F401xB/C`
- Observed via probe:
  - Device ID: `0x423`
  - Flash size: `128 KB`

## Firmware Implementation Implications

### 中文說明

因為這顆 MCU 資源有限，V1 韌體應維持精簡，先以狀態機和固定大小 buffer 為主，不要一開始就做太重的框架。

- Keep V1 firmware footprint conservative for 128 KB flash.
- Start with no RTOS, main loop + interrupt model.
- Keep logs compact (ring buffer) and avoid heavy printf formatting in runtime path.
- Use fixed-size buffers for command parser and UART RX line handling.

## Suggested CubeMX Starting Point (for F401xB/C)

### 中文說明

即使你目前不想先用 Cube，這裡還是保留一份適合 F401 的起始配置方向，方便未來要切回 CubeMX 時有依據。

- SYSCLK: stable configuration suitable for 1 ms scheduler tick.
- Time base: SysTick 1 ms.
- UART/USB CDC: one control channel for text command protocol.
- GPIO groups:
  - safety/fault inputs
  - sequencer outputs (precharge, bus, discharge, driver)
  - trigger outputs (start/end/fault)
- ADC channels:
  - BUS_V_ADC
  - CAP_V_ADC
  - optional TEMP/CURRENT monitor channels

## Host Software Implications

### 中文說明

PC 端軟體目前採用 Python 是合理的，因為它夠快完成 bring-up，也容易後續再加 GUI、紀錄或 SCPI 控制。

- Existing Python CLI skeleton is compatible with text protocol workflow.
- Instrument automation is optional in V1. If added later, start with SCPI scripts for DSO-X 4024G snapshot/export tasks.

## Bring-Up With Current Available Hardware

### 中文說明

在你目前只有示波器、MCU 板與訊號產生器的情況下，仍然可以先完成一個有價值的縮小版整合里程碑，也就是先驗證 SYNC 計數與示波器控制。

The currently available bench set is sufficient for an initial reduced integration milestone:

- MCU counts function generator SYNC pulses
- host software reads `SYNC_COUNT` over serial
- host software controls DSO-X 4024G over SCPI/TCP

This is enough to validate:

- MCU input capture path
- serial telemetry path
- PC-to-scope control path

without needing the full power path or DUT stress hardware yet.
