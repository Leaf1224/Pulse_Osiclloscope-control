from os.path import join

Import("env")


BUILD_DIR = env.subst("$BUILD_DIR")
FRAMEWORK_DIR = env.PioPlatform().get_package_dir("framework-stm32cubef4")

if not FRAMEWORK_DIR:
    raise RuntimeError("framework-stm32cubef4 package not found")


external_env = env.Clone()
external_env.ProcessUnFlags(["-Werror"])
external_env.Append(CCFLAGS=["-Wno-error", "-Wno-sign-compare"])


def build_external_library(target_name, source_dir, source_filter):
    lib_dir = join(BUILD_DIR, target_name)
    lib = external_env.BuildLibrary(lib_dir, source_dir, src_filter=source_filter)
    env.Prepend(LIBS=[lib])


build_external_library(
    "stm32cube_hal",
    join(FRAMEWORK_DIR, "Drivers", "STM32F4xx_HAL_Driver", "Src"),
    "\n".join(
        [
            "+<stm32f4xx_hal.c>",
            "+<stm32f4xx_hal_cortex.c>",
            "+<stm32f4xx_hal_flash.c>",
            "+<stm32f4xx_hal_flash_ex.c>",
            "+<stm32f4xx_hal_gpio.c>",
            "+<stm32f4xx_hal_pcd.c>",
            "+<stm32f4xx_hal_pcd_ex.c>",
            "+<stm32f4xx_hal_pwr.c>",
            "+<stm32f4xx_hal_rcc.c>",
            "+<stm32f4xx_hal_rcc_ex.c>",
            "+<stm32f4xx_ll_usb.c>",
        ]
    ),
)

build_external_library(
    "stm32cube_usb_core",
    join(FRAMEWORK_DIR, "Middlewares", "ST", "STM32_USB_Device_Library", "Core", "Src"),
    "\n".join(
        [
            "+<usbd_core.c>",
            "+<usbd_ctlreq.c>",
            "+<usbd_ioreq.c>",
        ]
    ),
)

build_external_library(
    "stm32cube_usb_cdc",
    join(FRAMEWORK_DIR, "Middlewares", "ST", "STM32_USB_Device_Library", "Class", "CDC", "Src"),
    "+<usbd_cdc.c>",
)
