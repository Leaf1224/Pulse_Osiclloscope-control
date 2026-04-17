#ifndef PLATFORM_H
#define PLATFORM_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum {
    PLATFORM_PORT_A = 0,
    PLATFORM_PORT_B,
    PLATFORM_PORT_C,
    PLATFORM_PORT_INVALID
} platform_port_t;

typedef struct {
    platform_port_t port;
    uint8_t pin;
    bool active_high;
    bool pull_up;
} platform_pin_t;

void platform_init(void);
uint32_t platform_now_ms(void);

void platform_gpio_make_output(const platform_pin_t* pin);
void platform_gpio_make_input(const platform_pin_t* pin);
void platform_gpio_write(const platform_pin_t* pin, bool asserted);
bool platform_gpio_read(const platform_pin_t* pin);

void platform_pulse_counter_init(const platform_pin_t* pin);
uint32_t platform_pulse_counter_get(void);
void platform_pulse_counter_reset(void);

void platform_uart_write_str(const char* s);
void platform_uart_write_line(const char* s);
bool platform_uart_read_line(char* out, size_t out_size);

#endif
