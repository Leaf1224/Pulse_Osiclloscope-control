#ifndef APP_CONFIG_H
#define APP_CONFIG_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint32_t loop_period_ms;
    uint32_t precharge_timeout_ms;
    uint32_t bus_ready_timeout_ms;
    uint32_t discharge_timeout_ms;
    uint32_t run_timeout_ms;
    uint32_t trigger_pulse_ms;
    uint32_t target_pulse_count;

    float bus_ready_threshold_v;
    float bus_safe_threshold_v;
    float bus_uv_threshold_v;

    bool active_high_precharge_en;
    bool active_high_bus_main_en;
    bool active_high_discharge_en;
    bool active_high_driver_en;
    bool active_high_fault_inputs;
} app_config_t;

void app_config_load_defaults(app_config_t* cfg);

#endif
