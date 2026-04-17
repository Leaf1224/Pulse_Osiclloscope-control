#ifndef APP_FAULT_H
#define APP_FAULT_H

#include <stdbool.h>
#include "app_types.h"

typedef struct {
    bool latched;
    fault_code_t code;
    uint32_t pulse_at_fault;
} app_fault_state_t;

void app_fault_init(app_fault_state_t* fs);
void app_fault_latch(app_fault_state_t* fs, fault_code_t code, uint32_t pulse_count);
void app_fault_clear(app_fault_state_t* fs);
bool app_fault_is_latched(const app_fault_state_t* fs);

#endif
