#include "AD5675R.h"
#include "stm32f4xx_hal.h"

/* ===== 電壓轉 16-bit===== */
static uint16_t AD5675_VoltageToCode(float voltage, AD5675_FullScale_t fs)
{
    float full_scale = (fs == AD5675_FS_2V5) ? 2.5f : 5.0f;//if fs == D5675_FS_2V5 ; yes:full_scale=2.5f else:5.0f

    if (voltage < 0.0f) voltage = 0.0f;
    if (voltage > full_scale) voltage = full_scale;

    uint32_t code = (uint32_t)((voltage / full_scale) * 65535.0f + 0.5f);
    if (code > 65535) code = 65535;

    return (uint16_t)code;
}

/* ===== 設定電壓 ===== */
HAL_StatusTypeDef AD5675R_SetVoltage(I2C_HandleTypeDef *hi2c,
                                     uint8_t dev_addr,
                                     AD5675_FullScale_t fs,
                                     AD5675_DAC_Channel_t dac,
                                     float voltage)
{
    /* 檢查 i2c_ch及DAC_ch是否有效 */
    if (hi2c == NULL)
        return HAL_ERROR;

    if (dac > AD5675_DAC_7)
        return HAL_ERROR;

    uint16_t dac_code = AD5675_VoltageToCode(voltage, fs);

    /* AD5675R Write & Update DAC command */
    uint8_t cmd = (0x3 << 4) | (dac & 0x0F);//0x0f=00001111保留8 bit做and運算留下要得Dac號碼

    uint8_t tx_buf[2];
    tx_buf[0] = (dac_code >> 8) & 0xFF;   // 高 8 bit
    tx_buf[1] = dac_code & 0xFF;          // 低 8 bit

    /* 使用 HAL_I2C_Mem_Write */
    HAL_StatusTypeDef status;
    status = HAL_I2C_Mem_Write(hi2c, (dev_addr << 1), cmd,
                               I2C_MEMADD_SIZE_8BIT, tx_buf, 2, 100);

    return status;
}
