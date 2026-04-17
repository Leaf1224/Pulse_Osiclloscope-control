#ifndef BOARD_CONFIG_H
#define BOARD_CONFIG_H

#include "platform.h"

typedef struct {
    platform_pin_t precharge_en;
    platform_pin_t bus_main_en;
    platform_pin_t discharge_en;
    platform_pin_t driver_en;
    platform_pin_t reset_latch;
    platform_pin_t start_trig;
    platform_pin_t end_trig;
    platform_pin_t fault_trig;
    platform_pin_t led_run;
    platform_pin_t led_fault;

    platform_pin_t ps_ok_all_in;
    platform_pin_t interlock_in;
    platform_pin_t estop_in;
    platform_pin_t ocp_fault_in;
    platform_pin_t timeout_fault_in;
    platform_pin_t thermal_fault_in;
    platform_pin_t dut_off_check_in;
    platform_pin_t fg_pulse_mon_in;
} board_gpio_map_t;

const board_gpio_map_t* board_config_get(void);
void board_config_init_gpio(void);

#endif
