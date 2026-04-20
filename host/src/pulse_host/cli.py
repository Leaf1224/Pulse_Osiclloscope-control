from __future__ import annotations

import argparse
import time

from .client import CsvRecorder
from .client import HostClient
from .config import load_config
from .generator_33250a import Generator33250AConfig
from .generator_33250a import create_generator_33250a_client
from .generator_33250a import list_generator_visa_resources
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
        "gen-identify",
        "gen-list-resources",
        "gen-output-on",
        "gen-output-off",
        "gen-apply",
        "gen-trigger",
        "gen-error",
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
    parser.add_argument("--gen-mode", default=None, choices=["visa", "serial"])
    parser.add_argument("--gen-resource", default=None)
    parser.add_argument("--gen-port", default=None)
    parser.add_argument("--gen-baudrate", type=int, default=None)
    parser.add_argument("--gen-timeout", type=float, default=None)
    parser.add_argument("--gen-function", default="PULS")
    parser.add_argument("--gen-frequency", type=float, default=1000.0)
    parser.add_argument("--gen-amplitude", type=float, default=5.0)
    parser.add_argument("--gen-offset", type=float, default=0.0)
    parser.add_argument("--gen-trigger-source", default="IMM", choices=["IMM", "EXT", "BUS"])
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


def run_generator_action(action: str, config: Generator33250AConfig, args: argparse.Namespace) -> None:
    if action == "gen-list-resources":
        for resource in list_generator_visa_resources():
            print(resource)
        return

    generator = create_generator_33250a_client(config)
    try:
        if action == "gen-identify":
            print(generator.identify())
        elif action == "gen-output-on":
            generator.output_on()
            print("OK")
        elif action == "gen-output-off":
            generator.output_off()
            print("OK")
        elif action == "gen-apply":
            generator.apply(
                args.gen_function,
                args.gen_frequency,
                args.gen_amplitude,
                args.gen_offset,
            )
            generator.set_trigger_source(args.gen_trigger_source)
            print("OK")
        elif action == "gen-trigger":
            generator.trigger()
            print("OK")
        elif action == "gen-error":
            print(generator.get_error())
        else:
            raise ValueError(f"Unknown generator action: {action}")
    finally:
        generator.close()


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
    generator_config = Generator33250AConfig(
        mode=args.gen_mode or cfg.gen_mode,
        resource=args.gen_resource if args.gen_resource is not None else cfg.gen_resource,
        port=args.gen_port if args.gen_port is not None else cfg.gen_port,
        baudrate=args.gen_baudrate or cfg.gen_baudrate,
        timeout_s=args.gen_timeout if args.gen_timeout is not None else cfg.gen_timeout_s,
    )

    if args.action.startswith("scope-"):
        run_scope_action(args.action, scope_config)
        return
    if args.action.startswith("gen-"):
        run_generator_action(args.action, generator_config, args)
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
