#include "usbd_core.h"
#include "usbd_desc.h"
#include "usbd_conf.h"

#define USBD_VID                       0x1209U
#define USBD_PID                       0x4010U
#define USBD_LANGID_STRING             0x0409U
#define USBD_MANUFACTURER_STRING       "ISTA"
#define USBD_PRODUCT_FS_STRING         "V1 Pulse Platform CDC"
#define USBD_CONFIGURATION_FS_STRING   "CDC Config"
#define USBD_INTERFACE_FS_STRING       "CDC Interface"

static uint8_t* usb_device_descriptor(USBD_SpeedTypeDef speed, uint16_t* length);
static uint8_t* usb_langid_descriptor(USBD_SpeedTypeDef speed, uint16_t* length);
static uint8_t* usb_manufacturer_descriptor(USBD_SpeedTypeDef speed, uint16_t* length);
static uint8_t* usb_product_descriptor(USBD_SpeedTypeDef speed, uint16_t* length);
static uint8_t* usb_serial_descriptor(USBD_SpeedTypeDef speed, uint16_t* length);
static uint8_t* usb_config_descriptor(USBD_SpeedTypeDef speed, uint16_t* length);
static uint8_t* usb_interface_descriptor(USBD_SpeedTypeDef speed, uint16_t* length);
static void int_to_unicode(uint32_t value, uint8_t* out, uint8_t len);
static void update_serial_string(void);

USBD_DescriptorsTypeDef g_usb_vcp_desc = {
    usb_device_descriptor,
    usb_langid_descriptor,
    usb_manufacturer_descriptor,
    usb_product_descriptor,
    usb_serial_descriptor,
    usb_config_descriptor,
    usb_interface_descriptor,
};

__ALIGN_BEGIN static uint8_t g_device_desc[USB_LEN_DEV_DESC] __ALIGN_END = {
    0x12U,
    USB_DESC_TYPE_DEVICE,
    0x00U, 0x02U,
    0x02U,
    0x02U,
    0x00U,
    USB_MAX_EP0_SIZE,
    LOBYTE(USBD_VID), HIBYTE(USBD_VID),
    LOBYTE(USBD_PID), HIBYTE(USBD_PID),
    0x00U, 0x01U,
    USBD_IDX_MFC_STR,
    USBD_IDX_PRODUCT_STR,
    USBD_IDX_SERIAL_STR,
    USBD_MAX_NUM_CONFIGURATION
};

__ALIGN_BEGIN static uint8_t g_lang_id_desc[USB_LEN_LANGID_STR_DESC] __ALIGN_END = {
    USB_LEN_LANGID_STR_DESC,
    USB_DESC_TYPE_STRING,
    LOBYTE(USBD_LANGID_STRING), HIBYTE(USBD_LANGID_STRING),
};

__ALIGN_BEGIN static uint8_t g_serial_desc[USB_SIZ_STRING_SERIAL] __ALIGN_END = {
    USB_SIZ_STRING_SERIAL,
    USB_DESC_TYPE_STRING,
};

__ALIGN_BEGIN static uint8_t g_str_desc[USBD_MAX_STR_DESC_SIZ] __ALIGN_END;

static uint8_t* usb_device_descriptor(USBD_SpeedTypeDef speed, uint16_t* length) {
    UNUSED(speed);
    *length = sizeof(g_device_desc);
    return g_device_desc;
}

static uint8_t* usb_langid_descriptor(USBD_SpeedTypeDef speed, uint16_t* length) {
    UNUSED(speed);
    *length = sizeof(g_lang_id_desc);
    return g_lang_id_desc;
}

static uint8_t* usb_manufacturer_descriptor(USBD_SpeedTypeDef speed, uint16_t* length) {
    UNUSED(speed);
    USBD_GetString((uint8_t*)USBD_MANUFACTURER_STRING, g_str_desc, length);
    return g_str_desc;
}

static uint8_t* usb_product_descriptor(USBD_SpeedTypeDef speed, uint16_t* length) {
    UNUSED(speed);
    USBD_GetString((uint8_t*)USBD_PRODUCT_FS_STRING, g_str_desc, length);
    return g_str_desc;
}

static uint8_t* usb_serial_descriptor(USBD_SpeedTypeDef speed, uint16_t* length) {
    UNUSED(speed);
    *length = USB_SIZ_STRING_SERIAL;
    update_serial_string();
    return g_serial_desc;
}

static uint8_t* usb_config_descriptor(USBD_SpeedTypeDef speed, uint16_t* length) {
    UNUSED(speed);
    USBD_GetString((uint8_t*)USBD_CONFIGURATION_FS_STRING, g_str_desc, length);
    return g_str_desc;
}

static uint8_t* usb_interface_descriptor(USBD_SpeedTypeDef speed, uint16_t* length) {
    UNUSED(speed);
    USBD_GetString((uint8_t*)USBD_INTERFACE_FS_STRING, g_str_desc, length);
    return g_str_desc;
}

static void update_serial_string(void) {
    uint32_t serial0 = *(uint32_t*)DEVICE_ID1;
    uint32_t serial1 = *(uint32_t*)DEVICE_ID2;
    uint32_t serial2 = *(uint32_t*)DEVICE_ID3;

    serial0 += serial2;
    if (serial0 != 0U) {
        int_to_unicode(serial0, &g_serial_desc[2], 8U);
        int_to_unicode(serial1, &g_serial_desc[18], 4U);
    }
}

static void int_to_unicode(uint32_t value, uint8_t* out, uint8_t len) {
    for (uint8_t i = 0U; i < len; ++i) {
        out[2U * i] = ((value >> 28) < 0xAU) ? (uint8_t)((value >> 28) + '0')
                                             : (uint8_t)((value >> 28) + 'A' - 10U);
        out[2U * i + 1U] = 0U;
        value <<= 4U;
    }
}
