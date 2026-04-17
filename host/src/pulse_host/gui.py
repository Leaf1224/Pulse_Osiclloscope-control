from __future__ import annotations

import os
import re
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from pulse_host.client import CsvRecorder
    from pulse_host.client import HostClient
    from pulse_host.config import HostConfig
    from pulse_host.config import load_config
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
    from .scope import ScopeConfig
    from .scope import ScopeClient
    from .scope import create_scope_client
    from .scope import list_visa_resources
    from .serial_link import available_ports


class PulseHostApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Pulse Bench Console")
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        window_w = min(1180, max(900, screen_w - 120))
        window_h = min(820, max(640, screen_h - 140))
        self.root.geometry(f"{window_w}x{window_h}")
        self.root.minsize(820, 620)

        self.client: HostClient | None = None
        self.scope_client: ScopeClient | None = None
        self.recorder: CsvRecorder | None = None
        self.monitor_job: str | None = None
        self._tab_canvases: list[tk.Canvas] = []

        self.config_path = tk.StringVar()
        self.port_var = tk.StringVar(value="COM20")
        self.baudrate_var = tk.StringVar(value="115200")
        self.timeout_var = tk.StringVar(value="0.5")
        self.count_var = tk.StringVar(value="100")
        self.interval_var = tk.StringVar(value="0.5")
        self.csv_var = tk.StringVar()
        self.capture_timeout_var = tk.StringVar(value="15")
        self.capture_path_var = tk.StringVar()

        self.scope_mode_var = tk.StringVar(value="usb")
        self.scope_host_var = tk.StringVar(value="192.168.0.100")
        self.scope_port_var = tk.StringVar(value="5025")
        self.scope_resource_var = tk.StringVar(value="")
        self.scope_trigger_source_var = tk.StringVar(value="CH4")
        self.scope_trigger_level_var = tk.StringVar(value="1.0")
        self.scope_trigger_sweep_var = tk.StringVar(value="NORMAL")
        self.scope_timebase_var = tk.StringVar(value="0.002")

        self.connection_var = tk.StringVar(value="MCU 未連線")
        self.scope_connection_var = tk.StringVar(value="示波器未連線")
        self.status_var = tk.StringVar(value="STATUS N/A")
        self.fault_var = tk.StringVar(value="FAULT N/A")
        self.count_rsp_var = tk.StringVar(value="COUNT N/A")
        self.sync_rsp_var = tk.StringVar(value="SYNC_COUNT N/A")
        self.workflow_var = tk.StringVar(value="先連 MCU，再確認 PING / STATUS。")

        self._build_style()
        self._build_layout()
        self.refresh_ports()
        self._on_scope_mode_change()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", font=("Segoe UI", 12))
        style.configure("TLabelframe.Label", font=("Segoe UI", 12, "bold"))
        style.configure("TEntry", font=("Segoe UI", 12))
        style.configure("TCombobox", font=("Segoe UI", 12))
        style.configure("TNotebook.Tab", font=("Segoe UI", 12, "bold"), padding=(12, 6))
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Hint.TLabel", foreground="#4b5563")
        style.configure("CardTitle.TLabel", font=("Segoe UI", 13, "bold"), foreground="#334155")
        style.configure("CardValue.TLabel", font=("Consolas", 24, "bold"), foreground="#111827")

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(16, 10, 16, 2))
        header.grid(row=0, column=0, sticky="nsew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Bench Bring-Up 操作台", style="Title.TLabel").grid(row=0, column=0, sticky="w")

        body = ttk.Frame(self.root, padding=(16, 2, 16, 16))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

        # Make main work area resizable by user: notebook (top) and log (bottom).
        main_split = tk.PanedWindow(body, orient=tk.VERTICAL, sashrelief="raised", sashwidth=8, bd=0)
        main_split.grid(row=0, column=0, sticky="nsew")

        top_area = ttk.Frame(main_split)
        top_area.columnconfigure(0, weight=1)
        top_area.rowconfigure(0, weight=1)
        bottom_area = ttk.Frame(main_split)
        bottom_area.columnconfigure(0, weight=1)
        bottom_area.rowconfigure(0, weight=1)
        main_split.add(top_area, stretch="always")
        main_split.add(bottom_area, minsize=180)

        notebook = ttk.Notebook(top_area)
        notebook.grid(row=0, column=0, sticky="nsew")

        mcu_tab = self._create_scrollable_tab(notebook, "MCU")
        mcu_tab.columnconfigure(0, weight=1)
        self._build_mcu_panel(mcu_tab).grid(row=0, column=0, sticky="nsew", pady=(0, 12))

        mcu_lower = ttk.Frame(mcu_tab)
        mcu_lower.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        mcu_lower.columnconfigure(0, weight=3, uniform="mcu-lower")
        mcu_lower.columnconfigure(1, weight=2, uniform="mcu-lower")

        self._build_status_panel(mcu_lower).grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._build_monitor_panel(mcu_lower).grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        scope_tab = self._create_scrollable_tab(notebook, "示波器")
        scope_tab.columnconfigure(0, weight=1)
        self._build_scope_panel(scope_tab).grid(row=0, column=0, sticky="nsew", pady=(0, 12))

        guide_tab = self._create_scrollable_tab(notebook, "操作說明")
        guide_tab.columnconfigure(0, weight=1)
        self._build_workflow_panel(guide_tab).grid(row=0, column=0, sticky="nsew", pady=(0, 12))

        self._build_log_panel(bottom_area).grid(row=0, column=0, sticky="nsew")

    def _create_scrollable_tab(self, notebook: ttk.Notebook, title: str) -> ttk.Frame:
        host = ttk.Frame(notebook, padding=(8, 8, 8, 8))
        host.columnconfigure(0, weight=1)
        host.rowconfigure(0, weight=1)

        canvas = tk.Canvas(host, highlightthickness=0, borderwidth=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(host, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        content = ttk.Frame(canvas)
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

    def _build_mcu_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="MCU 連線與控制")
        for col in range(4):
            frame.columnconfigure(col, weight=1, uniform="mcu")

        ttk.Label(frame, text="COM Port").grid(row=0, column=0, sticky="w", padx=8, pady=(10, 6))
        self.port_combo = ttk.Combobox(frame, textvariable=self.port_var, state="normal")
        self.port_combo.grid(row=0, column=1, sticky="ew", padx=8, pady=(10, 6))
        self._make_button(frame, "重新掃描", self.refresh_ports).grid(row=0, column=2, sticky="nsew", padx=8, pady=(10, 6))
        ttk.Label(frame, textvariable=self.connection_var).grid(row=0, column=3, sticky="w", padx=8, pady=(10, 6))

        self._make_button(frame, "連接 MCU", self.connect).grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self._make_button(frame, "斷開 MCU", self.disconnect).grid(row=1, column=1, sticky="nsew", padx=8, pady=8)
        self._make_button(frame, "PING", lambda: self.send_action("ping")).grid(row=1, column=2, sticky="nsew", padx=8, pady=8)
        self._make_button(frame, "更新狀態", self.refresh_snapshot).grid(row=1, column=3, sticky="nsew", padx=8, pady=8)

        ttk.Label(frame, text="Pulse Count").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frame, textvariable=self.count_var).grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        self._make_button(frame, "Reset SYNC", lambda: self.send_action("reset-sync-count")).grid(row=2, column=2, sticky="nsew", padx=8, pady=6)
        self._make_button(frame, "Bench 檢查", self.run_bench_check).grid(row=2, column=3, sticky="nsew", padx=8, pady=6)

        ttk.Label(frame, text="快速操作", style="Hint.TLabel").grid(row=3, column=0, columnspan=4, sticky="w", padx=8, pady=(2, 2))

        common_buttons = [
            ("Start", self.start_run),
            ("Stop", lambda: self.send_action("stop")),
            ("Arm", lambda: self.send_action("arm")),
            ("Discharge", lambda: self.send_action("discharge")),
        ]
        for idx, (label, cmd) in enumerate(common_buttons):
            self._make_button(frame, label, cmd).grid(
                row=4 + idx // 4,
                column=idx % 4,
                sticky="nsew",
                padx=8,
                pady=(4, 6),
            )

        advanced = self._create_collapsible_section(frame, "進階 MCU 控制", row=6, columnspan=4, expanded=False)
        for col in range(4):
            advanced.columnconfigure(col, weight=1, uniform="mcu-adv")

        ttk.Label(advanced, text="設定檔").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 6))
        ttk.Entry(advanced, textvariable=self.config_path).grid(row=0, column=1, columnspan=2, sticky="ew", padx=8, pady=(8, 6))
        self._make_button(advanced, "載入", self.load_config_file).grid(row=0, column=3, sticky="nsew", padx=8, pady=(8, 6))

        ttk.Label(advanced, text="Baudrate").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(advanced, textvariable=self.baudrate_var).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(advanced, text="Timeout").grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(advanced, textvariable=self.timeout_var).grid(row=1, column=3, sticky="ew", padx=8, pady=6)

        self._make_button(advanced, "Reset Fault", lambda: self.send_action("reset-fault")).grid(
            row=2, column=0, sticky="nsew", padx=8, pady=(6, 8)
        )
        self._make_button(advanced, "Precharge", lambda: self.send_action("precharge")).grid(
            row=2, column=1, sticky="nsew", padx=8, pady=(6, 8)
        )
        return frame

    def _build_scope_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="示波器控制")
        for col in range(4):
            frame.columnconfigure(col, weight=1, uniform="scope")

        ttk.Label(frame, text="模式").grid(row=0, column=0, sticky="w", padx=8, pady=(10, 6))
        mode_combo = ttk.Combobox(frame, textvariable=self.scope_mode_var, values=["usb", "lan"], state="readonly")
        mode_combo.grid(row=0, column=1, sticky="ew", padx=8, pady=(10, 6))
        mode_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_scope_mode_change())
        ttk.Label(frame, text="狀態").grid(row=0, column=2, sticky="w", padx=8, pady=(10, 6))
        ttk.Label(frame, textvariable=self.scope_connection_var).grid(row=0, column=3, sticky="w", padx=8, pady=(10, 6))

        self.scope_host_label = ttk.Label(frame, text="IP")
        self.scope_host_label.grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.scope_host_entry = ttk.Entry(frame, textvariable=self.scope_host_var)
        self.scope_host_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        self.scope_port_label = ttk.Label(frame, text="Port")
        self.scope_port_label.grid(row=1, column=2, sticky="w", padx=8, pady=6)
        self.scope_port_entry = ttk.Entry(frame, textvariable=self.scope_port_var)
        self.scope_port_entry.grid(row=1, column=3, sticky="ew", padx=8, pady=6)

        self.scope_resource_label = ttk.Label(frame, text="VISA Resource")
        self.scope_resource_label.grid(row=2, column=0, sticky="w", padx=8, pady=6)
        self.scope_resource_entry = ttk.Entry(frame, textvariable=self.scope_resource_var)
        self.scope_resource_entry.grid(row=2, column=1, columnspan=3, sticky="ew", padx=8, pady=6)

        self._make_button(frame, "連接示波器", self.connect_scope).grid(row=3, column=0, sticky="nsew", padx=8, pady=6)
        self._make_button(frame, "斷開示波器", self.disconnect_scope).grid(row=3, column=1, sticky="nsew", padx=8, pady=6)
        self._make_button(frame, "Identify", self.scope_identify).grid(row=3, column=2, sticky="nsew", padx=8, pady=6)
        self._make_button(frame, "Preset + Single", self.scope_preset_single).grid(row=3, column=3, sticky="nsew", padx=8, pady=6)

        common_scope_buttons = [
            ("Run", self.scope_run),
            ("Stop", self.scope_stop),
            ("Single", self.scope_single),
            ("Autoscale", self.scope_autoscale),
        ]
        for idx, (label, cmd) in enumerate(common_scope_buttons):
            self._make_button(frame, label, cmd).grid(
                row=4 + idx // 4,
                column=idx % 4,
                sticky="nsew",
                padx=8,
                pady=(6, 6),
            )

        advanced = self._create_collapsible_section(frame, "進階示波器控制", row=6, columnspan=4, expanded=False)
        for col in range(4):
            advanced.columnconfigure(col, weight=1, uniform="scope-adv")

        self._make_button(advanced, "列出 VISA 裝置", self.scope_list_resources).grid(
            row=0, column=0, sticky="nsew", padx=8, pady=(8, 6)
        )
        self._make_button(advanced, "套用第一個裝置", self.scope_pick_first_resource).grid(
            row=0, column=1, sticky="nsew", padx=8, pady=(8, 6)
        )
        self._make_button(advanced, "Clear", self.scope_clear).grid(
            row=0, column=2, sticky="nsew", padx=8, pady=(8, 6)
        )
        self._make_button(advanced, "Trigger Preset", self.scope_preset_trigger).grid(
            row=0, column=3, sticky="nsew", padx=8, pady=(8, 6)
        )
        ttk.Label(advanced, text="Trigger Source").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Combobox(
            advanced,
            textvariable=self.scope_trigger_source_var,
            values=["CH1", "CH2", "CH3", "CH4"],
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(advanced, text="Trigger Level (V)").grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(advanced, textvariable=self.scope_trigger_level_var).grid(row=1, column=3, sticky="ew", padx=8, pady=6)
        ttk.Label(advanced, text="Trigger Sweep").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Combobox(
            advanced,
            textvariable=self.scope_trigger_sweep_var,
            values=["AUTO", "NORMAL"],
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(advanced, text="Timebase (s/div)").grid(row=2, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(advanced, textvariable=self.scope_timebase_var).grid(row=2, column=3, sticky="ew", padx=8, pady=6)
        self._make_button(advanced, "套用 Trigger", self.scope_apply_trigger_settings).grid(
            row=3, column=2, sticky="nsew", padx=8, pady=6
        )
        self._make_button(advanced, "立即截圖", self.scope_capture_now).grid(
            row=3, column=3, sticky="nsew", padx=8, pady=6
        )

        ttk.Label(
            frame,
            text="USB 模式請填 VISA resource，例如 USB0::0x0957::...::INSTR；LAN 模式請填 IP / Port。",
            wraplength=520,
            style="Hint.TLabel",
        ).grid(row=7, column=0, columnspan=4, sticky="w", padx=8, pady=(4, 10))
        return frame

    def _create_collapsible_section(
        self,
        parent: tk.Misc,
        title: str,
        row: int,
        columnspan: int,
        expanded: bool = False,
    ) -> ttk.Frame:
        container = ttk.Frame(parent)
        container.grid(row=row, column=0, columnspan=columnspan, sticky="nsew", padx=8, pady=(4, 8))
        container.columnconfigure(0, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text=title, style="Hint.TLabel").grid(row=0, column=0, sticky="w")
        toggle = self._make_button(header, "收起" if expanded else "展開", lambda: None)
        toggle.grid(row=0, column=1, sticky="e")

        body = ttk.Frame(container)
        body.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        body.columnconfigure(0, weight=1)

        def set_expanded(state: bool) -> None:
            body._expanded = state  # type: ignore[attr-defined]
            toggle.configure(text="收起" if state else "展開", wraplength=120)
            if state:
                body.grid()
            else:
                body.grid_remove()
            canvas = self._find_scroll_canvas(container)
            if canvas is not None:
                self.root.after_idle(lambda current_canvas=canvas: self._update_canvas_scroll_region(current_canvas))

        toggle.configure(command=lambda: set_expanded(not getattr(body, "_expanded", expanded)))
        set_expanded(expanded)
        return body

    def _build_status_panel(self, parent: tk.Misc) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="即時狀態")
        for col in range(2):
            frame.columnconfigure(col, weight=1)
        for row in range(2):
            frame.rowconfigure(row, weight=1)

        self._add_status_card(frame, "狀態", self.status_var, 0, 0)
        self._add_status_card(frame, "故障", self.fault_var, 0, 1)
        self._add_status_card(frame, "Pulse Count", self.count_rsp_var, 1, 0)
        self._add_status_card(frame, "SYNC Count", self.sync_rsp_var, 1, 1)
        return frame

    def _add_status_card(self, parent: ttk.LabelFrame, title: str, value_var: tk.StringVar, row: int, col: int) -> None:
        card = ttk.Frame(parent, padding=16)
        card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
        card.columnconfigure(0, weight=1)
        title_label = ttk.Label(card, text=title, style="CardTitle.TLabel")
        title_label.grid(row=0, column=0, sticky="w")
        value_label = ttk.Label(card, textvariable=value_var, style="CardValue.TLabel")
        value_label.grid(row=1, column=0, sticky="w", pady=(8, 0))

        # Keep status text readable even when panel-scale shrinks.
        title_label._base_font_size = 13  # type: ignore[attr-defined]
        title_label._min_font_size = 11  # type: ignore[attr-defined]
        value_label._base_font_size = 24  # type: ignore[attr-defined]
        value_label._min_font_size = 18  # type: ignore[attr-defined]

    def _build_workflow_panel(self, parent: tk.Misc) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="目前建議流程")
        frame.columnconfigure(0, weight=1)

        workflow = (
            "1. MCU 用 Type-C 接 PC，確認 COM 埠出現。\n"
            "2. FG 的 SYNC OUT 接到 MCU 的 FG_PULSE_MON_IN。\n"
            "3. 先按「連接 MCU」，再按「PING」或「Bench 檢查」。\n"
            "4. 若公司 LAN 被鎖，示波器改用 USB DEVICE + VISA。\n"
            "5. 用 Monitor 觀察 SYNC_COUNT 是否持續增加。\n"
            "6. 示波器連線後，用 Identify / Preset + Single 驗證控制鏈路。\n"
            "7. 要自動擷取波形，請到 MCU 分頁右下設定截圖檔案，再按「Pulse 結束後截圖」。\n"
            "8. 截圖完成後，可按「開啟截圖」直接查看 PNG。"
        )
        ttk.Label(frame, text=workflow, justify="left", wraplength=360).grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 8))
        ttk.Label(frame, textvariable=self.workflow_var, style="Hint.TLabel", wraplength=360).grid(
            row=1, column=0, sticky="w", padx=12, pady=(0, 10)
        )
        self._make_button(frame, "複製 CLI 指令提示", self.copy_bench_commands).grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        return frame

    def _build_log_panel(self, parent: tk.Misc) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="操作紀錄")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.log_text_font = tkfont.Font(family="Consolas", size=13)
        self.log_text = tk.Text(frame, wrap="word", height=8, font=self.log_text_font)
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.log_text._adaptive_font = self.log_text_font  # type: ignore[attr-defined]
        self.log_text._base_font_size = 13  # type: ignore[attr-defined]
        self.log_text._min_font_size = 11  # type: ignore[attr-defined]

        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        self._make_button(buttons, "清空紀錄", self.clear_log).grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._make_button(buttons, "儲存紀錄", self.save_log).grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        return frame

    def _build_monitor_panel(self, parent: tk.Misc) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="輪詢與紀錄")
        for col in range(2):
            frame.columnconfigure(col, weight=1, uniform="monitor")

        ttk.Label(frame, text="Interval (s)").grid(row=0, column=0, sticky="w", padx=8, pady=(10, 6))
        ttk.Entry(frame, textvariable=self.interval_var).grid(row=0, column=1, sticky="ew", padx=8, pady=(10, 6))
        ttk.Label(frame, text="CSV").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frame, textvariable=self.csv_var).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        self._make_button(frame, "選擇檔案", self.pick_csv).grid(row=2, column=0, sticky="nsew", padx=8, pady=6)
        self._make_button(frame, "Start Monitor", self.start_monitor).grid(row=2, column=1, sticky="nsew", padx=8, pady=6)
        self._make_button(frame, "Stop Monitor", self.stop_monitor).grid(row=3, column=0, sticky="nsew", padx=8, pady=6)
        self._make_button(frame, "立即刷新快照", self.refresh_snapshot).grid(row=3, column=1, sticky="nsew", padx=8, pady=6)
        self._make_button(frame, "讀一次 SYNC_COUNT", self.read_sync_once).grid(row=4, column=0, sticky="nsew", padx=8, pady=(6, 12))
        self._make_button(frame, "Reset + 讀一次", self.reset_and_read_sync).grid(row=4, column=1, sticky="nsew", padx=8, pady=(6, 12))
        ttk.Separator(frame, orient="horizontal").grid(row=5, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 8))
        ttk.Label(frame, text="截圖 Timeout (s)").grid(row=6, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frame, textvariable=self.capture_timeout_var).grid(row=6, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(frame, text="截圖檔案").grid(row=7, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frame, textvariable=self.capture_path_var).grid(row=7, column=1, sticky="ew", padx=8, pady=6)
        self._make_button(frame, "選擇截圖檔案", self.pick_capture_path).grid(row=8, column=0, sticky="nsew", padx=8, pady=6)
        self._make_button(frame, "Pulse 首尾截圖", self.run_pulse_capture).grid(row=8, column=1, sticky="nsew", padx=8, pady=6)
        self._make_button(frame, "開啟截圖", self.open_capture_path).grid(row=9, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 10))
        return frame

    def _make_button(self, parent: tk.Misc, text: str, command) -> tk.Button:
        font = tkfont.Font(family="Segoe UI", size=12)
        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=font,
            relief="groove",
            bd=1,
            padx=4,
            pady=4,
            justify="center",
            wraplength=180,
        )
        return button

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
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def clear_log(self) -> None:
        self.log_text.delete("1.0", "end")
        self.append_log("Log cleared.")

    def save_log(self) -> None:
        selected = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
        )
        if not selected:
            return
        Path(selected).write_text(self.log_text.get("1.0", "end-1c"), encoding="utf-8")
        self.append_log(f"Saved log to {selected}")

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

    def load_config_file(self) -> None:
        path = self.config_path.get().strip()
        if not path:
            selected = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*.*")])
            if not selected:
                return
            path = selected
            self.config_path.set(path)

        try:
            cfg = load_config(path)
        except Exception as exc:
            messagebox.showerror("Config Error", str(exc))
            return

        self.apply_config(cfg)
        self.append_log(f"Loaded config from {path}")

    def apply_config(self, cfg: HostConfig) -> None:
        self.port_var.set(cfg.port)
        self.baudrate_var.set(str(cfg.baudrate))
        self.timeout_var.set(str(cfg.timeout_s))
        self.scope_mode_var.set(cfg.scope_mode)
        self.scope_host_var.set(cfg.scope_host)
        self.scope_port_var.set(str(cfg.scope_port))
        self.scope_resource_var.set(cfg.scope_resource)
        self._on_scope_mode_change()

    def refresh_ports(self) -> None:
        ports = available_ports()
        self.port_combo["values"] = ports
        if ports and self.port_var.get() not in ports:
            self.port_var.set("COM20" if "COM20" in ports else ports[0])
        self.append_log(f"Ports: {', '.join(ports) if ports else 'none'}")

    def _scope_config(self) -> ScopeConfig:
        return ScopeConfig(
            mode=self.scope_mode_var.get().strip().lower(),
            host=self.scope_host_var.get().strip(),
            port=int(self.scope_port_var.get().strip() or "5025"),
            timeout_s=2.0,
            resource=self.scope_resource_var.get().strip(),
        )

    def scope_list_resources(self) -> None:
        try:
            preferred_resources = list_visa_resources(include_serial=False)
            all_resources = list_visa_resources(include_serial=True)
        except Exception as exc:
            messagebox.showerror("VISA Error", str(exc))
            self.append_log(f"list-visa-resources: ERROR {exc}")
            return

        if not all_resources:
            self.append_log("VISA resources: none")
            messagebox.showinfo("VISA", "沒有找到任何 VISA 裝置。")
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
        messagebox.showinfo(
            "VISA",
            "目前只找到 ASRL 串口資源，尚未找到示波器的 USB/TCPIP VISA 裝置。",
        )

    def scope_pick_first_resource(self) -> None:
        try:
            resources = list_visa_resources(include_serial=False)
        except Exception as exc:
            messagebox.showerror("VISA Error", str(exc))
            self.append_log(f"pick-visa-resource: ERROR {exc}")
            return

        if not resources:
            messagebox.showinfo("VISA", "沒有找到可用的示波器 VISA 資源。")
            return

        self.scope_resource_var.set(resources[0])
        self.scope_mode_var.set("usb")
        self._on_scope_mode_change()
        self.append_log(f"Selected VISA resource: {resources[0]}")

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
            messagebox.showerror("Connection Error", str(exc))
            return

        self.connection_var.set(f"MCU 已連線: {self.port_var.get().strip()}")
        self.workflow_var.set("MCU 已連線，下一步可以按 PING 或 Bench 檢查。")
        self.append_log(f"Connected to {self.port_var.get().strip()}")
        self.refresh_snapshot()

    def disconnect(self) -> None:
        self.stop_monitor()
        if self.client:
            self.client.close()
            self.client = None
            self.append_log("MCU disconnected")
        self.connection_var.set("MCU 未連線")

    def connect_scope(self) -> None:
        self.disconnect_scope()
        try:
            self.scope_client = create_scope_client(self._scope_config())
            ident = self.scope_client.identify()
        except Exception as exc:
            self.scope_client = None
            self.scope_connection_var.set("示波器連線失敗")
            messagebox.showerror("Scope Error", str(exc))
            return

        self.scope_connection_var.set("示波器已連線")
        self.workflow_var.set("示波器已連線，現在可以按 Identify 或 Preset + Single。")
        self.append_log(f"Scope connected: {ident}")

    def disconnect_scope(self) -> None:
        if self.scope_client is not None:
            self.scope_client.close()
            self.scope_client = None
            self.append_log("Scope disconnected")
        self.scope_connection_var.set("示波器未連線")

    def require_scope(self) -> ScopeClient | None:
        if self.scope_client is None:
            messagebox.showwarning("Scope Not Connected", "先連接示波器。")
            return None
        return self.scope_client

    def scope_identify(self) -> None:
        scope = self.require_scope()
        if scope is None:
            return
        try:
            ident = scope.identify()
        except Exception as exc:
            messagebox.showerror("Scope Error", str(exc))
            return
        self.append_log(f"Scope ID: {ident}")

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
            scope.set_edge_trigger(source, level)
            scope.set_trigger_sweep(sweep)
            scope.set_timebase(self._scope_timebase())
        except Exception as exc:
            messagebox.showerror("Scope Error", str(exc))
            return
        self.append_log(
            f"Scope: trigger -> {source}, {level:.3f}V, sweep={sweep}, timebase={self._scope_timebase():.6g}s/div"
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
            messagebox.showerror("Scope Error", str(exc))
            self.append_log(f"scope-capture-now: ERROR {exc}")
            return
        finally:
            scope.set_timeout_s(original_timeout)
        self.capture_path_var.set(str(saved))
        self.append_log(f"Scope screenshot saved: {saved}")
        self.workflow_var.set(f"示波器立即截圖完成：{saved.name}")

    def scope_preset_trigger(self) -> None:
        scope = self.require_scope()
        if scope is None:
            return
        try:
            source = self._scope_trigger_source_scpi()
            level = self._scope_trigger_level()
            sweep = self.scope_trigger_sweep_var.get().strip().upper() or "NORMAL"
            timebase = self._scope_timebase()
            scope.set_channel_display(1, True)
            scope.set_channel_display(2, True)
            scope.set_channel_display(3, True)
            scope.set_channel_display(4, True)
            scope.set_edge_trigger(source, level)
            scope.set_trigger_sweep(sweep)
            scope.set_timebase(timebase)
        except Exception as exc:
            messagebox.showerror("Scope Error", str(exc))
            return
        self.append_log(f"Scope: preset trigger -> {source}, {level:.3f}V, sweep={sweep}, {timebase:.6g} s/div")

    def scope_preset_single(self) -> None:
        self.scope_preset_trigger()
        scope = self.require_scope()
        if scope is None:
            return
        scope.single()
        self.append_log("Scope: preset + SINGLE")

    def require_client(self) -> HostClient | None:
        if self.client is None:
            messagebox.showwarning("MCU Not Connected", "先連接 MCU。")
            return None
        return self.client

    def send_action(self, action: str) -> None:
        client = self.require_client()
        if client is None:
            return
        try:
            response = client.request_action(action)
        except Exception as exc:
            messagebox.showerror("Command Error", str(exc))
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
            messagebox.showerror("Invalid Count", "Pulse count must be an integer.")
            return
        try:
            response = client.request_action("start", count)
        except Exception as exc:
            messagebox.showerror("Command Error", str(exc))
            self.append_log(f"start: ERROR {exc}")
            return
        self.append_log(f"start COUNT={count}: {response}")
        self.refresh_snapshot()

    def read_sync_once(self) -> None:
        client = self.require_client()
        if client is None:
            return
        try:
            response = client.request_action("get-sync-count")
        except Exception as exc:
            messagebox.showerror("Read Error", str(exc))
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

        parent = base_path.parent
        first_path = parent / f"{stem}_{stamp}_first{suffix}"
        last_path = parent / f"{stem}_{stamp}_last{suffix}"
        return first_path, last_path

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
            messagebox.showerror("設定錯誤", "Pulse Count 與截圖 Timeout 必須是數字。")
            return

        first_path, last_path = self._capture_path_pair(count)
        self.capture_path_var.set(str(first_path))
        original_timeout = scope.get_timeout_s()

        try:
            scope.set_timeout_s(max(5.0, timeout_s))
            self.scope_preset_trigger()
            scope.single()
            self.append_log("Scope: armed single capture for first-pulse screenshot")

            start_response = client.request_action("start", count)
            self.append_log(f"start COUNT={count}: {start_response}")

            deadline = time.time() + max(1.0, timeout_s)
            seen_running = False
            final_snapshot = None
            first_saved: Path | None = None

            while time.time() < deadline:
                snapshot = client.read_snapshot()
                final_snapshot = snapshot
                self.status_var.set(snapshot.status)
                self.fault_var.set(snapshot.fault)
                self.count_rsp_var.set(snapshot.count)
                self.sync_rsp_var.set(snapshot.sync_count)

                state_name = self._snapshot_state_name(snapshot.status)
                run_count = self._parse_first_int(snapshot.count) or 0
                fault_count = self._parse_first_int(snapshot.fault) or 0

                if state_name == "RUNNING":
                    seen_running = True

                if fault_count > 0 or state_name == "FAULT":
                    raise RuntimeError(f"Pulse 執行期間進入 fault: {snapshot.fault}")

                sync_count = self._parse_first_int(snapshot.sync_count) or 0
                if first_saved is None and (run_count > 0 or sync_count > 0 or seen_running):
                    scope.stop()
                    time.sleep(0.3)
                    first_saved = scope.save_screenshot(first_path)
                    self.append_log(f"Saved first-pulse screenshot: {first_saved}")
                    scope.run()
                    self.append_log("Scope: switched to RUN for end-of-run screenshot")

                if run_count >= count:
                    break

                if seen_running and state_name in {"IDLE", "ARMED", "DISCHARGE", "SAFE_OFF"}:
                    break

                self.root.update()
                time.sleep(0.2)

            else:
                raise TimeoutError(f"等待 pulse 完成逾時 ({timeout_s:.1f} s)")

            if first_saved is None:
                scope.stop()
                time.sleep(0.3)
                first_saved = scope.save_screenshot(first_path)
                self.append_log(f"Saved first-pulse screenshot (fallback): {first_saved}")

            scope.stop()
            time.sleep(0.3)
            last_saved = scope.save_screenshot(last_path)
            self.append_log(f"Saved end-of-run screenshot: {last_saved}")
            if final_snapshot is not None:
                self.append_log(
                    f"Pulse capture done: {final_snapshot.status} | {final_snapshot.fault} | "
                    f"{final_snapshot.count} | {final_snapshot.sync_count}"
                )
            self.workflow_var.set(f"Pulse 首尾截圖完成：{first_saved.name} / {last_saved.name}")
            messagebox.showinfo(
                "Pulse 首尾截圖完成",
                f"第一張：\n{first_saved}\n\n最後一張：\n{last_saved}\n\n可按「開啟截圖」直接查看。",
            )
        except Exception as exc:
            messagebox.showerror("Pulse 擷取失敗", str(exc))
            self.append_log(f"pulse-capture: ERROR {exc}")

        finally:
            scope.set_timeout_s(original_timeout)

    def refresh_snapshot(self) -> None:
        client = self.require_client()
        if client is None:
            return
        try:
            snapshot = client.read_snapshot()
        except Exception as exc:
            messagebox.showerror("Read Error", str(exc))
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
            messagebox.showerror("Bench Check Error", str(exc))
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
        self.workflow_var.set("Bench 檢查完成。若 SYNC_COUNT 不增加，先檢查 FG 的 SYNC 接線與輸出。")

    def copy_bench_commands(self) -> None:
        commands = "\n".join([
            f"python -m host.src.pulse_host.cli --port {self.port_var.get().strip()} ping",
            f"python -m host.src.pulse_host.cli --port {self.port_var.get().strip()} get-sync-count",
            f"python -m host.src.pulse_host.cli --port {self.port_var.get().strip()} monitor --interval 0.5",
            f"python -m host.src.pulse_host.cli scope-identify --scope-mode {self.scope_mode_var.get().strip()} --scope-resource \"{self.scope_resource_var.get().strip()}\" --scope-host {self.scope_host_var.get().strip()}",
        ])
        self.root.clipboard_clear()
        self.root.clipboard_append(commands)
        self.append_log("Copied bench CLI commands to clipboard.")

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
                messagebox.showerror("CSV Error", str(exc))
                return
        self.append_log("Monitor started")
        self.workflow_var.set("Monitor 進行中，可觀察 SYNC_COUNT 是否持續增加。")
        self.schedule_monitor()

    def schedule_monitor(self) -> None:
        try:
            interval_ms = max(100, int(float(self.interval_var.get().strip()) * 1000.0))
        except ValueError:
            messagebox.showerror("Interval Error", "Interval must be numeric.")
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

    def on_close(self) -> None:
        self.disconnect()
        self.disconnect_scope()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = PulseHostApp(root)
    app.append_log("GUI ready")
    root.mainloop()


if __name__ == "__main__":
    main()
