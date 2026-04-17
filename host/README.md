# Host Software (Python)

## 中文說明

這個資料夾是 PC 端軟體，負責和 STM32 通訊，並在 V1 階段提供基本操作介面、狀態查詢、紀錄，以及示波器控制。

This host package now includes both:

- a serial CLI for scripting and bring-up
- a desktop GUI for operator control and monitoring
- a PDF extraction CLI for converting manuals/specs into text

## Install

### 中文說明

先在 `host/` 內建立 Python 虛擬環境，再用 `pip install -e .` 安裝成可直接執行的本機工具。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Usage

### 中文說明

CLI 適合做快速測試、批次腳本、或在 GUI 還沒接上前先確認通訊協定正常。

```powershell
pulse-host --port COM3 ping
pulse-host --port COM3 status
pulse-host --port COM3 arm
pulse-host --port COM3 start --count 1000
pulse-host --port COM3 get-fault
pulse-host --port COM3 monitor --csv run_log.csv --interval 0.5
pulse-host scope-identify --scope-host 192.168.0.100
pulse-host scope-preset-trigger --scope-host 192.168.0.100
pulse-host scope-single --scope-host 192.168.0.100
```

## PDF Tool

### 中文說明

已加入可直接讀取 PDF 的工具。它會先用 pypdf 擷取文字，若內容幾乎為空，再自動改用 pymupdf 嘗試擷取。
這對儀器手冊、規格文件整理很有幫助。

```powershell
pulse-pdf ..\docs\instruments\DSO-X-4024G-programmer.pdf --out .\out\scope_manual.txt
```

OCR 範例（強制 OCR，適合掃描型 PDF）：

```powershell
pulse-pdf ..\docs\instruments\DSO-X-4024G-programmer.pdf --ocr-mode force --ocr-lang eng --out .\out\scope_manual_ocr.txt
```

中文 OCR 範例（繁中+英文）：

```powershell
pulse-pdf .\your_scan.pdf --ocr-mode force --ocr-lang chi_tra+eng --out .\out\scan_ocr.txt
```

可選參數：

- `--max-pages N`：只先抽前 N 頁，適合快速測試
- `--out PATH`：指定輸出文字檔路徑
- `--ocr-mode off|auto|force`：是否啟用 OCR
- `--ocr-lang`：OCR 語言，例如 `eng`、`chi_tra+eng`
- `--ocr-dpi`：OCR 圖像 DPI，預設 300

### OCR 環境注意事項（Windows）

- 除了 Python 套件外，還需要安裝 Tesseract OCR 可執行檔。
- 安裝後請把 `tesseract.exe` 所在路徑加到 `PATH`。
- 若你還沒安裝 Tesseract，`--ocr-mode force` 會提示缺少可執行檔。

## GUI

### 中文說明

GUI 是給實驗台操作用的桌面介面，適合連線、查狀態、執行基本指令與監看資料。

```powershell
pulse-host-gui
```

GUI functions currently included:

### 中文說明

目前 GUI 已包含串口控制、狀態輪詢、CSV 紀錄，以及示波器的基本 SCPI 控制。對 V1 bring-up 已經夠用。

- serial port selection and connect/disconnect
- `Ping`, `Precharge`, `Arm`, `Start`, `Stop`, `Reset Fault`, `Discharge`
- live `STATUS`, `FAULT`, `COUNT` refresh
- live `SYNC_COUNT` refresh for function generator sync pulse counting
- periodic monitor polling
- optional CSV logging during monitor mode
- basic Keysight scope control over SCPI/TCP (`*IDN?`, Run, Stop, Single, Clear, Autoscale, trigger preset)

## Qt Designer (Optional)

### 中文說明

如果你想要接近 C# 拖拉式編輯 UI 的流程，可以改用 PySide6 + Qt Designer。
這可以在 VS Code 內開啟終端後直接啟動，不需要離開目前開發流程。

安裝：

```powershell
pip install -e .[qt]
```

啟動 Designer（編輯 .ui）：

```powershell
pulse-host-qt-designer
```

預覽 .ui（不需先轉成 .py）：

```powershell
pulse-host-qt-preview
```

指定 UI 檔：

```powershell
pulse-host-qt-designer --ui .\src\pulse_host\ui\main_window.ui
pulse-host-qt-preview --ui .\src\pulse_host\ui\main_window.ui
```

## Scope CLI

### 中文說明

現在除了 GUI，也可以直接用 CLI 對 `Keysight DSO-X 4024G` 做基本 SCPI 控制，適合先做 bench bring-up 或腳本化驗證。

```powershell
pulse-host scope-identify --scope-host 192.168.0.100
pulse-host scope-run --scope-host 192.168.0.100
pulse-host scope-stop --scope-host 192.168.0.100
pulse-host scope-single --scope-host 192.168.0.100
pulse-host scope-clear --scope-host 192.168.0.100
pulse-host scope-autoscale --scope-host 192.168.0.100
pulse-host scope-preset-trigger --scope-host 192.168.0.100
```

可搭配參數：

- `--scope-host`
- `--scope-port`
- `--scope-timeout`

## Current Bring-Up Target

### 中文說明

如果你手上只有 MCU 板、訊號產生器和示波器，也可以先做出第一階段整合。這個階段的目的不是 DUT 測試，而是先打通計數、通訊與儀器控制鏈路。

With only these items on hand:

- STM32 board
- function generator with SYNC output
- Keysight DSO-X 4024G

you can already start on this reduced flow:

1. wire FG `SYNC OUT` to the MCU `FG_PULSE_MON_IN` pin
2. read `SYNC_COUNT` from the MCU over serial
3. control the oscilloscope from the host GUI or CLI over SCPI/TCP

Current firmware default mapping for `FG_PULSE_MON_IN` is `PB12`; adjust it in `firmware/Core/Src/board_config.c` if needed.

中文補充：如果你的 SYNC 線不是接到 `PB12`，請直接修改 `firmware/Core/Src/board_config.c` 內的 `fg_pulse_mon_in` 定義。
