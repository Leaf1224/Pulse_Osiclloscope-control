#ifndef PLATFORM_COMM_H
#define PLATFORM_COMM_H

#include <stdbool.h>
#include <stddef.h>

void platform_comm_init(void);
bool platform_comm_is_usb_active(void);
bool platform_comm_read_line(char* out, size_t out_size);
void platform_comm_write_str(const char* s);
void platform_comm_write_line(const char* s);

#endif
