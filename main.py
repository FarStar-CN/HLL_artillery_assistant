import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from config import CFG, load_settings, apply_loaded_settings
from ui.main_window import MainWindow


def main():
    project_dir = Path(__file__).resolve().parent
    loaded = load_settings(project_dir)
    if loaded is not None:
        apply_loaded_settings(loaded, CFG)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
