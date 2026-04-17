#include "cmd_core_internal.h"
#include "cmd_utils.h"
#include "INA228_Read.h"
#include <stdlib.h> // strtol
#include <stdio.h>
#include <cdc_print.h>

bool cmd_ina228_read_vbus(int argc, char* argv[])
{
    if (argc != 2)
    {
        CDC_Printf("argc ERROR");
        return false;
    }
    // 解析 I2C
    I2C_HandleTypeDef* hi2c = parse_i2c(argv[0]);
    if (!hi2c)
    {
        CDC_Printf("hi2c ERROR");
        return false;
    }
    // 解析 address
    uint8_t addr = (uint8_t)strtol(argv[1], NULL, 0);

    // 呼叫 Driver
    float vbus = INA228_ReadVbus(hi2c, addr);

    if (vbus < 0)   //driver 用 -1 當錯誤
    {
        CDC_Printf("INA228_READ_VBUS %s %s ERROR\n",
                   argv[0], argv[1]);
        return false;
    }

    // 成功才回傳數值
    CDC_Printf("OK INA228_READ_VBUS %s %s %.6f\n",
               argv[0], argv[1], vbus);

    return true;
}