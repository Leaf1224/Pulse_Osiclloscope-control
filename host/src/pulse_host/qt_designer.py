from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def default_ui_path() -> Path:
    return Path(__file__).resolve().parent / "ui" / "main_window.ui"


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch Qt Designer for editing .ui files")
    parser.add_argument("--ui", default=str(default_ui_path()), help="Path to .ui file")
    args = parser.parse_args()

    ui_path = Path(args.ui).expanduser().resolve()
    if not ui_path.exists():
        raise SystemExit(f"UI file not found: {ui_path}")

    designer = shutil.which("pyside6-designer")
    if not designer:
        raise SystemExit("pyside6-designer not found. Install PySide6 first.")

    subprocess.run([designer, str(ui_path)], check=False)


if __name__ == "__main__":
    main()
