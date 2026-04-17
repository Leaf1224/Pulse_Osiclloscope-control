#pragma once

#include <stdint.h>
#include <stdbool.h>

/* ----- handler type ----- */
typedef bool (*cmd_handler_t)(int argc, char* argv[]);

/* ----- command descriptor ----- */
typedef struct
{
    const char*     name;       // 指令名稱，例如 "PCA8575_IO"
    uint8_t         argc;       // 需要幾個參數
    cmd_handler_t   handler;    // 對應的 handler function
} CmdDescriptor;

/* ----- Command Table ----- */
extern const CmdDescriptor cmd_table[];
extern const uint8_t cmd_table_size;

/* ----- Glue / Handler prototypes ----- */
// PCA8575 handler
bool cmd_pca8575_io(int argc, char* argv[]);
// AD5675R handler
bool cmd_ad5675r_set_voltage(int argc, char* argv[]);
// INA228 handler
bool cmd_ina228_read_vbus(int argc, char* argv[]);
// 其他 IC handler 之後新增即可