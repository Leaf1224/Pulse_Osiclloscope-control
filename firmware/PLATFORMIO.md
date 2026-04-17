# PlatformIO Usage

This firmware can now be built in two ways:

- `CMakeLists.txt` for manual/native build flows
- `platformio.ini` for VS Code PlatformIO build/upload/debug flows

## VS Code / PlatformIO

From the repository root:

```powershell
pio run
pio run -t upload
pio device monitor -b 115200
```

The PlatformIO environment:

- reuses the existing sources in `firmware/Core/Src`
- uses the existing linker script in `firmware/linker/STM32F401xC_FLASH.ld`
- reuses the installed `framework-stm32cubef4` package for HAL + USB CDC middleware
- excludes `platform_usb_cdc_template.c`

## Notes

- Board target: `genericSTM32F401CC`
- Upload protocol: `stlink`
- USB CDC pins remain `PA11/PA12`
