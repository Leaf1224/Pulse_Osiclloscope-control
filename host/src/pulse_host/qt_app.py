from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QFile
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QDialog
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QInputDialog
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QWidget
from PySide6.QtUiTools import QUiLoader


REPO_ROOT = Path(__file__).resolve().parents[3]
UI_DIR = Path(__file__).resolve().parent / "ui"
PROFILE_PATH = REPO_ROOT / ".pulse_bench_profiles.json"


def default_main_ui_path() -> Path:
    return UI_DIR / "main_window.ui"


def default_settings_ui_path() -> Path:
    return UI_DIR / "settings_dialog.ui"


def load_ui(path: Path) -> QWidget:
    loader = QUiLoader()
    ui_file = QFile(str(path))
    if not ui_file.open(QFile.ReadOnly):
        raise RuntimeError(f"Cannot open UI file: {path}")
    try:
        widget = loader.load(ui_file)
    finally:
        ui_file.close()
    if widget is None:
        raise RuntimeError(f"Failed to load UI file: {path}")
    return widget


def default_profiles() -> dict:
    return {
        "active_profile": "Default",
        "profiles": {
            "Default": {
                "operator": "",
                "config_path": "",
                "capture_folder": str(REPO_ROOT / "captures"),
                "notes": "",
                "mcu_port": "COM20",
                "mcu_baudrate": "115200",
                "mcu_timeout": "0.5",
                "scope_mode": "usb",
                "scope_resource": "",
                "scope_host": "192.168.0.100",
                "scope_port": "5025",
                "scope_trigger_source": "CH4",
                "scope_trigger_level": "1.0",
                "scope_sweep": "NORMAL",
                "scope_timebase": "0.002",
                "gen_mode": "visa",
                "gen_resource": "",
                "gen_port": "",
                "gen_baudrate": "9600",
                "gen_function": "PULS",
                "gen_frequency": "1000",
                "gen_amplitude": "5.0",
                "gen_offset": "0.0",
                "gen_trigger": "IMM",
                "capture_timeout": "15",
                "capture_file": "",
            }
        },
    }


class PresetStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            data = default_profiles()
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return data
        return json.loads(self.path.read_text(encoding="utf-8"))

    def reload(self) -> None:
        self.data = self._load()

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    @property
    def active_profile(self) -> str:
        return str(self.data.get("active_profile", "Default"))

    @active_profile.setter
    def active_profile(self, name: str) -> None:
        self.data["active_profile"] = name

    @property
    def profiles(self) -> dict:
        return self.data.setdefault("profiles", {})


class SettingsDialogController:
    def __init__(self, store: PresetStore) -> None:
        dialog = load_ui(default_settings_ui_path())
        if not isinstance(dialog, QDialog):
            raise RuntimeError("settings_dialog.ui must load as QDialog")
        self.dialog = dialog
        self.store = store
        self._current_profile_name: str | None = None

        self.list_profiles = self.dialog.findChild(QWidget, "listProfiles")
        self.edit_profile_name = self.dialog.findChild(QWidget, "editProfileName")
        self.edit_operator = self.dialog.findChild(QWidget, "editOperator")
        self.edit_config_path = self.dialog.findChild(QWidget, "editConfigPath")
        self.edit_capture_folder = self.dialog.findChild(QWidget, "editCaptureFolder")
        self.edit_notes = self.dialog.findChild(QWidget, "editNotes")
        self.edit_mcu_port = self.dialog.findChild(QWidget, "editMcuPort")
        self.edit_mcu_baudrate = self.dialog.findChild(QWidget, "editMcuBaudrate")
        self.edit_mcu_timeout = self.dialog.findChild(QWidget, "editMcuTimeout")
        self.combo_scope_mode = self.dialog.findChild(QWidget, "comboScopeMode")
        self.edit_scope_resource = self.dialog.findChild(QWidget, "editScopeResource")
        self.edit_scope_host = self.dialog.findChild(QWidget, "editScopeHost")
        self.edit_scope_port = self.dialog.findChild(QWidget, "editScopePort")
        self.combo_scope_trigger_source = self.dialog.findChild(QWidget, "comboScopeTriggerSource")
        self.edit_scope_trigger_level = self.dialog.findChild(QWidget, "editScopeTriggerLevel")
        self.combo_scope_sweep = self.dialog.findChild(QWidget, "comboScopeSweep")
        self.edit_scope_timebase = self.dialog.findChild(QWidget, "editScopeTimebase")
        self.combo_gen_mode = self.dialog.findChild(QWidget, "comboGenMode")
        self.edit_gen_resource = self.dialog.findChild(QWidget, "editGenResource")
        self.edit_gen_port = self.dialog.findChild(QWidget, "editGenPort")
        self.edit_gen_baudrate = self.dialog.findChild(QWidget, "editGenBaudrate")
        self.combo_gen_function = self.dialog.findChild(QWidget, "comboGenFunction")
        self.edit_gen_frequency = self.dialog.findChild(QWidget, "editGenFrequency")
        self.edit_gen_amplitude = self.dialog.findChild(QWidget, "editGenAmplitude")
        self.edit_gen_offset = self.dialog.findChild(QWidget, "editGenOffset")
        self.combo_gen_trigger = self.dialog.findChild(QWidget, "comboGenTrigger")
        self.edit_capture_timeout = self.dialog.findChild(QWidget, "editCaptureTimeout")
        self.edit_capture_file = self.dialog.findChild(QWidget, "editCaptureFile")

        self.btn_profile_new = self.dialog.findChild(QWidget, "btnProfileNew")
        self.btn_profile_clone = self.dialog.findChild(QWidget, "btnProfileClone")
        self.btn_profile_delete = self.dialog.findChild(QWidget, "btnProfileDelete")
        self.btn_save_profiles = self.dialog.findChild(QWidget, "btnSaveProfiles")
        self.btn_close_dialog = self.dialog.findChild(QWidget, "btnCloseDialog")

        self.btn_profile_new.clicked.connect(self.new_profile)
        self.btn_profile_clone.clicked.connect(self.clone_profile)
        self.btn_profile_delete.clicked.connect(self.delete_profile)
        self.btn_save_profiles.clicked.connect(self.save_and_accept)
        self.btn_close_dialog.clicked.connect(self.dialog.accept)
        self.list_profiles.currentTextChanged.connect(self.on_profile_changed)

        self.populate_profile_list()

    def populate_profile_list(self) -> None:
        self.list_profiles.clear()
        for name in sorted(self.store.profiles):
            self.list_profiles.addItem(name)

        target = self.store.active_profile
        items = self.list_profiles.findItems(target, 0)
        if items:
            self.list_profiles.setCurrentItem(items[0])
        elif self.list_profiles.count():
            self.list_profiles.setCurrentRow(0)

    def save_current_profile(self) -> None:
        if not self._current_profile_name:
            return
        name = self.edit_profile_name.text().strip() or self._current_profile_name
        profile = {
            "operator": self.edit_operator.text().strip(),
            "config_path": self.edit_config_path.text().strip(),
            "capture_folder": self.edit_capture_folder.text().strip(),
            "notes": self.edit_notes.toPlainText().strip(),
            "mcu_port": self.edit_mcu_port.text().strip(),
            "mcu_baudrate": self.edit_mcu_baudrate.text().strip(),
            "mcu_timeout": self.edit_mcu_timeout.text().strip(),
            "scope_mode": self.combo_scope_mode.currentText().strip(),
            "scope_resource": self.edit_scope_resource.text().strip(),
            "scope_host": self.edit_scope_host.text().strip(),
            "scope_port": self.edit_scope_port.text().strip(),
            "scope_trigger_source": self.combo_scope_trigger_source.currentText().strip(),
            "scope_trigger_level": self.edit_scope_trigger_level.text().strip(),
            "scope_sweep": self.combo_scope_sweep.currentText().strip(),
            "scope_timebase": self.edit_scope_timebase.text().strip(),
            "gen_mode": self.combo_gen_mode.currentText().strip(),
            "gen_resource": self.edit_gen_resource.text().strip(),
            "gen_port": self.edit_gen_port.text().strip(),
            "gen_baudrate": self.edit_gen_baudrate.text().strip(),
            "gen_function": self.combo_gen_function.currentText().strip(),
            "gen_frequency": self.edit_gen_frequency.text().strip(),
            "gen_amplitude": self.edit_gen_amplitude.text().strip(),
            "gen_offset": self.edit_gen_offset.text().strip(),
            "gen_trigger": self.combo_gen_trigger.currentText().strip(),
            "capture_timeout": self.edit_capture_timeout.text().strip(),
            "capture_file": self.edit_capture_file.text().strip(),
        }

        if name != self._current_profile_name:
            self.store.profiles.pop(self._current_profile_name, None)
            self._current_profile_name = name
        self.store.profiles[name] = profile
        self.store.active_profile = name

    def load_profile(self, name: str) -> None:
        if not name:
            return
        profile = self.store.profiles.get(name, {})
        self._current_profile_name = name
        self.edit_profile_name.setText(name)
        self.edit_operator.setText(profile.get("operator", ""))
        self.edit_config_path.setText(profile.get("config_path", ""))
        self.edit_capture_folder.setText(profile.get("capture_folder", ""))
        self.edit_notes.setPlainText(profile.get("notes", ""))
        self.edit_mcu_port.setText(profile.get("mcu_port", ""))
        self.edit_mcu_baudrate.setText(profile.get("mcu_baudrate", ""))
        self.edit_mcu_timeout.setText(profile.get("mcu_timeout", ""))
        self.combo_scope_mode.setCurrentText(profile.get("scope_mode", "usb"))
        self.edit_scope_resource.setText(profile.get("scope_resource", ""))
        self.edit_scope_host.setText(profile.get("scope_host", ""))
        self.edit_scope_port.setText(profile.get("scope_port", ""))
        self.combo_scope_trigger_source.setCurrentText(profile.get("scope_trigger_source", "CH4"))
        self.edit_scope_trigger_level.setText(profile.get("scope_trigger_level", "1.0"))
        self.combo_scope_sweep.setCurrentText(profile.get("scope_sweep", "NORMAL"))
        self.edit_scope_timebase.setText(profile.get("scope_timebase", "0.002"))
        self.combo_gen_mode.setCurrentText(profile.get("gen_mode", "visa"))
        self.edit_gen_resource.setText(profile.get("gen_resource", ""))
        self.edit_gen_port.setText(profile.get("gen_port", ""))
        self.edit_gen_baudrate.setText(profile.get("gen_baudrate", "9600"))
        self.combo_gen_function.setCurrentText(profile.get("gen_function", "PULS"))
        self.edit_gen_frequency.setText(profile.get("gen_frequency", "1000"))
        self.edit_gen_amplitude.setText(profile.get("gen_amplitude", "5.0"))
        self.edit_gen_offset.setText(profile.get("gen_offset", "0.0"))
        self.combo_gen_trigger.setCurrentText(profile.get("gen_trigger", "IMM"))
        self.edit_capture_timeout.setText(profile.get("capture_timeout", "15"))
        self.edit_capture_file.setText(profile.get("capture_file", ""))

    def on_profile_changed(self, name: str) -> None:
        if self._current_profile_name is not None:
            self.save_current_profile()
        self.load_profile(name)

    def new_profile(self) -> None:
        name, ok = QInputDialog.getText(self.dialog, "新增 Profile", "請輸入新 profile 名稱：")
        name = name.strip()
        if not ok or not name:
            return
        if name in self.store.profiles:
            QMessageBox.warning(self.dialog, "名稱已存在", f"{name} 已存在。")
            return
        self.store.profiles[name] = default_profiles()["profiles"]["Default"].copy()
        self.store.active_profile = name
        self.populate_profile_list()

    def clone_profile(self) -> None:
        current = self._current_profile_name or self.store.active_profile
        if current not in self.store.profiles:
            return
        name, ok = QInputDialog.getText(self.dialog, "複製 Profile", "請輸入新 profile 名稱：")
        name = name.strip()
        if not ok or not name:
            return
        if name in self.store.profiles:
            QMessageBox.warning(self.dialog, "名稱已存在", f"{name} 已存在。")
            return
        self.save_current_profile()
        self.store.profiles[name] = dict(self.store.profiles[current])
        self.store.active_profile = name
        self.populate_profile_list()

    def delete_profile(self) -> None:
        current = self._current_profile_name or self.store.active_profile
        if current not in self.store.profiles:
            return
        if len(self.store.profiles) <= 1:
            QMessageBox.warning(self.dialog, "無法刪除", "至少要保留一個 profile。")
            return
        answer = QMessageBox.question(self.dialog, "刪除 Profile", f"確定刪除 {current}？")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.store.profiles.pop(current, None)
        self.store.active_profile = sorted(self.store.profiles)[0]
        self.populate_profile_list()

    def save_and_accept(self) -> None:
        self.save_current_profile()
        self.store.save()
        self.dialog.accept()

    def exec(self) -> int:
        return self.dialog.exec()


class MainWindowController:
    def __init__(self) -> None:
        window = load_ui(default_main_ui_path())
        if not isinstance(window, QMainWindow):
            raise RuntimeError("main_window.ui must load as QMainWindow")
        self.window = window
        self.store = PresetStore(PROFILE_PATH)

        self.label_active_profile_value = self.window.findChild(QWidget, "labelActiveProfileValue")
        self.label_active_profile_meta = self.window.findChild(QWidget, "labelActiveProfileMeta")
        self.label_mcu_summary = self.window.findChild(QWidget, "labelMcuSummary")
        self.label_scope_summary = self.window.findChild(QWidget, "labelScopeSummary")
        self.label_generator_summary = self.window.findChild(QWidget, "labelGeneratorSummary")
        self.label_capture_summary = self.window.findChild(QWidget, "labelCaptureSummary")
        self.label_preset_com_value = self.window.findChild(QWidget, "labelPresetComValue")
        self.label_preset_scope_value = self.window.findChild(QWidget, "labelPresetScopeValue")
        self.label_preset_gen_value = self.window.findChild(QWidget, "labelPresetGenValue")
        self.label_preset_capture_value = self.window.findChild(QWidget, "labelPresetCaptureValue")
        self.text_profile_preview = self.window.findChild(QWidget, "textProfilePreview")
        self.text_log = self.window.findChild(QWidget, "textLog")
        self.btn_open_settings = self.window.findChild(QWidget, "btnOpenSettings")
        self.btn_reload_profiles = self.window.findChild(QWidget, "btnReloadProfiles")
        self.btn_open_classic_gui = self.window.findChild(QWidget, "btnOpenClassicGui")
        self.btn_clear_log = self.window.findChild(QWidget, "btnClearLog")
        self.btn_save_log = self.window.findChild(QWidget, "btnSaveLog")
        self.btn_action_open_capture_folder = self.window.findChild(QWidget, "btnActionOpenCaptureFolder")

        self.btn_open_settings.clicked.connect(self.open_settings)
        self.btn_reload_profiles.clicked.connect(self.reload_profiles)
        self.btn_open_classic_gui.clicked.connect(self.open_classic_gui)
        self.btn_clear_log.clicked.connect(self.clear_log)
        self.btn_save_log.clicked.connect(self.save_log)
        self.btn_action_open_capture_folder.clicked.connect(self.open_capture_folder)

        self.refresh_profile_summary()
        self.append_log("Qt UI ready")

    def append_log(self, text: str) -> None:
        self.text_log.appendPlainText(text)

    def active_profile_data(self) -> tuple[str, dict]:
        name = self.store.active_profile
        profile = self.store.profiles.get(name, {})
        return name, profile

    def refresh_profile_summary(self) -> None:
        name, profile = self.active_profile_data()
        self.label_active_profile_value.setText(name)
        self.label_active_profile_meta.setText(
            f"{profile.get('mcu_port', 'COM?')} / {profile.get('scope_mode', 'usb')} / {profile.get('gen_mode', 'visa')}"
        )
        self.label_mcu_summary.setText(profile.get("mcu_port", "未設定"))
        self.label_scope_summary.setText(profile.get("scope_mode", "未設定").upper())
        self.label_generator_summary.setText(profile.get("gen_function", "未設定"))
        self.label_capture_summary.setText(Path(profile.get("capture_folder", "captures")).name)
        self.label_preset_com_value.setText(
            f"{profile.get('mcu_port', 'COM?')} / {profile.get('mcu_baudrate', '115200')}"
        )
        self.label_preset_scope_value.setText(
            f"{profile.get('scope_mode', 'usb')} / {profile.get('scope_trigger_source', 'CH4')}"
        )
        self.label_preset_gen_value.setText(
            f"{profile.get('gen_mode', 'visa')} / {profile.get('gen_function', 'PULS')}"
        )
        self.label_preset_capture_value.setText(profile.get("capture_folder", str(REPO_ROOT / "captures")))
        self.text_profile_preview.setPlainText(json.dumps({"active_profile": name, "profile": profile}, ensure_ascii=False, indent=2))

    def open_settings(self) -> None:
        dialog = SettingsDialogController(self.store)
        if dialog.exec():
            self.store.reload()
            self.refresh_profile_summary()
            self.append_log(f"Profile saved: {self.store.active_profile}")

    def reload_profiles(self) -> None:
        self.store.reload()
        self.refresh_profile_summary()
        self.append_log("Profiles reloaded")

    def open_classic_gui(self) -> None:
        subprocess.Popen([sys.executable, "-m", "host.src.pulse_host.gui"], cwd=str(REPO_ROOT))
        self.append_log("Opened classic control window")

    def clear_log(self) -> None:
        self.text_log.clear()
        self.append_log("Log cleared")

    def save_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self.window,
            "儲存紀錄",
            str(REPO_ROOT / "captures" / "qt_ui_log.txt"),
            "Text Files (*.txt);;All Files (*)",
        )
        if not path:
            return
        Path(path).write_text(self.text_log.toPlainText(), encoding="utf-8")
        self.append_log(f"Saved log: {path}")

    def open_capture_folder(self) -> None:
        _, profile = self.active_profile_data()
        folder = Path(profile.get("capture_folder", str(REPO_ROOT / "captures")))
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", str(folder)])
        self.append_log(f"Opened capture folder: {folder}")

    def show(self) -> None:
        self.window.show()


def main() -> None:
    app = QApplication(sys.argv)
    controller = MainWindowController()
    controller.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
