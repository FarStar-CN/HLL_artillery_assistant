from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QTimer, Qt
from PySide6.QtGui import QAction, QDoubleValidator
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.capture import capture_overlay, remove_file
from core.config import CFG, VK, key_pressed
from core.country import COUNTRIES, DEFAULT_COUNTRY, get_profile
from sync.desktop_sync import DesktopSyncManager
from ui.map_view import MapView
from ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project_dir = Path(__file__).resolve().parent.parent
        self.time = QElapsedTimer()
        self.time.start()
        self.mode = "F1"
        self.calc_mode = "STD"
        self.country = DEFAULT_COUNTRY
        self.active_profile = get_profile(self.country, self.calc_mode)
        self.last_screenshot_path = None
        self.view = MapView(self)
        self.view.active_profile = self.active_profile
        self.sync_manager = DesktopSyncManager(self.project_dir, CFG)
        self.sync_manager.set_status_callback(self._handle_sync_status)

        self.setWindowTitle("HLL Artillery Assistant")
        self.resize(1050, 680)

        self._build_ui()
        self._build_menu()
        self._start_timer()

    def _build_ui(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view, 3)

        # ── side panel (dark theme) ──
        side = QFrame()
        side.setFixedWidth(250)
        side.setStyleSheet("""
            QFrame {
                background-color: #0f1923;
                border-left: 1px solid #1e3044;
            }
            QGroupBox {
                color: #7eb8da;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #1e3044;
                border-radius: 8px;
                margin-top: 12px;
                padding: 14px 10px 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QLabel {
                color: #c0d8f0;
                font-size: 13px;
            }
            QPushButton {
                background: #1a2a3a;
                color: #c0d8f0;
                border: 1px solid #2a4a6a;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #243850;
                border-color: #4a8abe;
            }
            QPushButton:pressed {
                background: #0f1a28;
            }
            QPushButton:checked {
                background: #1a3a5a;
                border-color: #5aacff;
            }
        """)
        side_layout = QVBoxLayout(side)
        side_layout.setSpacing(8)

        # ── Country selection ──
        country_row = QHBoxLayout()
        self._btn_country = {}
        for c in COUNTRIES:
            btn = QPushButton(c)
            btn.setCheckable(True)
            btn.setChecked(c == self.country)
            btn.clicked.connect(lambda checked, country=c: self._switch_country(country))
            country_row.addWidget(btn)
            self._btn_country[c] = btn
        side_layout.addLayout(country_row)

        # ── Mode toggle ──
        toggle_row = QHBoxLayout()
        self._btn_std = QPushButton("STD")
        self._btn_std.setCheckable(True)
        self._btn_std.setChecked(True)
        self._btn_std.clicked.connect(lambda: self._switch_calc_mode("STD"))
        toggle_row.addWidget(self._btn_std)

        self._btn_spg = QPushButton("SPG")
        self._btn_spg.setCheckable(True)
        self._btn_spg.clicked.connect(lambda: self._switch_calc_mode("SPG"))
        toggle_row.addWidget(self._btn_spg)
        side_layout.addLayout(toggle_row)

        # ── Telemetry ──
        grp_telem = QGroupBox("Telemetry")
        telem_form = QFormLayout(grp_telem)
        telem_form.setSpacing(4)

        EDIT_KEYS = {"x", "y", "mil", "ang", "tilt"}
        self._metric = {}
        self._edits = {}
        for key, label_text in [("mode", "Mode"), ("x", "Distance"), ("y", "Azimuth"),
                                ("mil", "MIL"), ("ang", "Relative"), ("tilt", "Tilt")]:
            if key in EDIT_KEYS:
                widget = QLineEdit("-")
                widget.setAlignment(Qt.AlignRight)
                widget.setValidator(QDoubleValidator())
                widget.returnPressed.connect(self._make_edit_handler(key))
                widget.setStyleSheet("""
                    QLineEdit {
                        font-size: 15px; font-weight: 700; color: #e8f4ff;
                        background: transparent; border: 1px solid transparent;
                        border-radius: 3px; padding: 2px 4px;
                    }
                    QLineEdit:hover {
                        background: rgba(255,255,255,0.04);
                        border: 1px solid #2a4a6a;
                    }
                    QLineEdit:focus {
                        background: rgba(255,255,255,0.08);
                        border: 1px solid #4a8abe;
                    }
                """)
                self._edits[key] = widget
            else:
                widget = QLabel("-")
                widget.setStyleSheet("font-size: 15px; font-weight: 700; color: #e8f4ff;")
            self._metric[key] = widget
            key_lbl = QLabel(label_text)
            key_lbl.setStyleSheet("font-size: 11px; color: #6a8aaa;")
            telem_form.addRow(key_lbl, widget)
        side_layout.addWidget(grp_telem)

        # ── Map Controls ──
        grp_ctrl = QGroupBox("Map Controls")
        ctrl_layout = QVBoxLayout(grp_ctrl)

        btn_set_a = QPushButton("Set A Point")
        btn_set_a.clicked.connect(self._enable_point_selection)
        ctrl_layout.addWidget(btn_set_a)

        self.btn_top = QPushButton("Always On Top")
        self.btn_top.setCheckable(True)
        self.btn_top.toggled.connect(self._toggle_topmost)
        ctrl_layout.addWidget(self.btn_top)

        btn_capture = QPushButton("Capture Overlay")
        btn_capture.clicked.connect(self._capture_and_overlay)
        ctrl_layout.addWidget(btn_capture)

        btn_clear = QPushButton("Clear Overlay")
        btn_clear.clicked.connect(self._clear_overlay_and_sync)
        ctrl_layout.addWidget(btn_clear)

        side_layout.addWidget(grp_ctrl)

        # ── Mobile Sync ──
        grp_sync = QGroupBox("Mobile Sync")
        sync_layout = QVBoxLayout(grp_sync)

        self._sync_indicator = QLabel("● Idle")
        self._sync_indicator.setStyleSheet("font-size: 13px; font-weight: 600; color: #6a8aaa;")
        sync_layout.addWidget(self._sync_indicator)

        self._sync_peer_lbl = QLabel("Peer: -")
        self._sync_peer_lbl.setStyleSheet("font-size: 11px; color: #6a8aaa;")
        self._sync_peer_lbl.setWordWrap(True)
        self._sync_peer_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._sync_peer_lbl.setCursor(Qt.IBeamCursor)
        sync_layout.addWidget(self._sync_peer_lbl)

        self._sync_viewer_lbl = QLabel("Viewer: -")
        self._sync_viewer_lbl.setStyleSheet("font-size: 11px; color: #6a8aaa;")
        self._sync_viewer_lbl.setWordWrap(True)
        sync_layout.addWidget(self._sync_viewer_lbl)

        btn_row = QHBoxLayout()
        btn_start = QPushButton("Start")
        btn_start.clicked.connect(self._start_mobile_sync)
        btn_start.setStyleSheet("QPushButton { color: #66f0a9; } QPushButton:hover { border-color: #66f0a9; }")
        btn_row.addWidget(btn_start)

        btn_stop = QPushButton("Stop")
        btn_stop.clicked.connect(self._stop_mobile_sync)
        btn_stop.setStyleSheet("QPushButton { color: #ff7070; } QPushButton:hover { border-color: #ff7070; }")
        btn_row.addWidget(btn_stop)

        sync_layout.addLayout(btn_row)
        side_layout.addWidget(grp_sync)

        side_layout.addStretch(1)
        layout.addWidget(side)
        self.setCentralWidget(container)
        self._update_metric_display(self.active_profile.max_distance, 0.0, self.active_profile.compute_mil(self.active_profile.max_distance), 0.0)

    def _build_menu(self):
        menu = self.menuBar().addMenu("File")
        menu.addAction(QAction("Open...", self, shortcut="Ctrl+O", triggered=self._open_map))
        menu.addSeparator()
        menu.addAction(QAction("Exit", self, shortcut="Ctrl+Q", triggered=self.close))

        self.menuBar().addAction(QAction("Settings...", self, shortcut="Ctrl+,", triggered=self._open_settings))

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

        if self.calc_mode != "SPG":
            if key_pressed(VK["F1"]):
                self.mode = "F1"
            elif key_pressed(VK["F2"]):
                self.mode = "F2"

        if self.calc_mode == "SPG":
            dx = 0.0
            dy_az = 0.0
            dy_head = 0.0
            if key_pressed(VK["W"]):
                dx += self.active_profile.move_speed_x * delta_time
            if key_pressed(VK["S"]):
                dx -= self.active_profile.move_speed_x * delta_time
            if key_pressed(VK["A"]):
                dy_az -= self.active_profile.move_speed_y * delta_time
            if key_pressed(VK["D"]):
                dy_az += self.active_profile.move_speed_y * delta_time
            if key_pressed(VK["Q"]):
                dy_head -= self.active_profile.move_speed_y * delta_time
            if key_pressed(VK["E"]):
                dy_head += self.active_profile.move_speed_y * delta_time
            if dy_head != 0.0:
                self.view.adjust_xy(0.0, dy_head, "F2")
            if dx != 0.0 or dy_az != 0.0:
                self.view.adjust_xy(dx, dy_az, "F1")
            return

        if self.mode == "F1":
            dx = 0.0
            dy = 0.0
            if key_pressed(VK["W"]):
                dx -= self.active_profile.move_speed_x * delta_time
            if key_pressed(VK["S"]):
                dx += self.active_profile.move_speed_x * delta_time
            if key_pressed(VK["A"]):
                dy -= self.active_profile.move_speed_y * delta_time
            if key_pressed(VK["D"]):
                dy += self.active_profile.move_speed_y * delta_time
            if dx != 0.0 or dy != 0.0:
                self.view.adjust_xy(dx, dy, self.mode)
            return

        dy = 0.0
        if key_pressed(VK["A"]):
            dy -= self.active_profile.move_speed_y * delta_time
        if key_pressed(VK["D"]):
            dy += self.active_profile.move_speed_y * delta_time
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
            self._publish_sync_assets()

    def _open_settings(self):
        dialog = SettingsDialog(self, self.project_dir)
        dialog.exec()

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
        self._publish_sync_assets()

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

    def _clear_overlay_and_sync(self):
        self.view.clear_overlay()
        self._publish_sync_assets()

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

    def _update_active_profile(self):
        self.active_profile = get_profile(self.country, self.calc_mode)
        self.view.active_profile = self.active_profile

    def _switch_country(self, country):
        if country == self.country:
            return
        self.country = country
        for c, btn in self._btn_country.items():
            btn.setChecked(c == country)
        self._update_active_profile()
        self.view._clear_targeting()
        self._publish_sync_assets()
        self._publish_sync_state()

    def _switch_calc_mode(self, new_mode):
        if new_mode == self.calc_mode:
            return
        self.calc_mode = new_mode
        self._btn_std.setChecked(new_mode == "STD")
        self._btn_spg.setChecked(new_mode == "SPG")
        self._update_active_profile()
        self.view.switch_calc_mode(new_mode)
        self._publish_sync_assets()
        self._publish_sync_state()

    def _publish_sync_state(self):
        if not self.sync_manager.is_running():
            return

        payload = self.view.export_sync_state(self.mode, self.calc_mode)
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

        color_map = {
            "connected": ("#66f0a9", "●"),
            "waiting_client": ("#ffcd70", "●"),
            "starting": ("#ffcd70", "○"),
            "error": ("#ff7070", "●"),
            "missing_dependency": ("#ff7070", "●"),
            "stopping": ("#6a8aaa", "○"),
        }
        dot_color, dot = color_map.get(status, ("#6a8aaa", "○"))

        label = self.sync_manager.connection_label
        extra = f" ({label})" if label else ""
        err = self.sync_manager.last_error
        extra += f" — {err}" if err else ""

        self._sync_indicator.setText(f"{dot} {status.replace('_',' ').title()}{extra}")
        self._sync_indicator.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {dot_color};")

        self._sync_peer_lbl.setText(f"Peer: {peer_id}")
        self._sync_viewer_lbl.setText(f"Viewer: {viewer_text}")

    def _update_metric_display(self, x_value, y_value, mil_value, angle_value, tilt_value=0.0):
        if self.calc_mode == "STD":
            mode_name = f"{self.country} · STD · {'Gunner' if self.mode == 'F1' else 'Loader'}"
            mode_color = '#71d8ff' if self.mode == 'F1' else '#ffcd70'
        else:
            mode_name = f"{self.country} · SPG"
            mode_color = '#90ffb0'
        self._metric["mode"].setText(mode_name)
        self._metric["mode"].setStyleSheet(f"font-size: 15px; font-weight: 700; color: {mode_color};")
        self._metric["x"].setText(f"{x_value:.1f}")
        self._metric["y"].setText(f"{y_value:.1f}")
        self._metric["mil"].setText(f"{mil_value:.2f}")
        self._metric["ang"].setText(f"{angle_value:.1f}")
        self._metric["tilt"].setText(f"{tilt_value:.1f}")

    def _make_edit_handler(self, key):
        def handler():
            text = self._edits[key].text().strip()
            try:
                value = float(text)
            except ValueError:
                self.view._notify_sidebar()
                return
            ok = False
            if key == "x":
                ok = self.view.set_distance(value)
            elif key == "y":
                ok = self.view.set_azimuth(value)
            elif key == "mil":
                ok = self.view.set_mil(value)
            elif key == "ang":
                ok = self.view.set_relative_angle(value)
            elif key == "tilt":
                ok = self.view.set_tilt(value)
            if not ok:
                self.view._notify_sidebar()
        return handler

    def update_sidebar(self, x_value, y_value, mil_value, angle_value, tilt_value=0.0):
        self._update_metric_display(x_value, y_value, mil_value, angle_value, tilt_value)

    def set_status_message(self, message):
        self.statusBar().showMessage(message)

    def clear_status_message(self):
        self.statusBar().clearMessage()

    def closeEvent(self, event):
        self.sync_manager.stop()
        remove_file(self.last_screenshot_path)
        event.accept()
