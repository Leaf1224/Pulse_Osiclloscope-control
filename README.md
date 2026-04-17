# V1 Controlled Short-Circuit Pulse Test Platform

## 中文說明

這個工作區目前已整理成一個可直接開發的 V1 專案骨架，分成三個主要部分：

- `firmware/`：STM32 韌體
- `host/`：PC 端軟體，包含 CLI 與 GUI
- `docs/`：需求文件、硬體基線與儀器資料

This workspace now includes an initial development environment scaffold for:

- STM32 firmware state-machine project skeleton (single-channel V1)
- Python host CLI for serial command/control and logging

## Confirmed Hardware Baseline

### 中文說明

目前已確認的開發基線如下：

- 示波器為 Keysight InfiniiVision DSO-X 4024G
- MCU 目標族群為 STM32F401xB/C
- 目前觀察到的晶片資訊為 Device ID `0x423`、Flash `128 KB`

- Oscilloscope: Keysight InfiniiVision DSO-X 4024G
- MCU family target: STM32F401xB/C
- Observed MCU identifiers:
  - Device ID: `0x423`
  - Flash size: `128 KB`

Detailed baseline notes are in `docs/hardware_baseline.md`.

## Workspace Layout

### 中文說明

建議把需求、韌體與 PC 軟體分開管理。現在的資料夾分法已經是這個方向，後續擴充時會比較不容易混亂。

```text
docs/
  context/
  instruments/
firmware/
  Core/
    Inc/
    Src/
host/
  src/pulse_host/
```

## Documentation Layout

### 中文說明

所有文件集中在 `docs/` 下方，方便把實作檔與參考檔分離。產品需求、儀器資料、硬體說明可以各自維護。

- Product context: `docs/context/`
- Hardware baseline and engineering notes: `docs/`
- Instrument-related files: `docs/instruments/`

## Quick Start

### 中文說明

如果你是第一次進來這個專案，建議先看需求文件，再決定要先做 FW 還是 SW。現在兩邊都已有骨架，可以直接往下接實機。

1. Read `docs/context/codex_fw_sw_context_v1_zh.md` or `docs/context/codex_fw_sw_context_v1_en.md` for product constraints.
2. Start firmware implementation from `firmware/Core/Src/main.c`.
3. Create Python virtual environment under `host/` and install dependencies.
4. Run the host CLI to talk to the STM32 over UART/USB CDC.

## Host Setup

### 中文說明

這一段是 PC 軟體的安裝方式。先進到 `host/`，建立 Python 虛擬環境，再安裝套件即可。

From `host/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Run Host CLI

### 中文說明

如果你只想先做基本通訊驗證，不一定要先開 GUI。CLI 很適合先做串口 bring-up 或測試指令流程。

```powershell
pulse-host --port COM3 ping
pulse-host --port COM3 status
pulse-host --port COM3 arm
```

## Manual Firmware Path

### 中文說明

如果你不想先用 CubeMX 產生專案，這裡已經有一套手寫的 STM32F401 韌體骨架可直接當起點使用，包含 startup、linker 與基本平台層。

If you do not want to generate a project in CubeMX first, use the handwritten STM32F401 firmware scaffold under `firmware/`.
It already includes a startup file, linker script, platform GPIO/UART layer, and a default pin map.
