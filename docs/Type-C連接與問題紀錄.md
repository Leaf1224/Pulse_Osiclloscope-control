# Type-C連接與問題紀錄

## 目的

這份文件記錄本專案在 `STM32F401CCU6` 小板上，透過 `USB Type-C` 與 PC 通訊時的接線重點、韌體配置、實際遇到的問題，以及最後確認可正常運作的結果。

目前已驗證：

- 板子可透過 `Type-C` 在 Windows 枚舉成虛擬 `COM Port`
- Host 可用 `pulse-host` / `python -m host.src.pulse_host.cli` 與板子通訊
- 指令 `ping`、`status` 可正常回應

## Type-C硬體連接重點

裝置端連接原則如下：

- `VBUS` 要能進板，提供 `5V`
- 板上電源需將 `VBUS` 轉為 `3.3V` 供 MCU 使用
- `GND` 必須共地
- `D-` 要接到 `PA11`
- `D+` 要接到 `PA12`
- `CC1` 與 `CC2` 需各自透過 `5.1k` 下拉到 `GND`

若以上其中一項有問題，PC 可能會完全沒有反應，甚至連「未知 USB 裝置」都不會出現。

## 韌體端對應配置

目前韌體採用 `USB FS CDC`，重點如下：

- MCU：`STM32F401CCU6`
- USB 腳位：
  - `PA11 = USB_DM`
  - `PA12 = USB_DP`
- 時鐘來源：
  - 外部 `25 MHz HSE`
  - 系統時鐘配置為 `84 MHz SYSCLK`
  - USB 使用有效的 `48 MHz` 時鐘

相關程式位置：

- USB CDC 初始化：[platform_usb_cdc.c](C:/Users/winston_YEH/Documents/25230/CODE/艾科/firmware/Core/Src/platform_usb_cdc.c:177)
- USB low-level / PCD 設定：[usbd_conf.c](C:/Users/winston_YEH/Documents/25230/CODE/艾科/firmware/Core/Src/usbd_conf.c:109)
- 時鐘初始化：[platform.c](C:/Users/winston_YEH/Documents/25230/CODE/艾科/firmware/Core/Src/platform.c:174)
- 中斷向量表：[startup_stm32f401xc.s](C:/Users/winston_YEH/Documents/25230/CODE/艾科/firmware/startup/startup_stm32f401xc.s:60)

## 這次實際遇到的問題

### 1. 一開始插 Type-C，Windows 完全沒反應

一開始的現象不是「未知裝置」，而是插上 `Type-C` 後 Windows 完全沒有任何反應。

這種情況最容易先懷疑：

- 線材不是資料線
- `CC1/CC2` 下拉有誤
- `VBUS / 3V3` 沒起來
- `D+ / D-` 沒接通
- USB 時鐘不正確

後續確認硬體方向正確後，問題主因不在 Type-C 連接本身，而在韌體。

### 2. USB初始化卡在 `HAL_PCD_Init()`

透過 CLI 與 debugger 追蹤後，發現 USB bring-up 會卡在：

- `USBD_Init()`
- `USBD_LL_Init()`
- `HAL_PCD_Init()`

所以問題不是 CDC descriptor 或命令 parser，而是更底層的 USB PCD bring-up。

### 3. 真正根因：中斷向量表排列錯位

最後確認真正問題是：

- [startup_stm32f401xc.s](C:/Users/winston_YEH/Documents/25230/CODE/艾科/firmware/startup/startup_stm32f401xc.s:60) 的中斷向量表順序原本有錯
- 導致 `EXTI15_10_IRQn` 落到 `Default_Handler`
- USB 初始化期間觸發到錯位的 IRQ 後，整個 bring-up 被打斷

修正後保留的關鍵項目：

- `EXTI15_10_IRQHandler` 放在正確的向量位置
- `OTG_FS_IRQHandler` 放在正確的向量位置
- 核心 exception handler 與外部 IRQ 順序對齊 STM32F401

這是本次能正常枚舉的關鍵修正。

### 4. 時鐘配置也一起修正

為了讓 USB FS 穩定工作，韌體改為使用板上的 `25 MHz HSE`，並配置出合法的 USB 時鐘。

目前配置為：

- `PLLM = 25`
- `PLLN = 336`
- `PLLP = 4`
- `PLLQ = 7`

對應結果：

- `SYSCLK = 84 MHz`
- `USB = 48 MHz`

## 最後驗證結果

修正完成後，Windows 已成功出現新的虛擬序列埠：

- `COM20`

並確認以下指令可正常回覆：

```powershell
python -m host.src.pulse_host.cli --port COM20 ping
python -m host.src.pulse_host.cli --port COM20 status
```

回覆結果：

```text
OK
STATUS IDLE COUNT=0 SYNC=1
```

表示：

- USB CDC 枚舉成功
- Host 與板子的收發正常
- 韌體主流程已正常進入 `IDLE`

## 後續建議

之後如果再次遇到「插 Type-C 完全沒反應」，建議依序檢查：

1. 線材是否為資料線
2. `VBUS`、`3V3`、`GND` 是否正常
3. `CC1/CC2` 是否各有 `5.1k` 下拉
4. `PA11/PA12` 與 `D-/D+` 是否接通
5. USB 時鐘是否為有效 `48 MHz`
6. 中斷向量表是否仍維持正確順序

若硬體正確但仍無法枚舉，優先檢查：

- `startup_stm32f401xc.s`
- `platform.c`
- `usbd_conf.c`
- `platform_usb_cdc.c`

## 補充

目前專案已同時支援：

- `PlatformIO`
- `CMake`

建議日常使用 `PlatformIO`：

- 編譯：`pio run`
- 燒錄：`pio run -t upload`

若要確認板子是否真的走 Type-C USB CDC，而不是 ST-Link 的虛擬串口，請以 Windows 裝置管理員中「插拔 Type-C 時新增/消失的 COM 埠」為準。
