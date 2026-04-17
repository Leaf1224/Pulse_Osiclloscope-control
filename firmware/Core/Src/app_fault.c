#include "app_fault.h"

void app_fault_init(app_fault_state_t* fs) {
    if (fs == 0) {
        return;
    }
    fs->latched = false;
    fs->code = FAULT_NONE;
    fs->pulse_at_fault = 0U;
}

void app_fault_latch(app_fault_state_t* fs, fault_code_t code, uint32_t pulse_count) {
    if (fs == 0 || fs->latched) {
        return;
    }
    fs->latched = true;
    fs->code = code;
    fs->pulse_at_fault = pulse_count;
}

void app_fault_clear(app_fault_state_t* fs) {
    if (fs == 0) {
        return;
    }
    fs->latched = false;
    fs->code = FAULT_NONE;
    fs->pulse_at_fault = 0U;
}

bool app_fault_is_latched(const app_fault_state_t* fs) {
    return (fs != 0) && fs->latched;
}
