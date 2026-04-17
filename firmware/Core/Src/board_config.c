#include "board_config.h"

/*
 * STM32F401CCU6 Type-C MCU board mapping from docs/STM32.pdf.
 * Most control/fault signals are only broken out on headers, not populated on-board.
 */
static const board_gpio_map_t g_map = {
    .precharge_en     = { PLATFORM_PORT_B, 0U,  true,  false },
    .bus_main_en      = { PLATFORM_PORT_B, 1U,  true,  false },
    .discharge_en     = { PLATFORM_PORT_B, 2U,  true,  false },
    .driver_en        = { PLATFORM_PORT_B, 10U, true,  false },
    .reset_latch      = { PLATFORM_PORT_A, 8U,  true,  false },
    .start_trig       = { PLATFORM_PORT_A, 9U,  true,  false },
    .end_trig         = { PLATFORM_PORT_A, 10U, true,  false },
    .fault_trig       = { PLATFORM_PORT_A, 15U, true,  false },
    .led_run          = { PLATFORM_PORT_C, 13U, true,  false },
    .led_fault        = { PLATFORM_PORT_INVALID, 0U, false, false },

    .ps_ok_all_in     = { PLATFORM_PORT_INVALID, 0U, false, false },
    .interlock_in     = { PLATFORM_PORT_INVALID, 0U, false, false },
    .estop_in         = { PLATFORM_PORT_INVALID, 0U, false, false },
    .ocp_fault_in     = { PLATFORM_PORT_INVALID, 0U, false, false },
    .timeout_fault_in = { PLATFORM_PORT_INVALID, 0U, false, false },
    .thermal_fault_in = { PLATFORM_PORT_INVALID, 0U, false, false },
    .dut_off_check_in = { PLATFORM_PORT_INVALID, 0U, false, false },
    .fg_pulse_mon_in  = { PLATFORM_PORT_B, 12U, true,  false },
};

const board_gpio_map_t* board_config_get(void) {
    return &g_map;
}

void board_config_init_gpio(void) {
    const board_gpio_map_t* map = board_config_get();

    platform_gpio_make_output(&map->precharge_en);
    platform_gpio_make_output(&map->bus_main_en);
    platform_gpio_make_output(&map->discharge_en);
    platform_gpio_make_output(&map->driver_en);
    platform_gpio_make_output(&map->reset_latch);
    platform_gpio_make_output(&map->start_trig);
    platform_gpio_make_output(&map->end_trig);
    platform_gpio_make_output(&map->fault_trig);
    platform_gpio_make_output(&map->led_run);
    platform_gpio_make_output(&map->led_fault);

    platform_gpio_make_input(&map->ps_ok_all_in);
    platform_gpio_make_input(&map->interlock_in);
    platform_gpio_make_input(&map->estop_in);
    platform_gpio_make_input(&map->ocp_fault_in);
    platform_gpio_make_input(&map->timeout_fault_in);
    platform_gpio_make_input(&map->thermal_fault_in);
    platform_gpio_make_input(&map->dut_off_check_in);
    platform_gpio_make_input(&map->fg_pulse_mon_in);
    platform_pulse_counter_init(&map->fg_pulse_mon_in);
}
