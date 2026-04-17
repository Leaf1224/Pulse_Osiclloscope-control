#ifndef USBD_CONF_H
#define USBD_CONF_H

#include "stm32f4xx_hal.h"

#include <stdlib.h>
#include <string.h>

#define USBD_MAX_NUM_INTERFACES     2U
#define USBD_MAX_NUM_CONFIGURATION  1U
#define USBD_MAX_STR_DESC_SIZ       0x100U
#define USBD_SELF_POWERED           1U
#define USBD_DEBUG_LEVEL            0U

#define USBD_malloc                 usbd_malloc
#define USBD_free                   usbd_free
#define USBD_memset                 memset
#define USBD_memcpy                 memcpy
#define USBD_Delay                  HAL_Delay

#define USBD_UsrLog(...)
#define USBD_ErrLog(...)
#define USBD_DbgLog(...)

void* usbd_malloc(size_t size);
void usbd_free(void* ptr);

#endif
