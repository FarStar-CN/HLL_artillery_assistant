import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

from config import CFG, load_settings, apply_loaded_settings
from ui.main_window import MainWindow


def _dark_palette():
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(15, 25, 35))
    palette.setColor(QPalette.WindowText,       QColor(192, 216, 240))
    palette.setColor(QPalette.Base,             QColor(18, 28, 40))
    palette.setColor(QPalette.AlternateBase,    QColor(24, 36, 50))
    palette.setColor(QPalette.Text,             QColor(192, 216, 240))
    palette.setColor(QPalette.Button,           QColor(26, 42, 58))
    palette.setColor(QPalette.ButtonText,       QColor(192, 216, 240))
    palette.setColor(QPalette.Highlight,        QColor(74, 138, 190))
    palette.setColor(QPalette.HighlightedText,  QColor(232, 244, 255))
    palette.setColor(QPalette.ToolTipBase,      QColor(18, 28, 40))
    palette.setColor(QPalette.ToolTipText,      QColor(192, 216, 240))
    # Disabled
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(80, 100, 120))
    palette.setColor(QPalette.Disabled, QPalette.Text,       QColor(80, 100, 120))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(80, 100, 120))
    return palette


def main():
    project_dir = Path(__file__).resolve().parent
    loaded = load_settings(project_dir)
    if loaded is not None:
        apply_loaded_settings(loaded, CFG)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(_dark_palette())
    app.setStyleSheet("""
        QMenuBar {
            background-color: #0d1922;
            color: #c0d8f0;
            border-bottom: 1px solid #1e3044;
            padding: 2px 4px;
        }
        QMenuBar::item:selected {
            background-color: #1a3a5a;
        }
        QMenu {
            background-color: #111e2a;
            color: #c0d8f0;
            border: 1px solid #1e3044;
        }
        QMenu::item:selected {
            background-color: #1a3a5a;
        }
        QMenu::separator {
            height: 1px;
            background: #1e3044;
            margin: 4px 8px;
        }
        QStatusBar {
            background-color: #0d1922;
            color: #6a8aaa;
            border-top: 1px solid #1e3044;
            font-size: 12px;
        }
        QMessageBox {
            background-color: #111e2a;
        }
        QFileDialog {
            background-color: #111e2a;
        }
    """)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
