from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HostConfig:
    port: str = "COM3"
    baudrate: int = 115200
    timeout_s: float = 0.5
    scope_mode: str = "lan"
    scope_host: str = "192.168.0.100"
    scope_port: int = 5025
    scope_timeout_s: float = 2.0
    scope_resource: str = ""
    gen_mode: str = "tcp"
    gen_resource: str = ""
    gen_port: str = ""
    gen_host: str = "192.168.3.3"
    gen_tcp_port: int = 5000
    gen_baudrate: int = 9600
    gen_handshake: str = "none"
    gen_timeout_s: float = 2.0
    gen_function: str = "PULS"
    gen_frequency_hz: float = 1000.0
    gen_amplitude_vpp: float = 5.0
    gen_offset_v: float = 0.0
    gen_trigger_source: str = "IMM"


def load_config(path: str | None) -> HostConfig:
    if not path:
        return HostConfig()

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return HostConfig(
        port=data.get("port", "COM3"),
        baudrate=int(data.get("baudrate", 115200)),
        timeout_s=float(data.get("timeout_s", 0.5)),
        scope_mode=data.get("scope_mode", "lan"),
        scope_host=data.get("scope_host", "192.168.0.100"),
        scope_port=int(data.get("scope_port", 5025)),
        scope_timeout_s=float(data.get("scope_timeout_s", 2.0)),
        scope_resource=data.get("scope_resource", ""),
        gen_mode=data.get("gen_mode", "tcp"),
        gen_resource=data.get("gen_resource", ""),
        gen_port=data.get("gen_port", ""),
        gen_host=data.get("gen_host", "192.168.3.3"),
        gen_tcp_port=int(data.get("gen_tcp_port", 5000)),
        gen_baudrate=int(data.get("gen_baudrate", 9600)),
        gen_handshake=str(data.get("gen_handshake", "none")).strip().lower() or "none",
        gen_timeout_s=float(data.get("gen_timeout_s", 2.0)),
        gen_function=data.get("gen_function", "PULS"),
        gen_frequency_hz=float(data.get("gen_frequency_hz", 1000.0)),
        gen_amplitude_vpp=float(data.get("gen_amplitude_vpp", 5.0)),
        gen_offset_v=float(data.get("gen_offset_v", 0.0)),
        gen_trigger_source=data.get("gen_trigger_source", "IMM"),
    )
