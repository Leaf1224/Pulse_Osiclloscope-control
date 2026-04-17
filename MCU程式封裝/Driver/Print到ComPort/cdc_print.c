#include "cdc_print.h"
#include "usbd_cdc_if.h"
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

void CDC_Printf(const char *fmt, ...)
{
    char buf[128];
    va_list args;

    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    while (CDC_Transmit_FS((uint8_t*)buf, strlen(buf)) == USBD_BUSY)
    {
        HAL_Delay(1);
    }
}