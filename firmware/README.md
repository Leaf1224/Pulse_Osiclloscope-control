# Firmware Skeleton (STM32, V1)

## 中文說明

這個資料夾是 STM32 韌體主體。它的目標不是先做滿所有功能，而是先建立一個安全、可擴充、可 bring-up 的 V1 基礎架構。

This directory follows the module structure requested in the V1 context document.

## Current Intent

### 中文說明

目前韌體的設計原則是：

- 快速保護以硬體為主，不把 MCU 當第一道防線
- MCU 主要負責狀態機、流程、記錄與通訊
- 不確定的極性與腳位都留成可調整項
- 先避免重度依賴 Cube 自動產碼

- Keep hardware-fast protection outside MCU firmware
- Implement deterministic state machine and fault policy in MCU
- Keep polarity/timing assumptions configurable
- Avoid mandatory CubeMX/CubeIDE clicking for initial project bring-up

## Manual Build Path

### 中文說明

這套骨架目前是手寫的 bare-metal 專案，先求可控、可理解、可直接改。你後面如果要再導回 Cube/HAL 也可以，但現在不需要先卡在 IDE 設定。

This scaffold now includes a handwritten bare-metal STM32F401xC environment:

- `CMakeLists.txt`
- `startup/startup_stm32f401xc.s`
- `linker/STM32F401xC_FLASH.ld`
- `Core/Src/platform.c`
- `Core/Src/platform_comm.c`
- `Core/Src/board_config.c`

Default assumptions:

### 中文說明

目前先用比較保守的預設條件：HSI 16 MHz、1 ms SysTick、USART2 當主控通訊埠。這些都可以在後續依板子設計再調整。

- MCU: `STM32F401xB/C`
- Clock source: HSI 16 MHz
- SysTick: 1 ms
- UART console: USART2 on `PA2/PA3`, 115200 baud

Use `board_config.c` as the single place to adapt GPIO mapping to your PCB.

## Type-C PC Communication (USB CDC)

### 中文說明

你提供的板子配置是 Type-C 直連 MCU 的 D+/D-（PA11/PA12）。
FW 現在已改成「通訊層抽象化」：

- 優先嘗試 USB CDC backend
- USB backend 未接上時自動回退 UART

實作入口：

- `Core/Src/platform_comm.c`
- `Core/Inc/platform_comm.h`

你需要做的最後一步是把 USB stack 接進來：

1. 將 `Core/Src/platform_usb_cdc_template.c` 複製為 `Core/Src/platform_usb_cdc.c`
2. 以 AT32/STM32 對應 USB library 實作三個函式：
	- `platform_usb_cdc_init()`
	- `platform_usb_cdc_read_line()`
	- `platform_usb_cdc_write_str()`
3. 把 `platform_usb_cdc.c` 加入建置

啟動訊息判讀：

- `BOOT V1_PULSE_PLATFORM COMM=USB_CDC`：代表 USB CDC backend 已啟用
- `BOOT V1_PULSE_PLATFORM COMM=UART_FALLBACK`：代表目前仍用 UART

### Important Note

From your schematic text extraction, the MCU symbol is `AT32F403ACCU`, not STM32F401.
Current firmware architecture is now ready for Type-C USB CDC, but the final USB backend implementation must match the actual MCU vendor USB SDK.

中文補充：如果你的 PCB 腳位跟目前預設不同，優先改 `board_config.c`，不要直接把上層狀態機或應用邏輯寫死在腳位上。

## Build Outputs

### 中文說明

建置完成後，主要會得到一個 ELF；如果工具鏈有 `objcopy`，也會額外產生 HEX 與 BIN，方便配合不同燒錄工具。

After building, the main firmware image is:

- `v1_pulse_platform_f401.elf`

If `arm-none-eabi-objcopy` is available, the build also generates:

- `v1_pulse_platform_f401.bin`
- `v1_pulse_platform_f401.hex`

## Which File To Flash

### 中文說明

如果你不確定燒哪個檔，先燒 `.elf`。只有在燒錄工具明確要求 raw binary，才改用 `.bin`，而且要記得地址是 `0x08000000`。

Use one of these, depending on your flashing tool:

- `v1_pulse_platform_f401.elf`
	- best if your tool understands ELF directly and you also want symbols for debug
- `v1_pulse_platform_f401.hex`
	- good for many GUI flash tools and production-style programming flows
- `v1_pulse_platform_f401.bin`
	- use only when your flash tool also lets you specify the start address explicitly

For this MCU, the flash base address is `0x08000000`.

If you are not sure which one to use, flash the `.elf` first.

## Recommended Default

### 中文說明

目前 bring-up 階段最簡單的選擇就是直接燒 `v1_pulse_platform_f401.elf`。

For current bring-up, the safest default answer is:

- flash `v1_pulse_platform_f401.elf`

Use `.bin` only if your programmer asks for a raw binary and lets you set address `0x08000000`.

## Core Modules

### 中文說明

模組拆分是依照功能責任切開，讓你後續接硬體或加功能時，不會所有東西都塞進 `main.c`。

- `app_state.*`: top-level state machine and sequencing
- `app_io.*`: abstracted digital/analog IO interface
- `app_fault.*`: fault latch, priority, reset behavior
- `app_counter.*`: pulse counting and simple timers
- `app_comm.*`: text command parsing and command handling
- `app_log.*`: event/fault ring buffer logging
- `app_config.*`: centralized static config defaults

## Integration Notes

### 中文說明

目前 `app_io.c` 裡還有 stub 值，這是刻意保留給實機整合用的。真正接板時，這裡要換成實際 GPIO/ADC/中斷來源。

- Replace software stubs in `app_io.c` with HAL GPIO/ADC reads and writes.
- Connect hardware fault inputs to EXTI or fast sampled paths as required.
- Keep fail-safe startup behavior: driver disabled by default.
