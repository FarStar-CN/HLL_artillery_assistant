from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from capture import capture_overlay, remove_file
from config import CFG, VK, key_pressed
from logic import compute_mil
from ui.map_view import MapView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project_dir = Path(__file__).resolve().parent.parent
        self.time = QElapsedTimer()
        self.time.start()
        self.mode = "F1"
        self.last_screenshot_path = None
        self.view = MapView(self)

        self.setWindowTitle("HLL_artillery_helper")
        self.resize(1050, 680)

        self._build_ui()
        self._build_menu()
        self._start_timer()

    def _build_ui(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view, 3)

        side_panel = QFrame()
        side_panel.setFixedWidth(240)
        side_panel.setStyleSheet(
            """
            QFrame {
                background-color: #f5f5f5;
                border-left: 1px solid #ccc;
            }
            """
        )
        side_layout = QVBoxLayout(side_panel)

        self.labels = {key: QLabel() for key in "x y mil ang mode".split()}
        for label in self.labels.values():
            label.setStyleSheet(
                """
                QLabel {
                    font-size: 14px;
                    padding: 6px;
                    color: #333;
                }
                """
            )
            side_layout.addWidget(label)

        title = QLabel("Map Controls")
        title.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 8px 6px;
                color: #222;
            }
            """
        )
        side_layout.addWidget(title)

        btn_set_a = QPushButton("Set A Point")
        btn_set_a.setStyleSheet("QPushButton { padding: 8px; font-size: 14px; }")
        btn_set_a.clicked.connect(self._enable_point_selection)
        side_layout.addWidget(btn_set_a)

        btn_top = QPushButton("Always On Top", checkable=True)
        btn_top.setStyleSheet(
            """
            QPushButton {
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:checked {
                background-color: #d0f0ff;
                border: 1px solid #66ccff;
            }
            """
        )
        btn_top.toggled.connect(self._toggle_topmost)
        side_layout.addWidget(btn_top)

        btn_capture = QPushButton("Capture Overlay")
        btn_capture.setStyleSheet("QPushButton { padding: 8px; font-size: 14px; }")
        btn_capture.clicked.connect(self._capture_and_overlay)
        side_layout.addWidget(btn_capture)

        btn_clear = QPushButton("Clear Overlay")
        btn_clear.setStyleSheet("QPushButton { padding: 8px; font-size: 14px; }")
        btn_clear.clicked.connect(self.view.clear_overlay)
        side_layout.addWidget(btn_clear)

        side_layout.addStretch(1)
        layout.addWidget(side_panel)
        self.setCentralWidget(container)
        self.update_sidebar(CFG["MAX_X"], 0.0, compute_mil(CFG["MAX_X"]), 0.0)

    def _build_menu(self):
        menu = self.menuBar().addMenu("File")
        menu.addAction(QAction("Open...", self, shortcut="Ctrl+O", triggered=self._open_map))
        menu.addSeparator()
        menu.addAction(QAction("Exit", self, shortcut="Ctrl+Q", triggered=self.close))

    def _start_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_keyboard)
        self.timer.start(CFG["POLL_MS"])

    def _enable_point_selection(self):
        self.view.begin_set_a_mode()

    def _poll_keyboard(self):
        if self.view.handle_interaction_shortcuts():
            self.time.restart()
            return

        delta_time = self.time.elapsed() / 1000.0
        self.time.restart()

        if key_pressed(VK["F1"]):
            self.mode = "F1"
        elif key_pressed(VK["F2"]):
            self.mode = "F2"

        if self.mode == "F1":
            dx = 0.0
            dy = 0.0
            if key_pressed(VK["W"]):
                dx -= CFG["MOVE_SPEED_X"] * delta_time
            if key_pressed(VK["S"]):
                dx += CFG["MOVE_SPEED_X"] * delta_time
            if key_pressed(VK["A"]):
                dy -= CFG["MOVE_SPEED_Y"] * delta_time
            if key_pressed(VK["D"]):
                dy += CFG["MOVE_SPEED_Y"] * delta_time
            if dx != 0.0 or dy != 0.0:
                self.view.adjust_xy(dx, dy, self.mode)
            return

        dy = 0.0
        if key_pressed(VK["A"]):
            dy -= CFG["MOVE_SPEED_Y"] * delta_time
        if key_pressed(VK["D"]):
            dy += CFG["MOVE_SPEED_Y"] * delta_time
        if dy != 0.0:
            self.view.adjust_xy(0.0, dy, self.mode)

    def _toggle_topmost(self, enabled):
        flags = self.windowFlags()
        if enabled:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    def _open_map(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Map",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)",
        )
        if path:
            self.view.load_img(path)

    def _capture_and_overlay(self):
        try:
            cropped, save_path = capture_overlay(
                str(self.project_dir),
                CFG["LEFT"],
                CFG["TOP"],
                CFG["RIGHT"],
                CFG["BOTTOM"],
                previous_path=self.last_screenshot_path,
            )
        except RuntimeError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return
        except ValueError as exc:
            QMessageBox.warning(self, "Crop Error", str(exc))
            return

        self.last_screenshot_path = save_path
        self.view.set_overlay(cropped, opacity=CFG["OPACITY"])

    def update_sidebar(self, x_value, y_value, mil_value, angle_value):
        mode_name = "Gunner" if self.mode == "F1" else "Loader"
        self.labels["mode"].setText(f"Mode: {mode_name}")
        self.labels["x"].setText(f"Distance: {x_value:.1f} m")
        self.labels["y"].setText(f"Azimuth: {y_value:.1f} deg")
        self.labels["mil"].setText(f"MIL: {mil_value:.2f}")
        self.labels["ang"].setText(f"Relative Angle: {angle_value:.1f} deg")

    def set_status_message(self, message):
        self.statusBar().showMessage(message)

    def clear_status_message(self):
        self.statusBar().clearMessage()

    def closeEvent(self, event):
        remove_file(self.last_screenshot_path)
        event.accept()
