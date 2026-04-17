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
    )
