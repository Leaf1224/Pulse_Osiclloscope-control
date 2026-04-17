from __future__ import annotations


def build_command(action: str, count: int | None = None) -> str:
    table = {
        "ping": "PING",
        "status": "GET_STATUS",
        "get-fault": "GET_FAULT",
        "get-count": "GET_COUNT",
        "get-sync-count": "GET_SYNC_COUNT",
        "arm": "ARM",
        "stop": "STOP",
        "reset-fault": "RESET_FAULT",
        "reset-sync-count": "RESET_SYNC_COUNT",
        "precharge": "PRECHARGE",
        "discharge": "DISCHARGE",
    }

    if action == "start":
        if count is None:
            return "START"
        return f"START COUNT={count}"

    if action not in table:
        raise ValueError(f"Unknown action: {action}")
    return table[action]
