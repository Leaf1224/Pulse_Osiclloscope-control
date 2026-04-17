#include "platform.h"
#include "stm32f4xx_hal.h"
#include "usbd_conf.h"
#include "usbd_core.h"

#define USBD_HEAP_SIZE 1024U

PCD_HandleTypeDef hpcd_USB_OTG_FS;
static uint8_t g_usbd_heap[USBD_HEAP_SIZE];
static size_t g_usbd_heap_used = 0U;

void* usbd_malloc(size_t size) {
    size_t aligned = (size + 3U) & ~((size_t)3U);
    void* out;

    if ((g_usbd_heap_used + aligned) > sizeof(g_usbd_heap)) {
        return 0;
    }

    out = &g_usbd_heap[g_usbd_heap_used];
    g_usbd_heap_used += aligned;
    return out;
}

void usbd_free(void* ptr) {
    (void)ptr;
}

void HAL_PCD_MspInit(PCD_HandleTypeDef* hpcd) {
    GPIO_InitTypeDef gpio_init = {0};

    if (hpcd->Instance != USB_OTG_FS) {
        return;
    }

    __HAL_RCC_SYSCFG_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_USB_OTG_FS_CLK_ENABLE();

    gpio_init.Pin = GPIO_PIN_11 | GPIO_PIN_12;
    gpio_init.Mode = GPIO_MODE_AF_PP;
    gpio_init.Pull = GPIO_NOPULL;
    gpio_init.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio_init.Alternate = GPIO_AF10_OTG_FS;
    HAL_GPIO_Init(GPIOA, &gpio_init);

    gpio_init.Pin = GPIO_PIN_9;
    gpio_init.Mode = GPIO_MODE_INPUT;
    gpio_init.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOA, &gpio_init);

    gpio_init.Pin = GPIO_PIN_10;
    gpio_init.Mode = GPIO_MODE_AF_OD;
    gpio_init.Pull = GPIO_PULLUP;
    gpio_init.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio_init.Alternate = GPIO_AF10_OTG_FS;
    HAL_GPIO_Init(GPIOA, &gpio_init);

    HAL_NVIC_SetPriority(OTG_FS_IRQn, 6U, 0U);
    HAL_NVIC_EnableIRQ(OTG_FS_IRQn);
}

void HAL_PCD_MspDeInit(PCD_HandleTypeDef* hpcd) {
    if (hpcd->Instance != USB_OTG_FS) {
        return;
    }

    HAL_NVIC_DisableIRQ(OTG_FS_IRQn);
    __HAL_RCC_USB_OTG_FS_CLK_DISABLE();
}

void HAL_PCD_SetupStageCallback(PCD_HandleTypeDef* hpcd) {
    USBD_LL_SetupStage((USBD_HandleTypeDef*)hpcd->pData, (uint8_t*)hpcd->Setup);
}

void HAL_PCD_DataOutStageCallback(PCD_HandleTypeDef* hpcd, uint8_t epnum) {
    USBD_LL_DataOutStage((USBD_HandleTypeDef*)hpcd->pData, epnum, hpcd->OUT_ep[epnum].xfer_buff);
}

void HAL_PCD_DataInStageCallback(PCD_HandleTypeDef* hpcd, uint8_t epnum) {
    USBD_LL_DataInStage((USBD_HandleTypeDef*)hpcd->pData, epnum, hpcd->IN_ep[epnum].xfer_buff);
}

void HAL_PCD_SOFCallback(PCD_HandleTypeDef* hpcd) {
    USBD_LL_SOF((USBD_HandleTypeDef*)hpcd->pData);
}

void HAL_PCD_ResetCallback(PCD_HandleTypeDef* hpcd) {
    USBD_LL_SetSpeed((USBD_HandleTypeDef*)hpcd->pData, USBD_SPEED_FULL);
    USBD_LL_Reset((USBD_HandleTypeDef*)hpcd->pData);
}

void HAL_PCD_SuspendCallback(PCD_HandleTypeDef* hpcd) {
    USBD_LL_Suspend((USBD_HandleTypeDef*)hpcd->pData);
}

void HAL_PCD_ResumeCallback(PCD_HandleTypeDef* hpcd) {
    USBD_LL_Resume((USBD_HandleTypeDef*)hpcd->pData);
}

void HAL_PCD_ConnectCallback(PCD_HandleTypeDef* hpcd) {
    USBD_LL_DevConnected((USBD_HandleTypeDef*)hpcd->pData);
}

void HAL_PCD_DisconnectCallback(PCD_HandleTypeDef* hpcd) {
    USBD_LL_DevDisconnected((USBD_HandleTypeDef*)hpcd->pData);
}

USBD_StatusTypeDef USBD_LL_Init(USBD_HandleTypeDef* pdev) {
    HAL_NVIC_SetPriority(SysTick_IRQn, 0U, 0U);
    hpcd_USB_OTG_FS.Instance = USB_OTG_FS;
    hpcd_USB_OTG_FS.Init.dev_endpoints = 4U;
    hpcd_USB_OTG_FS.Init.use_dedicated_ep1 = 0U;
    hpcd_USB_OTG_FS.Init.dma_enable = 0U;
    hpcd_USB_OTG_FS.Init.low_power_enable = 0U;
    hpcd_USB_OTG_FS.Init.phy_itface = PCD_PHY_EMBEDDED;
    hpcd_USB_OTG_FS.Init.Sof_enable = 0U;
    hpcd_USB_OTG_FS.Init.speed = PCD_SPEED_FULL;
    hpcd_USB_OTG_FS.Init.vbus_sensing_enable = 0U;
    hpcd_USB_OTG_FS.Init.lpm_enable = 0U;

    hpcd_USB_OTG_FS.pData = pdev;
    pdev->pData = &hpcd_USB_OTG_FS;

    if (HAL_PCD_Init(&hpcd_USB_OTG_FS) != HAL_OK) {
        return USBD_FAIL;
    }

    HAL_PCDEx_SetRxFiFo(&hpcd_USB_OTG_FS, 0x80U);
    HAL_PCDEx_SetTxFiFo(&hpcd_USB_OTG_FS, 0U, 0x40U);
    HAL_PCDEx_SetTxFiFo(&hpcd_USB_OTG_FS, 1U, 0x80U);
    return USBD_OK;
}

USBD_StatusTypeDef USBD_LL_DeInit(USBD_HandleTypeDef* pdev) {
    return (HAL_PCD_DeInit((PCD_HandleTypeDef*)pdev->pData) == HAL_OK) ? USBD_OK : USBD_FAIL;
}

USBD_StatusTypeDef USBD_LL_Start(USBD_HandleTypeDef* pdev) {
    return (HAL_PCD_Start((PCD_HandleTypeDef*)pdev->pData) == HAL_OK) ? USBD_OK : USBD_FAIL;
}

USBD_StatusTypeDef USBD_LL_Stop(USBD_HandleTypeDef* pdev) {
    return (HAL_PCD_Stop((PCD_HandleTypeDef*)pdev->pData) == HAL_OK) ? USBD_OK : USBD_FAIL;
}

USBD_StatusTypeDef USBD_LL_OpenEP(USBD_HandleTypeDef* pdev, uint8_t ep_addr, uint8_t ep_type, uint16_t ep_mps) {
    return (HAL_PCD_EP_Open((PCD_HandleTypeDef*)pdev->pData, ep_addr, ep_mps, ep_type) == HAL_OK) ? USBD_OK : USBD_FAIL;
}

USBD_StatusTypeDef USBD_LL_CloseEP(USBD_HandleTypeDef* pdev, uint8_t ep_addr) {
    return (HAL_PCD_EP_Close((PCD_HandleTypeDef*)pdev->pData, ep_addr) == HAL_OK) ? USBD_OK : USBD_FAIL;
}

USBD_StatusTypeDef USBD_LL_FlushEP(USBD_HandleTypeDef* pdev, uint8_t ep_addr) {
    return (HAL_PCD_EP_Flush((PCD_HandleTypeDef*)pdev->pData, ep_addr) == HAL_OK) ? USBD_OK : USBD_FAIL;
}

USBD_StatusTypeDef USBD_LL_StallEP(USBD_HandleTypeDef* pdev, uint8_t ep_addr) {
    return (HAL_PCD_EP_SetStall((PCD_HandleTypeDef*)pdev->pData, ep_addr) == HAL_OK) ? USBD_OK : USBD_FAIL;
}

USBD_StatusTypeDef USBD_LL_ClearStallEP(USBD_HandleTypeDef* pdev, uint8_t ep_addr) {
    return (HAL_PCD_EP_ClrStall((PCD_HandleTypeDef*)pdev->pData, ep_addr) == HAL_OK) ? USBD_OK : USBD_FAIL;
}

uint8_t USBD_LL_IsStallEP(USBD_HandleTypeDef* pdev, uint8_t ep_addr) {
    PCD_HandleTypeDef* hpcd = (PCD_HandleTypeDef*)pdev->pData;
    if ((ep_addr & 0x80U) != 0U) {
        return hpcd->IN_ep[ep_addr & 0x7FU].is_stall;
    }
    return hpcd->OUT_ep[ep_addr & 0x7FU].is_stall;
}

USBD_StatusTypeDef USBD_LL_SetUSBAddress(USBD_HandleTypeDef* pdev, uint8_t dev_addr) {
    return (HAL_PCD_SetAddress((PCD_HandleTypeDef*)pdev->pData, dev_addr) == HAL_OK) ? USBD_OK : USBD_FAIL;
}

USBD_StatusTypeDef USBD_LL_Transmit(USBD_HandleTypeDef* pdev, uint8_t ep_addr, uint8_t* pbuf, uint32_t size) {
    return (HAL_PCD_EP_Transmit((PCD_HandleTypeDef*)pdev->pData, ep_addr, pbuf, size) == HAL_OK) ? USBD_OK : USBD_FAIL;
}

USBD_StatusTypeDef USBD_LL_PrepareReceive(USBD_HandleTypeDef* pdev, uint8_t ep_addr, uint8_t* pbuf, uint32_t size) {
    return (HAL_PCD_EP_Receive((PCD_HandleTypeDef*)pdev->pData, ep_addr, pbuf, size) == HAL_OK) ? USBD_OK : USBD_FAIL;
}

uint32_t USBD_LL_GetRxDataSize(USBD_HandleTypeDef* pdev, uint8_t ep_addr) {
    return HAL_PCD_EP_GetRxCount((PCD_HandleTypeDef*)pdev->pData, ep_addr);
}

void USBD_LL_Delay(uint32_t delay_ms) {
    HAL_Delay(delay_ms);
}

void OTG_FS_IRQHandler(void) {
    HAL_PCD_IRQHandler(&hpcd_USB_OTG_FS);
}
