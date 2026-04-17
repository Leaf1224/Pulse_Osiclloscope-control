#ifndef APP_IO_H
#define APP_IO_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    bool ps_ok_all_in;
    bool interlock_in;
    bool estop_in;
    bool ocp_fault_in;
    bool timeout_fault_in;
    bool thermal_fault_in;
    bool dut_off_check_in;
    bool fg_pulse_mon_in;

    float bus_v_adc;
    float cap_v_adc;
    uint32_t fg_sync_count;
} app_inputs_t;

typedef struct {
    bool precharge_en;
    bool bus_main_en;
    bool discharge_en;
    bool driver_en;
    bool reset_latch;
    bool start_trig;
    bool end_trig;
    bool fault_trig;
    bool led_run;
    bool led_fault;
} app_outputs_t;

void app_io_init(void);
void app_io_read_inputs(app_inputs_t* in);
void app_io_apply_outputs(const app_outputs_t* out);

#endif
