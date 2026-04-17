#include "app_state.h"

static void state_enter(app_ctx_t* ctx, app_state_t next_state, uint32_t now_ms) {
    app_log_entry_t e;

    ctx->state = next_state;
    app_counter_reset_state_timer(&ctx->counter);

    e.ms = now_ms;
    e.state = next_state;
    e.fault = ctx->fault.code;
    e.count = ctx->counter.pulse_count;
    app_log_push(&ctx->log, e);
}

static void force_fault(app_ctx_t* ctx, fault_code_t code, uint32_t now_ms) {
    app_fault_latch(&ctx->fault, code, ctx->counter.pulse_count);
    ctx->out.driver_en = false;
    ctx->out.precharge_en = false;
    ctx->out.bus_main_en = false;
    ctx->out.discharge_en = true;
    ctx->out.fault_trig = true;
    ctx->out.led_fault = true;
    ctx->out.led_run = false;
    state_enter(ctx, APP_STATE_FAULT, now_ms);
}

void app_state_init(app_ctx_t* ctx) {
    if (ctx == 0) {
        return;
    }

    app_config_load_defaults(&ctx->cfg);
    app_counter_init(&ctx->counter);
    app_fault_init(&ctx->fault);
    app_log_init(&ctx->log);

    ctx->state = APP_STATE_BOOT;
    ctx->start_requested = false;
    ctx->stop_requested = false;
    ctx->arm_requested = false;
    ctx->reset_fault_requested = false;
    ctx->precharge_requested = false;
    ctx->discharge_requested = false;

    ctx->out.precharge_en = false;
    ctx->out.bus_main_en = false;
    ctx->out.discharge_en = false;
    ctx->out.driver_en = false;
    ctx->out.reset_latch = false;
    ctx->out.start_trig = false;
    ctx->out.end_trig = false;
    ctx->out.fault_trig = false;
    ctx->out.led_run = false;
    ctx->out.led_fault = false;
}

void app_state_on_command(app_ctx_t* ctx, const app_cmd_frame_t* cmd) {
    if (ctx == 0 || cmd == 0) {
        return;
    }

    switch (cmd->command) {
        case CMD_ARM: ctx->arm_requested = true; break;
        case CMD_START:
            ctx->start_requested = true;
            if (cmd->has_count_arg) {
                ctx->cfg.target_pulse_count = cmd->count_arg;
            }
            break;
        case CMD_STOP: ctx->stop_requested = true; break;
        case CMD_RESET_FAULT: ctx->reset_fault_requested = true; break;
        case CMD_PRECHARGE: ctx->precharge_requested = true; break;
        case CMD_DISCHARGE: ctx->discharge_requested = true; break;
        default: break;
    }
}

void app_state_tick(app_ctx_t* ctx, uint32_t now_ms) {
    app_inputs_t in;

    if (ctx == 0) {
        return;
    }

    app_io_read_inputs(&in);
    app_counter_on_tick(&ctx->counter, ctx->cfg.loop_period_ms);
    app_counter_set_fg_sync_count(&ctx->counter, in.fg_sync_count);

    if (in.estop_in) {
        force_fault(ctx, FAULT_ESTOP, now_ms);
        app_io_apply_outputs(&ctx->out);
        return;
    }

    if (in.ocp_fault_in) {
        force_fault(ctx, FAULT_OCP, now_ms);
        app_io_apply_outputs(&ctx->out);
        return;
    }

    switch (ctx->state) {
        case APP_STATE_BOOT:
            state_enter(ctx, APP_STATE_IDLE, now_ms);
            break;

        case APP_STATE_IDLE:
            ctx->out.driver_en = false;
            ctx->out.precharge_en = false;
            ctx->out.bus_main_en = false;
            ctx->out.discharge_en = false;
            ctx->out.led_run = false;

            if (ctx->precharge_requested || ctx->arm_requested) {
                ctx->precharge_requested = false;
                state_enter(ctx, APP_STATE_PRECHARGE, now_ms);
            }
            break;

        case APP_STATE_PRECHARGE:
            ctx->out.precharge_en = true;
            ctx->out.bus_main_en = false;
            if (!in.ps_ok_all_in) {
                force_fault(ctx, FAULT_PSU_NOT_OK, now_ms);
                break;
            }
            if (in.bus_v_adc >= ctx->cfg.bus_ready_threshold_v) {
                state_enter(ctx, APP_STATE_WAIT_BUS_READY, now_ms);
            } else if (ctx->counter.state_elapsed_ms > ctx->cfg.precharge_timeout_ms) {
                force_fault(ctx, FAULT_PRECHARGE_TIMEOUT, now_ms);
            }
            break;

        case APP_STATE_WAIT_BUS_READY:
            if (in.bus_v_adc >= ctx->cfg.bus_ready_threshold_v && in.interlock_in) {
                ctx->out.precharge_en = false;
                ctx->out.bus_main_en = true;
                state_enter(ctx, APP_STATE_ARMED, now_ms);
            } else if (ctx->counter.state_elapsed_ms > ctx->cfg.bus_ready_timeout_ms) {
                force_fault(ctx, FAULT_BUS_NOT_READY, now_ms);
            }
            break;

        case APP_STATE_ARMED:
            ctx->out.driver_en = false;
            ctx->out.led_run = true;

            if (in.bus_v_adc < ctx->cfg.bus_uv_threshold_v) {
                force_fault(ctx, FAULT_BUS_NOT_READY, now_ms);
                break;
            }
            if (ctx->start_requested) {
                ctx->start_requested = false;
                state_enter(ctx, APP_STATE_RUNNING, now_ms);
            }
            if (ctx->discharge_requested) {
                ctx->discharge_requested = false;
                state_enter(ctx, APP_STATE_DISCHARGE, now_ms);
            }
            break;

        case APP_STATE_RUNNING:
            ctx->out.driver_en = true;
            ctx->out.start_trig = true;
            app_counter_inc_pulse(&ctx->counter);
            ctx->out.start_trig = false;

            if (ctx->stop_requested) {
                ctx->stop_requested = false;
                ctx->out.end_trig = true;
                ctx->out.driver_en = false;
                state_enter(ctx, APP_STATE_ARMED, now_ms);
                ctx->out.end_trig = false;
                break;
            }
            if (app_counter_target_reached(&ctx->counter, ctx->cfg.target_pulse_count)) {
                ctx->out.end_trig = true;
                ctx->out.driver_en = false;
                state_enter(ctx, APP_STATE_ARMED, now_ms);
                ctx->out.end_trig = false;
            }
            break;

        case APP_STATE_FAULT:
            ctx->out.driver_en = false;
            ctx->out.precharge_en = false;
            ctx->out.bus_main_en = false;
            ctx->out.discharge_en = true;
            ctx->out.led_fault = true;

            if (ctx->reset_fault_requested && in.bus_v_adc <= ctx->cfg.bus_safe_threshold_v) {
                ctx->reset_fault_requested = false;
                app_fault_clear(&ctx->fault);
                ctx->out.fault_trig = false;
                ctx->out.led_fault = false;
                state_enter(ctx, APP_STATE_IDLE, now_ms);
            }
            break;

        case APP_STATE_DISCHARGE:
            ctx->out.driver_en = false;
            ctx->out.bus_main_en = false;
            ctx->out.precharge_en = false;
            ctx->out.discharge_en = true;

            if (in.bus_v_adc <= ctx->cfg.bus_safe_threshold_v) {
                ctx->out.discharge_en = false;
                state_enter(ctx, APP_STATE_SAFE_OFF, now_ms);
            } else if (ctx->counter.state_elapsed_ms > ctx->cfg.discharge_timeout_ms) {
                force_fault(ctx, FAULT_DISCHARGE_TIMEOUT, now_ms);
            }
            break;

        case APP_STATE_SAFE_OFF:
            ctx->out.driver_en = false;
            ctx->out.precharge_en = false;
            ctx->out.bus_main_en = false;
            ctx->out.discharge_en = false;
            if (ctx->arm_requested) {
                ctx->arm_requested = false;
                state_enter(ctx, APP_STATE_PRECHARGE, now_ms);
            }
            break;

        default:
            force_fault(ctx, FAULT_UNKNOWN, now_ms);
            break;
    }

    app_io_apply_outputs(&ctx->out);
}
