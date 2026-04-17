#ifndef __PCA8575_H
#define __PCA8575_H

#include "stm32f4xx_hal.h"   // 換成你的 STM32 系列

/* ====== Pin 定義 ====== */
typedef enum //PCA8575是P0~P7、P10~P17共16Pin
{
    P0  = 0,
    P1,
    P2,
    P3,
    P4,
    P5,
    P6,
    P7,
    P10,
    P11,
    P12,
    P13,
    P14,
    P15,
    P16,
    P17
} PCA8575_Pin_t;

/* ====== SET / RESET ====== */
typedef enum
{
    PCA8575_RESET = 0,
    PCA8575_SET
} PCA8575_State_t;

/* ====== API ====== */
HAL_StatusTypeDef PCA8575_Init(I2C_HandleTypeDef *hi2c,
                               uint8_t devAddr);

HAL_StatusTypeDef PCA8575_IO(I2C_HandleTypeDef *hi2c,
                             uint8_t devAddr,
                             PCA8575_Pin_t pin,
                             PCA8575_State_t state);

#endif