#include "cmd_core_internal.h"
#include "cmd_utils.h"
#include "AD5675R.h"
#include <stdlib.h> // strtol
#include <stdio.h>
#include <string.h>

bool cmd_ad5675r_set_voltage(int argc, char* argv[])
{
    if (argc != 5) return false;

    I2C_HandleTypeDef* hi2c = parse_i2c(argv[0]);
    if (!hi2c) return false;

    uint8_t addr = (uint8_t)strtol(argv[1], NULL, 0);

    /* FullScale: 0 or 1 */
    int fs_input = atoi(argv[2]);
    if (fs_input < 0 || fs_input > 1)
        return false;

    AD5675_FullScale_t fs = (AD5675_FullScale_t)fs_input;

    /* DAC Channel: 0~7 */
    int dac_input = atoi(argv[3]);
    if (dac_input < 0 || dac_input > 7)
        return false;

    AD5675_DAC_Channel_t dac =
        (AD5675_DAC_Channel_t)dac_input;

    float voltage = strtof(argv[4], NULL);

    if (AD5675R_SetVoltage(hi2c, addr, fs, dac, voltage) != HAL_OK)
        return false;

    return true;
}