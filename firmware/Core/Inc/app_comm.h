#ifndef APP_COMM_H
#define APP_COMM_H

#include <stdbool.h>
#include <stddef.h>
#include "app_types.h"

typedef enum {
    CMD_NONE = 0,
    CMD_PING,
    CMD_GET_STATUS,
    CMD_GET_FAULT,
    CMD_GET_COUNT,
    CMD_GET_SYNC_COUNT,
    CMD_RESET_SYNC_COUNT,
    CMD_ARM,
    CMD_START,
    CMD_STOP,
    CMD_RESET_FAULT,
    CMD_PRECHARGE,
    CMD_DISCHARGE
} app_command_t;

typedef struct {
    app_command_t command;
    uint32_t count_arg;
    bool has_count_arg;
} app_cmd_frame_t;

bool app_comm_parse_line(const char* line, app_cmd_frame_t* out);
size_t app_comm_format_fault(fault_code_t code, char* out, size_t out_size);

#endif
