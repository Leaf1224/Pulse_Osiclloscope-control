#pragma once
#include <stdbool.h>

/**
 * @brief 執行一條已確認 CRC 並去掉 '$', '*CRC', '\n' 的 payload 指令
 * @param payload 字串，格式: CMD ARG1 ARG2 ...
 * @return true  成功執行
 * @return false 執行失敗 (UNKNOWN CMD / ARG ERROR / hardware error)
 */
bool cmd_execute(const char* payload);