#pragma once
#include "stm32f4xx_hal.h"  // hi2c1, hi2c2 等 I2C bus handle

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief 將 I2C 名稱字串轉換為 MCU 上的 I2C_HandleTypeDef*
 * @param str I2C 名稱，例如 "I2C1"
 * @return 指向對應的 I2C_HandleTypeDef，找不到返回 NULL
 */
I2C_HandleTypeDef* parse_i2c(const char* str);

#ifdef __cplusplus
}
#endif