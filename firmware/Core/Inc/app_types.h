#ifndef APP_TYPES_H
#define APP_TYPES_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    APP_STATE_BOOT = 0,
    APP_STATE_IDLE,
    APP_STATE_PRECHARGE,
    APP_STATE_WAIT_BUS_READY,
    APP_STATE_ARMED,
    APP_STATE_RUNNING,
    APP_STATE_FAULT,
    APP_STATE_DISCHARGE,
    APP_STATE_SAFE_OFF
} app_state_t;

typedef enum {
    FAULT_NONE = 0,
    FAULT_ESTOP,
    FAULT_OCP,
    FAULT_TIMEOUT,
    FAULT_OFF_CHECK,
    FAULT_THERMAL,
    FAULT_BUS_NOT_READY,
    FAULT_PRECHARGE_TIMEOUT,
    FAULT_DISCHARGE_TIMEOUT,
    FAULT_PSU_NOT_OK,
    FAULT_LATCH_MISMATCH,
    FAULT_USER_ABORT,
    FAULT_UNKNOWN
} fault_code_t;

typedef struct {
    bool level;
    bool pulse;
} digital_out_t;

#endif
