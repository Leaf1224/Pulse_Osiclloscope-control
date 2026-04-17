/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
#include "stm32f4xx_hal.h"
#include <string.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdbool.h>

/* ======== UART & RX line buffer ======== */
UART_HandleTypeDef huart2;           // USART2 on PA2/PA3
#define RX_BUF_SZ 128
static uint8_t rx_byte;
static char linebuf[RX_BUF_SZ];
static volatile uint32_t line_len = 0;

/* ======== Prototypes ======== */
static void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART2_UART_Init(void);

/* ======== Small helpers ======== */
static void uart_print(const char* s){
    HAL_UART_Transmit(&huart2, (uint8_t*)s, strlen(s), HAL_MAX_DELAY);
}
static void uart_printf(const char* fmt, ...){
    char buf[128];
    va_list args; va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    uart_print(buf);
}
static GPIO_TypeDef* port_from_char(char c){
    switch(c){
        case 'A': return GPIOA;
        case 'B': return GPIOB;
        case 'C': return GPIOC;
        case 'D': return GPIOD;
        case 'E': return GPIOE;
        case 'H': return GPIOH;
        default:  return NULL;
    }
}
static void enable_gpio_clock(GPIO_TypeDef* port){
    if (port == GPIOA) __HAL_RCC_GPIOA_CLK_ENABLE();
    else if (port == GPIOB) __HAL_RCC_GPIOB_CLK_ENABLE();
    else if (port == GPIOC) __HAL_RCC_GPIOC_CLK_ENABLE();
    else if (port == GPIOD) __HAL_RCC_GPIOD_CLK_ENABLE();
    else if (port == GPIOE) __HAL_RCC_GPIOE_CLK_ENABLE();
    else if (port == GPIOH) __HAL_RCC_GPIOH_CLK_ENABLE();
}
static uint16_t pin_from_num(int num){
    if (num < 0 || num > 15) return 0;
    return (uint16_t)(1U << num);
}

/* ======== Command parser ========
 * CSV commands over UART (115200 8N1):
 *   MODE,<PORT>,<PIN>,<IN|OUT|AN|PU|PD>
 *   WRITE,<PORT>,<PIN>,<0|1>
 *   READ,<PORT>,<PIN>
 * Replies:
 *   OK,MODE / OK,WRITE / VALUE,<PORT>,<PIN>,<0|1> / ERR,xxxx
 */
static void handle_line(const char* line){
    char mode[4]={0}, portc=0;
    int pinnum=0, value=0;

    if (sscanf(line, "MODE,%c,%d,%3s", &portc, &pinnum, mode) == 3){
        GPIO_TypeDef* port = port_from_char(portc);
        if (!port){ uart_print("ERR,BADPORT\r\n"); return; }
        uint16_t pin = pin_from_num(pinnum);
        if (!pin){ uart_print("ERR,BADPIN\r\n"); return; }
        enable_gpio_clock(port);

        GPIO_InitTypeDef gi = {0};
        gi.Pin = pin;
        if (!strcmp(mode,"IN")) { gi.Mode = GPIO_MODE_INPUT;      gi.Pull = GPIO_NOPULL; }
        else if (!strcmp(mode,"PU")){ gi.Mode = GPIO_MODE_INPUT;  gi.Pull = GPIO_PULLUP; }
        else if (!strcmp(mode,"PD")){ gi.Mode = GPIO_MODE_INPUT;  gi.Pull = GPIO_PULLDOWN; }
        else if (!strcmp(mode,"OUT")){gi.Mode = GPIO_MODE_OUTPUT_PP; gi.Pull = GPIO_NOPULL; gi.Speed = GPIO_SPEED_FREQ_LOW; }
        else if (!strcmp(mode,"AN")) { gi.Mode = GPIO_MODE_ANALOG; gi.Pull = GPIO_NOPULL; }
        else { uart_print("ERR,BADMODE\r\n"); return; }

        HAL_GPIO_Init(port, &gi);
        uart_print("OK,MODE\r\n");
        return;
    }

    if (sscanf(line, "WRITE,%c,%d,%d", &portc, &pinnum, &value) == 3){
        GPIO_TypeDef* port = port_from_char(portc);
        if (!port){ uart_print("ERR,BADPORT\r\n"); return; }
        uint16_t pin = pin_from_num(pinnum);
        if (!pin){ uart_print("ERR,BADPIN\r\n"); return; }
        HAL_GPIO_WritePin(port, pin, value ? GPIO_PIN_SET : GPIO_PIN_RESET);
        uart_print("OK,WRITE\r\n");
        return;
    }

    if (sscanf(line, "READ,%c,%d", &portc, &pinnum) == 2){
        GPIO_TypeDef* port = port_from_char(portc);
        if (!port){ uart_print("ERR,BADPORT\r\n"); return; }
        uint16_t pin = pin_from_num(pinnum);
        if (!pin){ uart_print("ERR,BADPIN\r\n"); return; }
        GPIO_PinState st = HAL_GPIO_ReadPin(port, pin);
        uart_printf("VALUE,%c,%d,%d\r\n", portc, pinnum, (st==GPIO_PIN_SET)?1:0);
        return;
    }

    uart_print("ERR,BADCMD\r\n");
}

/* ======== Main ======== */
int main(void){
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART2_UART_Init();

    uart_print("READY\r\n");
    HAL_UART_Receive_IT(&huart2, &rx_byte, 1);   // start RX interrupt
    //uint32_t t0 = HAL_GetTick();
    while (1){
        /*f (HAL_GetTick() - t0 >= 500) {
            t0 += 500;
            uart_print("PING\r\n");
        }*/
        // main loop can be empty; everything via UART IRQ
    }
}

/* ======== UART RX IRQ callback: line collector ======== */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart){
    if (huart->Instance == USART2){
        if (rx_byte == '\n' || rx_byte == '\r'){
            if (line_len > 0){
                linebuf[line_len] = 0;
                handle_line(linebuf);
                line_len = 0;
            }
        } else {
            if (line_len < RX_BUF_SZ - 1){
                linebuf[line_len++] = (char)rx_byte;
            } else {
                line_len = 0; // overflow protect
                uart_print("ERR,TOOLONG\r\n");
            }
        }
        HAL_UART_Receive_IT(&huart2, &rx_byte, 1);
    }
}

/* ======== Peripherals init ======== */
static void MX_USART2_UART_Init(void){
    __HAL_RCC_USART2_CLK_ENABLE();

    // GPIO for USART2: PA2=TX, PA3=RX (AF7)
    __HAL_RCC_GPIOA_CLK_ENABLE();
    GPIO_InitTypeDef gi = {0};
    gi.Pin = GPIO_PIN_2 | GPIO_PIN_3;
    gi.Mode = GPIO_MODE_AF_PP;
    gi.Pull = GPIO_PULLUP;
    gi.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gi.Alternate = GPIO_AF7_USART2;
    HAL_GPIO_Init(GPIOA, &gi);

    huart2.Instance = USART2;
    huart2.Init.BaudRate = 115200;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    if (HAL_UART_Init(&huart2) != HAL_OK){ while(1){} }
    /* ★ 強制開 USART2 的 IRQ（就算 MSP 沒設也無妨） */
    HAL_NVIC_SetPriority(USART2_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(USART2_IRQn);
}

static void MX_GPIO_Init(void){
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_GPIOE_CLK_ENABLE();
    __HAL_RCC_GPIOH_CLK_ENABLE();

    // Example default: PC13 as output (common LED)
    GPIO_InitTypeDef gi = {0};
    gi.Pin = GPIO_PIN_13;
    gi.Mode = GPIO_MODE_OUTPUT_PP;
    gi.Pull = GPIO_NOPULL;
    gi.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOC, &gi);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET); // LED OFF (typical low-active)
}

/* ======== Clock config: HSE=25MHz -> PLL 84MHz ======== */
static void SystemClock_Config(void){
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE2);

    // HSE ON (25 MHz). If your HSE is fed by MCO, use RCC_HSE_BYPASS instead.
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState       = RCC_HSE_ON;
    RCC_OscInitStruct.PLL.PLLState   = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource  = RCC_PLLSOURCE_HSE;

    // PLL: (25 / 25) * 168 / 2 = 84 MHz
    RCC_OscInitStruct.PLL.PLLM = 25;
    RCC_OscInitStruct.PLL.PLLN = 168;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
    RCC_OscInitStruct.PLL.PLLQ = 4;   // not used for USB here
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK){ while(1){} }

    RCC_ClkInitStruct.ClockType      = RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK |
                                       RCC_CLOCKTYPE_PCLK1  | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource   = RCC_SYSCLKSOURCE_PLLCLK;  // SYSCLK = 84 MHz
    RCC_ClkInitStruct.AHBCLKDivider  = RCC_SYSCLK_DIV1;          // HCLK  = 84 MHz
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;            // PCLK1 = 42 MHz
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;            // PCLK2 = 84 MHz

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK){ while(1){} }
}

/* ======== HAL basics ======== */

void Error_Handler(void){ __disable_irq(); while(1){} }


