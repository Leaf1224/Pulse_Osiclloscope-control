#include "app_io.h"

#include "board_config.h"
#include "platform.h"

static app_outputs_t g_out;

void app_io_init(void) {
    board_config_init_gpio();

    g_out.precharge_en = false;
    g_out.bus_main_en = false;
    g_out.discharge_en = false;
    g_out.driver_en = false;
    g_out.reset_latch = false;
    g_out.start_trig = false;
    g_out.end_trig = false;
    g_out.fault_trig = false;
    g_out.led_run = false;
    g_out.led_fault = false;
}

void app_io_read_inputs(app_inputs_t* in) {
    const board_gpio_map_t* map = board_config_get();

    if (in == 0) {
        return;
    }

    in->ps_ok_all_in = platform_gpio_read(&map->ps_ok_all_in);
    in->interlock_in = platform_gpio_read(&map->interlock_in);
    in->estop_in = platform_gpio_read(&map->estop_in);
    in->ocp_fault_in = platform_gpio_read(&map->ocp_fault_in);
    in->timeout_fault_in = platform_gpio_read(&map->timeout_fault_in);
    in->thermal_fault_in = platform_gpio_read(&map->thermal_fault_in);
    in->dut_off_check_in = platform_gpio_read(&map->dut_off_check_in);
    in->fg_pulse_mon_in = platform_gpio_read(&map->fg_pulse_mon_in);
    in->bus_v_adc = 14.0f;
    in->cap_v_adc = 14.0f;
    in->fg_sync_count = platform_pulse_counter_get();
}

void app_io_apply_outputs(const app_outputs_t* out) {
    const board_gpio_map_t* map = board_config_get();

    if (out == 0) {
        return;
    }
    g_out = *out;

    platform_gpio_write(&map->precharge_en, g_out.precharge_en);
    platform_gpio_write(&map->bus_main_en, g_out.bus_main_en);
    platform_gpio_write(&map->discharge_en, g_out.discharge_en);
    platform_gpio_write(&map->driver_en, g_out.driver_en);
    platform_gpio_write(&map->reset_latch, g_out.reset_latch);
    platform_gpio_write(&map->start_trig, g_out.start_trig);
    platform_gpio_write(&map->end_trig, g_out.end_trig);
    platform_gpio_write(&map->fault_trig, g_out.fault_trig);
    platform_gpio_write(&map->led_run, g_out.led_run);
    platform_gpio_write(&map->led_fault, g_out.led_fault);
}
