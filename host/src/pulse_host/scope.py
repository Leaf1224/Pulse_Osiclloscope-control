from __future__ import annotations

import socket
from dataclasses import dataclass
from pathlib import Path


def _open_visa_resource_manager(pyvisa_module):
    """Try system VISA first, then fall back to pyvisa-py backend."""
    errors: list[str] = []
    try:
        return pyvisa_module.ResourceManager()
    except Exception as exc:
        errors.append(f"system backend: {exc}")

    try:
        return pyvisa_module.ResourceManager("@py")
    except Exception as exc:
        errors.append(f"pyvisa-py backend: {exc}")
        detail = " | ".join(errors)
        raise RuntimeError(
            "無法初始化 VISA backend，請確認已安裝 NI-VISA 或 Keysight IO Libraries，"
            "以及 pyvisa-py / pyusb / libusb-package。"
            f" 詳細錯誤: {detail}"
        ) from exc


def _read_exact(read_chunk, length: int) -> bytes:
    data = bytearray()
    while len(data) < length:
        chunk = read_chunk(length - len(data))
        if not chunk:
            raise RuntimeError("Unexpected EOF while reading binary block data.")
        data.extend(chunk)
    return bytes(data)


def _read_ieee4882_block(read_chunk) -> bytes:
    first = read_chunk(1)
    if not first:
        raise RuntimeError("No response data from scope.")
    if first != b"#":
        prefix = first + read_chunk(64)
        raise RuntimeError(f"Unexpected binary block prefix: {prefix!r}")

    digits_raw = read_chunk(1)
    if not digits_raw:
        raise RuntimeError("Incomplete IEEE-488.2 block header.")
    digits = int(digits_raw.decode("ascii"))
    if digits <= 0:
        raise RuntimeError("Unsupported IEEE-488.2 block length header.")

    length_raw = _read_exact(read_chunk, digits)
    length = int(length_raw.decode("ascii"))
    payload = _read_exact(read_chunk, length)

    trailer = read_chunk(1)
    if trailer == b"\r":
        read_chunk(1)
    return payload


@dataclass
class ScopeConfig:
    mode: str = "lan"
    host: str = "192.168.0.100"
    port: int = 5025
    timeout_s: float = 2.0
    resource: str = ""


class ScopeClient:
    def close(self) -> None:
        raise NotImplementedError

    def write(self, command: str) -> None:
        raise NotImplementedError

    def query(self, command: str) -> str:
        raise NotImplementedError

    def identify(self) -> str:
        return self.query("*IDN?")

    def stop(self) -> None:
        self.write(":STOP")

    def run(self) -> None:
        self.write(":RUN")

    def single(self) -> None:
        self.write(":SINGLE")

    def clear(self) -> None:
        self.write(":CDISPLAY")

    def autoscale(self) -> None:
        self.write(":AUTOSCALE")

    def set_edge_trigger(self, source: str = "CHAN4", level_v: float = 1.0) -> None:
        self.write(f":TRIGGER:EDGE:SOURCE {source}")
        self.write(":TRIGGER:EDGE:SLOPE POSITIVE")
        self.write(f":TRIGGER:LEVEL {level_v}")

    def set_trigger_sweep(self, mode: str = "NORMAL") -> None:
        sweep = mode.strip().upper()
        if sweep not in {"AUTO", "NORMAL"}:
            raise ValueError(f"Unsupported trigger sweep: {mode}")
        scope_value = "AUTO" if sweep == "AUTO" else "NORM"
        self.write(f":TRIGGER:SWEEP {scope_value}")

    def set_timebase(self, scale_s: float) -> None:
        self.write(f":TIMEBASE:SCALE {scale_s}")

    def set_channel_display(self, channel: int, enabled: bool) -> None:
        state = "ON" if enabled else "OFF"
        self.write(f":CHANNEL{channel}:DISPLAY {state}")

    def capture_screen_png(self) -> bytes:
        raise NotImplementedError

    def get_timeout_s(self) -> float:
        raise NotImplementedError

    def set_timeout_s(self, timeout_s: float) -> None:
        raise NotImplementedError

    def save_screenshot(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.capture_screen_png())
        return target


class LanScopeClient(ScopeClient):
    def __init__(self, config: ScopeConfig) -> None:
        self._sock = socket.create_connection((config.host, config.port), timeout=config.timeout_s)
        self._sock.settimeout(config.timeout_s)

    def close(self) -> None:
        self._sock.close()

    def write(self, command: str) -> None:
        self._sock.sendall((command + "\n").encode("ascii"))

    def get_timeout_s(self) -> float:
        timeout = self._sock.gettimeout()
        return float(timeout if timeout is not None else 0.0)

    def set_timeout_s(self, timeout_s: float) -> None:
        self._sock.settimeout(timeout_s)

    def query(self, command: str) -> str:
        self.write(command)
        return self._recv_line()

    def _recv_line(self) -> str:
        chunks = bytearray()
        while True:
            data = self._sock.recv(1)
            if not data:
                break
            if data == b"\n":
                break
            chunks.extend(data)
        return chunks.decode("ascii", errors="replace").strip()

    def capture_screen_png(self) -> bytes:
        self.write(":HARDcopy:INKSaver OFF")
        self.write(":DISPlay:DATA? PNG,COLor")
        return _read_ieee4882_block(self._sock.recv)


class VisaScopeClient(ScopeClient):
    def __init__(self, config: ScopeConfig) -> None:
        try:
            import pyvisa
        except ImportError as exc:
            raise RuntimeError("USB/VISA 模式需要先安裝 pyvisa。") from exc

        resource_name = config.resource.strip()
        if not resource_name:
            raise RuntimeError("USB/VISA 模式需要提供 VISA resource，例如 USB0::...::INSTR")

        self._rm = _open_visa_resource_manager(pyvisa)
        self._inst = self._rm.open_resource(resource_name)
        self._inst.timeout = int(config.timeout_s * 1000)
        self._inst.write_termination = "\n"
        self._inst.read_termination = "\n"

    def close(self) -> None:
        self._inst.close()
        self._rm.close()

    def write(self, command: str) -> None:
        self._inst.write(command)

    def get_timeout_s(self) -> float:
        return float(self._inst.timeout) / 1000.0

    def set_timeout_s(self, timeout_s: float) -> None:
        self._inst.timeout = int(timeout_s * 1000)

    def query(self, command: str) -> str:
        return str(self._inst.query(command)).strip()

    def capture_screen_png(self) -> bytes:
        self.write(":HARDcopy:INKSaver OFF")
        self._inst.write(":DISPlay:DATA? PNG,COLor")
        return _read_ieee4882_block(self._inst.read_bytes)


def _resource_priority(resource: str) -> tuple[int, str]:
    upper = resource.upper()
    if upper.startswith("USB"):
        return (0, upper)
    if upper.startswith("TCPIP"):
        return (1, upper)
    if upper.startswith("GPIB"):
        return (2, upper)
    if upper.startswith("ASRL"):
        return (9, upper)
    return (5, upper)


def list_visa_resources(include_serial: bool = True) -> list[str]:
    try:
        import pyvisa
    except ImportError as exc:
        raise RuntimeError("列出 USB/VISA 裝置前請先安裝 pyvisa。") from exc

    rm = _open_visa_resource_manager(pyvisa)
    try:
        resources = sorted(list(rm.list_resources()), key=_resource_priority)
        if include_serial:
            return resources
        return [resource for resource in resources if not resource.upper().startswith("ASRL")]
    finally:
        rm.close()


def create_scope_client(config: ScopeConfig) -> ScopeClient:
    mode = config.mode.strip().lower()
    if mode == "lan":
        return LanScopeClient(config)
    if mode == "usb":
        return VisaScopeClient(config)
    raise ValueError(f"Unknown scope mode: {config.mode}")
