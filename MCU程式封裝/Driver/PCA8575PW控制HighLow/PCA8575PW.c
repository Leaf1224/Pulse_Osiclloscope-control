#include "PCA8575PW.h"

static uint16_t pca8575_shadow = 0x0000;

HAL_StatusTypeDef PCA8575_Init(I2C_HandleTypeDef *hi2c, uint8_t devAddr)
{
    uint8_t buf[2];

    /* 設定初始上電狀態 */
    pca8575_shadow = 0x0000;

    /* 由 shadow 產生實際要寫的資料 */
    buf[0] =  pca8575_shadow        & 0xFF;
    buf[1] = (pca8575_shadow >> 8)  & 0xFF;

    return HAL_I2C_Master_Transmit(hi2c,
                                   devAddr << 1,
                                   buf,
                                   2,
                                   HAL_MAX_DELAY);
}

HAL_StatusTypeDef PCA8575_IO(I2C_HandleTypeDef *hi2c,
                             uint8_t devAddr,
                             PCA8575_Pin_t pin,
                             PCA8575_State_t state)
{
    uint8_t txBuf[2];

    switch (state)
    {
        case SET:
            pca8575_shadow |=  (1U << pin);
            break;

        case RESET:
            pca8575_shadow &= ~(1U << pin);
            break;

        default:
            return HAL_ERROR;
    }
    txBuf[0] = pca8575_shadow & 0xFF;        // Low byte (P0~P7)
    txBuf[1] = (pca8575_shadow >> 8) & 0xFF; // High byte (P10~P17)

    return HAL_I2C_Master_Transmit(hi2c,
                                   devAddr << 1,   // HAL 需要 8-bit address
                                   txBuf,
                                   2,
                                   HAL_MAX_DELAY);
}   