MCU 程式封裝 — 專案總覽
=================================

目標
----
本專案提供一組以 USB CDC 接收文字指令，透過 I2C 驅動數位 DAC (AD5675R)、電源監控 IC (INA228)、以及 GPIO 擴展 (PCA8575) 等外設的韌體模組。指令採用簡單的文字介面（含 CRC 校驗），在 MCU 端由 parser、CRC 檢查、command core、glue 層與 driver 層按序處理。

目錄與模組概覽
----------------
- `CORE/`
  - `cmd_core.c`, `cmd_core.h`, `cmd_core_internal.h`
    - 指令執行的核心：`cmd_execute(const char* payload)` 會在命令表 (`cmd_table[]`) 中尋找命令名稱，檢查參數數量並呼叫對應 handler。
    - `cmd_core_internal.h` 定義 `CmdDescriptor` 與 glue handler 的 prototype。

- `glue/`
  - 將解析過的字串參數轉為驅動呼叫，包含：
    - `cmd_pca8575_io.c` -> `cmd_pca8575_io(int argc, char* argv[])`：呼叫 `PCA8575_IO()`。
    - `cmd_ad5675r_set_voltage.c` -> `cmd_ad5675r_set_voltage(...)`：解析 I2C、addr、fullscale、DAC 編號、電壓字串，呼叫 `AD5675R_SetVoltage()`。
    - `cmd_ina228_read_voltage.c` -> `cmd_ina228_read_vbus(...)`：呼叫 `INA228_ReadVbus()` 並用 `CDC_Printf` 回傳結果。

- `table/`
  - `cmd_table.c`：命令表（例如 `PCA8575_IO`, `AD5675R_SET_VOLTAGE`, `INA228_READ_VBUS`），每項包含 name、argc、handler。

- `Driver/`
  - `AD5675R輸出/`：`AD5675R.c/.h` — 封裝 AD5675 的電壓轉碼與 I2C 寫入 (使用 HAL_I2C_Mem_Write)。
  - `INA228讀電壓/`：`INA228_Read.c/.h` — 讀取 INA228 的 VBUS 與 VSHUNT register，將 raw 轉為實際電壓。
  - `PCA8575PW控制HighLow/`：`PCA8575PW.c/.h` — 以 shadow register 管理 16-bit 輸出並寫入 I2C。
  - `Print到ComPort/`：`cdc_print.c/.h` — `CDC_Printf()` 包裝 `CDC_Transmit_FS`，提供格式化輸出。

- `CRC_check/`
  - `CRC16_CCITT.c/.h`：提供 `CRC16_CCITT_Check(const char* cmd)`，格式為 `"$PAYLOAD*XXXX"`（XXXX 為 4 個 hex 字），以 CRC16-CCITT 計算並比對。

- `text_recive/`
  - `parser.c/h`：實作一個 ring buffer，`Parser_PushBytes()` 在 USB receive 中呼叫以存入輸入資料；`parser_poll()` 在主迴圈中輪詢找出以 `$` 開頭、`
` 結尾的 packet（parser.c 提供 `parser_get_packet()`）。
  - `usbd_cdc_if.c`：USB CDC 接收時呼叫 `Parser_PushBytes()`。CDC transmit/receive 介面由 STM32Cube 產生。

- `utils/`
  - `cmd_utils.c/.h`：工具函式，例如 `parse_i2c(const char* str)` 回傳 `I2C_HandleTypeDef*`（目前僅支援 `I2C1` 映射為 `&hi2c1`）。

指令通訊格式（使用說明）
-------------------------
- Packet frame (送向 MCU)：
  - 以 `$` 開始，以 `\n` 結束，中間 payload 後可加 `*XXXX`（4 個 hex）作 CRC，例如：
    - `$AD5675R_SET_VOLTAGE I2C1 0x0C 1 0 0.5*ABCD\n`
  - CRC 的計算方法：CRC16-CCITT（此專案 `CRC16_CCITT_Check` 會在接收到的字串中尋找 `*` 與後方 4 個 hex 字串並跟計算值比對）。

- Core 流程（推測的 call flow，請於 main 裡實作）
  1. USB 收到資料 -> `CDC_Receive_FS()` 呼叫 `Parser_PushBytes()`。
  2. 主迴圈呼叫 `parser_poll()`，當回傳 true 時使用 `parser_get_packet()` 取得完整 packet（包含 `$` 和 `*CRC`）。
  3. 呼叫 `CRC16_CCITT_Check(packet)` 驗證 CRC。
  4. 若 CRC 正確，去除開頭 `$` 與尾端 `*XXXX`、`\n`，得到 payload 字串（例如 `AD5675R_SET_VOLTAGE ...`）。
  5. 呼叫 `cmd_execute(payload)`；`cmd_execute` 會 tokenize、match `cmd_table[]`、並呼叫對應的 glue handler。
  6. handler 呼叫 driver 做實際硬體操作，必要時使用 `CDC_Printf()` 回傳結果或錯誤。

內建命令與範例
----------------
- `PCA8575_IO <I2C> <addr> <pin> <state>`
  - 範例: `$PCA8575_IO I2C1 0x20 0 1*XXXX\n`  // 將 PCA8575 的 P0 設為 1

- `AD5675R_SET_VOLTAGE <I2C> <addr> <fullscale> <dac> <voltage>`
  - 範例: `$AD5675R_SET_VOLTAGE I2C1 0x0C 1 0 0.5*XXXX\n`  // 設 DAC0 為 0.5V

- `INA228_READ_VBUS <I2C> <addr>`
  - 範例: `$INA228_READ_VBUS I2C1 0x40*XXXX\n`  // 讀取 Vbus，成功時會由 MCU 回傳 `OK INA228_READ_VBUS ... <value>`

注意事項與建議改進（重要）
-------------------------
1. parser.h 與 parser.c 的函式命名不一致：
   - `parser.c` 實作 `parser_get_packet()`，但 `parser.h` 宣告 `parser_get_CRC_packet()` 與 `parser_get_CMD_payload()`。
   - 建議：統一介面。額外提供 `parser_get_CRC_packet()` 回傳包含 CRC 的原始 packet，並提供 `parser_get_CMD_payload()` 回傳去除 `$`、`*CRC` 與換行的 payload。

2. CRC 檢查：目前有 `CRC16_CCITT_Check()`，但我尚未在程式中看到哪裡呼叫它（應在 main loop 在取得 packet 後呼叫）。請在 main 裡加入：
   - 取 packet -> CRC 檢查 -> 若正確呼叫 `cmd_execute()`，否則 `CDC_Printf("ERR:CRC\n")`。

3. 緩衝區大小與安全性：`cmd_execute` 將 payload 複製到固定長度 128 bytes 的 buffer 並用 `strtok`，請確認上層 parser 不會傳入過長的 packet 或加上更嚴格的檢查。

4. `cmd_utils.c` 的 `parse_i2c()` 目前只支援 `I2C1`，如果在不同 MCU 或需支援多個 I2C bus，擴充 mapping 或使用配置宏。

5. 錯誤回報一致性：部分 handler 使用 `CDC_Printf` 回傳錯誤字串，有些 handler 只回 false。建議建立統一的錯誤回報慣例（例如回傳 `ERR:<code>` 或 `OK ...`）。

建議的 main loop 範例（簡短）
-------------------------
- 初始化 USB、I2C、drivers、parser。
- while (1) {
    if (parser_poll()) {
      const char *pkt = parser_get_packet();
      if (!CRC16_CCITT_Check(pkt)) { CDC_Printf("ERR:CRC\n"); continue; }
      // 取出 payload 部分，把 $ 和 *CRC 與末尾 \n 去掉
      // 呼叫 cmd_execute(payload)
    }
  }

後續我可以幫忙的項目
--------------------
- 修正 `parser.h` / `parser.c` 的介面不一致並在 `main` 中加入 CRC 檢查與 `cmd_execute` 的整合示例。
- 產生簡單的 unit test（模擬 packet 與 CRC 檢查）或一個小工具幫你從 payload 計算 CRC 並產生完整 packet（方便在 PC 端測試）。

結語
----
我已讀取並分析了核心檔案、glue、主要 driver、CDC 與 CRC 程式，並把關鍵操作流程、指令格式與範例整理在上面 README 中。若要我把 README 實際 commit 到 repo（我剛已建立檔案），或希望我繼續：
- 修正 parser 的介面錯誤並整合 CRC -> cmd_execute 流程，或
- 幫你產生一個簡單的 PC 端 Python 腳本來送測試指令（包含 CRC 計算），
請告訴我下一步想要我執行的工作。