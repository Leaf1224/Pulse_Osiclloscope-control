#ifndef __INA228_READ_H
#define __INA228_READ_H

#include "stm32f4xx_hal.h"
#include <stdint.h>

#define INA228_REG_VBUS   0x05    // VBus register
#define INA228_REG_Vshunt   0x04    // Vshunt register

// 初始化函式（可選，看你是否需要）
void INA228_Init(I2C_HandleTypeDef *hi2c, uint8_t address);

// 讀 VBus 電壓
float INA228_ReadVbus(I2C_HandleTypeDef *hi2c, uint8_t address);
// 讀 Vshunt 電壓
float INA228_ReadVshunt(I2C_HandleTypeDef *hi2c, uint8_t address);
#endif /* __INA228_READ_H */