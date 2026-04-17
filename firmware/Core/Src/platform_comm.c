#include "platform_comm.h"

#include "platform.h"

/*
 * Communication policy:
 * 1) Try USB CDC first (Type-C D+/D- on PA11/PA12).
 * 2) Fall back to UART when USB CDC backend is not linked yet.
 */
static bool g_usb_active = false;

/*
 * These weak hooks let you link vendor USB CDC implementation later
 * (AT32 or STM32 library) without changing app logic.
 */
__attribute__((weak)) bool platform_usb_cdc_init(void) {
    return false;
}

__attribute__((weak)) bool platform_usb_cdc_read_line(char* out, size_t out_size) {
    (void)out;
    (void)out_size;
    return false;
}

__attribute__((weak)) void platform_usb_cdc_write_str(const char* s) {
    (void)s;
}

void platform_comm_init(void) {
    g_usb_active = platform_usb_cdc_init();
}

bool platform_comm_is_usb_active(void) {
    return g_usb_active;
}

bool platform_comm_read_line(char* out, size_t out_size) {
    if (g_usb_active) {
        return platform_usb_cdc_read_line(out, out_size);
    }
    return platform_uart_read_line(out, out_size);
}

void platform_comm_write_str(const char* s) {
    if (g_usb_active) {
        platform_usb_cdc_write_str(s);
        return;
    }
    platform_uart_write_str(s);
}

void platform_comm_write_line(const char* s) {
    platform_comm_write_str(s);
    platform_comm_write_str("\n");
}
