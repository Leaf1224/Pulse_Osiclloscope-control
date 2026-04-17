#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "app_comm.h"
#include "app_io.h"
#include "platform_comm.h"
#include "platform.h"
#include "app_state.h"

static const char* state_name(app_state_t state) {
    switch (state) {
        case APP_STATE_BOOT: return "BOOT";
        case APP_STATE_IDLE: return "IDLE";
        case APP_STATE_PRECHARGE: return "PRECHARGE";
        case APP_STATE_WAIT_BUS_READY: return "WAIT_BUS_READY";
        case APP_STATE_ARMED: return "ARMED";
        case APP_STATE_RUNNING: return "RUNNING";
        case APP_STATE_FAULT: return "FAULT";
        case APP_STATE_DISCHARGE: return "DISCHARGE";
        case APP_STATE_SAFE_OFF: return "SAFE_OFF";
        default: return "UNKNOWN";
    }
}

static void respond_status(const app_ctx_t* ctx) {
    char msg[96];
    (void)snprintf(msg, sizeof(msg), "STATUS %s COUNT=%lu SYNC=%lu",
                   state_name(ctx->state),
                   (unsigned long)ctx->counter.pulse_count,
                   (unsigned long)ctx->counter.fg_sync_count);
    platform_comm_write_line(msg);
}

static void respond_fault(const app_ctx_t* ctx) {
    char fault_name[32];
    char msg[96];

    app_comm_format_fault(ctx->fault.code, fault_name, sizeof(fault_name));
    (void)snprintf(msg, sizeof(msg), "FAULT %s COUNT=%lu",
                   fault_name, (unsigned long)ctx->fault.pulse_at_fault);
    platform_comm_write_line(msg);
}

static void handle_command(app_ctx_t* ctx, const app_cmd_frame_t* cmd) {
    switch (cmd->command) {
        case CMD_PING:
            platform_comm_write_line("OK");
            break;
        case CMD_GET_STATUS:
            respond_status(ctx);
            break;
        case CMD_GET_FAULT:
            respond_fault(ctx);
            break;
        case CMD_GET_COUNT: {
            char msg[48];
            (void)snprintf(msg, sizeof(msg), "COUNT %lu", (unsigned long)ctx->counter.pulse_count);
            platform_comm_write_line(msg);
            break;
        }
        case CMD_GET_SYNC_COUNT: {
            char msg[48];
            (void)snprintf(msg, sizeof(msg), "SYNC_COUNT %lu", (unsigned long)ctx->counter.fg_sync_count);
            platform_comm_write_line(msg);
            break;
        }
        case CMD_RESET_SYNC_COUNT:
            platform_pulse_counter_reset();
            ctx->counter.fg_sync_count = 0U;
            platform_comm_write_line("OK");
            break;
        default:
            app_state_on_command(ctx, cmd);
            platform_comm_write_line("OK");
            break;
    }
}

int main(void) {
    app_ctx_t ctx;
    app_cmd_frame_t cmd;
    char rx_line[128];
    uint32_t last_tick_ms;

    platform_init();
    app_io_init();
    platform_comm_init();
    app_state_init(&ctx);

    cmd.command = CMD_NONE;
    last_tick_ms = platform_now_ms();
    if (platform_comm_is_usb_active()) {
        platform_comm_write_line("BOOT V1_PULSE_PLATFORM COMM=USB_CDC");
    } else {
        platform_comm_write_line("BOOT V1_PULSE_PLATFORM COMM=UART_FALLBACK");
    }

    while (1) {
        uint32_t now_ms = platform_now_ms();
        if (now_ms != last_tick_ms) {
            last_tick_ms = now_ms;
            app_state_tick(&ctx, now_ms);
        }

        if (platform_comm_read_line(rx_line, sizeof(rx_line))) {
            if (app_comm_parse_line(rx_line, &cmd)) {
                handle_command(&ctx, &cmd);
            } else {
                platform_comm_write_line("ERR BAD_CMD");
            }
        }
    }
}
