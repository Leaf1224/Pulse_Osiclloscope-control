#ifndef __AD5675R_H
#define __AD5675R_H

#include "stm32f4xx_hal.h"
#include <stdint.h>

/* ===== Full Scale 選擇 ===== */
typedef enum
{
    AD5675_FS_2V5 = 0,   // Gain = 1
    AD5675_FS_5V0        // Gain = 2
} AD5675_FullScale_t;

/* ===== DAC Channel ===== */
typedef enum
{
    AD5675_DAC_0 = 0,
    AD5675_DAC_1,
    AD5675_DAC_2,
    AD5675_DAC_3,
    AD5675_DAC_4,
    AD5675_DAC_5,
    AD5675_DAC_6,
    AD5675_DAC_7
} AD5675_DAC_Channel_t;

HAL_StatusTypeDef AD5675R_SetVoltage(I2C_HandleTypeDef *hi2c,
                                     uint8_t dev_addr,
                                     AD5675_FullScale_t fs,
                                     AD5675_DAC_Channel_t dac,
                                     float voltage);//範例 :AD5675R_SetVoltage(&hi2c1, 0x0C,1,0,0.5f)，pc給AD5675R_SET_VOLTAGE I2C1 0X0C 1 0 0.5

#endif