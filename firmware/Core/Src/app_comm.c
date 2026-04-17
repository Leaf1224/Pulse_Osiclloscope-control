#include "app_comm.h"

#include <stdio.h>
#include <string.h>

static bool starts_with(const char* s, const char* pfx) {
    return strncmp(s, pfx, strlen(pfx)) == 0;
}

bool app_comm_parse_line(const char* line, app_cmd_frame_t* out) {
    unsigned long value;
    const char* count_pos;

    if (line == 0 || out == 0) {
        return false;
    }

    out->command = CMD_NONE;
    out->count_arg = 0U;
    out->has_count_arg = false;

    if (strcmp(line, "PING") == 0) {
        out->command = CMD_PING;
    } else if (strcmp(line, "GET_STATUS") == 0) {
        out->command = CMD_GET_STATUS;
    } else if (strcmp(line, "GET_FAULT") == 0) {
        out->command = CMD_GET_FAULT;
    } else if (strcmp(line, "GET_COUNT") == 0) {
        out->command = CMD_GET_COUNT;
    } else if (strcmp(line, "GET_SYNC_COUNT") == 0) {
        out->command = CMD_GET_SYNC_COUNT;
    } else if (strcmp(line, "RESET_SYNC_COUNT") == 0) {
        out->command = CMD_RESET_SYNC_COUNT;
    } else if (strcmp(line, "ARM") == 0) {
        out->command = CMD_ARM;
    } else if (starts_with(line, "START")) {
        out->command = CMD_START;
        count_pos = strstr(line, "COUNT=");
        if (count_pos != 0) {
            if (sscanf(count_pos, "COUNT=%lu", &value) == 1) {
                out->count_arg = (uint32_t)value;
                out->has_count_arg = true;
            }
        }
    } else if (strcmp(line, "STOP") == 0) {
        out->command = CMD_STOP;
    } else if (strcmp(line, "RESET_FAULT") == 0) {
        out->command = CMD_RESET_FAULT;
    } else if (strcmp(line, "PRECHARGE") == 0) {
        out->command = CMD_PRECHARGE;
    } else if (strcmp(line, "DISCHARGE") == 0) {
        out->command = CMD_DISCHARGE;
    }

    return out->command != CMD_NONE;
}

size_t app_comm_format_fault(fault_code_t code, char* out, size_t out_size) {
    const char* name = "UNKNOWN";

    switch (code) {
        case FAULT_NONE: name = "NONE"; break;
        case FAULT_ESTOP: name = "ESTOP"; break;
        case FAULT_OCP: name = "OCP"; break;
        case FAULT_TIMEOUT: name = "TIMEOUT"; break;
        case FAULT_OFF_CHECK: name = "OFF_CHECK"; break;
        case FAULT_THERMAL: name = "THERMAL"; break;
        case FAULT_BUS_NOT_READY: name = "BUS_NOT_READY"; break;
        case FAULT_PRECHARGE_TIMEOUT: name = "PRECHARGE_TIMEOUT"; break;
        case FAULT_DISCHARGE_TIMEOUT: name = "DISCHARGE_TIMEOUT"; break;
        case FAULT_PSU_NOT_OK: name = "PSU_NOT_OK"; break;
        case FAULT_LATCH_MISMATCH: name = "LATCH_MISMATCH"; break;
        case FAULT_USER_ABORT: name = "USER_ABORT"; break;
        default: break;
    }

    if (out == 0 || out_size == 0U) {
        return 0U;
    }
    return (size_t)snprintf(out, out_size, "%s", name);
}
