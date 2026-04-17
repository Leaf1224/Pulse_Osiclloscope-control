#include <stdbool.h>
#include <stddef.h>

/*
 * USB CDC backend template.
 *
 * Rename this file to platform_usb_cdc.c and implement with your vendor USB stack.
 * Required physical routing for your board (from schematic):
 * - PA11 -> USB DM
 * - PA12 -> USB DP
 * - Type-C CC1/CC2 pull-down present (5.1k) as UFP device role
 */

bool platform_usb_cdc_init(void) {
    /*
     * TODO:
     * 1. Initialize USB clock and pins (PA11/PA12)
     * 2. Initialize USB device core
     * 3. Register CDC ACM class
     * 4. Start USB device stack
     *
     * Return true only if CDC backend is ready.
     */
    return false;
}

bool platform_usb_cdc_read_line(char* out, size_t out_size) {
    (void)out;
    (void)out_size;
    /*
     * TODO:
     * - Read bytes from CDC RX buffer
     * - Assemble LF-terminated line
     * - Return true when a full line is available
     */
    return false;
}

void platform_usb_cdc_write_str(const char* s) {
    (void)s;
    /*
     * TODO:
     * - Write bytes through CDC TX endpoint
     */
}
