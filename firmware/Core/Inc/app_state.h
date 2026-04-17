#ifndef APP_STATE_H
#define APP_STATE_H

#include <stdbool.h>
#include <stdint.h>
#include "app_comm.h"
#include "app_config.h"
#include "app_counter.h"
#include "app_fault.h"
#include "app_io.h"
#include "app_log.h"
#include "app_types.h"

typedef struct {
    app_state_t state;
    app_config_t cfg;
    app_counter_t counter;
    app_fault_state_t fault;
    app_log_t log;

    bool start_requested;
    bool stop_requested;
    bool arm_requested;
    bool reset_fault_requested;
    bool precharge_requested;
    bool discharge_requested;

    app_outputs_t out;
} app_ctx_t;

void app_state_init(app_ctx_t* ctx);
void app_state_tick(app_ctx_t* ctx, uint32_t now_ms);
void app_state_on_command(app_ctx_t* ctx, const app_cmd_frame_t* cmd);

#endif
