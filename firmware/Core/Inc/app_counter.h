#ifndef APP_COUNTER_H
#define APP_COUNTER_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint32_t pulse_count;
    uint32_t state_elapsed_ms;
    uint32_t fg_sync_count;
} app_counter_t;

void app_counter_init(app_counter_t* c);
void app_counter_on_tick(app_counter_t* c, uint32_t period_ms);
void app_counter_reset_state_timer(app_counter_t* c);
void app_counter_inc_pulse(app_counter_t* c);
void app_counter_set_fg_sync_count(app_counter_t* c, uint32_t fg_sync_count);
bool app_counter_target_reached(const app_counter_t* c, uint32_t target);

#endif
