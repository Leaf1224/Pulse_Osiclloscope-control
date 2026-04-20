from __future__ import annotations

import socket
from dataclasses import dataclass


def _open_visa_resource_manager(pyvisa_module):
    errors: list[str] = []
    try:
        return pyvisa_module.ResourceManager()
    except Exception as exc:
        errors.append(f"system backend: {exc}")

    try:
        return pyvisa_module.ResourceManager("@py")
    except Exception as exc:
        errors.append(f"py backend: {exc}")
        detail = " | ".join(errors)
        raise RuntimeError(
            "無法開啟 VISA backend，請確認已安裝 Keysight IO Libraries / NI-VISA，"
            "或安裝 pyvisa-py。"
            f" 詳細錯誤: {detail}"
        ) from exc


@dataclass
class Generator33250AConfig:
    mode: str = "tcp"
    resource: str = ""
    port: str = ""
    host: str = "192.168.3.3"
    tcp_port: int = 5000
    baudrate: int = 9600
    handshake: str = "none"
    timeout_s: float = 2.0


class Generator33250AClient:
    def close(self) -> None:
        raise NotImplementedError

    def write(self, command: str) -> None:
        raise NotImplementedError

    def query(self, command: str) -> str:
        raise NotImplementedError

    def identify(self) -> str:
        return self.query("*IDN?")

    def set_remote(self) -> None:
        # 33250A supports remote lock via SYST:RWLock when needed.
        self.write("SYST:RWLock")

    def set_local(self) -> None:
        self.write("SYST:LOCal")

    def output_on(self) -> None:
        self.write("OUTP ON")

    def output_off(self) -> None:
        self.write("OUTP OFF")

    def set_function(self, function_name: str) -> None:
        self.write(f"FUNC {function_name}")

    def set_frequency(self, frequency_hz: float) -> None:
        self.write(f"FREQ {frequency_hz}")

    def set_amplitude_vpp(self, amplitude_vpp: float) -> None:
        self.write(f"VOLT {amplitude_vpp} VPP")

    def set_offset(self, offset_v: float) -> None:
        self.write(f"VOLT:OFFS {offset_v}")

    def apply(
        self,
        function_name: str,
        frequency_hz: float,
        amplitude_vpp: float,
        offset_v: float,
    ) -> None:
        function_token = function_name.strip().upper()
        self.write(
            f"APPL:{function_token} {frequency_hz}, {amplitude_vpp} VPP, {offset_v} V"
        )

    def set_trigger_source(self, source: str) -> None:
        source_token = source.strip().upper()
        if source_token not in {"IMM", "EXT", "BUS"}:
            raise ValueError(f"Unsupported trigger source: {source}")
        mapping = {"IMM": "IMM", "EXT": "EXT", "BUS": "BUS"}
        self.write(f"TRIG:SOUR {mapping[source_token]}")

    def trigger(self) -> None:
        # BUS trigger is supported via TRIG or *TRG.
        self.write("TRIG")

    def get_error(self) -> str:
        return self.query("SYST:ERR?")


class VisaGenerator33250AClient(Generator33250AClient):
    def __init__(self, config: Generator33250AConfig) -> None:
        try:
            import pyvisa
        except ImportError as exc:
            raise RuntimeError("使用 VISA 控制 33250A 需要安裝 pyvisa。") from exc

        resource_name = config.resource.strip()
        if not resource_name:
            raise RuntimeError("VISA 模式需要提供 33250A 的 VISA resource。")

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

    def query(self, command: str) -> str:
        return str(self._inst.query(command)).strip()


class SerialGenerator33250AClient(Generator33250AClient):
    def __init__(self, config: Generator33250AConfig) -> None:
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("使用 Serial 控制 33250A 需要安裝 pyserial。") from exc

        port_name = config.port.strip()
        if not port_name:
            raise RuntimeError("Serial 模式需要提供串列埠。")

        handshake = config.handshake.strip().lower() or "none"
        if handshake not in {"none", "dsrdtr", "rtscts", "xonxoff"}:
            raise RuntimeError(f"不支援的 serial handshake: {config.handshake}")

        self._serial = serial.Serial(
            port=port_name,
            baudrate=config.baudrate,
            timeout=config.timeout_s,
            write_timeout=config.timeout_s,
            xonxoff=handshake == "xonxoff",
            rtscts=handshake == "rtscts",
            dsrdtr=handshake == "dsrdtr",
        )
        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()

    def close(self) -> None:
        self._serial.close()

    def write(self, command: str) -> None:
        self._serial.write((command + "\n").encode("ascii"))

    def query(self, command: str) -> str:
        self.write(command)
        raw = self._serial.readline()
        if not raw:
            raise RuntimeError(
                "33250A 沒有回應。請確認 COM 埠是否接對、序列參數是否為 9600/8/N/1，"
                "以及轉接器設定工具是否仍占用這個埠。"
            )
        return raw.decode("ascii", errors="replace").strip()


class TcpGenerator33250AClient(Generator33250AClient):
    def __init__(self, config: Generator33250AConfig) -> None:
        host = config.host.strip()
        if not host:
            raise RuntimeError("TCP 模式需要提供 33250A 轉接器的 IP 位址。")
        tcp_port = int(config.tcp_port)
        try:
            self._sock = socket.create_connection((host, tcp_port), timeout=config.timeout_s)
        except TimeoutError as exc:
            raise RuntimeError(
                f"無法連到 33250A TCP 轉接器 {host}:{tcp_port}，連線逾時。"
                " 請確認這裡填的是 33250A 轉接器位址，並檢查電腦乙太網路 IP 是否與設備在同一網段。"
            ) from exc
        except OSError as exc:
            raise RuntimeError(f"無法連到 33250A TCP 轉接器 {host}:{tcp_port}：{exc}") from exc
        self._sock.settimeout(config.timeout_s)

    def close(self) -> None:
        self._sock.close()

    def write(self, command: str) -> None:
        self._sock.sendall((command + "\n").encode("ascii"))

    def query(self, command: str) -> str:
        self.write(command)
        chunks = bytearray()
        try:
            while True:
                data = self._sock.recv(1)
                if not data:
                    break
                if data == b"\n":
                    break
                if data != b"\r":
                    chunks.extend(data)
        except TimeoutError as exc:
            raise RuntimeError("33250A TCP 已連上，但讀取回應逾時。請確認轉接器與儀器序列設定。") from exc
        if not chunks:
            raise RuntimeError("33250A TCP 沒有回應。")
        return chunks.decode("ascii", errors="replace").strip()


def list_generator_visa_resources() -> list[str]:
    try:
        import pyvisa
    except ImportError as exc:
        raise RuntimeError("列出 33250A VISA resource 需要安裝 pyvisa。") from exc

    rm = _open_visa_resource_manager(pyvisa)
    try:
        return sorted(str(resource) for resource in rm.list_resources())
    finally:
        rm.close()


def create_generator_33250a_client(config: Generator33250AConfig) -> Generator33250AClient:
    mode = config.mode.strip().lower()
    if mode == "visa":
        return VisaGenerator33250AClient(config)
    if mode == "serial":
        return SerialGenerator33250AClient(config)
    if mode == "tcp":
        return TcpGenerator33250AClient(config)
    raise ValueError(f"Unknown 33250A mode: {config.mode}")
