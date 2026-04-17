from __future__ import annotations

from dataclasses import dataclass

import serial
from serial.tools import list_ports


@dataclass
class SerialLink:
    port: str
    baudrate: int
    timeout_s: float

    def __post_init__(self) -> None:
        self._ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout_s)

    def request(self, cmd: str) -> str:
        self._ser.write((cmd + "\n").encode("ascii"))
        line = self._ser.readline().decode("ascii", errors="replace").strip()
        return line

    def close(self) -> None:
        self._ser.close()


def available_ports() -> list[str]:
    return [port.device for port in list_ports.comports()]
