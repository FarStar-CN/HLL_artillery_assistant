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
from sync.desktop_sync import DesktopSyncManager
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
        self.sync_manager = DesktopSyncManager(self.project_dir, CFG)
        self.sync_manager.set_status_callback(self._handle_sync_status)

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

        sync_title = QLabel("Mobile Sync")
        sync_title.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 12px 6px 8px;
                color: #222;
            }
            """
        )
        side_layout.addWidget(sync_title)

        self.sync_status = QLabel("Sync: idle")
        self.sync_status.setWordWrap(True)
        self.sync_status.setStyleSheet("QLabel { font-size: 13px; padding: 4px 6px; color: #333; }")
        side_layout.addWidget(self.sync_status)

        self.sync_peer = QLabel("Peer ID: -")
        self.sync_peer.setWordWrap(True)
        self.sync_peer.setStyleSheet("QLabel { font-size: 12px; padding: 4px 6px; color: #333; }")
        side_layout.addWidget(self.sync_peer)

        self.sync_viewer = QLabel("Viewer file: -")
        self.sync_viewer.setWordWrap(True)
        self.sync_viewer.setStyleSheet("QLabel { font-size: 12px; padding: 4px 6px; color: #333; }")
        side_layout.addWidget(self.sync_viewer)

        btn_start_sync = QPushButton("Start Mobile Sync")
        btn_start_sync.setStyleSheet("QPushButton { padding: 8px; font-size: 14px; }")
        btn_start_sync.clicked.connect(self._start_mobile_sync)
        side_layout.addWidget(btn_start_sync)

        btn_stop_sync = QPushButton("Stop Mobile Sync")
        btn_stop_sync.setStyleSheet("QPushButton { padding: 8px; font-size: 14px; }")
        btn_stop_sync.clicked.connect(self._stop_mobile_sync)
        side_layout.addWidget(btn_stop_sync)

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

        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self._publish_sync_state)
        self.sync_timer.start(int(1000 / CFG["SYNC_STATE_FPS"]))

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

    def _start_mobile_sync(self):
        started = self.sync_manager.start()
        if not started:
            self._refresh_sync_ui()
            return

        self._refresh_sync_ui()
        self._publish_sync_assets()
        self._publish_sync_state()

    def _stop_mobile_sync(self):
        self.sync_manager.stop()
        self._refresh_sync_ui()

    def _publish_sync_assets(self):
        if not self.sync_manager.is_running():
            return

        state = self.view.export_sync_assets()
        base_map = state.get("base_map")
        if base_map is not None:
            self.sync_manager.publish_asset("base_map", **base_map)

        overlay = state.get("overlay")
        if overlay is not None:
            self.sync_manager.publish_asset("overlay", **overlay)
        else:
            self.sync_manager.clear_asset("overlay")

    def _publish_sync_state(self):
        if not self.sync_manager.is_running():
            return

        payload = self.view.export_sync_state(self.mode)
        self.sync_manager.publish_state(payload)

    def _handle_sync_status(self, status, error_message):
        self._refresh_sync_ui()
        if error_message:
            self.set_status_message(f"Sync error: {error_message}")

    def _refresh_sync_ui(self):
        status = self.sync_manager.status
        peer_id = self.sync_manager.peer_id or "-"
        viewer_file = self.sync_manager.viewer_file
        viewer_text = str(viewer_file) if viewer_file else "-"

        status_line = f"Sync: {status}"
        if self.sync_manager.connection_label:
            status_line += f" ({self.sync_manager.connection_label})"
        if self.sync_manager.last_error:
            status_line += f" | {self.sync_manager.last_error}"

        self.sync_status.setText(status_line)
        self.sync_peer.setText(f"Peer ID: {peer_id}")
        self.sync_viewer.setText(f"Viewer file: {viewer_text}")

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
        self.sync_manager.stop()
        remove_file(self.last_screenshot_path)
        event.accept()
