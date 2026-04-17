from __future__ import annotations

import argparse
import time

from .client import CsvRecorder
from .client import HostClient
from .config import load_config
from .scope import ScopeConfig
from .scope import create_scope_client
from .scope import list_visa_resources


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V1 pulse platform host CLI")
    parser.add_argument("action", choices=[
        "ping",
        "status",
        "get-fault",
        "get-count",
        "get-sync-count",
        "arm",
        "start",
        "stop",
        "reset-fault",
        "reset-sync-count",
        "precharge",
        "discharge",
        "monitor",
        "scope-identify",
        "scope-list-resources",
        "scope-run",
        "scope-stop",
        "scope-single",
        "scope-clear",
        "scope-autoscale",
        "scope-preset-trigger",
    ])
    parser.add_argument("--port", default=None)
    parser.add_argument("--baudrate", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("--count", type=int, default=None)
    parser.add_argument("--config", default=None)
    parser.add_argument("--csv", default=None)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--scope-mode", default=None, choices=["lan", "usb"])
    parser.add_argument("--scope-host", default=None)
    parser.add_argument("--scope-port", type=int, default=None)
    parser.add_argument("--scope-timeout", type=float, default=None)
    parser.add_argument("--scope-resource", default=None)
    return parser.parse_args()


def run_monitor(client: HostClient, csv_path: str | None, interval: float) -> None:
    recorder = CsvRecorder(csv_path) if csv_path else None
    try:
        while True:
            snapshot = client.read_snapshot()
            print(
                f"{snapshot.timestamp:.3f} "
                f"{snapshot.status} | {snapshot.fault} | {snapshot.count} | {snapshot.sync_count}"
            )
            if recorder:
                recorder.write(snapshot)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Monitor stopped.")
    finally:
        if recorder:
            recorder.close()


def run_scope_action(action: str, config: ScopeConfig) -> None:
    if action == "scope-list-resources":
        for resource in list_visa_resources():
            print(resource)
        return

    scope = create_scope_client(config)
    try:
        if action == "scope-identify":
            print(scope.identify())
        elif action == "scope-run":
            scope.run()
            print("OK")
        elif action == "scope-stop":
            scope.stop()
            print("OK")
        elif action == "scope-single":
            scope.single()
            print("OK")
        elif action == "scope-clear":
            scope.clear()
            print("OK")
        elif action == "scope-autoscale":
            scope.autoscale()
            print("OK")
        elif action == "scope-preset-trigger":
            scope.set_channel_display(1, True)
            scope.set_channel_display(2, True)
            scope.set_channel_display(3, True)
            scope.set_channel_display(4, True)
            scope.set_edge_trigger("CHAN4", 1.0)
            scope.set_timebase(0.002)
            print("OK")
        else:
            raise ValueError(f"Unknown scope action: {action}")
    finally:
        scope.close()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    port = args.port or cfg.port
    baudrate = args.baudrate or cfg.baudrate
    timeout_s = args.timeout if args.timeout is not None else cfg.timeout_s
    scope_config = ScopeConfig(
        mode=args.scope_mode or cfg.scope_mode,
        host=args.scope_host or cfg.scope_host,
        port=args.scope_port or cfg.scope_port,
        timeout_s=args.scope_timeout if args.scope_timeout is not None else cfg.scope_timeout_s,
        resource=args.scope_resource if args.scope_resource is not None else cfg.scope_resource,
    )

    if args.action.startswith("scope-"):
        run_scope_action(args.action, scope_config)
        return

    client = HostClient(port=port, baudrate=baudrate, timeout_s=timeout_s)
    try:
        if args.action == "monitor":
            run_monitor(client, args.csv, args.interval)
            return
        print(client.request_action(args.action, args.count))
    finally:
        client.close()


if __name__ == "__main__":
    main()
