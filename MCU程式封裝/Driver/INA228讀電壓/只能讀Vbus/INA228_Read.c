#include "INA228_Read.h"

// INA228_Init 可以留空或做一些配置
void INA228_Init(I2C_HandleTypeDef *hi2c, uint8_t address)
{
    // INA228 在 power-on 後自動初始化
    // 如果需要寫配置寄存器，可以在這裡做
}

// 讀 VBus 電壓
float INA228_ReadVbus(I2C_HandleTypeDef *hi2c, uint8_t address)
{
    uint8_t buf[3];
    uint32_t raw;
    float vbus;

    if(HAL_I2C_Mem_Read(hi2c, address << 1, INA228_REG_VBUS, I2C_MEMADD_SIZE_8BIT, buf, 3, 1000) != HAL_OK)
    {
        return -1;  // 讀取失敗，返回 -1 當作錯誤
    }

    raw = ((uint32_t)buf[0] << 16) |
          ((uint32_t)buf[1] << 8)  |
           (uint32_t)buf[2];

    raw >>= 4;                 //3-0 Reserved. Always reads 0
    vbus = raw * 195.3125e-6;  //Conversion factor: 195.3125 µV/LSB

    return vbus;
}