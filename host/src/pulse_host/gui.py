from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from typing import Any
from typing import Mapping

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from pulse_host.client import CsvRecorder
    from pulse_host.client import HostClient
    from pulse_host.config import HostConfig
    from pulse_host.config import load_config
    from pulse_host.generator_33250a import Generator33250AConfig
    from pulse_host.generator_33250a import Generator33250AClient
    from pulse_host.generator_33250a import create_generator_33250a_client
    from pulse_host.generator_33250a import list_generator_visa_resources
    from pulse_host.scope import ScopeConfig
    from pulse_host.scope import ScopeClient
    from pulse_host.scope import create_scope_client
    from pulse_host.scope import list_visa_resources
    from pulse_host.serial_link import available_ports
else:
    from .client import CsvRecorder
    from .client import HostClient
    from .config import HostConfig
    from .config import load_config
    from .generator_33250a import Generator33250AConfig
    from .generator_33250a import Generator33250AClient
    from .generator_33250a import create_generator_33250a_client
    from .generator_33250a import list_generator_visa_resources
    from .scope import ScopeConfig
    from .scope import ScopeClient
    from .scope import create_scope_client
    from .scope import list_visa_resources
    from .serial_link import available_ports


APP_STORAGE_DIR = Path.home() / ".pulse_host"
SESSION_STATE_PATH = APP_STORAGE_DIR / "session_state.json"
PRESET_LIBRARY_PATH = APP_STORAGE_DIR / "presets.json"


class PulseHostApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Pulse Bench Studio")
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        window_w = min(1500, max(1180, screen_w - 120))
        window_h = min(980, max(760, screen_h - 120))
        self.root.geometry(f"{window_w}x{window_h}")
        self.root.minsize(1120, 760)

        self.colors = {
            "bg": "#f3efe7",
            "surface": "#fffdfa",
            "surface_alt": "#f7f4ee",
            "hero": "#10233f",
            "hero_alt": "#183a63",
            "ink": "#172033",
            "muted": "#6b7280",
            "border": "#ddd6c8",
            "accent": "#0f766e",
            "accent_active": "#115e59",
            "accent_soft": "#d8f1ed",
            "danger": "#b42318",
            "danger_active": "#912018",
            "danger_soft": "#fbe9e7",
            "warning": "#b54708",
            "warning_soft": "#fef0c7",
            "success": "#15803d",
            "success_soft": "#dcfce7",
            "chip_idle": "#e5e7eb",
            "chip_text": "#334155",
        }

        self.client: HostClient | None = None
        self.scope_client: ScopeClient | None = None
        self.generator_client: Generator33250AClient | None = None
        self.recorder: CsvRecorder | None = None
        self.monitor_job: str | None = None
        self._tab_canvases: list[tk.Canvas] = []
        self.settings_window: tk.Toplevel | None = None
        self.preset_window: tk.Toplevel | None = None
        self.preset_tree: ttk.Treeview | None = None
        self.preset_preview_text: tk.Text | None = None
        self.action_panel_window: tk.Toplevel | None = None
        self.action_panel_owner: tk.Misc | None = None
        self.tooltip_window: tk.Toplevel | None = None
        self.tooltip_job: str | None = None
        self.tooltip_widget: tk.Misc | None = None
        self.toast_window: tk.Toplevel | None = None
        self.toast_job: str | None = None
        self._current_button_action_label: str | None = None
        self._current_button_action_failed = False
        self.connection_badges: dict[str, tk.Label] = {}
        self.connection_details: dict[str, tk.Label] = {}
        self.runtime_tag_labels: dict[str, tk.Label] = {}
        self.preset_library: dict[str, dict[str, Any]] = {}
        self.monitor_active = False
        self.pulse_capture_active = False
        self.pulse_capture_cancel_requested = False
        self.quick_start_button: tk.Frame | None = None
        self.quick_stop_button: tk.Frame | None = None

        self.config_path = tk.StringVar()
        self.port_var = tk.StringVar(value="COM20")
        self.baudrate_var = tk.StringVar(value="115200")
        self.timeout_var = tk.StringVar(value="0.5")
        self.count_var = tk.StringVar(value="100")
        self.interval_var = tk.StringVar(value="0.5")
        self.csv_var = tk.StringVar()
        self.capture_timeout_var = tk.StringVar(value="15")
        self.capture_path_var = tk.StringVar()
        self.final_single_lead_var = tk.StringVar(value="2")
        self.capture_render_delay_var = tk.StringVar(value="0.6")

        self.scope_mode_var = tk.StringVar(value="usb")
        self.scope_host_var = tk.StringVar(value="192.168.0.100")
        self.scope_port_var = tk.StringVar(value="5025")
        self.scope_timeout_var = tk.StringVar(value="2.0")
        self.scope_resource_var = tk.StringVar(value="")
        self.scope_trigger_source_var = tk.StringVar(value="CH4")
        self.scope_trigger_level_var = tk.StringVar(value="1.0")
        self.scope_trigger_sweep_var = tk.StringVar(value="NORMAL")
        self.scope_timebase_var = tk.StringVar(value="0.002")
        self.scope_ch1_enabled_var = tk.BooleanVar(value=True)
        self.scope_ch2_enabled_var = tk.BooleanVar(value=True)
        self.scope_ch3_enabled_var = tk.BooleanVar(value=True)
        self.scope_ch4_enabled_var = tk.BooleanVar(value=True)
        self.scope_trigger_summary_var = tk.StringVar(value="")

        self.gen_mode_var = tk.StringVar(value="tcp")
        self.gen_resource_var = tk.StringVar(value="")
        self.gen_port_var = tk.StringVar(value="")
        self.gen_host_var = tk.StringVar(value="192.168.3.3")
        self.gen_tcp_port_var = tk.StringVar(value="5000")
        self.gen_local_ip_var = tk.StringVar(value="尚未偵測")
        self.gen_local_ip_detected = ""
        self.gen_baudrate_var = tk.StringVar(value="9600")
        self.gen_handshake_var = tk.StringVar(value="none")
        self.gen_timeout_var = tk.StringVar(value="2.0")
        self.gen_function_var = tk.StringVar(value="PULS")
        self.gen_frequency_var = tk.StringVar(value="1000")
        self.gen_amplitude_var = tk.StringVar(value="5.0")
        self.gen_offset_var = tk.StringVar(value="0.0")
        self.gen_trigger_source_var = tk.StringVar(value="IMM")

        self.connection_var = tk.StringVar(value="MCU 尚未連線")
        self.scope_connection_var = tk.StringVar(value="示波器尚未連線")
        self.generator_connection_var = tk.StringVar(value="33250A 尚未連線")
        self.status_var = tk.StringVar(value="STATUS N/A")
        self.fault_var = tk.StringVar(value="FAULT N/A")
        self.count_rsp_var = tk.StringVar(value="COUNT N/A")
        self.sync_rsp_var = tk.StringVar(value="SYNC_COUNT N/A")
        self.workflow_var = tk.StringVar(value="先建立設備連線，再開始 bench bring-up。")
        self.last_output_var = tk.StringVar(value="尚未產生截圖或匯出檔案")
        self.session_note_var = tk.StringVar(value="這個版本支援個人 Preset、設定彈窗與子分頁。")
        self.active_preset_var = tk.StringVar(value="")
        self.run_state_var = tk.StringVar(value="待機中，按 Start Run 後會顯示目前流程狀態。")
        self.quick_run_use_generator_var = tk.BooleanVar(value=False)

        for variable in (
            self.scope_trigger_source_var,
            self.scope_trigger_level_var,
            self.scope_trigger_sweep_var,
            self.scope_timebase_var,
            self.final_single_lead_var,
            self.capture_render_delay_var,
            self.scope_ch1_enabled_var,
            self.scope_ch2_enabled_var,
            self.scope_ch3_enabled_var,
            self.scope_ch4_enabled_var,
        ):
            variable.trace_add("write", self._update_scope_trigger_summary)

        self._build_style()
        self._build_layout()
        self._install_messagebox_hooks()
        self._load_preset_library()
        self._load_session_state()
        self.refresh_ports()
        self.generator_refresh_ports()
        self._refresh_preset_combobox()
        self._on_scope_mode_change()
        self._on_generator_mode_change()
        self._update_scope_trigger_summary()
        self._update_connection_summary()
        self._update_run_action_state()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_style(self) -> None:
        self.root.configure(bg=self.colors["bg"])
        self.root.option_add("*Font", "{Segoe UI} 11")
        self.root.option_add("*TCombobox*Listbox.font", "{Segoe UI} 11")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TFrame", background=self.colors["bg"])
        style.configure("Surface.TFrame", background=self.colors["surface"])
        style.configure("Surface.TLabel", background=self.colors["surface"], foreground=self.colors["ink"])
        style.configure("Muted.TLabel", background=self.colors["surface"], foreground=self.colors["muted"])
        style.configure(
            "Section.TLabelframe",
            background=self.colors["surface"],
            bordercolor=self.colors["border"],
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "Section.TLabelframe.Label",
            background=self.colors["surface"],
            foreground=self.colors["ink"],
            font=("Segoe UI Semibold", 12),
        )
        style.configure("Modern.TLabel", background=self.colors["surface"], foreground=self.colors["ink"])
        style.configure("Hint.TLabel", background=self.colors["surface"], foreground=self.colors["muted"])
        style.configure(
            "Modern.TNotebook",
            background=self.colors["bg"],
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        style.configure(
            "Modern.TNotebook.Tab",
            font=("Segoe UI Semibold", 11),
            padding=(16, 10),
            background=self.colors["surface_alt"],
            foreground=self.colors["ink"],
        )
        style.map(
            "Modern.TNotebook.Tab",
            background=[("selected", self.colors["surface"])],
            foreground=[("selected", self.colors["accent"])],
        )
        style.configure(
            "Modern.TEntry",
            fieldbackground="#ffffff",
            background="#ffffff",
            foreground=self.colors["ink"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            padding=6,
        )
        style.configure(
            "Modern.TCombobox",
            fieldbackground="#ffffff",
            background="#ffffff",
            foreground=self.colors["ink"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            padding=5,
        )
        style.configure(
            "Modern.Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground=self.colors["ink"],
            rowheight=30,
            bordercolor=self.colors["border"],
        )
        style.configure(
            "Modern.Treeview.Heading",
            background=self.colors["surface_alt"],
            foreground=self.colors["ink"],
            relief="flat",
            font=("Segoe UI Semibold", 10),
        )

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        app = ttk.Frame(self.root, style="App.TFrame", padding=18)
        app.grid(row=0, column=0, sticky="nsew")
        app.columnconfigure(0, weight=1)
        app.rowconfigure(1, weight=1)

        header = tk.Frame(app, bg=self.colors["hero"], padx=24, pady=20)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)

        title_col = tk.Frame(header, bg=self.colors["hero"])
        title_col.grid(row=0, column=0, sticky="w")
        tk.Label(
            title_col,
            text="Pulse Bench Studio",
            bg=self.colors["hero"],
            fg="white",
            font=("Segoe UI Semibold", 24),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            title_col,
            text="更像工作台的桌面控制介面，讓 MCU / Scope / 33250A 的流程整理在同一個 session 裡。",
            bg=self.colors["hero"],
            fg="#dbe7ff",
            font=("Segoe UI", 11),
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        header_actions = tk.Frame(header, bg=self.colors["hero"])
        header_actions.grid(row=0, column=1, sticky="e")
        self._make_button(header_actions, "設定彈窗", self.open_settings_dialog, kind="hero").grid(
            row=0, column=0, padx=(0, 8)
        )
        self._make_button(header_actions, "Preset 管理", self.open_preset_manager, kind="hero_alt").grid(
            row=0, column=1, padx=(0, 8)
        )
        self._make_button(header_actions, "匯入 JSON", self.load_config_file, kind="hero_alt").grid(
            row=0, column=2, padx=(0, 8)
        )
        self._make_button(header_actions, "匯出 JSON", self.export_current_config, kind="hero_alt").grid(
            row=0, column=3
        )

        body = ttk.Frame(app, style="App.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        sidebar_host = tk.Frame(
            body,
            bg=self.colors["surface_alt"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        sidebar_host.grid(row=0, column=0, sticky="nsw", padx=(0, 16))
        sidebar_host.grid_propagate(False)
        sidebar_host.configure(width=330)
        sidebar_host.columnconfigure(0, weight=1)
        sidebar_host.rowconfigure(0, weight=1)

        sidebar_canvas = tk.Canvas(
            sidebar_host,
            bg=self.colors["surface_alt"],
            highlightthickness=0,
            borderwidth=0,
            width=330,
        )
        sidebar_canvas.grid(row=0, column=0, sticky="nsew")
        sidebar_scrollbar = ttk.Scrollbar(sidebar_host, orient="vertical", command=sidebar_canvas.yview)
        sidebar_scrollbar.grid(row=0, column=1, sticky="ns")
        sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)

        sidebar = tk.Frame(
            sidebar_canvas,
            bg=self.colors["surface_alt"],
            padx=16,
            pady=16,
        )
        sidebar_window = sidebar_canvas.create_window((0, 0), window=sidebar, anchor="nw")
        sidebar._scroll_canvas_ref = sidebar_canvas  # type: ignore[attr-defined]
        sidebar.bind(
            "<Configure>",
            lambda _event, current_canvas=sidebar_canvas: self._update_canvas_scroll_region(current_canvas),
            add="+",
        )
        sidebar_canvas.bind(
            "<Configure>",
            lambda event, current_canvas=sidebar_canvas, current_window=sidebar_window: self._resize_canvas_content(
                current_canvas, current_window, event
            ),
            add="+",
        )
        self._build_sidebar(sidebar)

        content = ttk.Frame(body, style="App.TFrame")
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        self.main_notebook = ttk.Notebook(content, style="Modern.TNotebook")
        self.main_notebook.grid(row=0, column=0, sticky="nsew")
        self.root.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

        dashboard_tab = self._create_scrollable_tab(self.main_notebook, "總覽")
        devices_tab = self._create_scrollable_tab(self.main_notebook, "設備工作區")
        automation_tab = self._create_scrollable_tab(self.main_notebook, "自動化流程")
        logs_tab = self._create_scrollable_tab(self.main_notebook, "記錄與匯出")
        help_tab = self._create_scrollable_tab(self.main_notebook, "操作說明")

        self._build_dashboard_tab(dashboard_tab)
        self._build_devices_tab(devices_tab)
        self._build_automation_tab(automation_tab)
        self._build_logs_tab(logs_tab)
        self._build_help_tab(help_tab)

    def _build_sidebar(self, parent: tk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        session_card = self._sidebar_card(parent, "Session", "快速套用個人化參數")
        ttk.Label(session_card, text="目前 Preset", style="Hint.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        self.preset_combo = ttk.Combobox(
            session_card,
            textvariable=self.active_preset_var,
            state="readonly",
            style="Modern.TCombobox",
            width=24,
        )
        self.preset_combo.grid(row=1, column=0, sticky="ew")
        preset_buttons = tk.Frame(session_card, bg=self.colors["surface"])
        preset_buttons.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        preset_buttons.columnconfigure(0, weight=1)
        preset_buttons.columnconfigure(1, weight=1)
        self._make_button(preset_buttons, "套用", self.apply_selected_preset, kind="accent").grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        self._make_button(preset_buttons, "另存目前", self.save_current_as_preset, kind="neutral").grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

        connection_card = self._sidebar_card(parent, "設備狀態", "看一眼就知道哪台機器在線上")
        self._build_connection_chip(connection_card, "MCU", "mcu", row=0)
        self._build_connection_chip(connection_card, "Scope", "scope", row=1)
        self._build_connection_chip(connection_card, "33250A", "generator", row=2)

        runtime_card = self._sidebar_card(parent, "執行中功能", "用 Tag 看現在有哪些流程正在跑")
        self._build_runtime_tags(runtime_card)

        quick_card = self._sidebar_card(parent, "快捷操作", "常用動作放在同一排")
        quick_card.columnconfigure(0, weight=1)
        quick_card.columnconfigure(1, weight=1)
        self._make_action_group(
            quick_card,
            "連接相關",
            "儀器連接",
            [
                ("連接 MCU", self.connect, "accent"),
                ("中斷 MCU", self.disconnect, "neutral"),
                ("連接示波器", self.connect_scope, "accent"),
                ("中斷示波器", self.disconnect_scope, "neutral"),
                ("連接 33250A", self.connect_generator, "accent"),
                ("中斷 33250A", self.disconnect_generator, "neutral"),
            ],
            kind="accent",
            columns=2,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        self._make_button(quick_card, "刷新 Snapshot", self.refresh_snapshot, kind="neutral").grid(
            row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 8)
        )
        self._make_button(quick_card, "Bench Check", self.run_bench_check, kind="neutral").grid(
            row=1, column=0, sticky="ew", padx=(0, 6), pady=(0, 8)
        )
        self._make_button(quick_card, "Monitor 開關", self.toggle_monitor, kind="neutral").grid(
            row=1, column=1, sticky="ew", padx=(6, 0), pady=(0, 8)
        )
        self._make_button(quick_card, "Reset Sync", lambda: self.send_action("reset-sync-count"), kind="neutral").grid(
            row=2, column=0, sticky="ew", padx=(0, 6), pady=(0, 8)
        )
        self.quick_start_button = self._make_button(quick_card, "Start Run", self.quick_start_run, kind="accent")
        self.quick_start_button.grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=(0, 8))
        run_options = tk.Frame(quick_card, bg=self.colors["surface"])
        run_options.grid(row=3, column=0, sticky="w", padx=(0, 6), pady=(0, 8))
        self._make_scope_channel_toggle(run_options, "有接 33250A", self.quick_run_use_generator_var).grid(
            row=0, column=0, sticky="w"
        )
        self.quick_stop_button = self._make_button(quick_card, "終止流程", self.cancel_pulse_capture, kind="danger")
        self.quick_stop_button.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        tk.Label(
            quick_card,
            textvariable=self.run_state_var,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            wraplength=250,
            justify="left",
            anchor="nw",
        ).grid(row=5, column=0, columnspan=2, sticky="ew")

        memo_card = self._sidebar_card(parent, "Session 筆記", "把關鍵狀態放在左側")
        tk.Label(
            memo_card,
            textvariable=self.workflow_var,
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            wraplength=250,
            justify="left",
            anchor="nw",
        ).grid(row=0, column=0, sticky="ew")
        tk.Label(
            memo_card,
            textvariable=self.last_output_var,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            wraplength=250,
            justify="left",
            anchor="nw",
        ).grid(row=1, column=0, sticky="ew", pady=(12, 0))

        note_card = self._sidebar_card(parent, "這次改版", "新介面的核心想法")
        tk.Label(
            note_card,
            textvariable=self.session_note_var,
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            wraplength=250,
            justify="left",
            anchor="nw",
        ).grid(row=0, column=0, sticky="ew")

    def _build_dashboard_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=3)
        parent.columnconfigure(1, weight=2)

        hero = self._surface_card(parent, row=0, column=0, columnspan=2, padx=(0, 0), pady=(0, 14))
        hero.columnconfigure(0, weight=1)
        hero.columnconfigure(1, weight=0)
        tk.Label(
            hero,
            text="Bench 總覽",
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            font=("Segoe UI Semibold", 20),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            hero,
            text="從這裡看目前設備連線、MCU 狀態、最近一次輸出，以及最常用的 bring-up 動作。",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 11),
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        hero_actions = tk.Frame(hero, bg=self.colors["surface"])
        hero_actions.grid(row=0, column=1, rowspan=2, sticky="e")
        self._make_button(hero_actions, "設定彈窗", self.open_settings_dialog, kind="neutral").grid(
            row=0, column=0, padx=(0, 8)
        )
        self._make_button(hero_actions, "Pulse 擷取", self.run_pulse_capture, kind="accent").grid(row=0, column=1)

        metrics = tk.Frame(parent, bg=self.colors["bg"])
        metrics.grid(row=1, column=0, sticky="nsew", padx=(0, 14), pady=(0, 14))
        for col in range(2):
            metrics.columnconfigure(col, weight=1)
        self._metric_card(metrics, "系統狀態", self.status_var, 0, 0)
        self._metric_card(metrics, "Fault", self.fault_var, 0, 1)
        self._metric_card(metrics, "Pulse Count", self.count_rsp_var, 1, 0)
        self._metric_card(metrics, "Sync Count", self.sync_rsp_var, 1, 1)

        run_card = self._surface_card(parent, row=1, column=1, padx=(0, 0), pady=(0, 14))
        run_card.columnconfigure(0, weight=1)
        run_card.columnconfigure(1, weight=1)
        self._card_title(run_card, "快速控制", "把常用 MCU 動作放在首頁")
        ttk.Label(run_card, text="Pulse Count", style="Hint.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 4))
        ttk.Entry(run_card, textvariable=self.count_var, style="Modern.TEntry").grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10)
        )
        self._make_button(run_card, "PING", lambda: self.send_action("ping"), kind="neutral").grid(
            row=3, column=0, sticky="ew", padx=(0, 6), pady=(0, 8)
        )
        self._make_button(run_card, "Bench Check", self.run_bench_check, kind="neutral").grid(
            row=3, column=1, sticky="ew", padx=(6, 0), pady=(0, 8)
        )
        self._make_button(run_card, "Arm", lambda: self.send_action("arm"), kind="neutral").grid(
            row=4, column=0, sticky="ew", padx=(0, 6), pady=(0, 8)
        )
        self._make_button(run_card, "Start", self.start_run, kind="accent").grid(
            row=4, column=1, sticky="ew", padx=(6, 0), pady=(0, 8)
        )
        self._make_button(run_card, "Stop", lambda: self.send_action("stop"), kind="neutral").grid(
            row=5, column=0, sticky="ew", padx=(0, 6)
        )
        self._make_button(run_card, "Discharge", lambda: self.send_action("discharge"), kind="danger").grid(
            row=5, column=1, sticky="ew", padx=(6, 0)
        )

        workflow_card = self._surface_card(parent, row=2, column=0, padx=(0, 14), pady=(0, 14))
        self._card_title(workflow_card, "工作流", "讓操作順序更直覺")
        tk.Label(
            workflow_card,
            text=(
                "1. 先連接 MCU 與示波器\n"
                "2. Bench Check 確認 STATUS / FAULT / COUNT / SYNC\n"
                "3. 在設備子分頁微調 trigger 與 generator 參數\n"
                "4. 開始 Monitor 或直接進行 Pulse 擷取\n"
                "5. 圖片與 log 可在記錄頁集中整理"
            ),
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            justify="left",
            anchor="nw",
            wraplength=520,
        ).grid(row=1, column=0, sticky="ew", pady=(8, 10))
        tk.Label(
            workflow_card,
            textvariable=self.workflow_var,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            justify="left",
            anchor="nw",
            wraplength=520,
        ).grid(row=2, column=0, sticky="ew")

        output_card = self._surface_card(parent, row=2, column=1, padx=(0, 0), pady=(0, 14))
        output_card.columnconfigure(0, weight=1)
        self._card_title(output_card, "最近輸出", "截圖與匯出路徑")
        ttk.Label(output_card, text="Capture 路徑", style="Hint.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 4))
        ttk.Entry(output_card, textvariable=self.capture_path_var, style="Modern.TEntry").grid(
            row=2, column=0, sticky="ew", pady=(0, 8)
        )
        ttk.Label(output_card, text="CSV 路徑", style="Hint.TLabel").grid(row=3, column=0, sticky="w", pady=(4, 4))
        ttk.Entry(output_card, textvariable=self.csv_var, style="Modern.TEntry").grid(
            row=4, column=0, sticky="ew", pady=(0, 8)
        )
        tk.Label(
            output_card,
            textvariable=self.last_output_var,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            justify="left",
            anchor="nw",
            wraplength=360,
        ).grid(row=5, column=0, sticky="ew", pady=(0, 10))
        output_actions = tk.Frame(output_card, bg=self.colors["surface"])
        output_actions.grid(row=6, column=0, sticky="ew")
        output_actions.columnconfigure(0, weight=1)
        output_actions.columnconfigure(1, weight=1)
        self._make_button(output_actions, "選擇 Capture", self.pick_capture_path, kind="neutral").grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        self._make_button(output_actions, "開啟位置", self.open_capture_path, kind="neutral").grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

    def _build_devices_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(parent, style="Modern.TNotebook")
        notebook.grid(row=0, column=0, sticky="nsew")

        mcu_tab = self._create_scrollable_tab(notebook, "MCU")
        scope_tab = self._create_scrollable_tab(notebook, "示波器")
        generator_tab = self._create_scrollable_tab(notebook, "33250A")

        self._build_mcu_panel(mcu_tab)
        self._build_scope_panel(scope_tab)
        self._build_generator_panel(generator_tab)

    def _build_mcu_panel(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

        connection = ttk.LabelFrame(parent, text="MCU 連線", style="Section.TLabelframe", padding=16)
        connection.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 12))
        for col in range(2):
            connection.columnconfigure(col, weight=1)

        ttk.Label(connection, text="COM Port", style="Modern.TLabel").grid(row=0, column=0, sticky="w")
        self.port_combo = ttk.Combobox(connection, textvariable=self.port_var, state="normal", style="Modern.TCombobox")
        self.port_combo.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 10))
        ttk.Label(connection, text="Baudrate", style="Modern.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Entry(connection, textvariable=self.baudrate_var, style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", pady=(4, 10)
        )

        ttk.Label(connection, text="Timeout (s)", style="Modern.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Entry(connection, textvariable=self.timeout_var, style="Modern.TEntry").grid(
            row=3, column=0, sticky="ew", padx=(0, 8), pady=(4, 10)
        )
        ttk.Label(connection, text="狀態", style="Modern.TLabel").grid(row=2, column=1, sticky="w")
        ttk.Label(connection, textvariable=self.connection_var, style="Hint.TLabel", wraplength=320).grid(
            row=3, column=1, sticky="w", pady=(4, 10)
        )

        mcu_actions = tk.Frame(connection, bg=self.colors["surface"])
        mcu_actions.grid(row=4, column=0, columnspan=2, sticky="ew")
        for col in range(3):
            mcu_actions.columnconfigure(col, weight=1)
        self._make_button(mcu_actions, "刷新 Ports", self.refresh_ports, kind="neutral").grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        self._make_button(mcu_actions, "連接", self.connect, kind="accent").grid(
            row=0, column=1, sticky="ew", padx=6
        )
        self._make_button(mcu_actions, "中斷", self.disconnect, kind="neutral").grid(
            row=0, column=2, sticky="ew", padx=(6, 0)
        )

        control = ttk.LabelFrame(parent, text="MCU 控制台", style="Section.TLabelframe", padding=16)
        control.grid(row=0, column=1, sticky="nsew", pady=(0, 12))
        for col in range(2):
            control.columnconfigure(col, weight=1)
        ttk.Label(control, text="Pulse Count", style="Modern.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(control, textvariable=self.count_var, style="Modern.TEntry").grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(4, 12)
        )
        groups = [
            (
                "檢查與快照",
                "MCU 檢查與快照",
                [
                    ("PING", lambda: self.send_action("ping"), "neutral"),
                    ("Snapshot", self.refresh_snapshot, "neutral"),
                    ("Bench Check", self.run_bench_check, "neutral"),
                    ("Reset Sync", lambda: self.send_action("reset-sync-count"), "neutral"),
                ],
                "neutral",
            ),
            (
                "脈衝控制",
                "MCU 脈衝控制",
                [
                    ("Precharge", lambda: self.send_action("precharge"), "neutral"),
                    ("Arm", lambda: self.send_action("arm"), "neutral"),
                    ("Start", self.start_run, "accent"),
                    ("Stop", lambda: self.send_action("stop"), "neutral"),
                ],
                "accent",
            ),
            (
                "安全與復位",
                "MCU 安全與復位",
                [
                    ("Discharge", lambda: self.send_action("discharge"), "danger"),
                    ("Reset Fault", lambda: self.send_action("reset-fault"), "danger"),
                ],
                "neutral",
            ),
        ]
        for idx, (label, panel_title, actions, kind) in enumerate(groups):
            row = 2 + idx // 2
            col = idx % 2
            self._make_action_group(control, label, panel_title, actions, kind=kind).grid(
                row=row,
                column=col,
                sticky="ew",
                padx=(0, 6) if col == 0 else (6, 0),
                pady=(0, 8),
            )

        status = ttk.LabelFrame(parent, text="即時數值", style="Section.TLabelframe", padding=16)
        status.grid(row=1, column=0, columnspan=2, sticky="nsew")
        for col in range(4):
            status.columnconfigure(col, weight=1)
        self._status_mini_card(status, "STATUS", self.status_var, 0)
        self._status_mini_card(status, "FAULT", self.fault_var, 1)
        self._status_mini_card(status, "COUNT", self.count_rsp_var, 2)
        self._status_mini_card(status, "SYNC", self.sync_rsp_var, 3)

    def _build_scope_panel(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

        connection = ttk.LabelFrame(parent, text="示波器連線", style="Section.TLabelframe", padding=16)
        connection.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 12))
        for col in range(2):
            connection.columnconfigure(col, weight=1)

        ttk.Label(connection, text="模式", style="Modern.TLabel").grid(row=0, column=0, sticky="w")
        scope_mode_combo = ttk.Combobox(
            connection,
            textvariable=self.scope_mode_var,
            values=["usb", "lan"],
            state="readonly",
            style="Modern.TCombobox",
        )
        scope_mode_combo.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 10))
        scope_mode_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_scope_mode_change())

        ttk.Label(connection, text="Timeout (s)", style="Modern.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Entry(connection, textvariable=self.scope_timeout_var, style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", pady=(4, 10)
        )

        self.scope_host_label = ttk.Label(connection, text="IP", style="Modern.TLabel")
        self.scope_host_label.grid(row=2, column=0, sticky="w")
        self.scope_host_entry = ttk.Entry(connection, textvariable=self.scope_host_var, style="Modern.TEntry")
        self.scope_host_entry.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(4, 10))

        self.scope_port_label = ttk.Label(connection, text="Port", style="Modern.TLabel")
        self.scope_port_label.grid(row=2, column=1, sticky="w")
        self.scope_port_entry = ttk.Entry(connection, textvariable=self.scope_port_var, style="Modern.TEntry")
        self.scope_port_entry.grid(row=3, column=1, sticky="ew", pady=(4, 10))

        self.scope_resource_label = ttk.Label(connection, text="VISA Resource", style="Modern.TLabel")
        self.scope_resource_label.grid(row=4, column=0, sticky="w")
        self.scope_resource_entry = ttk.Entry(connection, textvariable=self.scope_resource_var, style="Modern.TEntry")
        self.scope_resource_entry.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 10))

        ttk.Label(connection, text="狀態", style="Modern.TLabel").grid(row=6, column=0, sticky="w")
        ttk.Label(connection, textvariable=self.scope_connection_var, style="Hint.TLabel", wraplength=420).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(4, 10)
        )

        connection_buttons = tk.Frame(connection, bg=self.colors["surface"])
        connection_buttons.grid(row=8, column=0, columnspan=2, sticky="ew")
        for col in range(2):
            connection_buttons.columnconfigure(col, weight=1)
        self._make_action_group(
            connection_buttons,
            "資源與連線",
            "示波器資源與連線",
            [
                ("列出 VISA", self.scope_list_resources, "neutral"),
                ("選第一個", self.scope_pick_first_resource, "neutral"),
                ("連接", self.connect_scope, "accent"),
                ("中斷", self.disconnect_scope, "neutral"),
            ],
            kind="accent",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._make_action_group(
            connection_buttons,
            "識別與預設",
            "示波器識別與預設",
            [
                ("Identify", self.scope_identify, "neutral"),
                ("Preset + Single", self.scope_preset_single, "accent"),
            ],
            kind="neutral",
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        capture = ttk.LabelFrame(parent, text="Trigger 與擷取", style="Section.TLabelframe", padding=16)
        capture.grid(row=0, column=1, sticky="nsew", pady=(0, 12))
        for col in range(2):
            capture.columnconfigure(col, weight=1)
        ttk.Label(capture, text="Trigger Source", style="Modern.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            capture,
            textvariable=self.scope_trigger_source_var,
            values=["CH1", "CH2", "CH3", "CH4"],
            state="readonly",
            style="Modern.TCombobox",
        ).grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 10))
        ttk.Label(capture, text="Trigger Level (V)", style="Modern.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Entry(capture, textvariable=self.scope_trigger_level_var, style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", pady=(4, 10)
        )

        ttk.Label(capture, text="Trigger Sweep", style="Modern.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Combobox(
            capture,
            textvariable=self.scope_trigger_sweep_var,
            values=["AUTO", "NORMAL"],
            state="readonly",
            style="Modern.TCombobox",
        ).grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(4, 10))
        ttk.Label(capture, text="Timebase (s/div)", style="Modern.TLabel").grid(row=2, column=1, sticky="w")
        ttk.Entry(capture, textvariable=self.scope_timebase_var, style="Modern.TEntry").grid(
            row=3, column=1, sticky="ew", pady=(4, 10)
        )

        ttk.Label(capture, text="Capture Timeout (s)", style="Modern.TLabel").grid(row=4, column=0, sticky="w")
        ttk.Entry(capture, textvariable=self.capture_timeout_var, style="Modern.TEntry").grid(
            row=5, column=0, sticky="ew", padx=(0, 8), pady=(4, 10)
        )
        ttk.Label(capture, text="Capture 路徑", style="Modern.TLabel").grid(row=4, column=1, sticky="w")
        ttk.Entry(capture, textvariable=self.capture_path_var, style="Modern.TEntry").grid(
            row=5, column=1, sticky="ew", pady=(4, 10)
        )
        ttk.Label(capture, text="最後截圖提前量", style="Modern.TLabel").grid(row=6, column=0, sticky="w")
        ttk.Entry(capture, textvariable=self.final_single_lead_var, style="Modern.TEntry").grid(
            row=7, column=0, sticky="ew", padx=(0, 8), pady=(4, 10)
        )
        ttk.Label(capture, text="Trigger後截圖等待 (s)", style="Modern.TLabel").grid(row=6, column=1, sticky="w")
        ttk.Entry(capture, textvariable=self.capture_render_delay_var, style="Modern.TEntry").grid(
            row=7, column=1, sticky="ew", pady=(4, 10)
        )
        ttk.Label(capture, text="顯示中的通道", style="Modern.TLabel").grid(row=8, column=0, sticky="w")
        channel_row = tk.Frame(capture, bg=self.colors["surface"])
        channel_row.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(4, 10))
        for col in range(4):
            channel_row.columnconfigure(col, weight=1)
        self._make_scope_channel_toggle(channel_row, "CH1", self.scope_ch1_enabled_var).grid(row=0, column=0, sticky="w")
        self._make_scope_channel_toggle(channel_row, "CH2", self.scope_ch2_enabled_var).grid(row=0, column=1, sticky="w")
        self._make_scope_channel_toggle(channel_row, "CH3", self.scope_ch3_enabled_var).grid(row=0, column=2, sticky="w")
        self._make_scope_channel_toggle(channel_row, "CH4", self.scope_ch4_enabled_var).grid(row=0, column=3, sticky="w")
        tk.Label(
            capture,
            text="填 1 代表最後一發前才切回 SINGLE，填 2 代表保留最後兩發給示波器重新等待。",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            justify="left",
            anchor="nw",
            wraplength=220,
        ).grid(row=10, column=0, sticky="nw", padx=(0, 8), pady=(0, 10))
        tk.Label(
            capture,
            textvariable=self.scope_trigger_summary_var,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            justify="left",
            anchor="nw",
            wraplength=420,
        ).grid(row=10, column=1, sticky="ew", pady=(0, 10))

        groups = [
            (
                "Trigger 套用",
                "示波器 Trigger 套用",
                [("Apply Trigger", self.scope_apply_trigger_settings, "neutral")],
                "neutral",
            ),
            (
                "波形控制",
                "示波器波形控制",
                [
                    ("Run", self.scope_run, "neutral"),
                    ("Stop", self.scope_stop, "neutral"),
                    ("Single", self.scope_single, "neutral"),
                    ("Autoscale", self.scope_autoscale, "neutral"),
                    ("Clear", self.scope_clear, "neutral"),
                ],
                "neutral",
            ),
            (
                "截圖工具",
                "示波器截圖工具",
                [
                    ("手動截圖", self.scope_capture_now, "accent"),
                    ("選擇路徑", self.pick_capture_path, "neutral"),
                    ("開啟資料夾", self.open_capture_path, "neutral"),
                ],
                "accent",
            ),
        ]
        for idx, (label, panel_title, actions, kind) in enumerate(groups):
            row = 11 + idx // 2
            col = idx % 2
            self._make_action_group(capture, label, panel_title, actions, kind=kind).grid(
                row=row,
                column=col,
                sticky="ew",
                padx=(0, 6) if col == 0 else (6, 0),
                pady=(0, 8),
            )

    def _build_generator_panel(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

        connection = ttk.LabelFrame(parent, text="33250A 連線", style="Section.TLabelframe", padding=16)
        connection.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 12))
        for col in range(2):
            connection.columnconfigure(col, weight=1)

        ttk.Label(connection, text="模式", style="Modern.TLabel").grid(row=0, column=0, sticky="w")
        gen_mode_combo = ttk.Combobox(
            connection,
            textvariable=self.gen_mode_var,
            values=["visa", "serial", "tcp"],
            state="readonly",
            style="Modern.TCombobox",
        )
        gen_mode_combo.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 10))
        gen_mode_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_generator_mode_change())

        ttk.Label(connection, text="Timeout (s)", style="Modern.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Entry(connection, textvariable=self.gen_timeout_var, style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", pady=(4, 10)
        )

        self.gen_visa_section = tk.Frame(connection, bg=self.colors["surface"])
        self.gen_visa_section.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.gen_visa_section.columnconfigure(0, weight=1)
        self.gen_resource_label = ttk.Label(self.gen_visa_section, text="VISA Resource", style="Modern.TLabel")
        self.gen_resource_label.grid(row=0, column=0, sticky="w")
        self.gen_resource_entry = ttk.Entry(self.gen_visa_section, textvariable=self.gen_resource_var, style="Modern.TEntry")
        self.gen_resource_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        self.gen_serial_section = tk.Frame(connection, bg=self.colors["surface"])
        self.gen_serial_section.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.gen_serial_section.columnconfigure(0, weight=1)
        self.gen_serial_section.columnconfigure(1, weight=1)
        ttk.Label(self.gen_serial_section, text="Serial Port", style="Modern.TLabel").grid(row=0, column=0, sticky="w")
        self.gen_port_combo = ttk.Combobox(
            self.gen_serial_section,
            textvariable=self.gen_port_var,
            state="readonly",
            style="Modern.TCombobox",
        )
        self.gen_port_combo.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
        ttk.Label(self.gen_serial_section, text="Baudrate", style="Modern.TLabel").grid(row=0, column=1, sticky="w")
        self.gen_baudrate_entry = ttk.Entry(
            self.gen_serial_section,
            textvariable=self.gen_baudrate_var,
            style="Modern.TEntry",
        )
        self.gen_baudrate_entry.grid(row=1, column=1, sticky="ew", pady=(4, 0))
        ttk.Label(self.gen_serial_section, text="Handshake", style="Modern.TLabel").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        self.gen_handshake_combo = ttk.Combobox(
            self.gen_serial_section,
            textvariable=self.gen_handshake_var,
            values=["none", "dsrdtr", "rtscts", "xonxoff"],
            state="readonly",
            style="Modern.TCombobox",
        )
        self.gen_handshake_combo.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
        self.gen_port_entry = self.gen_port_combo

        self.gen_tcp_section = tk.Frame(connection, bg=self.colors["surface"])
        self.gen_tcp_section.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.gen_tcp_section.columnconfigure(0, weight=1)
        self.gen_tcp_section.columnconfigure(1, weight=1)
        self.gen_host_label = ttk.Label(self.gen_tcp_section, text="33250A / TCP轉接器 IP", style="Modern.TLabel")
        self.gen_host_label.grid(row=0, column=0, sticky="w")
        self.gen_host_entry = ttk.Entry(self.gen_tcp_section, textvariable=self.gen_host_var, style="Modern.TEntry")
        self.gen_host_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
        self.gen_tcp_port_label = ttk.Label(self.gen_tcp_section, text="TCP Port", style="Modern.TLabel")
        self.gen_tcp_port_label.grid(row=0, column=1, sticky="w")
        self.gen_tcp_port_entry = ttk.Entry(self.gen_tcp_section, textvariable=self.gen_tcp_port_var, style="Modern.TEntry")
        self.gen_tcp_port_entry.grid(row=1, column=1, sticky="ew", pady=(4, 0))

        self.gen_tcp_info_section = tk.Frame(connection, bg=self.colors["surface"])
        self.gen_tcp_info_section.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.gen_tcp_info_section.columnconfigure(0, weight=1)
        self.gen_tcp_info_section.columnconfigure(1, weight=0)
        self.gen_local_ip_hint = ttk.Label(
            self.gen_tcp_info_section,
            textvariable=self.gen_local_ip_var,
            style="Hint.TLabel",
            wraplength=320,
        )
        ttk.Label(
            self.gen_tcp_info_section,
            text="本機網卡 IPv4 (僅顯示，不會回填上方)",
            style="Modern.TLabel",
        ).grid(row=0, column=0, sticky="w", columnspan=2)
        self.gen_local_ip_hint.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        self._make_button(
            self.gen_tcp_info_section,
            "偵測本機 IP",
            self.refresh_generator_local_ip,
            kind="neutral",
        ).grid(row=1, column=1, sticky="e", pady=(4, 0))

        ttk.Label(connection, text="狀態", style="Modern.TLabel").grid(row=10, column=0, sticky="w")
        ttk.Label(connection, textvariable=self.generator_connection_var, style="Hint.TLabel", wraplength=420).grid(
            row=11, column=0, columnspan=2, sticky="w", pady=(4, 10)
        )

        connection_buttons = tk.Frame(connection, bg=self.colors["surface"])
        connection_buttons.grid(row=12, column=0, columnspan=2, sticky="ew")
        for col in range(2):
            connection_buttons.columnconfigure(col, weight=1)
        self._make_action_group(
            connection_buttons,
            "連線工具",
            "33250A 連線工具",
            [
                ("刷新 Serial", self.generator_refresh_ports, "neutral"),
                ("列出 VISA", self.generator_list_resources, "neutral"),
                ("連接", self.connect_generator, "accent"),
                ("中斷", self.disconnect_generator, "neutral"),
            ],
            kind="accent",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._make_action_group(
            connection_buttons,
            "診斷工具",
            "33250A 診斷工具",
            [
                ("Identify", self.generator_identify, "neutral"),
                ("讀取錯誤", self.generator_read_error, "neutral"),
            ],
            kind="neutral",
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        waveform = ttk.LabelFrame(parent, text="波形參數", style="Section.TLabelframe", padding=16)
        waveform.grid(row=0, column=1, sticky="nsew", pady=(0, 12))
        for col in range(2):
            waveform.columnconfigure(col, weight=1)

        ttk.Label(waveform, text="Function", style="Modern.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(waveform, textvariable=self.gen_function_var, style="Modern.TEntry").grid(
            row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 10)
        )
        ttk.Label(waveform, text="Frequency (Hz)", style="Modern.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Entry(waveform, textvariable=self.gen_frequency_var, style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", pady=(4, 10)
        )

        ttk.Label(waveform, text="Amplitude (Vpp)", style="Modern.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Entry(waveform, textvariable=self.gen_amplitude_var, style="Modern.TEntry").grid(
            row=3, column=0, sticky="ew", padx=(0, 8), pady=(4, 10)
        )
        ttk.Label(waveform, text="Offset (V)", style="Modern.TLabel").grid(row=2, column=1, sticky="w")
        ttk.Entry(waveform, textvariable=self.gen_offset_var, style="Modern.TEntry").grid(
            row=3, column=1, sticky="ew", pady=(4, 10)
        )

        ttk.Label(waveform, text="Trigger Source", style="Modern.TLabel").grid(row=4, column=0, sticky="w")
        ttk.Combobox(
            waveform,
            textvariable=self.gen_trigger_source_var,
            values=["IMM", "EXT", "BUS"],
            state="readonly",
            style="Modern.TCombobox",
        ).grid(row=5, column=0, sticky="ew", padx=(0, 8), pady=(4, 10))

        waveform_buttons = tk.Frame(waveform, bg=self.colors["surface"])
        waveform_buttons.grid(row=6, column=0, columnspan=2, sticky="ew")
        for col in range(2):
            waveform_buttons.columnconfigure(col, weight=1)
        self._make_action_group(
            waveform_buttons,
            "套用與觸發",
            "33250A 套用與觸發",
            [
                ("套用參數", self.generator_apply, "accent"),
                ("送出 Trigger", self.generator_trigger, "neutral"),
            ],
            kind="accent",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._make_action_group(
            waveform_buttons,
            "輸出控制",
            "33250A 輸出控制",
            [
                ("Output ON", self.generator_output_on, "accent"),
                ("Output OFF", self.generator_output_off, "danger"),
            ],
            kind="neutral",
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _build_automation_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

        monitor = ttk.LabelFrame(parent, text="Monitor 與記錄", style="Section.TLabelframe", padding=16)
        monitor.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 12))
        for col in range(2):
            monitor.columnconfigure(col, weight=1)
        ttk.Label(monitor, text="Interval (s)", style="Modern.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(monitor, textvariable=self.interval_var, style="Modern.TEntry").grid(
            row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 10)
        )
        ttk.Label(monitor, text="CSV 路徑", style="Modern.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Entry(monitor, textvariable=self.csv_var, style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", pady=(4, 10)
        )
        self._make_button(monitor, "選擇 CSV", self.pick_csv, kind="neutral").grid(
            row=2, column=0, sticky="ew", padx=(0, 6), pady=(0, 8)
        )
        self._make_button(monitor, "Start Monitor", self.start_monitor, kind="accent").grid(
            row=2, column=1, sticky="ew", padx=(6, 0), pady=(0, 8)
        )
        self._make_button(monitor, "Stop Monitor", self.stop_monitor, kind="neutral").grid(
            row=3, column=0, sticky="ew", padx=(0, 6), pady=(0, 8)
        )
        self._make_button(monitor, "刷新 Snapshot", self.refresh_snapshot, kind="neutral").grid(
            row=3, column=1, sticky="ew", padx=(6, 0), pady=(0, 8)
        )
        self._make_button(monitor, "讀取 Sync", self.read_sync_once, kind="neutral").grid(
            row=4, column=0, sticky="ew", padx=(0, 6)
        )
        self._make_button(monitor, "Reset + 讀取", self.reset_and_read_sync, kind="neutral").grid(
            row=4, column=1, sticky="ew", padx=(6, 0)
        )

        pulse = ttk.LabelFrame(parent, text="Pulse Capture", style="Section.TLabelframe", padding=16)
        pulse.grid(row=0, column=1, sticky="nsew", pady=(0, 12))
        for col in range(2):
            pulse.columnconfigure(col, weight=1)
        ttk.Label(pulse, text="Pulse Count", style="Modern.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(pulse, textvariable=self.count_var, style="Modern.TEntry").grid(
            row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 10)
        )
        ttk.Label(pulse, text="Capture Timeout (s)", style="Modern.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Entry(pulse, textvariable=self.capture_timeout_var, style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", pady=(4, 10)
        )
        ttk.Label(pulse, text="Capture 路徑", style="Modern.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Entry(pulse, textvariable=self.capture_path_var, style="Modern.TEntry").grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(4, 10)
        )
        ttk.Label(pulse, text="最後截圖提前量", style="Modern.TLabel").grid(row=4, column=0, sticky="w")
        ttk.Entry(pulse, textvariable=self.final_single_lead_var, style="Modern.TEntry").grid(
            row=5, column=0, sticky="ew", padx=(0, 8), pady=(4, 10)
        )
        tk.Label(
            pulse,
            text="剩幾發時切回 SINGLE 等最後一發。建議先從 2 開始試。",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            justify="left",
            anchor="nw",
            wraplength=420,
        ).grid(row=5, column=1, sticky="w", pady=(4, 10))
        ttk.Label(pulse, text="Trigger後截圖等待 (s)", style="Modern.TLabel").grid(row=6, column=0, sticky="w")
        ttk.Entry(pulse, textvariable=self.capture_render_delay_var, style="Modern.TEntry").grid(
            row=7, column=0, sticky="ew", padx=(0, 8), pady=(4, 10)
        )
        tk.Label(
            pulse,
            text="trigger 發生後再多等多久才截圖；如果還是太快，可以先試 0.8 或 1.0。",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            justify="left",
            anchor="nw",
            wraplength=420,
        ).grid(row=7, column=1, sticky="w", pady=(4, 10))
        self._make_button(pulse, "選擇路徑", self.pick_capture_path, kind="neutral").grid(
            row=8, column=0, sticky="ew", padx=(0, 6), pady=(0, 8)
        )
        self._make_button(pulse, "Pulse 擷取", self.run_pulse_capture, kind="accent").grid(
            row=8, column=1, sticky="ew", padx=(6, 0), pady=(0, 8)
        )
        self._make_button(pulse, "開啟輸出位置", self.open_capture_path, kind="neutral").grid(
            row=9, column=0, columnspan=2, sticky="ew"
        )

        guide = self._surface_card(parent, row=1, column=0, columnspan=2, padx=(0, 0), pady=(0, 12))
        guide.columnconfigure(0, weight=1)
        self._card_title(guide, "Bring-up 建議流程", "把操作步驟收進同一頁")
        tk.Label(
            guide,
            text=(
                "1. MCU 先確認 COM Port 與 Snapshot 正常\n"
                "2. Scope 先跑 Identify、設定 Trigger，再用 Preset + Single 驗證\n"
                "3. 33250A 套用波形參數並確認 Sync 觸發來源\n"
                "4. Start Monitor 觀察 SYNC_COUNT 的變化\n"
                "5. 最後做 Pulse 擷取，保留 first / last 的畫面"
            ),
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            justify="left",
            anchor="nw",
            wraplength=880,
        ).grid(row=1, column=0, sticky="ew", pady=(8, 12))
        guide_actions = tk.Frame(guide, bg=self.colors["surface"])
        guide_actions.grid(row=2, column=0, sticky="w")
        self._make_button(guide_actions, "複製 CLI 指令", self.copy_bench_commands, kind="neutral").grid(
            row=0, column=0, padx=(0, 8)
        )
        self._make_button(guide_actions, "打開 Preset 管理", self.open_preset_manager, kind="neutral").grid(
            row=0, column=1
        )

    def _build_logs_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        frame = ttk.LabelFrame(parent, text="操作記錄", style="Section.TLabelframe", padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.log_text_font = tkfont.Font(family="Consolas", size=11)
        self.log_text = tk.Text(
            frame,
            wrap="word",
            height=18,
            font=self.log_text_font,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="flat",
            padx=12,
            pady=12,
            insertbackground=self.colors["ink"],
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        buttons = tk.Frame(frame, bg=self.colors["surface"])
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        buttons.columnconfigure(2, weight=1)
        buttons.columnconfigure(3, weight=1)
        self._make_button(buttons, "清空 Log", self.clear_log, kind="neutral").grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        self._make_button(buttons, "儲存 Log", self.save_log, kind="neutral").grid(
            row=0, column=1, sticky="ew", padx=6
        )
        self._make_button(buttons, "匯出 JSON", self.export_current_config, kind="neutral").grid(
            row=0, column=2, sticky="ew", padx=6
        )
        self._make_button(buttons, "開啟設定", self.open_settings_dialog, kind="accent").grid(
            row=0, column=3, sticky="ew", padx=(6, 0)
        )

    def _build_help_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

        intro = self._surface_card(parent, row=0, column=0, columnspan=2, pady=(0, 14))
        intro.columnconfigure(0, weight=1)
        self._card_title(intro, "操作說明", "把 bench bring-up、量測與手動替代流程放在同一頁")
        tk.Label(
            intro,
            text=(
                "這個頁面給現場操作時快速查閱：先看標準流程，再依照你現在有沒有連 33250A "
                "選擇對應步驟。原則上 MCU 與示波器的操作不變，差別主要在誰負責出脈衝、"
                "誰負責送 trigger、以及流程能不能完全自動化。"
            ),
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            justify="left",
            anchor="nw",
            wraplength=920,
            font=("Segoe UI", 11),
        ).grid(row=1, column=0, sticky="ew", pady=(10, 0))

        standard = self._surface_card(parent, row=1, column=0, padx=(0, 8), pady=(0, 14))
        standard.columnconfigure(0, weight=1)
        self._card_title(standard, "標準流程", "有接 MCU、Scope、33250A 時")
        tk.Label(
            standard,
            text=(
                "1. 在 MCU 分頁確認 COM Port、連線，先做 Snapshot / Bench Check。\n"
                "2. 在示波器分頁確認連線、Identify，先套用 Trigger 與擷取設定。\n"
                "3. 在 33250A 分頁確認連線，套用波形參數，必要時開啟 Output。\n"
                "4. 到自動化流程分頁啟動 Start Monitor，觀察 SYNC_COUNT 是否穩定。\n"
                "5. 依需求執行 Pulse 擷取，或在 MCU 分頁做 Precharge、Arm、Start。"
            ),
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            justify="left",
            anchor="nw",
            wraplength=420,
            font=("Segoe UI", 11),
        ).grid(row=1, column=0, sticky="ew", pady=(10, 0))

        manual = self._surface_card(parent, row=1, column=1, padx=(8, 0), pady=(0, 14))
        manual.columnconfigure(0, weight=1)
        self._card_title(manual, "沒有 33250A 時", "改成外部手動給訊號")
        tk.Label(
            manual,
            text=(
                "1. MCU 連線、Snapshot、Bench Check 的操作一樣。\n"
                "2. 示波器連線與 Trigger 設定一樣，但要確認觸發來源對應你的手動訊號路徑。\n"
                "3. 不需要執行 33250A 的連接、套用參數、Output ON/OFF、送出 Trigger。\n"
                "4. 需要由你或外部設備在正確時機手動給 pulse / trigger。\n"
                "5. 若要做 Pulse 擷取，示波器要先進入正確等待狀態，再手動送訊號。"
            ),
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            justify="left",
            anchor="nw",
            wraplength=420,
            font=("Segoe UI", 11),
        ).grid(row=1, column=0, sticky="ew", pady=(10, 0))

        diff = self._surface_card(parent, row=2, column=0, columnspan=2, pady=(0, 14))
        diff.columnconfigure(0, weight=1)
        self._card_title(diff, "差異整理", "手動訊號模式和 33250A 自動模式的不同")
        tk.Label(
            diff,
            text=(
                "相同的部分：MCU 連線、Snapshot、Bench Check、Scope 擷取、Monitor 與 Log 紀錄都可以照常使用。\n\n"
                "不同的部分：\n"
                "• 有 33250A 時，GUI 可以幫你集中設定波形、控制輸出、送 trigger，重複性比較高。\n"
                "• 沒有 33250A 時，GUI 不會替你發波或送 trigger，脈衝時序要由外部手動控制。\n"
                "• 手動模式下，若示波器還沒進入等待狀態就先送訊號，容易漏抓；建議先 Single / Run 就緒再送。\n"
                "• 若 MCU 流程需要和外部 pulse 對時，手動模式要特別注意 Precharge、Arm、Start 的先後順序。"
            ),
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            justify="left",
            anchor="nw",
            wraplength=920,
            font=("Segoe UI", 11),
        ).grid(row=1, column=0, sticky="ew", pady=(10, 0))

        actions = tk.Frame(diff, bg=self.colors["surface"])
        actions.grid(row=2, column=0, sticky="w", pady=(12, 0))
        self._make_button(actions, "開啟設定", self.open_settings_dialog, kind="accent").grid(
            row=0, column=0, padx=(0, 8)
        )
        self._make_button(actions, "Preset 管理", self.open_preset_manager, kind="neutral").grid(
            row=0, column=1, padx=(0, 8)
        )
        self._make_button(actions, "匯出 JSON", self.export_current_config, kind="neutral").grid(
            row=0, column=2
        )

    def _create_scrollable_tab(self, notebook: ttk.Notebook, title: str) -> ttk.Frame:
        host = ttk.Frame(notebook, style="App.TFrame", padding=(4, 4, 4, 4))
        host.columnconfigure(0, weight=1)
        host.rowconfigure(0, weight=1)

        canvas = tk.Canvas(host, highlightthickness=0, borderwidth=0, bg=self.colors["bg"])
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(host, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        content = ttk.Frame(canvas, style="App.TFrame")
        content.columnconfigure(0, weight=1)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        content._scroll_canvas_ref = canvas  # type: ignore[attr-defined]
        content.bind(
            "<Configure>",
            lambda _event, current_canvas=canvas: self._update_canvas_scroll_region(current_canvas),
            add="+",
        )
        canvas.bind(
            "<Configure>",
            lambda event, current_canvas=canvas, current_window=window_id: self._resize_canvas_content(
                current_canvas, current_window, event
            ),
            add="+",
        )

        self._tab_canvases.append(canvas)
        notebook.add(host, text=title)
        return content

    def _surface_card(
        self,
        parent: tk.Misc,
        row: int,
        column: int,
        columnspan: int = 1,
        padx: tuple[int, int] = (0, 0),
        pady: tuple[int, int] = (0, 0),
    ) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=self.colors["surface"],
            padx=18,
            pady=18,
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        card.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=padx, pady=pady)
        return card

    def _sidebar_card(self, parent: tk.Frame, title: str, subtitle: str) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=self.colors["surface"],
            padx=14,
            pady=14,
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        row = parent.grid_size()[1]
        card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        card.columnconfigure(0, weight=1)
        tk.Label(
            card,
            text=title,
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            font=("Segoe UI Semibold", 13),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            card,
            text=subtitle,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))
        inner = tk.Frame(card, bg=self.colors["surface"])
        inner.grid(row=2, column=0, sticky="ew")
        inner.columnconfigure(0, weight=1)
        return inner

    def _metric_card(self, parent: tk.Misc, title: str, value_var: tk.StringVar, row: int, column: int) -> None:
        card = tk.Frame(
            parent,
            bg=self.colors["surface"],
            padx=18,
            pady=18,
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        card.grid(row=row, column=column, sticky="nsew", padx=(0, 12) if column == 0 else (0, 0), pady=(0, 12))
        card.columnconfigure(0, weight=1)
        tk.Label(
            card,
            text=title,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI Semibold", 11),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            card,
            textvariable=value_var,
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            font=("Segoe UI Semibold", 15),
            justify="left",
            anchor="nw",
            wraplength=300,
        ).grid(row=1, column=0, sticky="ew", pady=(10, 0))

    def _status_mini_card(self, parent: tk.Misc, title: str, value_var: tk.StringVar, column: int) -> None:
        frame = tk.Frame(parent, bg=self.colors["surface_alt"], padx=12, pady=12)
        frame.grid(row=0, column=column, sticky="nsew", padx=(0, 10) if column < 3 else (0, 0))
        frame.columnconfigure(0, weight=1)
        tk.Label(
            frame,
            text=title,
            bg=self.colors["surface_alt"],
            fg=self.colors["muted"],
            font=("Segoe UI Semibold", 10),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            frame,
            textvariable=value_var,
            bg=self.colors["surface_alt"],
            fg=self.colors["ink"],
            font=("Segoe UI Semibold", 11),
            justify="left",
            anchor="nw",
            wraplength=170,
        ).grid(row=1, column=0, sticky="ew", pady=(6, 0))

    def _card_title(self, parent: tk.Misc, title: str, subtitle: str) -> None:
        tk.Label(
            parent,
            text=title,
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            font=("Segoe UI Semibold", 15),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            parent,
            text=subtitle,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
        ).grid(row=0, column=1, sticky="e")

    def _build_connection_chip(self, parent: tk.Frame, label: str, key: str, row: int) -> None:
        row_frame = tk.Frame(parent, bg=self.colors["surface"])
        row_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10 if row < 2 else 0))
        row_frame.columnconfigure(1, weight=1)

        badge = tk.Label(
            row_frame,
            text="未連線",
            bg=self.colors["chip_idle"],
            fg=self.colors["chip_text"],
            padx=10,
            pady=5,
            font=("Segoe UI Semibold", 10),
        )
        badge.grid(row=0, column=0, sticky="w")
        detail = tk.Label(
            row_frame,
            text=label,
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            anchor="w",
            justify="left",
            wraplength=155,
        )
        detail.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        self.connection_badges[key] = badge
        self.connection_details[key] = detail

    def _build_runtime_tags(self, parent: tk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        tags_frame = tk.Frame(parent, bg=self.colors["surface"])
        tags_frame.grid(row=0, column=0, sticky="ew")
        for col in range(2):
            tags_frame.columnconfigure(col, weight=1)

        specs = [
            ("MONITOR", 0, 0),
            ("PULSE_CAPTURE", 0, 1),
            ("MCU", 1, 0),
            ("SCOPE", 1, 1),
            ("GENERATOR", 2, 0),
        ]
        for name, row, col in specs:
            tag = tk.Label(
                tags_frame,
                text=f"{name}=OFF",
                bg=self.colors["chip_idle"],
                fg=self.colors["chip_text"],
                padx=10,
                pady=7,
                font=("Consolas", 9, "bold"),
                anchor="center",
            )
            tag.grid(
                row=row,
                column=col,
                sticky="ew",
                padx=(0, 6) if col == 0 else (6, 0),
                pady=(0, 8) if row < 2 else (0, 0),
            )
            self.runtime_tag_labels[name] = tag
        self._refresh_runtime_tags()

    def _set_runtime_tag(self, name: str, enabled: bool) -> None:
        tag = self.runtime_tag_labels.get(name)
        if tag is None:
            return
        if enabled:
            tag.configure(
                text=f"{name}=ON",
                bg=self.colors["accent_soft"],
                fg=self.colors["accent_active"],
            )
        else:
            tag.configure(
                text=f"{name}=OFF",
                bg=self.colors["chip_idle"],
                fg=self.colors["chip_text"],
            )

    def _refresh_runtime_tags(self) -> None:
        self._set_runtime_tag("MONITOR", self.monitor_active)
        self._set_runtime_tag("PULSE_CAPTURE", self.pulse_capture_active)
        self._set_runtime_tag("MCU", self.client is not None)
        self._set_runtime_tag("SCOPE", self.scope_client is not None)
        self._set_runtime_tag("GENERATOR", self.generator_client is not None)
        self._update_run_action_state()

    def _set_embedded_button_enabled(self, container: tk.Frame | None, enabled: bool) -> None:
        if container is None:
            return
        button = getattr(container, "_button_widget", None)
        if isinstance(button, tk.Button):
            button.configure(state="normal" if enabled else "disabled")

    def _update_run_action_state(self) -> None:
        self._set_embedded_button_enabled(self.quick_start_button, not self.pulse_capture_active)
        self._set_embedded_button_enabled(self.quick_stop_button, self.pulse_capture_active)

    def _set_run_state(self, text: str) -> None:
        self.run_state_var.set(text)

    def _widget_background(self, widget: tk.Misc, fallback: str) -> str:
        for option in ("bg", "background"):
            try:
                value = str(widget.cget(option))
            except tk.TclError:
                continue
            if value:
                return value
        return fallback

    def _default_button_help(self, text: str) -> str:
        help_map = {
            "設定彈窗": "打開整體設定視窗，集中調整 MCU、Scope、33250A 與 session 參數。",
            "Preset 管理": "管理個人 Preset，可套用、覆寫、刪除目前保存的參數組。",
            "匯入 JSON": "從 JSON 載入一組現成設定，快速還原工作環境。",
            "匯出 JSON": "把目前畫面上的參數匯出成 JSON，方便備份或分享。",
            "套用": "將目前選到的 Preset 套用到整個工作台。",
            "另存目前": "把目前畫面上的參數另存成新的 Preset。",
            "連接 MCU": "依照左側或 MCU 分頁中的 COM 參數連接控制板。",
            "刷新 Snapshot": "重新讀取 MCU 的 STATUS、FAULT、COUNT 與 SYNC_COUNT。",
            "Bench Check": "一次檢查 PING 與主要狀態值，快速確認 bench 是否 ready。",
            "Start Monitor": "開始定時輪詢 MCU 狀態，必要時同步寫入 CSV。",
            "Arm": "讓 MCU 進入待發脈衝狀態，準備開始 pulse run。",
            "Start Run": "快捷流程：先啟動 Monitor，再執行 Pulse 擷取，於 pulse 開始與結束自動截圖。",
            "刷新 Ports": "重新掃描目前可用的序列埠清單。",
            "連接": "依照目前欄位參數連接設備。",
            "中斷": "中斷目前設備連線，但保留畫面上的參數。",
            "PING": "送出 PING 指令，確認 MCU 命令通道是否正常。",
            "Snapshot": "立即讀取一次 MCU 的完整快照資訊。",
            "Reset Sync": "將 MCU 內部的 SYNC_COUNT 歸零。",
            "Precharge": "送出預充電命令，進入正式 pulse 前的準備狀態。",
            "Start": "依照 Pulse Count 參數開始執行脈衝流程。",
            "Stop": "要求設備停止目前運行中的流程。",
            "Discharge": "執行放電流程，讓系統回到較安全的狀態。",
            "Reset Fault": "清除 MCU 目前記錄的 fault 狀態。",
            "列出 VISA": "搜尋目前系統看得到的 VISA 儀器資源。",
            "選第一個": "直接帶入第一個可用的 VISA resource，方便快速測試。",
            "Identify": "送出識別命令，確認目前連到的設備型號。",
            "Preset + Single": "將示波器套用預設 trigger 後切到單次擷取。",
            "Apply Trigger": "依照目前 trigger source、level、sweep 與 timebase 套用設定。",
            "Run": "讓示波器進入連續擷取模式。",
            "Single": "讓示波器只等待並擷取一次波形。",
            "Autoscale": "請示波器自動調整顯示比例。",
            "Clear": "清除示波器當前畫面或殘留顯示。",
            "手動截圖": "立即把示波器畫面存成 PNG 截圖。",
            "選擇路徑": "選擇截圖或輸出檔案要存放的位置。",
            "開啟資料夾": "打開目前截圖輸出位置，方便直接查看剛存好的檔案。",
            "刷新 Serial": "重新掃描 33250A 可用的序列埠。",
            "讀取錯誤": "向 33250A 查詢最近一次 SCPI 錯誤訊息。",
            "套用參數": "把目前 33250A 的波形與觸發參數送到儀器。",
            "送出 Trigger": "手動送出一次 trigger 命令給 33250A。",
            "Output ON": "開啟 33250A 的輸出。",
            "Output OFF": "關閉 33250A 的輸出。",
            "選擇 CSV": "選擇 Monitor 記錄要寫入的 CSV 路徑。",
            "讀取 Sync": "單次讀取 MCU 的 SYNC_COUNT 數值。",
            "Reset + 讀取": "先清零 SYNC_COUNT，再立刻讀回目前數值。",
            "Pulse 擷取": "自動完成 first/last 截圖與 pulse 運行監看。",
            "開啟輸出位置": "直接開啟目前截圖或輸出資料所在的資料夾。",
            "複製 CLI 指令": "把常用的 bench CLI 指令複製到剪貼簿。",
            "新增目前設定": "把目前畫面上的參數新增成一筆 Preset。",
            "套用選取": "套用 Preset 管理器裡目前選中的設定。",
            "以目前覆寫": "用當前畫面參數覆蓋已選 Preset。",
            "刪除": "刪除目前選中的 Preset。",
            "關閉": "關閉目前視窗，不會刪掉已儲存的內容。",
            "儲存": "確認儲存這次編輯的內容。",
            "清空 Log": "清除目前操作記錄區的文字。",
            "儲存 Log": "把目前操作記錄匯出成文字檔。",
            "開啟設定": "打開 Session Settings 視窗調整整體參數。",
        }
        help_map["偵測本機 IP"] = "偵測這台電腦目前的網卡 IPv4；這只是本機位址，不會自動填到上方的 33250A 目標 IP。"
        if text in help_map:
            return help_map[text]
        return f"執行「{text}」這個操作。"

    def _schedule_tooltip(self, widget: tk.Misc, text: str) -> None:
        self._hide_tooltip()
        self.tooltip_widget = widget
        self.tooltip_job = self.root.after(350, lambda current=widget, message=text: self._show_tooltip(current, message))

    def _show_tooltip(self, widget: tk.Misc, text: str) -> None:
        self.tooltip_job = None
        if not widget.winfo_exists():
            return
        self._hide_tooltip()
        tooltip = tk.Toplevel(self.root)
        self.tooltip_window = tooltip
        tooltip.wm_overrideredirect(True)
        tooltip.attributes("-topmost", True)
        tooltip.configure(bg=self.colors["ink"])

        label = tk.Label(
            tooltip,
            text=text,
            bg=self.colors["ink"],
            fg="white",
            justify="left",
            padx=10,
            pady=8,
            wraplength=260,
            font=("Segoe UI", 9),
        )
        label.pack()

        tooltip.update_idletasks()
        tooltip_width = tooltip.winfo_reqwidth()
        tooltip_height = tooltip.winfo_reqheight()

        screen_left = 8
        screen_top = 8
        screen_right = self.root.winfo_screenwidth() - 8
        screen_bottom = self.root.winfo_screenheight() - 8

        root_left = self.root.winfo_rootx() + 8
        root_top = self.root.winfo_rooty() + 8
        root_right = self.root.winfo_rootx() + self.root.winfo_width() - 8
        root_bottom = self.root.winfo_rooty() + self.root.winfo_height() - 8

        x = widget.winfo_rootx() + max(8, widget.winfo_width() // 2)
        y = widget.winfo_rooty() + widget.winfo_height() + 10

        if x + tooltip_width > root_right:
            x = widget.winfo_rootx() + widget.winfo_width() - tooltip_width
        if x + tooltip_width > screen_right:
            x = screen_right - tooltip_width
        x = max(screen_left, min(x, max(screen_left, root_right - tooltip_width)))

        if y + tooltip_height > root_bottom:
            y = widget.winfo_rooty() - tooltip_height - 10
        if y + tooltip_height > screen_bottom:
            y = screen_bottom - tooltip_height
        y = max(screen_top, min(y, max(screen_top, root_bottom - tooltip_height)))

        x = max(screen_left, x)
        y = max(screen_top, y)
        tooltip.wm_geometry(f"+{x}+{y}")

    def _hide_tooltip(self) -> None:
        if self.tooltip_job is not None:
            self.root.after_cancel(self.tooltip_job)
            self.tooltip_job = None
        if self.tooltip_window is not None:
            self.tooltip_window.destroy()
            self.tooltip_window = None
        self.tooltip_widget = None

    def _bind_tooltip(self, widget: tk.Misc, text: str) -> None:
        widget.bind("<Enter>", lambda _event, current=widget, message=text: self._schedule_tooltip(current, message), add="+")
        widget.bind("<Leave>", lambda _event: self._hide_tooltip(), add="+")
        widget.bind("<ButtonPress>", lambda _event: self._hide_tooltip(), add="+")
        widget.bind("<Destroy>", lambda _event: self._hide_tooltip(), add="+")

    def _close_action_panel(self) -> None:
        if self.action_panel_window is not None and self.action_panel_window.winfo_exists():
            self.action_panel_window.destroy()
        self.action_panel_window = None
        self.action_panel_owner = None

    def _toggle_action_panel(
        self,
        owner: tk.Misc,
        title: str,
        actions: list[tuple[str, object, str] | tuple[str, object, str, str]],
        columns: int = 2,
    ) -> None:
        if self.action_panel_window is not None and self.action_panel_owner is owner:
            self._close_action_panel()
            return

        self._close_action_panel()

        panel = tk.Toplevel(self.root)
        self.action_panel_window = panel
        self.action_panel_owner = owner
        panel.wm_overrideredirect(True)
        panel.attributes("-topmost", True)
        panel.configure(bg=self.colors["border"])
        panel.bind("<FocusOut>", lambda _event: self._close_action_panel())
        panel.bind("<Escape>", lambda _event: self._close_action_panel())

        shell = tk.Frame(panel, bg=self.colors["surface"], padx=12, pady=12)
        shell.pack()
        shell.columnconfigure(0, weight=1)

        tk.Label(
            shell,
            text=title,
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            font=("Segoe UI Semibold", 11),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            shell,
            text="點選後會執行對應功能",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="w", pady=(2, 10))

        body = tk.Frame(shell, bg=self.colors["surface"])
        body.grid(row=2, column=0, sticky="ew")
        for col in range(columns):
            body.columnconfigure(col, weight=1)

        for idx, item in enumerate(actions):
            if len(item) == 4:
                label, command, kind, help_text = item
            else:
                label, command, kind = item
                help_text = None

            def run_then_close(current_command=command) -> None:
                self._close_action_panel()
                current_command()

            launcher = self._make_button(
                body,
                str(label),
                run_then_close,
                kind=str(kind),
                help_text=None if help_text is None else str(help_text),
            )
            row = idx // columns
            col = idx % columns
            launcher.grid(
                row=row,
                column=col,
                sticky="ew",
                padx=(0, 6) if col < columns - 1 else (0, 0),
                pady=(0, 8),
            )

        owner.update_idletasks()
        panel.update_idletasks()
        panel_width = panel.winfo_reqwidth()
        panel_height = panel.winfo_reqheight()

        screen_left = 8
        screen_top = 8
        screen_right = self.root.winfo_screenwidth() - 8
        screen_bottom = self.root.winfo_screenheight() - 8

        root_left = self.root.winfo_rootx() + 8
        root_top = self.root.winfo_rooty() + 8
        root_right = self.root.winfo_rootx() + self.root.winfo_width() - 8
        root_bottom = self.root.winfo_rooty() + self.root.winfo_height() - 8

        x = owner.winfo_rootx()
        y = owner.winfo_rooty() + owner.winfo_height() + 8

        if x + panel_width > root_right:
            x = owner.winfo_rootx() + owner.winfo_width() - panel_width
        if x + panel_width > screen_right:
            x = screen_right - panel_width
        x = max(screen_left, min(x, max(screen_left, root_right - panel_width)))

        if y + panel_height > root_bottom:
            y = owner.winfo_rooty() - panel_height - 8
        if y + panel_height > screen_bottom:
            y = screen_bottom - panel_height
        y = max(screen_top, min(y, max(screen_top, root_bottom - panel_height)))

        x = max(screen_left, x)
        y = max(screen_top, y)
        panel.wm_geometry(f"+{x}+{y}")
        panel.focus_force()

    def _make_action_group(
        self,
        parent: tk.Misc,
        text: str,
        panel_title: str,
        actions: list[tuple[str, object, str] | tuple[str, object, str, str]],
        kind: str = "neutral",
        help_text: str | None = None,
        columns: int = 2,
    ) -> tk.Frame:
        launcher = self._make_button(parent, text, lambda: None, kind=kind, help_text=help_text)
        primary_button = getattr(launcher, "_button_widget", None)
        if isinstance(primary_button, tk.Button):
            primary_button.configure(
                command=lambda current=launcher, title=panel_title, items=actions, cols=columns: self._toggle_action_panel(
                    current,
                    title,
                    items,
                    cols,
                )
            )
        return launcher

    def _make_button(
        self,
        parent: tk.Misc,
        text: str,
        command,
        kind: str = "neutral",
        help_text: str | None = None,
    ) -> tk.Frame:
        palette = {
            "accent": (self.colors["accent"], "white", self.colors["accent_active"], "#f3fffc"),
            "neutral": ("#e8edf5", self.colors["ink"], "#d6dee9", "#667085"),
            "danger": (self.colors["danger"], "white", self.colors["danger_active"], "#fff7f5"),
            "hero": ("#ffffff", self.colors["hero"], "#e8eef9", self.colors["hero"]),
            "hero_alt": (self.colors["hero_alt"], "white", "#244e82", "#eff6ff"),
        }
        bg, fg, active, disabled_fg = palette[kind]
        container_bg = self._widget_background(
            parent,
            self.colors["hero"] if kind in {"hero", "hero_alt"} else self.colors["surface"],
        )
        container = tk.Frame(parent, bg=container_bg, highlightthickness=0, bd=0)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=0)
        container.rowconfigure(0, weight=1)

        def run_button_command(current_text=text, current_command=command) -> None:
            self._current_button_action_label = str(current_text)
            self._current_button_action_failed = False
            try:
                current_command()
            except Exception as exc:
                self._show_toast("error", f"{current_text} 失敗", str(exc))
                self.append_log(f"{current_text}: UNHANDLED ERROR {exc}")
            else:
                if not self._current_button_action_failed:
                    self._show_toast("success", f"{current_text} 成功", "指令已送出。")
            finally:
                self._current_button_action_label = None

        button = tk.Button(
            container,
            text=text,
            command=run_button_command,
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground=fg,
            relief="flat",
            bd=0,
            padx=12,
            pady=9,
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
            highlightthickness=0,
            disabledforeground=disabled_fg,
        )
        button.grid(row=0, column=0, sticky="nsew")
        container._button_widget = button  # type: ignore[attr-defined]

        info_text = help_text or self._default_button_help(text)
        badge = tk.Label(
            container,
            text="?",
            bg=container_bg,
            fg=self.colors["accent_active"],
            font=("Segoe UI Semibold", 9),
            width=2,
            cursor="question_arrow",
            relief="flat",
            bd=0,
            padx=4,
        )
        badge.grid(row=0, column=1, sticky="ns", padx=(6, 0))

        self._bind_tooltip(button, info_text)
        self._bind_tooltip(badge, info_text)
        return container

    def _install_messagebox_hooks(self) -> None:
        self._original_messagebox_showerror = messagebox.showerror
        self._original_messagebox_showwarning = messagebox.showwarning
        self._original_messagebox_showinfo = messagebox.showinfo
        messagebox.showerror = self._messagebox_showerror  # type: ignore[assignment]
        messagebox.showwarning = self._messagebox_showwarning  # type: ignore[assignment]
        messagebox.showinfo = self._messagebox_showinfo  # type: ignore[assignment]

    def _messagebox_showerror(self, title: str | None = None, message: str | None = None, **kwargs):
        self._current_button_action_failed = True
        self._show_toast("error", title or "錯誤", message or "")
        return self._original_messagebox_showerror(title=title, message=message, **kwargs)

    def _messagebox_showwarning(self, title: str | None = None, message: str | None = None, **kwargs):
        self._current_button_action_failed = True
        self._show_toast("warning", title or "提醒", message or "")
        return self._original_messagebox_showwarning(title=title, message=message, **kwargs)

    def _messagebox_showinfo(self, title: str | None = None, message: str | None = None, **kwargs):
        self._show_toast("success", title or "完成", message or "")
        return self._original_messagebox_showinfo(title=title, message=message, **kwargs)

    def _show_toast(self, kind: str, title: str, message: str, duration_ms: int = 2200) -> None:
        palettes = {
            "success": ("#dcfce7", "#166534", "#bbf7d0"),
            "warning": ("#fef3c7", "#92400e", "#fde68a"),
            "error": ("#fee2e2", "#991b1b", "#fecaca"),
        }
        bg, fg, border = palettes.get(kind, palettes["success"])

        if self.toast_job is not None:
            self.root.after_cancel(self.toast_job)
            self.toast_job = None
        if self.toast_window is not None and self.toast_window.winfo_exists():
            self.toast_window.destroy()
            self.toast_window = None

        toast = tk.Toplevel(self.root)
        self.toast_window = toast
        toast.wm_overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=border)

        shell = tk.Frame(toast, bg=bg, padx=12, pady=10)
        shell.pack()
        tk.Label(
            shell,
            text=title,
            bg=bg,
            fg=fg,
            font=("Segoe UI Semibold", 10),
            anchor="w",
            justify="left",
        ).pack(anchor="w")
        tk.Label(
            shell,
            text=message or "操作已完成。",
            bg=bg,
            fg=fg,
            font=("Segoe UI", 9),
            wraplength=280,
            anchor="w",
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        toast.update_idletasks()
        x = self.root.winfo_rootx() + self.root.winfo_width() - toast.winfo_reqwidth() - 20
        y = self.root.winfo_rooty() + 20
        toast.wm_geometry(f"+{max(12, x)}+{max(12, y)}")
        self.toast_job = self.root.after(duration_ms, self._hide_toast)

    def _hide_toast(self) -> None:
        if self.toast_job is not None:
            self.root.after_cancel(self.toast_job)
            self.toast_job = None
        if self.toast_window is not None and self.toast_window.winfo_exists():
            self.toast_window.destroy()
        self.toast_window = None

    def _make_scope_channel_toggle(self, parent: tk.Misc, label: str, variable: tk.BooleanVar) -> tk.Checkbutton:
        return tk.Checkbutton(
            parent,
            text=label,
            variable=variable,
            onvalue=True,
            offvalue=False,
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            activebackground=self.colors["surface"],
            activeforeground=self.colors["ink"],
            selectcolor=self.colors["surface"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 10),
        )

    def _update_canvas_scroll_region(self, canvas: tk.Canvas) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _resize_canvas_content(self, canvas: tk.Canvas, window_id: int, event: tk.Event) -> None:
        canvas.itemconfigure(window_id, width=event.width)
        self._update_canvas_scroll_region(canvas)

    def _find_scroll_canvas(self, widget: tk.Misc | None) -> tk.Canvas | None:
        current = widget
        while current is not None:
            canvas = getattr(current, "_scroll_canvas_ref", None)
            if isinstance(canvas, tk.Canvas):
                return canvas
            current = current.master
        return None

    def _on_mousewheel(self, event: tk.Event) -> None:
        canvas = self._find_scroll_canvas(getattr(event, "widget", None))
        if canvas is None:
            return
        delta = getattr(event, "delta", 0)
        if delta == 0:
            return
        canvas.yview_scroll(int(-delta / 120), "units")

    def append_log(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{stamp}] {text}\n")
        self.log_text.see("end")

    def clear_log(self) -> None:
        self.log_text.delete("1.0", "end")
        self.append_log("Log 已清空。")

    def save_log(self) -> None:
        selected = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
        )
        if not selected:
            return
        Path(selected).write_text(self.log_text.get("1.0", "end-1c"), encoding="utf-8")
        self.append_log(f"Log 已儲存到 {selected}")
        self.last_output_var.set(f"Log 已匯出到 {selected}")

    def _update_connection_summary(self) -> None:
        self._set_chip("mcu", self.client is not None, self.connection_var.get())
        self._set_chip("scope", self.scope_client is not None, self.scope_connection_var.get())
        self._set_chip("generator", self.generator_client is not None, self.generator_connection_var.get())
        self._refresh_runtime_tags()

    def _set_chip(self, key: str, connected: bool, detail: str) -> None:
        badge = self.connection_badges.get(key)
        detail_label = self.connection_details.get(key)
        if badge is None or detail_label is None:
            return
        if connected:
            badge.configure(text="已連線", bg=self.colors["success_soft"], fg=self.colors["success"])
        else:
            badge.configure(text="未連線", bg=self.colors["chip_idle"], fg=self.colors["chip_text"])
        detail_label.configure(text=detail)

    def _on_scope_mode_change(self) -> None:
        mode = self.scope_mode_var.get().strip().lower()
        if mode == "usb":
            self.scope_host_label.configure(text="USB 模式")
            self.scope_host_entry.configure(state="disabled")
            self.scope_port_entry.configure(state="disabled")
            self.scope_resource_entry.configure(state="normal")
        else:
            self.scope_host_label.configure(text="IP")
            self.scope_host_entry.configure(state="normal")
            self.scope_port_entry.configure(state="normal")
            self.scope_resource_entry.configure(state="disabled")

    def _on_generator_mode_change(self) -> None:
        mode = self.gen_mode_var.get().strip().lower()
        if mode == "visa":
            self.gen_resource_label.configure(text="VISA Resource")
            self.gen_resource_entry.configure(state="normal")
            self.gen_visa_section.grid()
            self.gen_serial_section.grid_remove()
            self.gen_tcp_section.grid_remove()
            self.gen_tcp_info_section.grid_remove()
        elif mode == "serial":
            self.gen_visa_section.grid_remove()
            self.gen_serial_section.grid()
            self.gen_tcp_section.grid_remove()
            self.gen_tcp_info_section.grid_remove()
        else:
            self.gen_visa_section.grid_remove()
            self.gen_serial_section.grid_remove()
            self.gen_tcp_section.grid()
            self.gen_tcp_info_section.grid()
        if mode == "tcp":
            self.refresh_generator_local_ip()
        else:
            self.gen_local_ip_var.set("切換到 TCP 模式後可偵測")

    def _generator_target_ipv4(self) -> ipaddress.IPv4Address | None:
        target = self.gen_host_var.get().strip()
        try:
            parsed = ipaddress.ip_address(target)
        except ValueError:
            return None
        return parsed if isinstance(parsed, ipaddress.IPv4Address) else None

    def _generator_local_ipv4_candidates(self) -> list[str]:
        target_host = self.gen_host_var.get().strip() or "192.168.3.3"
        try:
            target_port = int(self.gen_tcp_port_var.get().strip() or "5000")
        except ValueError:
            target_port = 5000

        candidates: list[str] = []

        def collect(value: str | None) -> None:
            if not value:
                return
            try:
                parsed = ipaddress.ip_address(value)
            except ValueError:
                return
            if not isinstance(parsed, ipaddress.IPv4Address) or parsed.is_loopback:
                return
            normalized = str(parsed)
            if normalized not in candidates:
                candidates.append(normalized)

        def probe(host: str, port: int) -> None:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(0.5)
                    sock.connect((host, port))
                    collect(sock.getsockname()[0])
            except OSError:
                return

        probe(target_host, target_port)
        probe("8.8.8.8", 80)

        try:
            for value in socket.gethostbyname_ex(socket.gethostname())[2]:
                collect(value)
        except OSError:
            pass

        return candidates

    def _format_generator_local_ipv4(self, value: str) -> str:
        parsed = ipaddress.ip_address(value)
        if not isinstance(parsed, ipaddress.IPv4Address):
            return value

        target_ip = self._generator_target_ipv4()
        if target_ip is None:
            return f"{value} (link-local)" if parsed.is_link_local else value
        if str(target_ip) == value:
            return f"{value} (這是本機 IP，不是 33250A / TCP 轉接器位址)"

        target_prefix = ".".join(str(target_ip).split(".")[:3])
        same_subnet = value.split(".")[:3] == str(target_ip).split(".")[:3]
        if same_subnet:
            return f"{value} (與 {target_prefix}.x 同網段)"
        if parsed.is_link_local:
            return f"{value} (未進入 {target_prefix}.x 網段)"
        return f"{value} (與 {target_prefix}.x 不同網段)"

    def refresh_generator_local_ip(self, log_result: bool = False) -> None:
        mode = self.gen_mode_var.get().strip().lower()
        if mode != "tcp":
            self.gen_local_ip_detected = ""
            self.gen_local_ip_var.set("切換到 TCP 模式後可偵測")
            return

        candidates = self._generator_local_ipv4_candidates()
        if not candidates:
            self.gen_local_ip_detected = ""
            display = "未偵測到有效 IPv4"
        else:
            target_ip = self._generator_target_ipv4()

            def rank(value: str) -> tuple[int, int, int]:
                parsed = ipaddress.ip_address(value)
                same_subnet = 0
                if isinstance(target_ip, ipaddress.IPv4Address):
                    same_subnet = 1 if value.split(".")[:3] == str(target_ip).split(".")[:3] else 0
                return (
                    same_subnet,
                    0 if parsed.is_link_local else 1,
                    1 if parsed.is_private else 0,
                )

            best_ip = max(candidates, key=rank)
            self.gen_local_ip_detected = best_ip
            display = self._format_generator_local_ipv4(best_ip)

        self.gen_local_ip_var.set(display)
        if log_result:
            self.append_log(f"33250A local IPv4: {display}")

    def _load_session_state(self) -> None:
        if not SESSION_STATE_PATH.exists():
            self.append_log("未找到上次 session，使用預設值。")
            return
        try:
            payload = json.loads(SESSION_STATE_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            self.append_log(f"讀取 session 失敗: {exc}")
            return
        state = payload.get("state", payload)
        if isinstance(state, Mapping):
            self._apply_state(state)
        preset_name = str(payload.get("active_preset", "")).strip()
        if preset_name:
            self.active_preset_var.set(preset_name)
        self.append_log("已載入上次 session 設定。")

    def _save_session_state(self) -> None:
        APP_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "active_preset": self.active_preset_var.get().strip(),
            "state": self._collect_state(),
        }
        SESSION_STATE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_preset_library(self) -> None:
        if not PRESET_LIBRARY_PATH.exists():
            self.preset_library = {}
            return
        try:
            payload = json.loads(PRESET_LIBRARY_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            self.preset_library = {}
            self.append_log(f"讀取 preset 失敗: {exc}")
            return

        presets: dict[str, dict[str, Any]] = {}
        raw_items = payload.get("presets", payload)
        if isinstance(raw_items, list):
            for item in raw_items:
                if not isinstance(item, Mapping):
                    continue
                name = str(item.get("name", "")).strip()
                if not name:
                    continue
                presets[name] = {
                    "name": name,
                    "notes": str(item.get("notes", "")).strip(),
                    "updated_at": str(item.get("updated_at", "")).strip(),
                    "state": dict(item.get("state", {})),
                }
        elif isinstance(raw_items, Mapping):
            for name, state in raw_items.items():
                preset_name = str(name).strip()
                if not preset_name:
                    continue
                if isinstance(state, Mapping) and "state" in state:
                    presets[preset_name] = {
                        "name": preset_name,
                        "notes": str(state.get("notes", "")).strip(),
                        "updated_at": str(state.get("updated_at", "")).strip(),
                        "state": dict(state.get("state", {})),
                    }
                elif isinstance(state, Mapping):
                    presets[preset_name] = {
                        "name": preset_name,
                        "notes": "",
                        "updated_at": "",
                        "state": dict(state),
                    }
        self.preset_library = presets

    def _save_preset_library(self) -> None:
        APP_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "presets": [
                self.preset_library[name]
                for name in sorted(self.preset_library, key=str.casefold)
            ],
        }
        PRESET_LIBRARY_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _refresh_preset_combobox(self) -> None:
        names = sorted(self.preset_library, key=str.casefold)
        self.preset_combo["values"] = names
        current = self.active_preset_var.get().strip()
        if current and current not in names:
            self.active_preset_var.set("")
        if self.preset_tree is not None:
            self._refresh_preset_tree()

    def _collect_state(self) -> dict[str, str]:
        return {
            "config_path": self.config_path.get().strip(),
            "port": self.port_var.get().strip(),
            "baudrate": self.baudrate_var.get().strip(),
            "timeout_s": self.timeout_var.get().strip(),
            "count": self.count_var.get().strip(),
            "interval_s": self.interval_var.get().strip(),
            "csv_path": self.csv_var.get().strip(),
            "capture_timeout_s": self.capture_timeout_var.get().strip(),
            "capture_path": self.capture_path_var.get().strip(),
            "final_single_lead": self.final_single_lead_var.get().strip(),
            "capture_render_delay_s": self.capture_render_delay_var.get().strip(),
            "quick_run_use_generator": str(bool(self.quick_run_use_generator_var.get())).lower(),
            "scope_mode": self.scope_mode_var.get().strip(),
            "scope_host": self.scope_host_var.get().strip(),
            "scope_port": self.scope_port_var.get().strip(),
            "scope_timeout_s": self.scope_timeout_var.get().strip(),
            "scope_resource": self.scope_resource_var.get().strip(),
            "scope_trigger_source": self.scope_trigger_source_var.get().strip(),
            "scope_trigger_level": self.scope_trigger_level_var.get().strip(),
            "scope_trigger_sweep": self.scope_trigger_sweep_var.get().strip(),
            "scope_timebase": self.scope_timebase_var.get().strip(),
            "scope_ch1_enabled": str(bool(self.scope_ch1_enabled_var.get())).lower(),
            "scope_ch2_enabled": str(bool(self.scope_ch2_enabled_var.get())).lower(),
            "scope_ch3_enabled": str(bool(self.scope_ch3_enabled_var.get())).lower(),
            "scope_ch4_enabled": str(bool(self.scope_ch4_enabled_var.get())).lower(),
            "gen_mode": self.gen_mode_var.get().strip(),
            "gen_resource": self.gen_resource_var.get().strip(),
            "gen_port": self.gen_port_var.get().strip(),
            "gen_host": self.gen_host_var.get().strip(),
            "gen_tcp_port": self.gen_tcp_port_var.get().strip(),
            "gen_baudrate": self.gen_baudrate_var.get().strip(),
            "gen_handshake": self.gen_handshake_var.get().strip(),
            "gen_timeout_s": self.gen_timeout_var.get().strip(),
            "gen_function": self.gen_function_var.get().strip(),
            "gen_frequency_hz": self.gen_frequency_var.get().strip(),
            "gen_amplitude_vpp": self.gen_amplitude_var.get().strip(),
            "gen_offset_v": self.gen_offset_var.get().strip(),
            "gen_trigger_source": self.gen_trigger_source_var.get().strip(),
        }

    def _apply_state(self, state: Mapping[str, Any]) -> None:
        field_map: dict[str, tk.StringVar] = {
            "config_path": self.config_path,
            "port": self.port_var,
            "baudrate": self.baudrate_var,
            "timeout_s": self.timeout_var,
            "count": self.count_var,
            "interval_s": self.interval_var,
            "csv_path": self.csv_var,
            "capture_timeout_s": self.capture_timeout_var,
            "capture_path": self.capture_path_var,
            "final_single_lead": self.final_single_lead_var,
            "capture_render_delay_s": self.capture_render_delay_var,
            "scope_mode": self.scope_mode_var,
            "scope_host": self.scope_host_var,
            "scope_port": self.scope_port_var,
            "scope_timeout_s": self.scope_timeout_var,
            "scope_resource": self.scope_resource_var,
            "scope_trigger_source": self.scope_trigger_source_var,
            "scope_trigger_level": self.scope_trigger_level_var,
            "scope_trigger_sweep": self.scope_trigger_sweep_var,
            "scope_timebase": self.scope_timebase_var,
            "gen_mode": self.gen_mode_var,
            "gen_resource": self.gen_resource_var,
            "gen_port": self.gen_port_var,
            "gen_host": self.gen_host_var,
            "gen_tcp_port": self.gen_tcp_port_var,
            "gen_baudrate": self.gen_baudrate_var,
            "gen_handshake": self.gen_handshake_var,
            "gen_timeout_s": self.gen_timeout_var,
            "gen_function": self.gen_function_var,
            "gen_frequency_hz": self.gen_frequency_var,
            "gen_amplitude_vpp": self.gen_amplitude_var,
            "gen_offset_v": self.gen_offset_var,
            "gen_trigger_source": self.gen_trigger_source_var,
        }
        for key, variable in field_map.items():
            if key in state:
                variable.set(str(state.get(key, "")).strip())
        bool_field_map: dict[str, tk.BooleanVar] = {
            "quick_run_use_generator": self.quick_run_use_generator_var,
            "scope_ch1_enabled": self.scope_ch1_enabled_var,
            "scope_ch2_enabled": self.scope_ch2_enabled_var,
            "scope_ch3_enabled": self.scope_ch3_enabled_var,
            "scope_ch4_enabled": self.scope_ch4_enabled_var,
        }
        for key, variable in bool_field_map.items():
            if key in state:
                value = str(state.get(key, "")).strip().lower()
                variable.set(value not in {"", "0", "false", "off", "no"})
        self._on_scope_mode_change()
        self._on_generator_mode_change()
        self.refresh_generator_local_ip()
        self._update_scope_trigger_summary()

    def _current_host_config(self) -> HostConfig:
        return HostConfig(
            port=self.port_var.get().strip() or "COM3",
            baudrate=int(self.baudrate_var.get().strip() or "115200"),
            timeout_s=float(self.timeout_var.get().strip() or "0.5"),
            scope_mode=self.scope_mode_var.get().strip().lower() or "lan",
            scope_host=self.scope_host_var.get().strip() or "192.168.0.100",
            scope_port=int(self.scope_port_var.get().strip() or "5025"),
            scope_timeout_s=float(self.scope_timeout_var.get().strip() or "2.0"),
            scope_resource=self.scope_resource_var.get().strip(),
            gen_mode=self.gen_mode_var.get().strip().lower() or "tcp",
            gen_resource=self.gen_resource_var.get().strip(),
            gen_port=self.gen_port_var.get().strip(),
            gen_host=self.gen_host_var.get().strip(),
            gen_tcp_port=int(self.gen_tcp_port_var.get().strip() or "5000"),
            gen_baudrate=int(self.gen_baudrate_var.get().strip() or "9600"),
            gen_handshake=self.gen_handshake_var.get().strip().lower() or "none",
            gen_timeout_s=float(self.gen_timeout_var.get().strip() or "2.0"),
            gen_function=self.gen_function_var.get().strip() or "PULS",
            gen_frequency_hz=float(self.gen_frequency_var.get().strip() or "1000"),
            gen_amplitude_vpp=float(self.gen_amplitude_var.get().strip() or "5.0"),
            gen_offset_v=float(self.gen_offset_var.get().strip() or "0.0"),
            gen_trigger_source=self.gen_trigger_source_var.get().strip() or "IMM",
        )

    def load_config_file(self) -> None:
        path = self.config_path.get().strip()
        if not path:
            selected = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*.*")])
            if not selected:
                return
            path = selected
            self.config_path.set(path)

        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            payload = None

        try:
            if isinstance(payload, Mapping):
                state = payload.get("state", payload)
                if isinstance(state, Mapping):
                    self._apply_state(state)
                if "port" not in state and "baudrate" not in state:
                    self.apply_config(load_config(path))
            else:
                self.apply_config(load_config(path))
        except Exception as exc:
            messagebox.showerror("設定載入失敗", str(exc))
            return

        self.append_log(f"已匯入設定檔 {path}")
        self.workflow_var.set("已載入外部 JSON 設定，可再微調後另存為個人 Preset。")
        self._save_session_state()

    def export_current_config(self) -> None:
        selected = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All", "*.*")],
        )
        if not selected:
            return
        payload = {
            "version": 1,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "active_preset": self.active_preset_var.get().strip(),
            "state": self._collect_state(),
        }
        Path(selected).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.append_log(f"已匯出目前設定到 {selected}")
        self.last_output_var.set(f"設定 JSON 已匯出到 {selected}")

    def apply_config(self, cfg: HostConfig) -> None:
        self.port_var.set(cfg.port)
        self.baudrate_var.set(str(cfg.baudrate))
        self.timeout_var.set(str(cfg.timeout_s))
        self.scope_mode_var.set(cfg.scope_mode)
        self.scope_host_var.set(cfg.scope_host)
        self.scope_port_var.set(str(cfg.scope_port))
        self.scope_timeout_var.set(str(cfg.scope_timeout_s))
        self.scope_resource_var.set(cfg.scope_resource)
        self.gen_mode_var.set(cfg.gen_mode)
        self.gen_resource_var.set(cfg.gen_resource)
        self.gen_port_var.set(cfg.gen_port)
        self.gen_host_var.set(cfg.gen_host)
        self.gen_tcp_port_var.set(str(cfg.gen_tcp_port))
        self.gen_baudrate_var.set(str(cfg.gen_baudrate))
        self.gen_handshake_var.set(cfg.gen_handshake)
        self.gen_timeout_var.set(str(cfg.gen_timeout_s))
        self.gen_function_var.set(cfg.gen_function)
        self.gen_frequency_var.set(str(cfg.gen_frequency_hz))
        self.gen_amplitude_var.set(str(cfg.gen_amplitude_vpp))
        self.gen_offset_var.set(str(cfg.gen_offset_v))
        self.gen_trigger_source_var.set(cfg.gen_trigger_source)
        self._on_scope_mode_change()
        self._on_generator_mode_change()

    def refresh_ports(self) -> None:
        ports = available_ports()
        self.port_combo["values"] = ports
        if ports and self.port_var.get() not in ports:
            self.port_var.set("COM20" if "COM20" in ports else ports[0])
        self.append_log(f"MCU ports: {', '.join(ports) if ports else 'none'}")

    def generator_refresh_ports(self) -> None:
        ports = available_ports()
        self.gen_port_combo["values"] = ports
        if ports and self.gen_port_var.get() not in ports:
            self.gen_port_var.set("COM21" if "COM21" in ports else ports[0])
        self.append_log(f"33250A serial ports: {', '.join(ports) if ports else 'none'}")

    def _generator_config(self) -> Generator33250AConfig:
        return Generator33250AConfig(
            mode=self.gen_mode_var.get().strip().lower(),
            resource=self.gen_resource_var.get().strip(),
            port=self.gen_port_var.get().strip(),
            host=self.gen_host_var.get().strip(),
            tcp_port=int(self.gen_tcp_port_var.get().strip() or "5000"),
            baudrate=int(self.gen_baudrate_var.get().strip() or "9600"),
            handshake=self.gen_handshake_var.get().strip().lower() or "none",
            timeout_s=float(self.gen_timeout_var.get().strip() or "2.0"),
        )

    def _scope_config(self) -> ScopeConfig:
        return ScopeConfig(
            mode=self.scope_mode_var.get().strip().lower(),
            host=self.scope_host_var.get().strip(),
            port=int(self.scope_port_var.get().strip() or "5025"),
            timeout_s=float(self.scope_timeout_var.get().strip() or "2.0"),
            resource=self.scope_resource_var.get().strip(),
        )

    def scope_list_resources(self) -> None:
        try:
            preferred_resources = list_visa_resources(include_serial=False)
            all_resources = list_visa_resources(include_serial=True)
        except Exception as exc:
            messagebox.showerror("VISA 錯誤", str(exc))
            self.append_log(f"list-visa-resources: ERROR {exc}")
            return

        if not all_resources:
            self.append_log("VISA resources: none")
            messagebox.showinfo("VISA", "目前沒有找到任何 VISA resource。")
            return

        if preferred_resources:
            self.append_log("VISA resources:")
            for resource in preferred_resources:
                self.append_log(f"  {resource}")
            serial_only = [resource for resource in all_resources if resource.upper().startswith("ASRL")]
            if serial_only:
                self.append_log("Other serial resources:")
                for resource in serial_only:
                    self.append_log(f"  {resource}")
            return

        self.append_log("VISA resources: only serial resources found")
        for resource in all_resources:
            self.append_log(f"  {resource}")
        messagebox.showinfo("VISA", "目前只找到序列埠資源，還沒有看到 USB/TCPIP 的 VISA 儀器。")

    def scope_pick_first_resource(self) -> None:
        try:
            resources = list_visa_resources(include_serial=False)
        except Exception as exc:
            messagebox.showerror("VISA 錯誤", str(exc))
            self.append_log(f"pick-visa-resource: ERROR {exc}")
            return

        if not resources:
            messagebox.showinfo("VISA", "找不到可直接使用的示波器 VISA resource。")
            return

        self.scope_resource_var.set(resources[0])
        self.scope_mode_var.set("usb")
        self._on_scope_mode_change()
        self.append_log(f"已選用示波器 VISA resource: {resources[0]}")

    def connect(self) -> None:
        self.disconnect()
        try:
            self.client = HostClient(
                port=self.port_var.get().strip(),
                baudrate=int(self.baudrate_var.get().strip()),
                timeout_s=float(self.timeout_var.get().strip()),
            )
        except Exception as exc:
            self.client = None
            self.connection_var.set("MCU 連線失敗")
            self._update_connection_summary()
            messagebox.showerror("MCU 連線失敗", str(exc))
            return

        self.connection_var.set(f"MCU 已連線: {self.port_var.get().strip()}")
        self.workflow_var.set("MCU 已連上，下一步建議先做 PING 或 Bench Check。")
        self.append_log(f"Connected to MCU on {self.port_var.get().strip()}")
        self._update_connection_summary()
        self._save_session_state()
        self.refresh_snapshot()

    def disconnect(self) -> None:
        self.stop_monitor()
        if self.client:
            self.client.close()
            self.client = None
            self.append_log("MCU disconnected")
        self.connection_var.set("MCU 尚未連線")
        self._update_connection_summary()

    def connect_scope(self) -> None:
        self.disconnect_scope()
        try:
            self.scope_client = create_scope_client(self._scope_config())
            ident = self.scope_client.identify()
        except Exception as exc:
            self.scope_client = None
            self.scope_connection_var.set("示波器連線失敗")
            self._update_connection_summary()
            messagebox.showerror("示波器連線失敗", str(exc))
            return

        self.scope_connection_var.set(f"示波器已連線: {ident}")
        self.workflow_var.set("示波器已連線，可先用 Preset + Single 檢查 trigger。")
        self.append_log(f"Scope connected: {ident}")
        self._update_connection_summary()
        self._save_session_state()

    def disconnect_scope(self) -> None:
        if self.scope_client is not None:
            self.scope_client.close()
            self.scope_client = None
            self.append_log("Scope disconnected")
        self.scope_connection_var.set("示波器尚未連線")
        self._update_connection_summary()

    def require_scope(self) -> ScopeClient | None:
        if self.scope_client is None:
            messagebox.showwarning("示波器未連線", "請先連接示波器。")
            return None
        return self.scope_client

    def scope_identify(self) -> None:
        scope = self.require_scope()
        if scope is None:
            return
        try:
            ident = scope.identify()
        except Exception as exc:
            messagebox.showerror("示波器錯誤", str(exc))
            return
        self.append_log(f"Scope ID: {ident}")
        self.workflow_var.set(f"示波器回應正常: {ident}")

    def scope_run(self) -> None:
        scope = self.require_scope()
        if scope is None:
            return
        scope.run()
        self.append_log("Scope: RUN")

    def scope_stop(self) -> None:
        scope = self.require_scope()
        if scope is None:
            return
        scope.stop()
        self.append_log("Scope: STOP")

    def scope_single(self) -> None:
        scope = self.require_scope()
        if scope is None:
            return
        scope.clear_trigger_event()
        scope.single()
        self.append_log("Scope: SINGLE")

    def scope_clear(self) -> None:
        scope = self.require_scope()
        if scope is None:
            return
        scope.clear()
        self.append_log("Scope: CLEAR DISPLAY")

    def scope_autoscale(self) -> None:
        scope = self.require_scope()
        if scope is None:
            return
        scope.autoscale()
        self.append_log("Scope: AUTOSCALE")

    def _scope_trigger_source_scpi(self) -> str:
        source = self.scope_trigger_source_var.get().strip().upper()
        if source.startswith("CH"):
            return f"CHAN{source[2:]}"
        if source.startswith("CHAN"):
            return source
        raise ValueError(f"Unsupported trigger source: {source}")

    def _scope_trigger_level(self) -> float:
        return float(self.scope_trigger_level_var.get().strip())

    def _scope_timebase(self) -> float:
        return float(self.scope_timebase_var.get().strip())

    def _scope_channel_display_pairs(self) -> list[tuple[int, tk.BooleanVar]]:
        return [
            (1, self.scope_ch1_enabled_var),
            (2, self.scope_ch2_enabled_var),
            (3, self.scope_ch3_enabled_var),
            (4, self.scope_ch4_enabled_var),
        ]

    def _scope_visible_channels(self) -> list[str]:
        visible: list[str] = []
        for channel, variable in self._scope_channel_display_pairs():
            if bool(variable.get()):
                visible.append(f"CH{channel}")
        return visible

    def _ensure_scope_trigger_channel_visible(self) -> None:
        source = self.scope_trigger_source_var.get().strip().upper()
        if source.startswith("CH") and len(source) >= 3 and source[2:].isdigit():
            channel = int(source[2:])
            for current_channel, variable in self._scope_channel_display_pairs():
                if current_channel == channel and not variable.get():
                    variable.set(True)
                    break

    def _apply_scope_channel_display_settings(self, scope: ScopeClient) -> None:
        self._ensure_scope_trigger_channel_visible()
        for channel, variable in self._scope_channel_display_pairs():
            scope.set_channel_display(channel, bool(variable.get()))

    def _update_scope_trigger_summary(self, *_args) -> None:
        visible = ", ".join(self._scope_visible_channels()) or "none"
        source = self.scope_trigger_source_var.get().strip() or "CH4"
        level = self.scope_trigger_level_var.get().strip() or "1.0"
        sweep = self.scope_trigger_sweep_var.get().strip() or "NORMAL"
        timebase = self.scope_timebase_var.get().strip() or "0.002"
        final_single_lead = self.final_single_lead_var.get().strip() or "2"
        render_delay = self.capture_render_delay_var.get().strip() or "0.6"
        self.scope_trigger_summary_var.set(
            f"Trigger: {source} @ {level} V | Sweep: {sweep} | Timebase: {timebase} s/div | "
            f"Final SINGLE lead: {final_single_lead} | Render delay: {render_delay}s | Visible: {visible}"
        )

    def _scope_capture_timeout(self) -> float:
        return max(2.0, float(self.capture_timeout_var.get().strip()))

    def scope_apply_trigger_settings(self) -> None:
        scope = self.require_scope()
        if scope is None:
            return
        try:
            source = self._scope_trigger_source_scpi()
            level = self._scope_trigger_level()
            sweep = self.scope_trigger_sweep_var.get().strip().upper() or "NORMAL"
            timebase = self._scope_timebase()
            self._apply_scope_channel_display_settings(scope)
            scope.set_edge_trigger(source, level)
            scope.set_trigger_sweep(sweep)
            scope.set_timebase(timebase)
        except Exception as exc:
            messagebox.showerror("示波器錯誤", str(exc))
            return
        self.append_log(
            f"Scope trigger -> {source}, {level:.3f}V, sweep={sweep}, {timebase:.6g}s/div, "
            f"visible={', '.join(self._scope_visible_channels())}"
        )

    def _default_manual_capture_path(self) -> Path:
        stamp = datetime.now().strftime("%H%M%S")
        return Path.cwd() / "captures" / f"scope_{stamp}.png"

    def scope_capture_now(self) -> None:
        scope = self.require_scope()
        if scope is None:
            return
        raw = self.capture_path_var.get().strip()
        target = Path(raw) if raw else self._default_manual_capture_path()
        if target.suffix.lower() != ".png":
            target = target.with_suffix(".png")
        original_timeout = scope.get_timeout_s()
        try:
            scope.set_timeout_s(self._scope_capture_timeout())
            saved = scope.save_screenshot(target)
        except Exception as exc:
            messagebox.showerror("示波器錯誤", str(exc))
            self.append_log(f"scope-capture-now: ERROR {exc}")
            return
        finally:
            scope.set_timeout_s(original_timeout)
        self.capture_path_var.set(str(saved))
        self.last_output_var.set(f"示波器截圖已儲存: {saved}")
        self.append_log(f"Scope screenshot saved: {saved}")
        self.workflow_var.set(f"示波器截圖完成: {saved.name}")

    def scope_preset_trigger(self) -> None:
        scope = self.require_scope()
        if scope is None:
            return
        try:
            source = self._scope_trigger_source_scpi()
            level = self._scope_trigger_level()
            sweep = self.scope_trigger_sweep_var.get().strip().upper() or "NORMAL"
            timebase = self._scope_timebase()
            self._apply_scope_channel_display_settings(scope)
            scope.set_edge_trigger(source, level)
            scope.set_trigger_sweep(sweep)
            scope.set_timebase(timebase)
        except Exception as exc:
            messagebox.showerror("示波器錯誤", str(exc))
            return
        self.append_log(
            f"Scope preset trigger -> {source}, {level:.3f}V, sweep={sweep}, {timebase:.6g}s/div, "
            f"visible={', '.join(self._scope_visible_channels())}"
        )

    def scope_preset_single(self) -> None:
        self.scope_preset_trigger()
        scope = self.require_scope()
        if scope is None:
            return
        scope.clear_trigger_event()
        scope.single()
        self.append_log("Scope: preset + SINGLE")

    def generator_list_resources(self) -> None:
        try:
            resources = list_generator_visa_resources()
        except Exception as exc:
            messagebox.showerror("33250A 錯誤", str(exc))
            self.append_log(f"33250A list-resources: ERROR {exc}")
            return

        if not resources:
            messagebox.showinfo("33250A", "目前沒有找到可用的 VISA resource。")
            self.append_log("33250A VISA resources: none")
            return

        self.append_log("33250A VISA resources:")
        for resource in resources:
            self.append_log(f"  {resource}")

    def connect_generator(self) -> None:
        self.disconnect_generator()
        self.refresh_generator_local_ip(log_result=True)
        host = self.gen_host_var.get().strip()
        if self.gen_mode_var.get().strip().lower() == "tcp" and host and host == self.gen_local_ip_detected:
            message = (
                f"目前上方填入的 TCP Host / IP 是本機位址 {host}。\n"
                "這裡要填的是 33250A 的 RS232-to-TCP/IP 轉接器位址，不是電腦自己的網卡 IP。"
            )
            self.generator_connection_var.set("33250A 目標位址疑似填錯")
            self._update_connection_summary()
            self.append_log(f"33250A connect blocked: target host matches local IP ({host})")
            messagebox.showerror("33250A 位址設定錯誤", message)
            return
        target = self._generator_target_summary()
        pending_client = None
        try:
            pending_client = create_generator_33250a_client(self._generator_config())
            ident = pending_client.identify()
        except Exception as exc:
            if pending_client is not None:
                try:
                    pending_client.close()
                except Exception:
                    pass
            self.generator_client = None
            self.generator_connection_var.set("33250A 連線失敗")
            self._update_connection_summary()
            self.append_log(f"33250A connect failed ({target}): {exc}")
            messagebox.showerror("33250A 連線失敗", str(exc))
            return

        self.generator_client = pending_client
        self.generator_connection_var.set(f"33250A 已連線: {ident}")
        self.append_log(f"33250A connected: {ident}")
        self.workflow_var.set("33250A 已連線，可開始調整波形參數與 trigger source。")
        self._update_connection_summary()
        self._save_session_state()

    def disconnect_generator(self) -> None:
        if self.generator_client is not None:
            self.generator_client.close()
            self.generator_client = None
            self.append_log("33250A disconnected")
        self.generator_connection_var.set("33250A 尚未連線")
        self._update_connection_summary()

    def _generator_target_summary(self) -> str:
        mode = self.gen_mode_var.get().strip().lower()
        if mode == "tcp":
            return f"tcp://{self.gen_host_var.get().strip()}:{self.gen_tcp_port_var.get().strip() or '5000'}"
        if mode == "serial":
            handshake = self.gen_handshake_var.get().strip().lower() or "none"
            return f"serial://{self.gen_port_var.get().strip()}?baud={self.gen_baudrate_var.get().strip() or '9600'}&handshake={handshake}"
        return self.gen_resource_var.get().strip() or "visa://(empty)"

    def require_generator(self) -> Generator33250AClient | None:
        if self.generator_client is None:
            messagebox.showwarning("33250A 未連線", "請先連接 33250A。")
            return None
        return self.generator_client

    def generator_identify(self) -> None:
        generator = self.require_generator()
        if generator is None:
            return
        try:
            ident = generator.identify()
        except Exception as exc:
            messagebox.showerror("33250A 錯誤", str(exc))
            return
        self.append_log(f"33250A ID: {ident}")

    def generator_apply(self) -> None:
        generator = self.require_generator()
        if generator is None:
            return
        try:
            generator.apply(
                self.gen_function_var.get().strip(),
                float(self.gen_frequency_var.get().strip()),
                float(self.gen_amplitude_var.get().strip()),
                float(self.gen_offset_var.get().strip()),
            )
            generator.set_trigger_source(self.gen_trigger_source_var.get().strip())
        except Exception as exc:
            messagebox.showerror("33250A 錯誤", str(exc))
            self.append_log(f"33250A apply: ERROR {exc}")
            return
        self.append_log(
            "33250A apply: "
            f"{self.gen_function_var.get().strip()} "
            f"{self.gen_frequency_var.get().strip()} Hz, "
            f"{self.gen_amplitude_var.get().strip()} Vpp, "
            f"offset {self.gen_offset_var.get().strip()} V, "
            f"trigger {self.gen_trigger_source_var.get().strip()}"
        )

    def generator_output_on(self) -> None:
        generator = self.require_generator()
        if generator is None:
            return
        try:
            generator.output_on()
        except Exception as exc:
            messagebox.showerror("33250A 錯誤", str(exc))
            return
        self.append_log("33250A: OUTPUT ON")

    def generator_output_off(self) -> None:
        generator = self.require_generator()
        if generator is None:
            return
        try:
            generator.output_off()
        except Exception as exc:
            messagebox.showerror("33250A 錯誤", str(exc))
            return
        self.append_log("33250A: OUTPUT OFF")

    def generator_trigger(self) -> None:
        generator = self.require_generator()
        if generator is None:
            return
        try:
            generator.trigger()
        except Exception as exc:
            messagebox.showerror("33250A 錯誤", str(exc))
            return
        self.append_log("33250A: TRIGGER")

    def generator_read_error(self) -> None:
        generator = self.require_generator()
        if generator is None:
            return
        try:
            error_text = generator.get_error()
        except Exception as exc:
            messagebox.showerror("33250A 錯誤", str(exc))
            return
        self.append_log(f"33250A error: {error_text}")

    def require_client(self) -> HostClient | None:
        if self.client is None:
            messagebox.showwarning("MCU 未連線", "請先連接 MCU。")
            return None
        return self.client

    def send_action(self, action: str) -> None:
        client = self.require_client()
        if client is None:
            return
        try:
            response = client.request_action(action)
        except Exception as exc:
            messagebox.showerror("命令失敗", str(exc))
            self.append_log(f"{action}: ERROR {exc}")
            return
        self.append_log(f"{action}: {response}")
        if action in {"arm", "precharge", "stop", "reset-fault", "discharge", "reset-sync-count"}:
            self.refresh_snapshot()

    def start_run(self) -> None:
        client = self.require_client()
        if client is None:
            return
        try:
            count = int(self.count_var.get().strip())
        except ValueError:
            messagebox.showerror("參數錯誤", "Pulse count 必須是整數。")
            return
        try:
            response = client.request_action("start", count)
        except Exception as exc:
            messagebox.showerror("命令失敗", str(exc))
            self.append_log(f"start: ERROR {exc}")
            return
        self.append_log(f"start COUNT={count}: {response}")
        self.workflow_var.set(f"MCU 已開始執行 {count} 次 pulse。")
        self.refresh_snapshot()

    def quick_start_run(self) -> None:
        if self.pulse_capture_active:
            self._set_run_state("Start Run 已在執行中，可按「終止流程」中斷。")
            return
        if not self.monitor_active or self.monitor_job is None:
            self._set_run_state("Start Run：先啟動 Monitor。")
            self.start_monitor()
        if not self.monitor_active:
            self._set_run_state("Start Run 未啟動，因為 Monitor 尚未成功開始。")
            return
        self.pulse_capture_cancel_requested = False
        self._set_run_state("Start Run：Monitor 已就緒，準備開始 Pulse 擷取。")
        if self.quick_run_use_generator_var.get():
            self.workflow_var.set("Start Run 快捷流程：啟動 Monitor，使用 33250A 送 trigger，並在 pulse 開始與結束時自動截圖。")
        else:
            self.workflow_var.set("Start Run 快捷流程：啟動 Monitor，並在 pulse 開始與結束時自動截圖。")
        self.run_controlled_start_run()

    def cancel_pulse_capture(self) -> None:
        if not self.pulse_capture_active:
            self._set_run_state("目前沒有執行中的 Start Run 流程。")
            return
        if self.pulse_capture_cancel_requested:
            self._set_run_state("已送出終止要求，正在等待 MCU 停止。")
            return
        self.pulse_capture_cancel_requested = True
        self._set_run_state("已要求終止流程，等待這一輪 snapshot 後送出 STOP。")
        self.workflow_var.set("Start Run：已收到終止要求，正在停止流程。")
        self.append_log("Start Run: cancellation requested")

    def run_controlled_start_run(self) -> None:
        client = self.require_client()
        scope = self.require_scope()
        generator = self.require_generator() if self.quick_run_use_generator_var.get() else None
        if client is None or scope is None:
            return
        if self.quick_run_use_generator_var.get() and generator is None:
            return

        try:
            count = int(self.count_var.get().strip())
            timeout_s = float(self.capture_timeout_var.get().strip())
        except ValueError:
            messagebox.showerror("Start Run 錯誤", "Pulse Count 和 Timeout 必須是數字。")
            self._set_run_state("Start Run：無法開始，Pulse Count 或 Timeout 格式不正確。")
            return

        first_path, last_path = self._capture_path_pair(count)
        self.capture_path_var.set(str(first_path))
        original_timeout = scope.get_timeout_s()
        suspended_monitor = self.monitor_job is not None
        if suspended_monitor:
            self.root.after_cancel(self.monitor_job)
            self.monitor_job = None
            self.append_log("Monitor polling paused during Start Run")

        self.pulse_capture_cancel_requested = False
        self.pulse_capture_active = True
        self._refresh_runtime_tags()

        try:
            self._set_run_state(f"Start Run：準備示波器 Trigger，目標 {count} 次 pulse。")
            scope.set_timeout_s(max(5.0, timeout_s))
            self.scope_preset_trigger()
            scope.clear_trigger_event()
            scope.single()
            self.append_log("Scope: armed single capture for Start Run")
            self._set_run_state("Start Run：示波器已進入 Single，準備送出 MCU start。")

            baseline_snapshot = client.read_snapshot()
            baseline_count = self._parse_first_int(baseline_snapshot.count) or 0
            baseline_sync_count = self._parse_first_int(baseline_snapshot.sync_count) or 0
            self.append_log(
                f"Start Run baseline -> {baseline_snapshot.status} | "
                f"count={baseline_count} | sync={baseline_sync_count}"
            )

            start_response = client.request_action("start", count)
            self.append_log(f"start COUNT={count}: {start_response}")
            if generator is not None:
                self._set_run_state(f"Start Run：MCU 已開始執行，等待 33250A 送出 pulse（目標 {count} 次）。")
            else:
                self._set_run_state(
                    f"Start Run：MCU 已開始執行，請在 {timeout_s:.1f} 秒內手動送入 pulse（目標 {count} 次）。"
                )
            if generator is not None:
                try:
                    generator.trigger()
                except Exception as exc:
                    raise RuntimeError(f"33250A trigger failed: {exc}") from exc
                self.append_log("33250A: TRIGGER during Start Run")
                self._set_run_state("Start Run：已送出 33250A trigger，等待 pulse 活動。")

            deadline = time.time() + max(1.0, timeout_s)
            poll_interval = self._capture_poll_interval_s()
            final_single_arm_delta = self._final_single_arm_delta(count)
            seen_running = False
            saw_pulse_activity = False
            cancelled = False
            stop_sent = False
            final_snapshot = None
            first_saved: Path | None = None
            last_saved: Path | None = None
            last_single_armed = final_single_arm_delta == 0

            while time.time() < deadline:
                snapshot = client.read_snapshot()
                final_snapshot = snapshot
                self.status_var.set(snapshot.status)
                self.fault_var.set(snapshot.fault)
                self.count_rsp_var.set(snapshot.count)
                self.sync_rsp_var.set(snapshot.sync_count)
                if self.monitor_active and self.recorder is not None:
                    self.recorder.write(snapshot)

                state_name = self._snapshot_state_name(snapshot.status)
                run_count = self._parse_first_int(snapshot.count) or 0
                fault_count = self._parse_first_int(snapshot.fault) or 0
                sync_count = self._parse_first_int(snapshot.sync_count) or 0
                count_delta = max(0, run_count - baseline_count)
                sync_delta = max(0, sync_count - baseline_sync_count)
                pulse_progress = max(count_delta, sync_delta)
                pulse_progress = max(count_delta, sync_delta)

                if state_name == "RUNNING":
                    seen_running = True
                if count_delta > 0 or sync_delta > 0:
                    saw_pulse_activity = True

                if fault_count > 0 or state_name == "FAULT":
                    raise RuntimeError(f"Pulse capture fault: {snapshot.fault}")

                if self.pulse_capture_cancel_requested and not stop_sent:
                    cancelled = True
                    self._set_run_state("Start Run：正在送出 STOP，等待 MCU 回到安全狀態。")
                    stop_response = client.request_action("stop")
                    self.append_log(f"stop during Start Run: {stop_response}")
                    stop_sent = True
                elif stop_sent:
                    self._set_run_state(
                        f"Start Run：已送 STOP，等待停止中（{snapshot.status} / {snapshot.count} / {snapshot.sync_count}）。"
                    )
                else:
                    self._set_run_state(
                        f"Start Run：執行中（progress={pulse_progress}/{count} | "
                        f"{snapshot.status} / {snapshot.count} / {snapshot.sync_count}）。"
                    )

                if first_saved is None and (count_delta > 0 or sync_delta > 0):
                    first_settle_delay = self._first_capture_settle_delay_s()
                    self._scope_wait_for_triggered_capture(
                        scope,
                        "first screenshot",
                        timeout_s=first_settle_delay + 0.8,
                        render_delay_s=first_settle_delay,
                    )
                    first_saved = scope.save_screenshot(first_path)
                    self.append_log(f"Saved first-pulse screenshot: {first_saved}")
                    scope.run()
                    self.append_log("Scope: switched to RUN for end-of-run screenshot")
                    self._set_run_state("Start Run：已保存開始截圖，持續等待流程結束。")

                if (
                    first_saved is not None
                    and not last_single_armed
                    and not stop_sent
                    and pulse_progress >= final_single_arm_delta
                ):
                    scope.clear_trigger_event()
                    scope.single()
                    last_single_armed = True
                    remaining = max(1, count - pulse_progress)
                    self.append_log(f"Scope: re-armed SINGLE with {remaining} pulse(s) remaining")
                    self._set_run_state(
                        f"Start Run：剩最後 {remaining} 發，示波器已切回 SINGLE 等最後一發。"
                    )
                    time.sleep(min(0.15, poll_interval * 2))

                if pulse_progress >= count:
                    break

                if stop_sent and state_name in {"IDLE", "ARMED", "DISCHARGE", "SAFE_OFF"}:
                    break

                if saw_pulse_activity and seen_running and state_name in {"IDLE", "ARMED", "DISCHARGE", "SAFE_OFF"}:
                    break

                self.root.update()
                time.sleep(poll_interval)
            else:
                if cancelled:
                    raise TimeoutError(f"Start Run 已送出 STOP，但 MCU 在 {timeout_s:.1f} s 內沒有停下來。")
                raise TimeoutError(f"Pulse capture timeout ({timeout_s:.1f} s)")

            if not cancelled and not saw_pulse_activity:
                if self.quick_run_use_generator_var.get():
                    raise RuntimeError(
                        "Start Run 沒有偵測到 pulse 計數變化。請檢查 33250A 是否已連線、trigger 是否成功送出、"
                        "輸出是否打開，以及示波器 trigger source/level 是否正確。"
                    )
                raise RuntimeError(
                    "Start Run 沒有偵測到 pulse 計數變化。這通常代表還沒手動送入 pulse，或 DUT / Sync / "
                    "示波器 trigger 設定尚未對上。"
                )

            settle_delay = self._capture_settle_delay_s()
            self._scope_wait_for_triggered_capture(
                scope,
                "final screenshot",
                timeout_s=settle_delay + 1.0,
                render_delay_s=settle_delay,
            )
            scope.stop()
            time.sleep(0.3)

            if first_saved is None and saw_pulse_activity:
                first_settle_delay = self._first_capture_settle_delay_s()
                self._scope_wait_for_triggered_capture(
                    scope,
                    "first screenshot fallback",
                    timeout_s=first_settle_delay + 0.8,
                    render_delay_s=first_settle_delay,
                )
                first_saved = scope.save_screenshot(first_path)
                self.append_log(f"Saved first-pulse screenshot (fallback): {first_saved}")

            last_saved = scope.save_screenshot(last_path)
            if cancelled and not saw_pulse_activity:
                self.append_log(f"Saved cancellation screenshot: {last_saved}")
            else:
                self.append_log(f"Saved end-of-run screenshot: {last_saved}")

            if final_snapshot is not None:
                self.append_log(
                    f"Start Run done: {final_snapshot.status} | {final_snapshot.fault} | "
                    f"{final_snapshot.count} | {final_snapshot.sync_count}"
                )

            snapshot_summary = (
                f"{final_snapshot.status} | {final_snapshot.fault} | "
                f"{final_snapshot.count} | {final_snapshot.sync_count}"
                if final_snapshot is not None
                else "Start Run completed"
            )
            try:
                self.refresh_snapshot()
                snapshot_summary = (
                    f"{self.status_var.get()} | {self.fault_var.get()} | "
                    f"{self.count_rsp_var.get()} | {self.sync_rsp_var.get()}"
                )
            except Exception as exc:
                self.append_log(f"snapshot-after-start-run: ERROR {exc}")

            first_name = first_saved.name if first_saved is not None else "未保存開始截圖"
            if cancelled:
                self.workflow_var.set(f"Start Run 已終止: {first_name} / {last_saved.name}\n{snapshot_summary}")
                self.last_output_var.set(f"流程已終止: {first_name} | {last_saved}\n快照: {snapshot_summary}")
                self._set_run_state("Start Run：流程已終止，已保留最後畫面與快照摘要。")
                messagebox.showinfo("Start Run 已終止", f"流程已停止。\n\n最後截圖：\n{last_saved}")
            else:
                self.workflow_var.set(f"Start Run 完成: {first_name} / {last_saved.name}\n{snapshot_summary}")
                self.last_output_var.set(f"截圖完成: {first_name} | {last_saved}\n快照: {snapshot_summary}")
                self._set_run_state("Start Run：流程完成，已更新快照與截圖。")
                messagebox.showinfo(
                    "Start Run 完成",
                    f"第一張截圖：\n{first_saved}\n\n最後一張截圖：\n{last_saved}",
                )

            self.count_var.set("0")
            self.append_log("Pulse Count reset to 0 after Start Run")
        except Exception as exc:
            self._set_run_state(f"Start Run：失敗，{exc}")
            messagebox.showerror("Start Run 錯誤", str(exc))
            self.append_log(f"start-run: ERROR {exc}")
        finally:
            self.pulse_capture_active = False
            self.pulse_capture_cancel_requested = False
            self._refresh_runtime_tags()
            scope.set_timeout_s(original_timeout)
            if suspended_monitor and self.monitor_active and self.monitor_job is None:
                self.schedule_monitor()
                self.append_log("Monitor polling resumed after Start Run")

    def read_sync_once(self) -> None:
        client = self.require_client()
        if client is None:
            return
        try:
            response = client.request_action("get-sync-count")
        except Exception as exc:
            messagebox.showerror("讀取失敗", str(exc))
            self.append_log(f"get-sync-count: ERROR {exc}")
            return
        self.sync_rsp_var.set(response)
        self.append_log(f"get-sync-count: {response}")

    def reset_and_read_sync(self) -> None:
        self.send_action("reset-sync-count")
        self.read_sync_once()

    def _parse_first_int(self, text: str) -> int | None:
        match = re.search(r"(-?\d+)", text)
        if match is None:
            return None
        return int(match.group(1))

    def _default_capture_path(self, count: int) -> Path:
        stamp = datetime.now().strftime("%H%M%S")
        return Path.cwd() / "captures" / f"pulse_{count}_{stamp}.png"

    def _capture_path_pair(self, count: int) -> tuple[Path, Path]:
        raw = self.capture_path_var.get().strip()
        base_path = Path(raw) if raw else self._default_capture_path(count)
        stamp = datetime.now().strftime("%H%M%S")

        suffix = base_path.suffix or ".png"
        if suffix.lower() != ".png":
            suffix = ".png"

        stem = base_path.stem
        if stem.endswith("_first"):
            stem = stem[:-6]
        if stem.endswith("_last"):
            stem = stem[:-5]
        stem = re.sub(r"(?:_\d{6})+$", "", stem)
        if not stem:
            stem = f"pulse_{count}"

        parent = base_path.parent
        first_path = parent / f"{stem}_{stamp}_first{suffix}"
        last_path = parent / f"{stem}_{stamp}_last{suffix}"
        return first_path, last_path

    def _capture_settle_delay_s(self) -> float:
        try:
            timebase = self._scope_timebase()
        except Exception:
            timebase = 0.0
        return max(self._capture_render_delay_s(), min(1.2, timebase * 8 if timebase > 0 else 0.4))

    def _first_capture_settle_delay_s(self) -> float:
        try:
            timebase = self._scope_timebase()
        except Exception:
            timebase = 0.0
        return max(self._capture_render_delay_s(), min(0.8, timebase * 4 if timebase > 0 else 0.2))

    def _capture_render_delay_s(self) -> float:
        try:
            delay_s = float(self.capture_render_delay_var.get().strip())
        except ValueError:
            delay_s = 0.6
        return max(0.05, min(delay_s, 3.0))

    def _scope_wait_for_triggered_capture(
        self,
        scope: ScopeClient,
        label: str,
        timeout_s: float,
        render_delay_s: float,
    ) -> bool:
        wait_timeout = max(0.3, min(timeout_s, 2.0))
        try:
            triggered = scope.wait_for_trigger_event(timeout_s=wait_timeout, poll_interval_s=0.03)
        except Exception as exc:
            self.append_log(f"Scope: wait for {label} trigger failed: {exc}")
            return False
        if triggered:
            self.append_log(f"Scope: {label} trigger event detected")
            time.sleep(render_delay_s)
            return True
        self.append_log(f"Scope: {label} trigger event not detected within {wait_timeout:.2f}s")
        return False

    def _capture_poll_interval_s(self) -> float:
        return 0.05

    def _final_single_lead(self) -> int:
        try:
            lead = int(self.final_single_lead_var.get().strip())
        except ValueError:
            lead = 2
        return max(1, min(lead, 20))

    def _final_single_arm_delta(self, count: int) -> int:
        if count <= 1:
            return 0
        lead = min(self._final_single_lead(), max(1, count - 1))
        return max(1, count - lead)

    def _snapshot_state_name(self, status_text: str) -> str:
        parts = status_text.split()
        if len(parts) >= 2 and parts[0].upper() == "STATUS":
            return parts[1].upper()
        return status_text.strip().upper()

    def run_pulse_capture(self) -> None:
        client = self.require_client()
        scope = self.require_scope()
        if client is None or scope is None:
            return

        try:
            count = int(self.count_var.get().strip())
            timeout_s = float(self.capture_timeout_var.get().strip())
        except ValueError:
            messagebox.showerror("參數錯誤", "Pulse Count 與 Timeout 必須是數字。")
            return

        first_path, last_path = self._capture_path_pair(count)
        self.capture_path_var.set(str(first_path))
        original_timeout = scope.get_timeout_s()
        suspended_monitor = self.monitor_job is not None
        if suspended_monitor:
            self.root.after_cancel(self.monitor_job)
            self.monitor_job = None
            self.append_log("Monitor polling paused during pulse capture")
        self.pulse_capture_cancel_requested = False
        self.pulse_capture_active = True
        self._refresh_runtime_tags()

        try:
            self._set_run_state(f"Start Run：準備示波器 Trigger，目標 {count} 次 pulse。")
            scope.set_timeout_s(max(5.0, timeout_s))
            self.scope_preset_trigger()
            scope.clear_trigger_event()
            scope.single()
            self.append_log("Scope: armed single capture for first-pulse screenshot")
            baseline_snapshot = client.read_snapshot()
            baseline_count = self._parse_first_int(baseline_snapshot.count) or 0
            baseline_sync_count = self._parse_first_int(baseline_snapshot.sync_count) or 0
            self.append_log(
                f"Pulse capture baseline -> {baseline_snapshot.status} | "
                f"count={baseline_count} | sync={baseline_sync_count}"
            )
            self._set_run_state("Start Run：示波器已進入 Single，準備送出 MCU start。")

            start_response = client.request_action("start", count)
            self.append_log(f"start COUNT={count}: {start_response}")
            self._set_run_state(f"Start Run：MCU 已開始執行，等待 pulse 活動（目標 {count} 次）。")

            deadline = time.time() + max(1.0, timeout_s)
            poll_interval = self._capture_poll_interval_s()
            final_single_arm_delta = self._final_single_arm_delta(count)
            seen_running = False
            saw_pulse_activity = False
            final_snapshot = None
            first_saved: Path | None = None
            last_saved: Path | None = None
            stop_sent = False
            cancelled = False
            last_single_armed = final_single_arm_delta == 0

            while time.time() < deadline:
                snapshot = client.read_snapshot()
                final_snapshot = snapshot
                self.status_var.set(snapshot.status)
                self.fault_var.set(snapshot.fault)
                self.count_rsp_var.set(snapshot.count)
                self.sync_rsp_var.set(snapshot.sync_count)
                if self.monitor_active and self.recorder is not None:
                    self.recorder.write(snapshot)

                state_name = self._snapshot_state_name(snapshot.status)
                run_count = self._parse_first_int(snapshot.count) or 0
                fault_count = self._parse_first_int(snapshot.fault) or 0
                sync_count = self._parse_first_int(snapshot.sync_count) or 0
                count_delta = max(0, run_count - baseline_count)
                sync_delta = max(0, sync_count - baseline_sync_count)

                if state_name == "RUNNING":
                    seen_running = True
                if count_delta > 0 or sync_delta > 0:
                    saw_pulse_activity = True

                if fault_count > 0 or state_name == "FAULT":
                    raise RuntimeError(f"Pulse 發生 fault: {snapshot.fault}")

                if self.pulse_capture_cancel_requested and not stop_sent:
                    cancelled = True
                    self._set_run_state("Start Run：正在送出 STOP，等待 MCU 回到安全狀態。")
                    stop_response = client.request_action("stop")
                    self.append_log(f"stop during Start Run: {stop_response}")
                    stop_sent = True
                elif stop_sent:
                    self._set_run_state(
                        f"Start Run：已送 STOP，等待停止中（{snapshot.status} / {snapshot.count} / {snapshot.sync_count}）。"
                    )
                else:
                    self._set_run_state(
                        f"Start Run：執行中（progress={pulse_progress}/{count} | "
                        f"{snapshot.status} / {snapshot.count} / {snapshot.sync_count}）。"
                    )

                if first_saved is None and (count_delta > 0 or sync_delta > 0):
                    first_settle_delay = self._first_capture_settle_delay_s()
                    self._scope_wait_for_triggered_capture(
                        scope,
                        "first screenshot",
                        timeout_s=first_settle_delay + 0.8,
                        render_delay_s=first_settle_delay,
                    )
                    first_saved = scope.save_screenshot(first_path)
                    self.append_log(f"Saved first-pulse screenshot: {first_saved}")
                    scope.run()
                    self.append_log("Scope: switched to RUN for end-of-run screenshot")
                    self._set_run_state("Start Run：已保存開始截圖，持續等待流程結束。")

                if (
                    first_saved is not None
                    and not last_single_armed
                    and not stop_sent
                    and pulse_progress >= final_single_arm_delta
                ):
                    scope.clear_trigger_event()
                    scope.single()
                    last_single_armed = True
                    remaining = max(1, count - pulse_progress)
                    self.append_log(f"Scope: re-armed SINGLE with {remaining} pulse(s) remaining")
                    self._set_run_state(
                        f"Start Run：剩最後 {remaining} 發，示波器已切回 SINGLE 等最後一發。"
                    )
                    time.sleep(min(0.15, poll_interval * 2))

                if pulse_progress >= count:
                    break

                if stop_sent and state_name in {"IDLE", "ARMED", "DISCHARGE", "SAFE_OFF"}:
                    break

                if saw_pulse_activity and seen_running and state_name in {"IDLE", "ARMED", "DISCHARGE", "SAFE_OFF"}:
                    break

                self.root.update()
                time.sleep(poll_interval)
            else:
                raise TimeoutError(f"Pulse capture 逾時 ({timeout_s:.1f} s)")

            if not saw_pulse_activity:
                raise RuntimeError("沒有觀察到 pulse 活動，請確認 DUT、FG Sync 與 MCU monitor 流程。")

            if first_saved is None:
                first_settle_delay = self._first_capture_settle_delay_s()
                self._scope_wait_for_triggered_capture(
                    scope,
                    "first screenshot fallback",
                    timeout_s=first_settle_delay + 0.8,
                    render_delay_s=first_settle_delay,
                )
                first_saved = scope.save_screenshot(first_path)
                self.append_log(f"Saved first-pulse screenshot (fallback): {first_saved}")

            settle_delay = self._capture_settle_delay_s()
            self._scope_wait_for_triggered_capture(
                scope,
                "final screenshot",
                timeout_s=settle_delay + 1.0,
                render_delay_s=settle_delay,
            )
            scope.stop()
            time.sleep(0.3)
            last_saved = scope.save_screenshot(last_path)
            self.append_log(f"Saved end-of-run screenshot: {last_saved}")
            if final_snapshot is not None:
                self.append_log(
                    f"Pulse capture done: {final_snapshot.status} | {final_snapshot.fault} | "
                    f"{final_snapshot.count} | {final_snapshot.sync_count}"
                )
            snapshot_summary = (
                f"{final_snapshot.status} | {final_snapshot.fault} | "
                f"{final_snapshot.count} | {final_snapshot.sync_count}"
                if final_snapshot is not None
                else "Pulse capture completed"
            )
            try:
                self.refresh_snapshot()
                snapshot_summary = (
                    f"{self.status_var.get()} | {self.fault_var.get()} | "
                    f"{self.count_rsp_var.get()} | {self.sync_rsp_var.get()}"
                )
            except Exception as exc:
                self.append_log(f"snapshot-after-capture: ERROR {exc}")
            self.workflow_var.set(f"Pulse capture 完成: {first_saved.name} / {last_saved.name}\n{snapshot_summary}")
            self.last_output_var.set(f"截圖完成: {first_saved} | {last_saved}\n快照: {snapshot_summary}")
            self.count_var.set("0")
            self.append_log("Pulse Count reset to 0 after pulse capture")
            messagebox.showinfo(
                "Pulse Capture 完成",
                f"第一張截圖:\n{first_saved}\n\n最後一張截圖:\n{last_saved}",
            )
        except Exception as exc:
            messagebox.showerror("Pulse Capture 失敗", str(exc))
            self.append_log(f"pulse-capture: ERROR {exc}")
        finally:
            self.pulse_capture_active = False
            self._refresh_runtime_tags()
            scope.set_timeout_s(original_timeout)
            if suspended_monitor and self.monitor_active and self.monitor_job is None:
                self.schedule_monitor()
                self.append_log("Monitor polling resumed after pulse capture")

    def refresh_snapshot(self) -> None:
        client = self.require_client()
        if client is None:
            return
        try:
            snapshot = client.read_snapshot()
        except Exception as exc:
            messagebox.showerror("讀取失敗", str(exc))
            self.append_log(f"snapshot: ERROR {exc}")
            return
        self.status_var.set(snapshot.status)
        self.fault_var.set(snapshot.fault)
        self.count_rsp_var.set(snapshot.count)
        self.sync_rsp_var.set(snapshot.sync_count)
        self.append_log(
            f"{snapshot.timestamp:.3f} {snapshot.status} | {snapshot.fault} | {snapshot.count} | {snapshot.sync_count}"
        )
        if self.recorder:
            self.recorder.write(snapshot)

    def run_bench_check(self) -> None:
        client = self.require_client()
        if client is None:
            return
        checks: list[tuple[str, str]] = []
        try:
            checks.append(("PING", client.request_action("ping")))
            snapshot = client.read_snapshot()
            checks.append(("STATUS", snapshot.status))
            checks.append(("FAULT", snapshot.fault))
            checks.append(("COUNT", snapshot.count))
            checks.append(("SYNC", snapshot.sync_count))
        except Exception as exc:
            messagebox.showerror("Bench Check 失敗", str(exc))
            self.append_log(f"bench-check: ERROR {exc}")
            return
        if self.scope_client is not None:
            try:
                checks.append(("SCOPE", self.scope_client.identify()))
            except Exception as exc:
                checks.append(("SCOPE", f"ERROR {exc}"))
        self.status_var.set(snapshot.status)
        self.fault_var.set(snapshot.fault)
        self.count_rsp_var.set(snapshot.count)
        self.sync_rsp_var.set(snapshot.sync_count)
        self.append_log("Bench check result:")
        for key, value in checks:
            self.append_log(f"  {key}: {value}")
        self.workflow_var.set("Bench Check 完成，請確認 SYNC_COUNT 與示波器觸發都合理。")

    def copy_bench_commands(self) -> None:
        commands = "\n".join(
            [
                f"python -m host.src.pulse_host.cli --port {self.port_var.get().strip()} ping",
                f"python -m host.src.pulse_host.cli --port {self.port_var.get().strip()} get-sync-count",
                f"python -m host.src.pulse_host.cli --port {self.port_var.get().strip()} monitor --interval {self.interval_var.get().strip() or '0.5'}",
                (
                    "python -m host.src.pulse_host.cli scope-identify "
                    f"--scope-mode {self.scope_mode_var.get().strip()} "
                    f"--scope-resource \"{self.scope_resource_var.get().strip()}\" "
                    f"--scope-host {self.scope_host_var.get().strip()} "
                    f"--scope-port {self.scope_port_var.get().strip() or '5025'}"
                ),
            ]
        )
        self.root.clipboard_clear()
        self.root.clipboard_append(commands)
        self.append_log("已複製 bench CLI 指令到剪貼簿。")

    def pick_csv(self) -> None:
        current = self.csv_var.get().strip()
        initial = Path(current).parent if current else Path.cwd()
        selected = filedialog.asksaveasfilename(
            initialdir=initial,
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")],
        )
        if selected:
            self.csv_var.set(selected)

    def pick_capture_path(self) -> None:
        current = self.capture_path_var.get().strip()
        initial = Path(current).parent if current else (Path.cwd() / "captures")
        selected = filedialog.asksaveasfilename(
            initialdir=initial,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("All", "*.*")],
        )
        if selected:
            self.capture_path_var.set(selected)

    def open_capture_path(self) -> None:
        raw = self.capture_path_var.get().strip()
        target = Path(raw) if raw else (Path.cwd() / "captures")

        if target.is_file():
            os.startfile(str(target))
            self.append_log(f"Opened screenshot: {target}")
            return

        folder = target.parent if target.suffix else target
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(str(folder))
        self.append_log(f"Opened capture folder: {folder}")

    def toggle_monitor(self) -> None:
        if self.monitor_active:
            self.stop_monitor()
            self._set_run_state("Monitor 已關閉。")
            return
        self.start_monitor()
        if self.monitor_active:
            self._set_run_state("Monitor 已開啟，會持續刷新快照。")

    def start_monitor(self) -> None:
        if self.monitor_job is not None:
            return
        client = self.require_client()
        if client is None:
            return
        csv_path = self.csv_var.get().strip()
        if csv_path and self.recorder is None:
            try:
                self.recorder = CsvRecorder(csv_path)
            except Exception as exc:
                messagebox.showerror("CSV 錯誤", str(exc))
                return
        self.monitor_active = True
        self._refresh_runtime_tags()
        self.append_log("Monitor started")
        self.workflow_var.set("Monitor 進行中，會定期刷新 STATUS / COUNT / SYNC_COUNT。")
        self.schedule_monitor()

    def schedule_monitor(self) -> None:
        try:
            interval_ms = max(100, int(float(self.interval_var.get().strip()) * 1000.0))
        except ValueError:
            messagebox.showerror("Interval 錯誤", "Interval 必須是數字。")
            self.stop_monitor()
            return
        self.refresh_snapshot()
        self.monitor_job = self.root.after(interval_ms, self.schedule_monitor)

    def stop_monitor(self) -> None:
        if self.monitor_job is not None:
            self.root.after_cancel(self.monitor_job)
            self.monitor_job = None
            self.append_log("Monitor stopped")
        if self.recorder is not None:
            self.recorder.close()
            self.recorder = None
        self.monitor_active = False
        self._refresh_runtime_tags()

    def apply_selected_preset(self) -> None:
        name = self.active_preset_var.get().strip()
        preset = self.preset_library.get(name)
        if not preset:
            messagebox.showinfo("Preset", "請先選一個 preset。")
            return
        state = preset.get("state", {})
        if isinstance(state, Mapping):
            self._apply_state(state)
        self.workflow_var.set(f"已套用 preset: {name}")
        self.append_log(f"Preset applied: {name}")
        self._save_session_state()
        self._refresh_preset_preview(name)

    def save_current_as_preset(self) -> None:
        current_name = self.active_preset_var.get().strip()
        current_note = self.preset_library.get(current_name, {}).get("notes", "") if current_name else ""
        result = self._open_preset_editor_dialog(
            title="儲存目前設定",
            initial_name=current_name,
            initial_note=str(current_note),
        )
        if result is None:
            return
        name, notes = result
        if name in self.preset_library:
            overwrite = messagebox.askyesno("Preset 已存在", f"要覆蓋既有 preset「{name}」嗎？")
            if not overwrite:
                return
        self.preset_library[name] = {
            "name": name,
            "notes": notes,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "state": self._collect_state(),
        }
        self.active_preset_var.set(name)
        self._save_preset_library()
        self._refresh_preset_combobox()
        self._save_session_state()
        self.workflow_var.set(f"已儲存個人 preset: {name}")
        self.append_log(f"Preset saved: {name}")
        self._refresh_preset_preview(name)

    def _open_preset_editor_dialog(
        self,
        title: str,
        initial_name: str = "",
        initial_note: str = "",
    ) -> tuple[str, str] | None:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.colors["surface"])
        dialog.resizable(False, False)

        frame = tk.Frame(dialog, bg=self.colors["surface"], padx=18, pady=18)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Preset 名稱", style="Modern.TLabel").grid(row=0, column=0, sticky="w")
        name_var = tk.StringVar(value=initial_name)
        ttk.Entry(frame, textvariable=name_var, style="Modern.TEntry", width=34).grid(
            row=1, column=0, sticky="ew", pady=(4, 10)
        )
        ttk.Label(frame, text="備註", style="Modern.TLabel").grid(row=2, column=0, sticky="w")
        note_text = tk.Text(
            frame,
            height=5,
            width=36,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="flat",
            padx=10,
            pady=10,
            insertbackground=self.colors["ink"],
            font=("Segoe UI", 10),
        )
        note_text.grid(row=3, column=0, sticky="ew", pady=(4, 12))
        note_text.insert("1.0", initial_note)

        result: dict[str, str] = {}

        def submit() -> None:
            name = name_var.get().strip()
            notes = note_text.get("1.0", "end-1c").strip()
            if not name:
                messagebox.showwarning("Preset", "Preset 名稱不能空白。", parent=dialog)
                return
            result["name"] = name
            result["notes"] = notes
            dialog.destroy()

        buttons = tk.Frame(frame, bg=self.colors["surface"])
        buttons.grid(row=4, column=0, sticky="e")
        self._make_button(buttons, "取消", dialog.destroy, kind="neutral").grid(row=0, column=0, padx=(0, 8))
        self._make_button(buttons, "儲存", submit, kind="accent").grid(row=0, column=1)

        dialog.wait_window()
        if "name" not in result:
            return None
        return result["name"], result["notes"]

    def open_preset_manager(self) -> None:
        if self.preset_window is not None and self.preset_window.winfo_exists():
            self.preset_window.focus_set()
            return

        window = tk.Toplevel(self.root)
        self.preset_window = window
        window.title("Preset 管理")
        window.geometry("880x520")
        window.configure(bg=self.colors["bg"])
        window.transient(self.root)
        window.protocol("WM_DELETE_WINDOW", self._close_preset_window)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        shell = ttk.Frame(window, style="App.TFrame", padding=16)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(shell, text="Preset 清單", style="Section.TLabelframe", padding=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        self.preset_tree = ttk.Treeview(
            left,
            columns=("note", "updated"),
            show="headings",
            style="Modern.Treeview",
            selectmode="browse",
        )
        self.preset_tree.heading("note", text="備註")
        self.preset_tree.heading("updated", text="更新時間")
        self.preset_tree.column("note", width=260, anchor="w")
        self.preset_tree.column("updated", width=150, anchor="w")
        self.preset_tree.grid(row=0, column=0, sticky="nsew")
        preset_scroll = ttk.Scrollbar(left, orient="vertical", command=self.preset_tree.yview)
        preset_scroll.grid(row=0, column=1, sticky="ns")
        self.preset_tree.configure(yscrollcommand=preset_scroll.set)
        self.preset_tree.bind("<<TreeviewSelect>>", self._on_preset_tree_select)

        right = ttk.LabelFrame(shell, text="Preset 詳情", style="Section.TLabelframe", padding=14)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.preset_preview_text = tk.Text(
            right,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="flat",
            wrap="word",
            padx=12,
            pady=12,
            font=("Segoe UI", 10),
            state="disabled",
        )
        self.preset_preview_text.grid(row=0, column=0, sticky="nsew")

        buttons = tk.Frame(right, bg=self.colors["surface"])
        buttons.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        for col in range(5):
            buttons.columnconfigure(col, weight=1)
        self._make_button(buttons, "新增目前設定", self.save_current_as_preset, kind="accent").grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        self._make_button(buttons, "套用選取", self._apply_selected_tree_preset, kind="neutral").grid(
            row=0, column=1, sticky="ew", padx=6
        )
        self._make_button(buttons, "以目前覆寫", self._overwrite_selected_tree_preset, kind="neutral").grid(
            row=0, column=2, sticky="ew", padx=6
        )
        self._make_button(buttons, "刪除", self._delete_selected_tree_preset, kind="danger").grid(
            row=0, column=3, sticky="ew", padx=6
        )
        self._make_button(buttons, "關閉", self._close_preset_window, kind="neutral").grid(
            row=0, column=4, sticky="ew", padx=(6, 0)
        )

        self._refresh_preset_tree()

    def _close_preset_window(self) -> None:
        if self.preset_window is not None and self.preset_window.winfo_exists():
            self.preset_window.destroy()
        self.preset_window = None
        self.preset_tree = None
        self.preset_preview_text = None

    def _refresh_preset_tree(self) -> None:
        if self.preset_tree is None:
            return
        selected_name = self._selected_tree_preset_name()
        self.preset_tree.delete(*self.preset_tree.get_children())
        for name in sorted(self.preset_library, key=str.casefold):
            preset = self.preset_library[name]
            note = str(preset.get("notes", "")).strip()
            updated = str(preset.get("updated_at", "")).strip()
            self.preset_tree.insert("", "end", iid=name, values=(note or "-", updated or "-"))
        if selected_name and selected_name in self.preset_library:
            self.preset_tree.selection_set(selected_name)
            self._refresh_preset_preview(selected_name)
        elif self.preset_tree.get_children():
            first = self.preset_tree.get_children()[0]
            self.preset_tree.selection_set(first)
            self._refresh_preset_preview(str(first))
        else:
            self._refresh_preset_preview("")

    def _selected_tree_preset_name(self) -> str:
        if self.preset_tree is None:
            return ""
        selection = self.preset_tree.selection()
        if not selection:
            return ""
        return str(selection[0])

    def _on_preset_tree_select(self, _event: tk.Event) -> None:
        self._refresh_preset_preview(self._selected_tree_preset_name())

    def _refresh_preset_preview(self, name: str) -> None:
        if self.preset_preview_text is None:
            return
        self.preset_preview_text.configure(state="normal")
        self.preset_preview_text.delete("1.0", "end")
        preset = self.preset_library.get(name)
        if not preset:
            self.preset_preview_text.insert("1.0", "尚未選取 preset。")
        else:
            state = dict(preset.get("state", {}))
            lines = [
                f"名稱: {name}",
                f"備註: {preset.get('notes', '') or '-'}",
                f"更新時間: {preset.get('updated_at', '') or '-'}",
                "",
                "主要參數",
                f"  MCU: {state.get('port', '')} / {state.get('baudrate', '')} / timeout {state.get('timeout_s', '')}",
                f"  Count / Monitor: {state.get('count', '')} / interval {state.get('interval_s', '')}",
                f"  Scope: {state.get('scope_mode', '')} / {state.get('scope_host', '')}:{state.get('scope_port', '')}",
                f"  Trigger: {state.get('scope_trigger_source', '')} @ {state.get('scope_trigger_level', '')}V",
                (
                    "  Visible CH: "
                    f"{' '.join([f'CH{i}' for i in range(1, 5) if str(state.get(f'scope_ch{i}_enabled', 'true')).lower() not in {'', '0', 'false', 'off', 'no'}]) or 'none'}"
                ),
                (
                    f"  33250A: {state.get('gen_mode', '')} / "
                    f"{state.get('gen_host', '') or state.get('gen_port', '') or state.get('gen_resource', '')} / "
                    f"{state.get('gen_function', '')} / {state.get('gen_frequency_hz', '')}Hz"
                ),
                f"  Amplitude / Offset: {state.get('gen_amplitude_vpp', '')} / {state.get('gen_offset_v', '')}",
                "",
                "完整狀態 JSON",
                json.dumps(state, ensure_ascii=False, indent=2),
            ]
            self.preset_preview_text.insert("1.0", "\n".join(lines))
        self.preset_preview_text.configure(state="disabled")

    def _apply_selected_tree_preset(self) -> None:
        name = self._selected_tree_preset_name()
        if not name:
            return
        self.active_preset_var.set(name)
        self.apply_selected_preset()

    def _overwrite_selected_tree_preset(self) -> None:
        name = self._selected_tree_preset_name()
        if not name:
            messagebox.showinfo("Preset", "請先選一個 preset。")
            return
        confirm = messagebox.askyesno("覆寫 preset", f"要用目前畫面上的設定覆寫「{name}」嗎？")
        if not confirm:
            return
        existing = self.preset_library.get(name, {})
        self.preset_library[name] = {
            "name": name,
            "notes": str(existing.get("notes", "")).strip(),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "state": self._collect_state(),
        }
        self._save_preset_library()
        self._refresh_preset_combobox()
        self._refresh_preset_preview(name)
        self.append_log(f"Preset overwritten: {name}")

    def _delete_selected_tree_preset(self) -> None:
        name = self._selected_tree_preset_name()
        if not name:
            messagebox.showinfo("Preset", "請先選一個 preset。")
            return
        confirm = messagebox.askyesno("刪除 preset", f"確定要刪除「{name}」嗎？")
        if not confirm:
            return
        self.preset_library.pop(name, None)
        if self.active_preset_var.get().strip() == name:
            self.active_preset_var.set("")
        self._save_preset_library()
        self._refresh_preset_combobox()
        self._refresh_preset_tree()
        self.append_log(f"Preset deleted: {name}")

    def open_settings_dialog(self) -> None:
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.focus_set()
            return

        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.title("Session Settings")
        window.geometry("920x650")
        window.configure(bg=self.colors["bg"])
        window.transient(self.root)
        window.protocol("WM_DELETE_WINDOW", self._close_settings_window)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        shell = ttk.Frame(window, style="App.TFrame", padding=16)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(shell, style="Modern.TNotebook")
        notebook.grid(row=0, column=0, sticky="nsew")

        general = ttk.Frame(notebook, style="Surface.TFrame", padding=18)
        mcu = ttk.Frame(notebook, style="Surface.TFrame", padding=18)
        scope = ttk.Frame(notebook, style="Surface.TFrame", padding=18)
        generator = ttk.Frame(notebook, style="Surface.TFrame", padding=18)
        for page in (general, mcu, scope, generator):
            page.columnconfigure(0, weight=1)
            page.columnconfigure(1, weight=1)

        notebook.add(general, text="General")
        notebook.add(mcu, text="MCU")
        notebook.add(scope, text="Scope")
        notebook.add(generator, text="33250A")

        self._settings_header(general, "Session 設定", "集中整理匯入匯出、Preset 與 session 狀態")
        ttk.Label(general, text="設定檔路徑", style="Modern.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 4))
        ttk.Entry(general, textvariable=self.config_path, style="Modern.TEntry").grid(
            row=2, column=0, columnspan=2, sticky="ew"
        )
        tk.Label(
            general,
            textvariable=self.session_note_var,
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            justify="left",
            anchor="w",
            wraplength=760,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 10))
        actions = tk.Frame(general, bg=self.colors["surface"])
        actions.grid(row=4, column=0, columnspan=2, sticky="w")
        self._make_button(actions, "匯入 JSON", self.load_config_file, kind="neutral").grid(row=0, column=0, padx=(0, 8))
        self._make_button(actions, "匯出 JSON", self.export_current_config, kind="neutral").grid(row=0, column=1, padx=(0, 8))
        self._make_button(actions, "管理 Preset", self.open_preset_manager, kind="accent").grid(row=0, column=2)

        self._settings_header(mcu, "MCU 參數", "連線與監控相關設定")
        self._settings_field(mcu, 1, "COM Port", self.port_var, column=0)
        self._settings_field(mcu, 1, "Baudrate", self.baudrate_var, column=1)
        self._settings_field(mcu, 3, "Timeout (s)", self.timeout_var, column=0)
        self._settings_field(mcu, 3, "Pulse Count", self.count_var, column=1)
        self._settings_field(mcu, 5, "Monitor Interval (s)", self.interval_var, column=0)
        self._settings_field(mcu, 5, "CSV 路徑", self.csv_var, column=1)

        self._settings_header(scope, "Scope 參數", "連線、trigger、截圖路徑都可以直接改")
        self._settings_combo(scope, 1, "模式", self.scope_mode_var, ["usb", "lan"], self._on_scope_mode_change, column=0)
        self._settings_field(scope, 1, "Timeout (s)", self.scope_timeout_var, column=1)
        self._settings_field(scope, 3, "Host / IP", self.scope_host_var, column=0)
        self._settings_field(scope, 3, "Port", self.scope_port_var, column=1)
        self._settings_field(scope, 5, "VISA Resource", self.scope_resource_var, column=0)
        self._settings_combo(
            scope,
            5,
            "Trigger Source",
            self.scope_trigger_source_var,
            ["CH1", "CH2", "CH3", "CH4"],
            None,
            column=1,
        )
        self._settings_field(scope, 7, "Trigger Level (V)", self.scope_trigger_level_var, column=0)
        self._settings_combo(
            scope,
            7,
            "Trigger Sweep",
            self.scope_trigger_sweep_var,
            ["AUTO", "NORMAL"],
            None,
            column=1,
        )
        self._settings_field(scope, 9, "Timebase (s/div)", self.scope_timebase_var, column=0)
        self._settings_field(scope, 9, "Capture Timeout (s)", self.capture_timeout_var, column=1)
        self._settings_field(scope, 11, "最後截圖提前量", self.final_single_lead_var, column=0)
        self._settings_field(scope, 11, "Trigger後截圖等待 (s)", self.capture_render_delay_var, column=1)
        ttk.Label(scope, text="Visible Channels", style="Modern.TLabel").grid(row=13, column=0, sticky="w", pady=(10, 4))
        settings_channel_row = tk.Frame(scope, bg=self.colors["surface"])
        settings_channel_row.grid(row=14, column=0, columnspan=2, sticky="ew")
        for col in range(4):
            settings_channel_row.columnconfigure(col, weight=1)
        self._make_scope_channel_toggle(settings_channel_row, "CH1", self.scope_ch1_enabled_var).grid(row=0, column=0, sticky="w")
        self._make_scope_channel_toggle(settings_channel_row, "CH2", self.scope_ch2_enabled_var).grid(row=0, column=1, sticky="w")
        self._make_scope_channel_toggle(settings_channel_row, "CH3", self.scope_ch3_enabled_var).grid(row=0, column=2, sticky="w")
        self._make_scope_channel_toggle(settings_channel_row, "CH4", self.scope_ch4_enabled_var).grid(row=0, column=3, sticky="w")
        tk.Label(
            scope,
            textvariable=self.scope_trigger_summary_var,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            justify="left",
            anchor="w",
            wraplength=760,
        ).grid(row=15, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        self._settings_field(scope, 16, "Capture 路徑", self.capture_path_var, column=0, columnspan=2)

        self._settings_header(generator, "33250A 參數", "波形與通訊參數")
        self._settings_combo(
            generator,
            1,
            "模式",
            self.gen_mode_var,
            ["visa", "serial", "tcp"],
            self._on_generator_mode_change,
            column=0,
        )
        self._settings_field(generator, 1, "Timeout (s)", self.gen_timeout_var, column=1)
        self._settings_field(generator, 3, "VISA Resource", self.gen_resource_var, column=0)
        self._settings_field(generator, 3, "Serial Port", self.gen_port_var, column=1)
        self._settings_field(generator, 5, "33250A / TCP轉接器 IP", self.gen_host_var, column=0)
        self._settings_field(generator, 5, "TCP Port", self.gen_tcp_port_var, column=1)
        self._settings_field(generator, 7, "Baudrate", self.gen_baudrate_var, column=0)
        self._settings_combo(
            generator,
            7,
            "Handshake",
            self.gen_handshake_var,
            ["none", "dsrdtr", "rtscts", "xonxoff"],
            None,
            column=1,
        )
        self._settings_field(generator, 9, "Function", self.gen_function_var, column=0)
        self._settings_field(generator, 9, "Frequency (Hz)", self.gen_frequency_var, column=1)
        self._settings_field(generator, 11, "Amplitude (Vpp)", self.gen_amplitude_var, column=0)
        self._settings_field(generator, 11, "Offset (V)", self.gen_offset_var, column=1)
        self._settings_combo(
            generator,
            13,
            "Trigger Source",
            self.gen_trigger_source_var,
            ["IMM", "EXT", "BUS"],
            None,
            column=1,
        )

        footer = tk.Frame(shell, bg=self.colors["bg"])
        footer.grid(row=1, column=0, sticky="e", pady=(12, 0))
        self._make_button(footer, "關閉", self._close_settings_window, kind="neutral").grid(row=0, column=0, padx=(0, 8))
        self._make_button(footer, "儲存目前為 Preset", self.save_current_as_preset, kind="accent").grid(row=0, column=1)

    def _close_settings_window(self) -> None:
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        self.settings_window = None

    def _settings_header(self, parent: ttk.Frame, title: str, subtitle: str) -> None:
        tk.Label(
            parent,
            text=title,
            bg=self.colors["surface"],
            fg=self.colors["ink"],
            font=("Segoe UI Semibold", 16),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            parent,
            text=subtitle,
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
        ).grid(row=0, column=1, sticky="e")

    def _settings_field(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        column: int,
        columnspan: int = 1,
    ) -> None:
        target_column = column
        ttk.Label(parent, text=label, style="Modern.TLabel").grid(
            row=row, column=target_column, sticky="w", pady=(10, 4)
        )
        ttk.Entry(parent, textvariable=variable, style="Modern.TEntry").grid(
            row=row + 1,
            column=target_column,
            columnspan=columnspan,
            sticky="ew",
            padx=(0, 12) if target_column == 0 and columnspan == 1 else (0, 0),
        )

    def _settings_combo(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        values: list[str],
        callback,
        column: int,
    ) -> None:
        ttk.Label(parent, text=label, style="Modern.TLabel").grid(row=row, column=column, sticky="w", pady=(10, 4))
        combo = ttk.Combobox(
            parent,
            textvariable=variable,
            values=values,
            state="readonly",
            style="Modern.TCombobox",
        )
        combo.grid(row=row + 1, column=column, sticky="ew", padx=(0, 12) if column == 0 else (0, 0))
        if callback is not None:
            combo.bind("<<ComboboxSelected>>", lambda _event: callback())

    def on_close(self) -> None:
        self._save_session_state()
        self.disconnect()
        self.disconnect_scope()
        self.disconnect_generator()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = PulseHostApp(root)
    app.append_log("GUI ready")
    root.mainloop()


if __name__ == "__main__":
    main()
