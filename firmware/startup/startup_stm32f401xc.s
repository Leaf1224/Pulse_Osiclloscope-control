.syntax unified
.cpu cortex-m4
.thumb

.global g_pfnVectors
.global Reset_Handler

.extern _estack
.extern _sidata
.extern _sdata
.extern _edata
.extern _sbss
.extern _ebss
.extern main
.extern Default_Handler
.extern NMI_Handler
.extern HardFault_Handler
.extern MemManage_Handler
.extern BusFault_Handler
.extern UsageFault_Handler
.extern SVC_Handler
.extern DebugMon_Handler
.extern PendSV_Handler
.extern SysTick_Handler
.extern EXTI15_10_IRQHandler
.extern OTG_FS_IRQHandler

.section .text.Reset_Handler
.weak Reset_Handler
.type Reset_Handler, %function
Reset_Handler:
    ldr r0, =_sdata
    ldr r1, =_edata
    ldr r2, =_sidata
1:
    cmp r0, r1
    ittt lt
    ldrlt r3, [r2], #4
    strlt r3, [r0], #4
    blt 1b

    ldr r0, =_sbss
    ldr r1, =_ebss
    movs r2, #0
2:
    cmp r0, r1
    itt lt
    strlt r2, [r0], #4
    blt 2b

    bl main

3:
    b 3b

.size Reset_Handler, .-Reset_Handler

.section .isr_vector, "a", %progbits
.type g_pfnVectors, %object
g_pfnVectors:
    .word _estack
    .word Reset_Handler
    .word NMI_Handler
    .word HardFault_Handler
    .word MemManage_Handler
    .word BusFault_Handler
    .word UsageFault_Handler
    .word 0
    .word 0
    .word 0
    .word 0
    .word SVC_Handler
    .word DebugMon_Handler
    .word 0
    .word PendSV_Handler
    .word SysTick_Handler

    /* External Interrupts */
    .word Default_Handler            /* WWDG                   */
    .word Default_Handler            /* PVD                    */
    .word Default_Handler            /* TAMP_STAMP             */
    .word Default_Handler            /* RTC_WKUP               */
    .word Default_Handler            /* FLASH                  */
    .word Default_Handler            /* RCC                    */
    .word Default_Handler            /* EXTI0                  */
    .word Default_Handler            /* EXTI1                  */
    .word Default_Handler            /* EXTI2                  */
    .word Default_Handler            /* EXTI3                  */
    .word Default_Handler            /* EXTI4                  */
    .word Default_Handler            /* DMA1_Stream0           */
    .word Default_Handler            /* DMA1_Stream1           */
    .word Default_Handler            /* DMA1_Stream2           */
    .word Default_Handler            /* DMA1_Stream3           */
    .word Default_Handler            /* DMA1_Stream4           */
    .word Default_Handler            /* DMA1_Stream5           */
    .word Default_Handler            /* DMA1_Stream6           */
    .word Default_Handler            /* ADC                    */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word Default_Handler            /* EXTI9_5                */
    .word Default_Handler            /* TIM1_BRK_TIM9          */
    .word Default_Handler            /* TIM1_UP_TIM10          */
    .word Default_Handler            /* TIM1_TRG_COM_TIM11     */
    .word Default_Handler            /* TIM1_CC                */
    .word Default_Handler            /* TIM2                   */
    .word Default_Handler            /* TIM3                   */
    .word Default_Handler            /* TIM4                   */
    .word Default_Handler            /* I2C1_EV                */
    .word Default_Handler            /* I2C1_ER                */
    .word Default_Handler            /* I2C2_EV                */
    .word Default_Handler            /* I2C2_ER                */
    .word Default_Handler            /* SPI1                   */
    .word Default_Handler            /* SPI2                   */
    .word Default_Handler            /* USART1                 */
    .word Default_Handler            /* USART2                 */
    .word 0                          /* Reserved               */
    .word EXTI15_10_IRQHandler       /* EXTI15_10              */
    .word Default_Handler            /* RTC_Alarm              */
    .word Default_Handler            /* OTG_FS_WKUP            */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word Default_Handler            /* DMA1_Stream7           */
    .word 0                          /* Reserved               */
    .word Default_Handler            /* SDIO                   */
    .word Default_Handler            /* TIM5                   */
    .word Default_Handler            /* SPI3                   */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word Default_Handler            /* DMA2_Stream0           */
    .word Default_Handler            /* DMA2_Stream1           */
    .word Default_Handler            /* DMA2_Stream2           */
    .word Default_Handler            /* DMA2_Stream3           */
    .word Default_Handler            /* DMA2_Stream4           */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word OTG_FS_IRQHandler          /* OTG_FS                 */
    .word Default_Handler            /* DMA2_Stream5           */
    .word Default_Handler            /* DMA2_Stream6           */
    .word Default_Handler            /* DMA2_Stream7           */
    .word Default_Handler            /* USART6                 */
    .word Default_Handler            /* I2C3_EV                */
    .word Default_Handler            /* I2C3_ER                */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word Default_Handler            /* FPU                    */
    .word 0                          /* Reserved               */
    .word 0                          /* Reserved               */
    .word Default_Handler            /* SPI4                   */
.size g_pfnVectors, .-g_pfnVectors
