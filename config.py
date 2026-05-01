import ctypes

from PySide6.QtGui import QColor


CFG = {
    "MAP_WIDTH_M": 2000.0,
    "R_A": 25,
    "R_B": 30,
    "COLOR_A": QColor(0, 255, 0, 220),
    "COLOR_B": QColor(255, 0, 0, 180),
    "LINE_COLOR": QColor(0, 0, 255, 180),
    "SECTOR_COLOR": QColor(0, 120, 255, 80),
    "SECTOR_ANG": 15,
    "SECTOR_R_M": 1600.0,
    "MIN_X": 100.0,
    "MAX_X": 1600.0,
    "MOVE_SPEED_X": 10.0,
    "MOVE_SPEED_Y": 1.0,
    "POLL_MS": 10,
    "SYNC_STATE_FPS": 30,
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
    "SYNC_DEBUG_LEVEL": 3,
    "SYNC_IMAGE_JPEG_QUALITY": 80,
    "LEFT": 724,
    "RIGHT": 1835,
    "TOP": 159,
    "BOTTOM": 1269,
    "OPACITY": 0.5,
    "PREVIEW_SECTOR_ALPHA": 45,
    "PREVIEW_ARROW_SIZE_PX": 50.0,
    "SET_A_MIN_DRAG_PX": 5.0,
}


VK = {
    "W": 0x57,
    "A": 0x41,
    "S": 0x53,
    "D": 0x44,
    "F1": 0x70,
    "F2": 0x71,
    "SHIFT": 0x10,
    "ESC": 0x1B,
}


user32 = ctypes.windll.user32
key_pressed = lambda vk: bool(user32.GetAsyncKeyState(vk) & 0x8000)
