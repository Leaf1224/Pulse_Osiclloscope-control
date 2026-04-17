#include "app_counter.h"

void app_counter_init(app_counter_t* c) {
    if (c == 0) {
        return;
    }
    c->pulse_count = 0U;
    c->state_elapsed_ms = 0U;
    c->fg_sync_count = 0U;
}

void app_counter_on_tick(app_counter_t* c, uint32_t period_ms) {
    if (c == 0) {
        return;
    }
    c->state_elapsed_ms += period_ms;
}

void app_counter_reset_state_timer(app_counter_t* c) {
    if (c == 0) {
        return;
    }
    c->state_elapsed_ms = 0U;
}

void app_counter_inc_pulse(app_counter_t* c) {
    if (c == 0) {
        return;
    }
    c->pulse_count += 1U;
}

void app_counter_set_fg_sync_count(app_counter_t* c, uint32_t fg_sync_count) {
    if (c == 0) {
        return;
    }
    c->fg_sync_count = fg_sync_count;
}

bool app_counter_target_reached(const app_counter_t* c, uint32_t target) {
    if (c == 0) {
        return false;
    }
    return c->pulse_count >= target;
}
