from os.path import join

Import("env")


PROJECT_DIR = env.subst("$PROJECT_DIR")
FRAMEWORK_DIR = env.PioPlatform().get_package_dir("framework-stm32cubef4")

if not FRAMEWORK_DIR:
    raise RuntimeError("framework-stm32cubef4 package not found")


firmware_dir = join(PROJECT_DIR, "firmware")

env.Replace(
    LDSCRIPT_PATH=join(firmware_dir, "linker", "STM32F401xC_FLASH.ld"),
)

env.Append(
    CPPPATH=[
        join(firmware_dir, "Core", "Inc"),
        join(FRAMEWORK_DIR, "Drivers", "CMSIS", "Include"),
        join(FRAMEWORK_DIR, "Drivers", "CMSIS", "Device", "ST", "STM32F4xx", "Include"),
        join(FRAMEWORK_DIR, "Drivers", "STM32F4xx_HAL_Driver", "Inc"),
        join(FRAMEWORK_DIR, "Drivers", "STM32F4xx_HAL_Driver", "Inc", "Legacy"),
        join(FRAMEWORK_DIR, "Middlewares", "ST", "STM32_USB_Device_Library", "Core", "Inc"),
        join(FRAMEWORK_DIR, "Middlewares", "ST", "STM32_USB_Device_Library", "Class", "CDC", "Inc"),
    ],
    LINKFLAGS=[
        "-nostartfiles",
        "-Wl,--gc-sections",
    ],
)
