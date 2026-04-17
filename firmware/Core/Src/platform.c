#include "platform.h"

#include <errno.h>
#include <sys/types.h>

#include "stm32f4xx_hal.h"

#ifndef RCC_BASE
#define RCC_BASE           (AHB1PERIPH_BASE + 0x3800UL)
#endif
#ifndef SYSCFG_BASE
#define SYSCFG_BASE        (APB2PERIPH_BASE + 0x3800UL)
#endif
#ifndef GPIOA_BASE
#define GPIOA_BASE         (AHB1PERIPH_BASE + 0x0000UL)
#endif
#ifndef GPIOB_BASE
#define GPIOB_BASE         (AHB1PERIPH_BASE + 0x0400UL)
#endif
#ifndef GPIOC_BASE
#define GPIOC_BASE         (AHB1PERIPH_BASE + 0x0800UL)
#endif
#ifndef USART2_BASE
#define USART2_BASE        (APB1PERIPH_BASE + 0x4400UL)
#endif
#ifndef EXTI_BASE
#define EXTI_BASE          (APB2PERIPH_BASE + 0x3C00UL)
#endif

#define SYST_CSR           (*(volatile uint32_t*)0xE000E010UL)
#define SYST_RVR           (*(volatile uint32_t*)0xE000E014UL)
#define SYST_CVR           (*(volatile uint32_t*)0xE000E018UL)

typedef struct {
    volatile uint32_t MODER;
    volatile uint32_t OTYPER;
    volatile uint32_t OSPEEDR;
    volatile uint32_t PUPDR;
    volatile uint32_t IDR;
    volatile uint32_t ODR;
    volatile uint32_t BSRR;
    volatile uint32_t LCKR;
    volatile uint32_t AFR[2];
} gpio_regs_t;

typedef struct {
    volatile uint32_t CR;
    volatile uint32_t PLLCFGR;
    volatile uint32_t CFGR;
    volatile uint32_t CIR;
    volatile uint32_t AHB1RSTR;
    volatile uint32_t AHB2RSTR;
    volatile uint32_t AHB3RSTR;
    uint32_t RESERVED0;
    volatile uint32_t APB1RSTR;
    volatile uint32_t APB2RSTR;
    uint32_t RESERVED1[2];
    volatile uint32_t AHB1ENR;
    volatile uint32_t AHB2ENR;
    volatile uint32_t AHB3ENR;
    uint32_t RESERVED2;
    volatile uint32_t APB1ENR;
    volatile uint32_t APB2ENR;
} rcc_regs_t;

typedef struct {
    volatile uint32_t SR;
    volatile uint32_t DR;
    volatile uint32_t BRR;
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t CR3;
    volatile uint32_t GTPR;
} usart_regs_t;

typedef struct {
    volatile uint32_t MEMRMP;
    volatile uint32_t PMC;
    volatile uint32_t EXTICR[4];
} syscfg_regs_t;

typedef struct {
    volatile uint32_t IMR;
    volatile uint32_t EMR;
    volatile uint32_t RTSR;
    volatile uint32_t FTSR;
    volatile uint32_t SWIER;
    volatile uint32_t PR;
} exti_regs_t;

static volatile uint32_t g_ms_ticks = 0U;
static volatile uint32_t g_fg_sync_count = 0U;
static char g_rx_buf[128];
static size_t g_rx_len = 0U;
static platform_pin_t g_fg_sync_pin = { PLATFORM_PORT_INVALID, 0U, true, false };

uint32_t SystemCoreClock = 16000000U;
const uint8_t AHBPrescTable[16] = {0U, 0U, 0U, 0U, 1U, 2U, 3U, 4U, 6U, 7U, 8U, 9U, 0U, 0U, 0U, 0U};
const uint8_t APBPrescTable[8] = {0U, 0U, 0U, 0U, 1U, 2U, 3U, 4U};

static gpio_regs_t* const GPIOA_REGS = (gpio_regs_t*)GPIOA_BASE;
static gpio_regs_t* const GPIOB_REGS = (gpio_regs_t*)GPIOB_BASE;
static gpio_regs_t* const GPIOC_REGS = (gpio_regs_t*)GPIOC_BASE;
static rcc_regs_t* const RCC_REGS = (rcc_regs_t*)RCC_BASE;
static usart_regs_t* const USART2_REGS = (usart_regs_t*)USART2_BASE;
static syscfg_regs_t* const SYSCFG_REGS = (syscfg_regs_t*)SYSCFG_BASE;
static exti_regs_t* const EXTI_REGS = (exti_regs_t*)EXTI_BASE;

static volatile uint32_t* const NVIC_ISER1 = (volatile uint32_t*)0xE000E104UL;

static gpio_regs_t* gpio_from_port(platform_port_t port) {
    switch (port) {
        case PLATFORM_PORT_A: return GPIOA_REGS;
        case PLATFORM_PORT_B: return GPIOB_REGS;
        case PLATFORM_PORT_C: return GPIOC_REGS;
        default: return GPIOA_REGS;
    }
}

static uint32_t exti_port_code(platform_port_t port) {
    switch (port) {
        case PLATFORM_PORT_A: return 0U;
        case PLATFORM_PORT_B: return 1U;
        case PLATFORM_PORT_C: return 2U;
        default: return 0U;
    }
}

static void gpio_set_mode(gpio_regs_t* gpio, uint8_t pin, uint32_t mode) {
    uint32_t shift = (uint32_t)pin * 2U;
    gpio->MODER &= ~(0x3UL << shift);
    gpio->MODER |= ((mode & 0x3UL) << shift);
}

static void gpio_set_pull(gpio_regs_t* gpio, uint8_t pin, bool pull_up) {
    uint32_t shift = (uint32_t)pin * 2U;
    gpio->PUPDR &= ~(0x3UL << shift);
    gpio->PUPDR |= ((pull_up ? 0x1UL : 0x0UL) << shift);
}

static void gpio_set_af(gpio_regs_t* gpio, uint8_t pin, uint32_t af) {
    uint32_t idx = (pin >= 8U) ? 1U : 0U;
    uint32_t shift = ((uint32_t)pin % 8U) * 4U;
    gpio->AFR[idx] &= ~(0xFUL << shift);
    gpio->AFR[idx] |= ((af & 0xFUL) << shift);
}

static void uart2_init(void) {
    RCC_REGS->AHB1ENR |= (1UL << 0) | (1UL << 1);
    RCC_REGS->APB1ENR |= (1UL << 17);

    gpio_set_mode(GPIOA_REGS, 2U, 0x2UL);
    gpio_set_mode(GPIOA_REGS, 3U, 0x2UL);
    gpio_set_pull(GPIOA_REGS, 2U, true);
    gpio_set_pull(GPIOA_REGS, 3U, true);
    gpio_set_af(GPIOA_REGS, 2U, 7U);
    gpio_set_af(GPIOA_REGS, 3U, 7U);

    /*
     * SYSCLK = 84 MHz, APB1 = 42 MHz.
     * USARTDIV = 42,000,000 / (16 * 115200) = 22.786...
     * BRR = mantissa 22, fraction round(0.786 * 16) = 13 => 0x16D.
     */
    USART2_REGS->BRR = 0x16DU;
    USART2_REGS->CR1 = (1UL << 13) | (1UL << 3) | (1UL << 2);
}

static void systick_init(void) {
    SYST_RVR = (SystemCoreClock / 1000U) - 1U;
    SYST_CVR = 0U;
    SYST_CSR = 0x7U;
}

static void clock_init_84mhz_from_hse_25mhz(void) {
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    __HAL_RCC_PWR_CLK_ENABLE();

    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLM = 25U;
    osc.PLL.PLLN = 336U;
    osc.PLL.PLLP = RCC_PLLP_DIV4;
    osc.PLL.PLLQ = 7U;

    if (HAL_RCC_OscConfig(&osc) != HAL_OK) {
        while (1) {
        }
    }

    clk.ClockType = RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV2;
    clk.APB2CLKDivider = RCC_HCLK_DIV1;

    if (HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_2) != HAL_OK) {
        while (1) {
        }
    }
}

void SysTick_Handler(void) {
    g_ms_ticks += 1U;
    HAL_IncTick();
}

void NMI_Handler(void) {
    while (1) {
    }
}

void HardFault_Handler(void) {
    while (1) {
    }
}

void MemManage_Handler(void) {
    while (1) {
    }
}

void BusFault_Handler(void) {
    while (1) {
    }
}

void UsageFault_Handler(void) {
    while (1) {
    }
}

void SVC_Handler(void) {
}

void DebugMon_Handler(void) {
}

void PendSV_Handler(void) {
}

void Default_Handler(void) {
    while (1) {
    }
}

uint32_t HAL_GetTick(void) {
    return g_ms_ticks;
}

void HAL_Delay(uint32_t delay_ms) {
    uint32_t start = HAL_GetTick();
    while ((HAL_GetTick() - start) < delay_ms) {
    }
}

caddr_t _sbrk(int incr) {
    (void)incr;
    errno = ENOMEM;
    return (caddr_t)-1;
}

void EXTI15_10_IRQHandler(void) {
    uint32_t mask;

    if (g_fg_sync_pin.port == PLATFORM_PORT_INVALID) {
        return;
    }

    mask = (1UL << g_fg_sync_pin.pin);
    if ((EXTI_REGS->PR & mask) != 0U) {
        EXTI_REGS->PR = mask;
        g_fg_sync_count += 1U;
    }
}

void platform_init(void) {
    HAL_Init();
    clock_init_84mhz_from_hse_25mhz();

    RCC_REGS->AHB1ENR |= (1UL << 0) | (1UL << 1) | (1UL << 2);
    RCC_REGS->APB2ENR |= (1UL << 14);

    systick_init();
    uart2_init();
}

uint32_t platform_now_ms(void) {
    return g_ms_ticks;
}

void platform_gpio_make_output(const platform_pin_t* pin) {
    gpio_regs_t* gpio;
    if (pin == 0 || pin->port == PLATFORM_PORT_INVALID) {
        return;
    }
    gpio = gpio_from_port(pin->port);
    gpio_set_mode(gpio, pin->pin, 0x1UL);
    gpio_set_pull(gpio, pin->pin, false);
    platform_gpio_write(pin, false);
}

void platform_gpio_make_input(const platform_pin_t* pin) {
    gpio_regs_t* gpio;
    if (pin == 0 || pin->port == PLATFORM_PORT_INVALID) {
        return;
    }
    gpio = gpio_from_port(pin->port);
    gpio_set_mode(gpio, pin->pin, 0x0UL);
    gpio_set_pull(gpio, pin->pin, pin->pull_up);
}

void platform_gpio_write(const platform_pin_t* pin, bool asserted) {
    gpio_regs_t* gpio;
    bool level;
    if (pin == 0 || pin->port == PLATFORM_PORT_INVALID) {
        return;
    }
    gpio = gpio_from_port(pin->port);
    level = pin->active_high ? asserted : !asserted;
    if (level) {
        gpio->BSRR = (1UL << pin->pin);
    } else {
        gpio->BSRR = (1UL << (pin->pin + 16U));
    }
}

bool platform_gpio_read(const platform_pin_t* pin) {
    gpio_regs_t* gpio;
    bool level;
    if (pin == 0 || pin->port == PLATFORM_PORT_INVALID) {
        return false;
    }
    gpio = gpio_from_port(pin->port);
    level = ((gpio->IDR >> pin->pin) & 0x1UL) != 0U;
    return pin->active_high ? level : !level;
}

void platform_pulse_counter_init(const platform_pin_t* pin) {
    uint32_t idx;
    uint32_t shift;

    if (pin == 0 || pin->port == PLATFORM_PORT_INVALID || pin->pin > 15U) {
        return;
    }

    g_fg_sync_pin = *pin;
    g_fg_sync_count = 0U;

    idx = pin->pin / 4U;
    shift = (pin->pin % 4U) * 4U;
    SYSCFG_REGS->EXTICR[idx] &= ~(0xFUL << shift);
    SYSCFG_REGS->EXTICR[idx] |= (exti_port_code(pin->port) << shift);

    EXTI_REGS->IMR |= (1UL << pin->pin);
    EXTI_REGS->FTSR &= ~(1UL << pin->pin);
    EXTI_REGS->RTSR |= (1UL << pin->pin);
    EXTI_REGS->PR = (1UL << pin->pin);

    *NVIC_ISER1 |= (1UL << (40U - 32U));
}

uint32_t platform_pulse_counter_get(void) {
    return g_fg_sync_count;
}

void platform_pulse_counter_reset(void) {
    g_fg_sync_count = 0U;
}

static void uart2_write_char(char c) {
    while ((USART2_REGS->SR & (1UL << 7)) == 0U) {
    }
    USART2_REGS->DR = (uint32_t)c;
}

void platform_uart_write_str(const char* s) {
    if (s == 0) {
        return;
    }
    while (*s != '\0') {
        if (*s == '\n') {
            uart2_write_char('\r');
        }
        uart2_write_char(*s++);
    }
}

void platform_uart_write_line(const char* s) {
    platform_uart_write_str(s);
    platform_uart_write_str("\n");
}

bool platform_uart_read_line(char* out, size_t out_size) {
    char ch;
    if (out == 0 || out_size < 2U) {
        return false;
    }

    while ((USART2_REGS->SR & (1UL << 5)) != 0U) {
        ch = (char)(USART2_REGS->DR & 0xFFU);
        if (ch == '\r') {
            continue;
        }
        if (ch == '\n') {
            g_rx_buf[g_rx_len] = '\0';
            if (g_rx_len >= out_size) {
                g_rx_len = 0U;
                return false;
            }
            for (size_t i = 0; i <= g_rx_len; ++i) {
                out[i] = g_rx_buf[i];
            }
            g_rx_len = 0U;
            return true;
        }
        if (g_rx_len + 1U < sizeof(g_rx_buf)) {
            g_rx_buf[g_rx_len++] = ch;
        } else {
            g_rx_len = 0U;
        }
    }

    return false;
}
