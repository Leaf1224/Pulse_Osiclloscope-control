#include "cmd_utils.h"
#include <string.h>

extern I2C_HandleTypeDef hi2c1;

I2C_HandleTypeDef* parse_i2c(const char* str)
{
    if (strcmp(str, "I2C1") == 0) return &hi2c1;
    // 未來新增 I2C bus 時加在這裡
    return NULL;
}