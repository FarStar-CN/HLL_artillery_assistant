import ctypes
from PySide6.QtGui    import QColor
CFG = {
    "MAP_WIDTH_M"   : 2000.0,
    "R_A"           : 25,
    "R_B"           : 30,
    "COLOR_A"       : QColor(0, 255, 0, 220),
    "COLOR_B"       : QColor(255, 0, 0, 180),
    "LINE_COLOR"    : QColor(0, 0, 255, 180),
    "SECTOR_COLOR"  : QColor(0, 120, 255, 80),
    "SECTOR_ANG"    : 15,            # 射界 +-15°
    "SECTOR_R_M"    : 1600.0,
    "FULL"          : 360,
    "MIN_X"         : 100.0,         # 最小距离
    "MAX_X"         : 1600.0,        # 最大距离
    "MOVE_SPEED_X"  : 10.0,          # 距离移动速度（米/秒）
    "MOVE_SPEED_Y"  : 1.0,           # 方位旋转速度（度/秒）
    "POLL_MS"       : 10,
    "LEFT": 724, #左，px
    "RIGHT": 1835, #右，px
    "TOP": 159, #上，px
    "BOTTOM": 1269,  #下,px
    "OPACITY": 0.5, #透明度
}
# 键值
VK = {
    "W": 0x57,
    "A": 0x41,
    "S": 0x53,
    "D": 0x44,
    "F1": 0x70,
    "F2": 0x71,
}

user32 = ctypes.windll.user32
key_pressed = lambda vk: bool(user32.GetAsyncKeyState(vk) & 0x8000)

