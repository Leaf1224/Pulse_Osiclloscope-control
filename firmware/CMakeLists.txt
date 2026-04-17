cmake_minimum_required(VERSION 3.20)

project(v1_pulse_platform_f401 C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_program(CMAKE_OBJCOPY arm-none-eabi-objcopy)

set(STM32CUBE_F4_ROOT "" CACHE PATH "Path to STM32Cube FW F4 package root")

if(NOT STM32CUBE_F4_ROOT)
    set(_cube_default "$ENV{USERPROFILE}/STM32Cube/Repository/STM32Cube_FW_F4_V1.28.3")
    set(_pio_default "$ENV{USERPROFILE}/.platformio/packages/framework-stm32cubef4")
    if(EXISTS "${_cube_default}")
        set(STM32CUBE_F4_ROOT "${_cube_default}")
    elseif(EXISTS "${_pio_default}")
        set(STM32CUBE_F4_ROOT "${_pio_default}")
    endif()
endif()

set(USB_CDC_SOURCES)
set(USB_CDC_INCLUDE_DIRS)

if(STM32CUBE_F4_ROOT AND EXISTS "${STM32CUBE_F4_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Core/Src/usbd_core.c")
    set(USB_CDC_SOURCES
        Core/Src/platform_usb_cdc.c
        Core/Src/usbd_conf.c
        Core/Src/usbd_desc.c
        ${STM32CUBE_F4_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal.c
        ${STM32CUBE_F4_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_cortex.c
        ${STM32CUBE_F4_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_gpio.c
        ${STM32CUBE_F4_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pcd.c
        ${STM32CUBE_F4_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pcd_ex.c
        ${STM32CUBE_F4_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pwr.c
        ${STM32CUBE_F4_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc.c
        ${STM32CUBE_F4_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc_ex.c
        ${STM32CUBE_F4_ROOT}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_usb.c
        ${STM32CUBE_F4_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Core/Src/usbd_core.c
        ${STM32CUBE_F4_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Core/Src/usbd_ctlreq.c
        ${STM32CUBE_F4_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Core/Src/usbd_ioreq.c
        ${STM32CUBE_F4_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Class/CDC/Src/usbd_cdc.c
    )

    set(USB_CDC_INCLUDE_DIRS
        ${STM32CUBE_F4_ROOT}/Drivers/CMSIS/Include
        ${STM32CUBE_F4_ROOT}/Drivers/CMSIS/Device/ST/STM32F4xx/Include
        ${STM32CUBE_F4_ROOT}/Drivers/STM32F4xx_HAL_Driver/Inc
        ${STM32CUBE_F4_ROOT}/Drivers/STM32F4xx_HAL_Driver/Inc/Legacy
        ${STM32CUBE_F4_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Core/Inc
        ${STM32CUBE_F4_ROOT}/Middlewares/ST/STM32_USB_Device_Library/Class/CDC/Inc
    )
endif()

add_executable(${PROJECT_NAME}
    startup/startup_stm32f401xc.s
    Core/Src/main.c
    Core/Src/platform.c
    Core/Src/platform_comm.c
    Core/Src/board_config.c
    Core/Src/app_comm.c
    Core/Src/app_config.c
    Core/Src/app_counter.c
    Core/Src/app_fault.c
    Core/Src/app_io.c
    Core/Src/app_log.c
    Core/Src/app_state.c
    ${USB_CDC_SOURCES}
)

if(USB_CDC_SOURCES)
    target_compile_definitions(${PROJECT_NAME} PRIVATE USE_USB_FS)
    set_source_files_properties(${USB_CDC_SOURCES} PROPERTIES COMPILE_OPTIONS "-Wno-error;-Wno-sign-compare")
    message(STATUS "USB CDC enabled using STM32Cube F4 from: ${STM32CUBE_F4_ROOT}")
else()
    message(WARNING "STM32Cube F4 USB sources not found; building UART-only fallback")
endif()

target_include_directories(${PROJECT_NAME} PRIVATE
    Core/Inc
    ${USB_CDC_INCLUDE_DIRS}
)

target_compile_options(${PROJECT_NAME} PRIVATE
    -mcpu=cortex-m4
    -mthumb
    -ffreestanding
    -fdata-sections
    -ffunction-sections
    -Wall
    -Wextra
    -Werror
)

target_compile_definitions(${PROJECT_NAME} PRIVATE STM32F401xC)

target_link_options(${PROJECT_NAME} PRIVATE
    -T${CMAKE_CURRENT_SOURCE_DIR}/linker/STM32F401xC_FLASH.ld
    -mcpu=cortex-m4
    -mthumb
    -nostartfiles
    -Wl,--gc-sections
    -Wl,-Map=${PROJECT_NAME}.map
)

set_target_properties(${PROJECT_NAME} PROPERTIES SUFFIX ".elf")

if(CMAKE_OBJCOPY)
    add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
        COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:${PROJECT_NAME}> ${PROJECT_NAME}.bin
        COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:${PROJECT_NAME}> ${PROJECT_NAME}.hex
        BYPRODUCTS ${PROJECT_NAME}.bin ${PROJECT_NAME}.hex
        COMMENT "Generating binary and Intel HEX images"
    )
else()
    message(WARNING "arm-none-eabi-objcopy not found; only ELF will be generated")
endif()
