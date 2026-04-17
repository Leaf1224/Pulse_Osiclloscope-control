#include "app_config.h"

void app_config_load_defaults(app_config_t* cfg) {
    if (cfg == 0) {
        return;
    }

    cfg->loop_period_ms = 1U;
    cfg->precharge_timeout_ms = 2000U;
    cfg->bus_ready_timeout_ms = 3000U;
    cfg->discharge_timeout_ms = 5000U;
    cfg->run_timeout_ms = 10U;
    cfg->trigger_pulse_ms = 1U;
    cfg->target_pulse_count = 1U;

    cfg->bus_ready_threshold_v = 13.5f;
    cfg->bus_safe_threshold_v = 2.0f;
    cfg->bus_uv_threshold_v = 12.5f;

    cfg->active_high_precharge_en = true;
    cfg->active_high_bus_main_en = true;
    cfg->active_high_discharge_en = true;
    cfg->active_high_driver_en = true;
    cfg->active_high_fault_inputs = true;
}
