from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path

from .protocol import build_command
from .serial_link import SerialLink


@dataclass
class StatusSnapshot:
    timestamp: float
    status: str
    fault: str
    count: str
    sync_count: str


class HostClient:
    def __init__(self, port: str, baudrate: int, timeout_s: float) -> None:
        self._link = SerialLink(port=port, baudrate=baudrate, timeout_s=timeout_s)

    def close(self) -> None:
        self._link.close()

    def request_raw(self, command: str) -> str:
        return self._link.request(command)

    def request_action(self, action: str, count: int | None = None) -> str:
        return self.request_raw(build_command(action, count))

    def read_snapshot(self) -> StatusSnapshot:
        now = time.time()
        return StatusSnapshot(
            timestamp=now,
            status=self.request_action("status"),
            fault=self.request_action("get-fault"),
            count=self.request_action("get-count"),
            sync_count=self.request_action("get-sync-count"),
        )


class CsvRecorder:
    def __init__(self, csv_path: str) -> None:
        self._path = Path(csv_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self._path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._handle)
        self._writer.writerow(["timestamp", "status", "fault", "count", "sync_count"])

    def write(self, snapshot: StatusSnapshot) -> None:
        self._writer.writerow([
            f"{snapshot.timestamp:.3f}",
            snapshot.status,
            snapshot.fault,
            snapshot.count,
            snapshot.sync_count,
        ])
        self._handle.flush()

    def close(self) -> None:
        self._handle.close()
