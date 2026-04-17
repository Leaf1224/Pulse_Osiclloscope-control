#include "platform.h"
#include "usbd_cdc.h"
#include "usbd_core.h"
#include "usbd_desc.h"

#include <string.h>

#define USB_RX_CHUNK_SIZE     64U
#define USB_RX_RING_SIZE      512U
#define USB_TX_RING_SIZE      1024U
#define USB_LINE_BUF_SIZE     128U
#define USB_DEVICE_INSTANCE   0U

static USBD_HandleTypeDef g_usb_device;

static uint8_t g_usb_rx_chunk[USB_RX_CHUNK_SIZE];
static uint8_t g_usb_rx_ring[USB_RX_RING_SIZE];
static uint8_t g_usb_tx_ring[USB_TX_RING_SIZE];
static uint8_t g_usb_tx_chunk[CDC_DATA_FS_MAX_PACKET_SIZE];

static volatile uint16_t g_rx_head = 0U;
static volatile uint16_t g_rx_tail = 0U;
static volatile uint16_t g_tx_head = 0U;
static volatile uint16_t g_tx_tail = 0U;
static volatile bool g_tx_busy = false;
static volatile bool g_usb_ready = false;

static int8_t usb_cdc_init(void);
static int8_t usb_cdc_deinit(void);
static int8_t usb_cdc_control(uint8_t cmd, uint8_t* pbuf, uint16_t length);
static int8_t usb_cdc_receive(uint8_t* buf, uint32_t* len);
static int8_t usb_cdc_transmit_complete(uint8_t* buf, uint32_t* len, uint8_t epnum);
static void usb_kick_tx(void);
static bool usb_is_configured(void);
static void rx_push(uint8_t byte);
static bool rx_pop(uint8_t* out);
static void tx_push_bytes(const uint8_t* data, size_t len);

static USBD_CDC_LineCodingTypeDef g_line_coding = {
    115200U,
    0x00U,
    0x00U,
    0x08U,
};

static USBD_CDC_ItfTypeDef g_usb_cdc_fops = {
    usb_cdc_init,
    usb_cdc_deinit,
    usb_cdc_control,
    usb_cdc_receive,
    usb_cdc_transmit_complete,
};

static int8_t usb_cdc_init(void) {
    USBD_CDC_SetTxBuffer(&g_usb_device, g_usb_tx_chunk, 0U);
    USBD_CDC_SetRxBuffer(&g_usb_device, g_usb_rx_chunk);
    return (USBD_CDC_ReceivePacket(&g_usb_device) == USBD_OK) ? (int8_t)USBD_OK : (int8_t)USBD_FAIL;
}

static int8_t usb_cdc_deinit(void) {
    g_usb_ready = false;
    g_tx_busy = false;
    g_rx_head = 0U;
    g_rx_tail = 0U;
    g_tx_head = 0U;
    g_tx_tail = 0U;
    return (int8_t)USBD_OK;
}

static int8_t usb_cdc_control(uint8_t cmd, uint8_t* pbuf, uint16_t length) {
    (void)length;

    switch (cmd) {
        case CDC_SET_LINE_CODING:
            g_line_coding.bitrate = (uint32_t)pbuf[0]
                                  | ((uint32_t)pbuf[1] << 8)
                                  | ((uint32_t)pbuf[2] << 16)
                                  | ((uint32_t)pbuf[3] << 24);
            g_line_coding.format = pbuf[4];
            g_line_coding.paritytype = pbuf[5];
            g_line_coding.datatype = pbuf[6];
            break;
        case CDC_GET_LINE_CODING:
            pbuf[0] = (uint8_t)(g_line_coding.bitrate);
            pbuf[1] = (uint8_t)(g_line_coding.bitrate >> 8);
            pbuf[2] = (uint8_t)(g_line_coding.bitrate >> 16);
            pbuf[3] = (uint8_t)(g_line_coding.bitrate >> 24);
            pbuf[4] = g_line_coding.format;
            pbuf[5] = g_line_coding.paritytype;
            pbuf[6] = g_line_coding.datatype;
            break;
        case CDC_SET_CONTROL_LINE_STATE:
            g_usb_ready = true;
            break;
        default:
            break;
    }

    return (int8_t)USBD_OK;
}

static int8_t usb_cdc_receive(uint8_t* buf, uint32_t* len) {
    uint32_t count = (len != 0) ? *len : 0U;
    for (uint32_t i = 0U; i < count; ++i) {
        rx_push(buf[i]);
    }

    USBD_CDC_SetRxBuffer(&g_usb_device, g_usb_rx_chunk);
    USBD_CDC_ReceivePacket(&g_usb_device);
    return (int8_t)USBD_OK;
}

static int8_t usb_cdc_transmit_complete(uint8_t* buf, uint32_t* len, uint8_t epnum) {
    (void)buf;
    (void)len;
    (void)epnum;
    g_tx_busy = false;
    usb_kick_tx();
    return (int8_t)USBD_OK;
}

static bool usb_is_configured(void) {
    return g_usb_device.dev_state == USBD_STATE_CONFIGURED;
}

static void rx_push(uint8_t byte) {
    uint16_t next = (uint16_t)((g_rx_head + 1U) % USB_RX_RING_SIZE);
    if (next == g_rx_tail) {
        g_rx_tail = (uint16_t)((g_rx_tail + 1U) % USB_RX_RING_SIZE);
    }
    g_usb_rx_ring[g_rx_head] = byte;
    g_rx_head = next;
}

static bool rx_pop(uint8_t* out) {
    if (g_rx_tail == g_rx_head) {
        return false;
    }
    *out = g_usb_rx_ring[g_rx_tail];
    g_rx_tail = (uint16_t)((g_rx_tail + 1U) % USB_RX_RING_SIZE);
    return true;
}

static void tx_push_bytes(const uint8_t* data, size_t len) {
    for (size_t i = 0U; i < len; ++i) {
        uint16_t next = (uint16_t)((g_tx_head + 1U) % USB_TX_RING_SIZE);
        if (next == g_tx_tail) {
            g_tx_tail = (uint16_t)((g_tx_tail + 1U) % USB_TX_RING_SIZE);
        }
        g_usb_tx_ring[g_tx_head] = data[i];
        g_tx_head = next;
    }
}

static void usb_kick_tx(void) {
    uint32_t count = 0U;

    if (!usb_is_configured() || g_tx_busy || (g_tx_tail == g_tx_head)) {
        return;
    }

    while ((g_tx_tail != g_tx_head) && (count < sizeof(g_usb_tx_chunk))) {
        g_usb_tx_chunk[count++] = g_usb_tx_ring[g_tx_tail];
        g_tx_tail = (uint16_t)((g_tx_tail + 1U) % USB_TX_RING_SIZE);
    }

    if (count == 0U) {
        return;
    }

    USBD_CDC_SetTxBuffer(&g_usb_device, g_usb_tx_chunk, count);
    if (USBD_CDC_TransmitPacket(&g_usb_device) == USBD_OK) {
        g_tx_busy = true;
    }
}

bool platform_usb_cdc_init(void) {
    g_usb_ready = false;
    g_tx_busy = false;
    g_rx_head = 0U;
    g_rx_tail = 0U;
    g_tx_head = 0U;
    g_tx_tail = 0U;

    if (USBD_Init(&g_usb_device, &g_usb_vcp_desc, USB_DEVICE_INSTANCE) != USBD_OK) {
        return false;
    }
    if (USBD_RegisterClass(&g_usb_device, USBD_CDC_CLASS) != USBD_OK) {
        return false;
    }
    if (USBD_CDC_RegisterInterface(&g_usb_device, &g_usb_cdc_fops) != USBD_OK) {
        return false;
    }
    if (USBD_Start(&g_usb_device) != USBD_OK) {
        return false;
    }
    return true;
}

bool platform_usb_cdc_read_line(char* out, size_t out_size) {
    static char line_buf[USB_LINE_BUF_SIZE];
    static size_t line_len = 0U;
    uint8_t byte;

    if (out == 0 || out_size < 2U) {
        return false;
    }

    while (rx_pop(&byte)) {
        if (byte == '\r') {
            continue;
        }
        if (byte == '\n') {
            if (line_len >= out_size) {
                line_len = 0U;
                return false;
            }
            line_buf[line_len] = '\0';
            memcpy(out, line_buf, line_len + 1U);
            line_len = 0U;
            return true;
        }
        if (line_len + 1U < sizeof(line_buf)) {
            line_buf[line_len++] = (char)byte;
        } else {
            line_len = 0U;
        }
    }

    return false;
}

void platform_usb_cdc_write_str(const char* s) {
    if (s == 0 || !usb_is_configured()) {
        return;
    }

    tx_push_bytes((const uint8_t*)s, strlen(s));
    usb_kick_tx();
}
