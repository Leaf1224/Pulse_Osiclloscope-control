#ifndef APP_LOG_H
#define APP_LOG_H

#include <stdbool.h>
#include <stdint.h>
#include "app_types.h"

#define APP_LOG_CAPACITY 64U

typedef struct {
    uint32_t ms;
    app_state_t state;
    fault_code_t fault;
    uint32_t count;
} app_log_entry_t;

typedef struct {
    app_log_entry_t entries[APP_LOG_CAPACITY];
    uint16_t head;
    uint16_t size;
} app_log_t;

void app_log_init(app_log_t* log);
void app_log_push(app_log_t* log, app_log_entry_t entry);
bool app_log_latest(const app_log_t* log, app_log_entry_t* out);

#endif
