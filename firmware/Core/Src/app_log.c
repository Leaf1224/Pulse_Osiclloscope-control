#include "app_log.h"

void app_log_init(app_log_t* log) {
    if (log == 0) {
        return;
    }
    log->head = 0U;
    log->size = 0U;
}

void app_log_push(app_log_t* log, app_log_entry_t entry) {
    uint16_t idx;
    if (log == 0) {
        return;
    }

    idx = log->head % APP_LOG_CAPACITY;
    log->entries[idx] = entry;
    log->head = (uint16_t)((log->head + 1U) % APP_LOG_CAPACITY);
    if (log->size < APP_LOG_CAPACITY) {
        log->size += 1U;
    }
}

bool app_log_latest(const app_log_t* log, app_log_entry_t* out) {
    uint16_t last_idx;
    if (log == 0 || out == 0 || log->size == 0U) {
        return false;
    }

    last_idx = (uint16_t)((log->head + APP_LOG_CAPACITY - 1U) % APP_LOG_CAPACITY);
    *out = log->entries[last_idx];
    return true;
}
