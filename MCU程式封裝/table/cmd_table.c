#include "cmd_core_internal.h"

const CmdDescriptor cmd_table[] =
{
    { "PCA8575_IO", 4, cmd_pca8575_io },//指令呼叫名稱,有幾個參數(不包含名稱),glue內函式名稱
    { "AD5675R_SET_VOLTAGE", 5, cmd_ad5675r_set_voltage },
    { "INA228_READ_VBUS", 2, cmd_ina228_read_vbus },
};

const uint8_t cmd_table_size =
    sizeof(cmd_table) / sizeof(cmd_table[0]);