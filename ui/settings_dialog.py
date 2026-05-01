from dataclasses import dataclass
from typing import Any, Optional

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import CFG, save_settings


@dataclass
class FieldSpec:
    key: str
    label: str
    widget_type: str  # "int_spin", "double_spin", "color", "checkbox", "lineedit"
    default: Any
    range_: Optional[tuple] = None
    decimals: Optional[int] = None


TAB_FIELDS = {
    "Appearance": [
        FieldSpec("R_A",                 "A-Point Radius (px)",       "int_spin",    25,     (1, 200)),
        FieldSpec("R_B",                 "B-Point Radius (px)",       "int_spin",    30,     (1, 200)),
        FieldSpec("PREVIEW_ARROW_SIZE_PX","Preview Arrow Size (px)",  "double_spin", 50.0,   (5.0, 200.0), 1),
        FieldSpec("SET_A_MIN_DRAG_PX",   "Min Drag to Set A (px)",   "double_spin", 5.0,    (0.0, 50.0), 1),
        FieldSpec("COLOR_A",             "A-Point Color",             "color", None),
        FieldSpec("COLOR_B",             "B-Point Color",             "color", None),
        FieldSpec("LINE_COLOR",          "Line Color",                "color", None),
        FieldSpec("SECTOR_COLOR",        "Sector Color",              "color", None),
    ],
    "Capture & Overlay": [
        FieldSpec("LEFT",           "Crop Left (px)",           "int_spin",    724,  (0, 9999)),
        FieldSpec("TOP",            "Crop Top (px)",            "int_spin",    159,  (0, 9999)),
        FieldSpec("RIGHT",          "Crop Right (px)",          "int_spin",    1835, (0, 9999)),
        FieldSpec("BOTTOM",         "Crop Bottom (px)",         "int_spin",    1269, (0, 9999)),
        FieldSpec("OPACITY",        "Overlay Opacity",          "double_spin", 0.5,  (0.0, 1.0), 2),
    ],
    "Mobile Sync": [
        FieldSpec("SYNC_STATE_FPS",         "State Sync FPS",       "int_spin",    30,  (1, 60)),
        FieldSpec("SYNC_IMAGE_JPEG_QUALITY","JPEG Quality",         "int_spin",    80,  (1, 100)),
        FieldSpec("SYNC_DEBUG_LEVEL",       "Debug Level",          "int_spin",    3,   (0, 5)),
        FieldSpec("SYNC_SIGNAL_HOST",       "Signal Host",          "lineedit",    "0.peerjs.com"),
        FieldSpec("SYNC_SIGNAL_PORT",       "Signal Port",          "int_spin",    443, (1, 65535)),
        FieldSpec("SYNC_SIGNAL_PATH",       "Signal Path",          "lineedit",    "/"),
        FieldSpec("SYNC_SIGNAL_KEY",        "Signal Key",           "lineedit",    "peerjs"),
        FieldSpec("SYNC_SIGNAL_SECURE",     "Secure Connection",    "checkbox",    True),
    ],
}


class SettingsDialog(QDialog):
    def __init__(self, parent, project_dir):
        super().__init__(parent)
        self.project_dir = project_dir
        self._working = {}
        self._widgets = {}
        self._color_labels = {}  # key -> QLabel showing rgba text

        self._seed_working()
        self._build_ui()
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)

    # ── working copy ──

    def _seed_working(self):
        for fields in TAB_FIELDS.values():
            for spec in fields:
                val = CFG.get(spec.key, spec.default)
                if isinstance(val, QColor):
                    val = [val.red(), val.green(), val.blue(), val.alpha()]
                self._working[spec.key] = val

    # ── build UI ──

    def _build_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        for tab_name, fields in TAB_FIELDS.items():
            tabs.addTab(self._build_tab(fields, tab_name), tab_name)
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_tab(self, fields, tab_name):
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(0, 0, 0, 0)

        if tab_name == "Capture & Overlay":
            outer.addWidget(self._make_crop_group(fields))
            outer.addWidget(self._make_overlay_group(fields))
            outer.addStretch()
        elif tab_name == "Mobile Sync":
            outer.addWidget(self._make_sync_timing_group(fields))
            outer.addWidget(self._make_signal_group(fields))
            outer.addStretch()
        else:
            form = QFormLayout()
            for spec in fields:
                form.addRow(spec.label, self._create_field(spec))
            outer.addLayout(form)
            outer.addStretch()

        return widget

    # ── groups ──

    def _make_crop_group(self, fields):
        grp = QGroupBox("Crop Region")
        form = QFormLayout(grp)
        for spec in fields:
            if spec.key in ("LEFT", "TOP", "RIGHT", "BOTTOM"):
                form.addRow(spec.label, self._create_field(spec))
        return grp

    def _make_overlay_group(self, fields):
        grp = QGroupBox("Overlay")
        form = QFormLayout(grp)
        for spec in fields:
            if spec.key == "OPACITY":
                form.addRow(spec.label, self._create_field(spec))
        return grp

    def _make_sync_timing_group(self, fields):
        grp = QGroupBox("Image & Timing")
        form = QFormLayout(grp)
        for spec in fields:
            if spec.key in ("SYNC_STATE_FPS", "SYNC_IMAGE_JPEG_QUALITY", "SYNC_DEBUG_LEVEL"):
                form.addRow(spec.label, self._create_field(spec))
        return grp

    def _make_signal_group(self, fields):
        grp = QGroupBox("Signal Server")
        form = QFormLayout(grp)
        for spec in fields:
            if spec.key in ("SYNC_SIGNAL_HOST", "SYNC_SIGNAL_PORT", "SYNC_SIGNAL_PATH",
                            "SYNC_SIGNAL_KEY", "SYNC_SIGNAL_SECURE"):
                form.addRow(spec.label, self._create_field(spec))
        return grp

    # ── field factories ──

    def _create_field(self, spec):
        if spec.widget_type == "int_spin":
            return self._create_int_spin(spec)
        elif spec.widget_type == "double_spin":
            return self._create_double_spin(spec)
        elif spec.widget_type == "color":
            return self._create_color_picker(spec)
        elif spec.widget_type == "checkbox":
            return self._create_checkbox(spec)
        elif spec.widget_type == "lineedit":
            return self._create_lineedit(spec)
        return QLabel("?")

    def _create_int_spin(self, spec):
        w = QSpinBox()
        lo, hi = spec.range_ or (0, 999999)
        w.setRange(lo, hi)
        w.setValue(int(self._working[spec.key]))
        w.valueChanged.connect(lambda v: self._working.update({spec.key: v}))
        self._widgets[spec.key] = w
        return w

    def _create_double_spin(self, spec):
        w = QDoubleSpinBox()
        lo, hi = spec.range_ or (0.0, 999999.0)
        decimals = spec.decimals or 2
        w.setRange(lo, hi)
        w.setDecimals(decimals)
        w.setSingleStep(10.0 ** -decimals)
        w.setValue(float(self._working[spec.key]))
        w.valueChanged.connect(lambda v: self._working.update({spec.key: v}))
        self._widgets[spec.key] = w
        return w

    def _create_checkbox(self, spec):
        w = QCheckBox()
        w.setChecked(bool(self._working[spec.key]))
        w.toggled.connect(lambda v: self._working.update({spec.key: v}))
        self._widgets[spec.key] = w
        return w

    def _create_lineedit(self, spec):
        w = QLineEdit()
        w.setText(str(self._working[spec.key]))
        w.textChanged.connect(lambda v: self._working.update({spec.key: v}))
        self._widgets[spec.key] = w
        return w

    def _create_color_picker(self, spec):
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)

        rgba = self._working[spec.key]
        qcolor = QColor(*rgba)

        swatch = QPushButton()
        swatch.setFixedSize(36, 24)
        swatch.setStyleSheet(self._swatch_style(qcolor))
        swatch.clicked.connect(lambda: self._pick_color(spec.key, swatch))
        row.addWidget(swatch)

        label = QLabel(f"rgba({rgba[0]}, {rgba[1]}, {rgba[2]}, {rgba[3]})")
        label.setStyleSheet("font-size: 12px; color: #aaa;")
        row.addWidget(label)
        row.addStretch()

        self._widgets[spec.key] = swatch
        self._color_labels[spec.key] = label
        return container

    def _pick_color(self, key, swatch):
        current = QColor(*self._working[key])
        color = QColorDialog.getColor(current, self, "Pick Color")
        if color.isValid():
            rgba = [color.red(), color.green(), color.blue(), color.alpha()]
            self._working[key] = rgba
            swatch.setStyleSheet(self._swatch_style(color))
            self._color_labels[key].setText(f"rgba({rgba[0]}, {rgba[1]}, {rgba[2]}, {rgba[3]})")

    @staticmethod
    def _swatch_style(qcolor):
        return (
            f"background-color: rgba({qcolor.red()},{qcolor.green()},"
            f"{qcolor.blue()},{qcolor.alpha()}); "
            f"border: 1px solid #888; border-radius: 3px;"
        )

    # ── accept ──

    def _on_accept(self):
        # Collect all keys managed by the dialog
        all_keys = []
        for fields in TAB_FIELDS.values():
            for spec in fields:
                all_keys.append(spec.key)

        # Apply working values to live CFG
        for key in all_keys:
            if key not in self._working:
                continue
            val = self._working[key]
            if isinstance(CFG.get(key), QColor) and isinstance(val, list) and len(val) == 4:
                CFG[key] = QColor(*val)
            else:
                CFG[key] = val

        # Persist
        save_settings(self.project_dir, all_keys, CFG)
        super().accept()
