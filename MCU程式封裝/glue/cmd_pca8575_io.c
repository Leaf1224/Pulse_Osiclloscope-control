#include "cmd_core_internal.h"
#include "cmd_utils.h"
#include "PCA8575PW.h"
#include <stdlib.h> // strtol
#include <stdio.h>

bool cmd_pca8575_io(int argc, char* argv[])
{
    if (argc != 4) return false;

    I2C_HandleTypeDef* hi2c = parse_i2c(argv[0]);
    if (!hi2c) return false;

    uint8_t addr           = (uint8_t)strtol(argv[1], NULL, 0);
    PCA8575_Pin_t pin      = (PCA8575_Pin_t)atoi(argv[2]);
    PCA8575_State_t state  = (PCA8575_State_t)atoi(argv[3]);

    PCA8575_IO(hi2c, addr, pin, state);
    return true;
}