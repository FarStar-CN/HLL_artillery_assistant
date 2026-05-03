import ctypes
import json
from pathlib import Path

from PySide6.QtGui import QColor


CFG = {
    # ================================================================
    #  Hardcoded / Calculation Constants
    #  (not exposed in Settings — change only in source)
    # ================================================================

    # Map & targeting model
    "MAP_WIDTH_M": 2000.0,
    "PREVIEW_SECTOR_ALPHA": 45,

    # Keyboard / input
    "POLL_MS": 10,

    # ================================================================
    #  User-Configurable Settings
    #  (editable via File > Settings...)
    # ================================================================

    # Appearance — points & lines
    "R_A": 25,
    "R_B": 30,
    "COLOR_A": QColor(0, 255, 0, 220),
    "COLOR_B": QColor(255, 0, 0, 180),
    "LINE_WIDTH":2,
    "LINE_COLOR": QColor(0, 0, 255, 180),
    "DASH_LINE_WIDTH":2,
    "DASH_LINE_COLOR":QColor(255, 255, 255, 80),
    "SECTOR_COLOR": QColor(0, 120, 255, 80),
    "PREVIEW_ARROW_SIZE_PX": 50.0,
    "SET_A_MIN_DRAG_PX": 5.0,

    # SPG sector layers
    "SPG_INNER_SECTOR_COLOR": QColor(0, 180, 255, 60),
    "SPG_OUTER_SECTOR_COLOR": QColor(0, 180, 255, 30),
    "SPG_MAX_RANGE_COLOR": QColor(0, 0, 0, 200),
    "SPG_MAX_RANGE_WIDTH": 8.0,
    "SPG_DYN_RANGE_COLOR": QColor(255, 0, 0, 180),
    "SPG_DYN_RANGE_WIDTH": 2.0,

    # SPG sector z-ordering
    "SPG_INNER_SECTOR_Z": 1.0,
    "SPG_OUTER_SECTOR_Z": 1.05,
    "SPG_MAX_RANGE_Z": 0.8,
    "SPG_DYN_RANGE_Z": 0.85,

    # Screen capture & overlay
    "LEFT": 724,
    "RIGHT": 1835,
    "TOP": 159,
    "BOTTOM": 1269,
    "OPACITY": 0.5,

    # Mobile sync — connection
    "SYNC_SIGNAL_HOST": "0.peerjs.com",
    "SYNC_SIGNAL_PORT": 443,
    "SYNC_SIGNAL_PATH": "/",
    "SYNC_SIGNAL_KEY": "peerjs",
    "SYNC_SIGNAL_SECURE": True,
    "SYNC_ICE_SERVERS": [
        {"urls": "stun:stun.l.google.com:19302"},
        {
            "urls": [
                "turn:openrelay.metered.ca:80",
                "turn:openrelay.metered.ca:443",
            ],
            "username": "openrelayproject",
            "credential": "openrelayproject",
        },
    ],

    # Mobile sync — behaviour
    "SYNC_STATE_FPS": 30,
    "SYNC_IMAGE_JPEG_QUALITY": 80,
    "SYNC_DEBUG_LEVEL": 3,
}


VK = {
    "W": 0x57,
    "A": 0x41,
    "S": 0x53,
    "D": 0x44,
    "Q": 0x51,
    "E": 0x45,
    "F1": 0x70,
    "F2": 0x71,
    "SHIFT": 0x10,
    "ESC": 0x1B,
}


user32 = ctypes.windll.user32
key_pressed = lambda vk: bool(user32.GetAsyncKeyState(vk) & 0x8000)

SETTINGS_FILE_NAME = "settings.json"


def _cfg_to_serializable(cfg, keys):
    """Convert CFG values to JSON-serializable plain types.
    QColor -> [r, g, b, a] list."""
    result = {}
    for key in keys:
        if key not in cfg:
            continue
        val = cfg[key]
        if isinstance(val, QColor):
            result[key] = [val.red(), val.green(), val.blue(), val.alpha()]
        else:
            result[key] = val
    return result


def save_settings(project_dir, keys, cfg):
    """Write settings for the given keys from cfg to settings.json."""
    data = _cfg_to_serializable(cfg, keys)
    path = Path(project_dir) / SETTINGS_FILE_NAME
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_settings(project_dir):
    """Read settings.json and return the dict, or None if missing/invalid."""
    path = Path(project_dir) / SETTINGS_FILE_NAME
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def apply_loaded_settings(loaded, target_cfg):
    """Merge loaded JSON dict into target CFG dict in place.
    Restores QColor from [r, g, b, a] lists."""
    for key, value in loaded.items():
        if key not in target_cfg:
            continue
        if isinstance(target_cfg[key], QColor) and isinstance(value, list) and len(value) == 4:
            target_cfg[key] = QColor(*value)
        else:
            target_cfg[key] = value
