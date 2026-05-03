"""
火炮 profiles 与 MIL-距离换算公式。

STD 模式: mil = mil_base - d / mil_k   (mil_k > 0, 距离越远 MIL 越小)
SPG 模式: mil = mil_base - d / mil_k   (mil_k < 0, 距离越远 MIL 越大)

SPG 扩展射程在标准段之外使用分段线性查表,
由 compute_mil / inverse_mil 自动处理。
"""

from dataclasses import dataclass

from core.logic import (
    effective_distance as _effective_distance,
    profile_compute_mil,
    profile_inverse_mil,
)

# STD 公式常量:  mil = 1002 - d / (1500/356)
MIL_K_DEFAULT = 1500.0 / 356.0
MIL_BASE_DEFAULT = 1002.0


@dataclass(frozen=True)
class ArtilleryProfile:
    """国家 + 射击模式的不可变 profile。"""

    country: str
    mode: str  # "STD" 或 "SPG"

    # ── MIL-距离线性公式系数 ──
    # mil = mil_base - distance / mil_k
    # STD: mil_k > 0, 距离增大时 MIL 减小
    # SPG: mil_k < 0, 距离增大时 MIL 增大
    mil_base: float = MIL_BASE_DEFAULT
    mil_k: float = MIL_K_DEFAULT

    # ── 有效距离范围 (米) ──
    min_distance: float = 100.0
    max_distance: float = 1600.0

    # ── 扇形形状 ──
    # 扇形覆盖 [heading - sector_angle, heading + sector_angle]
    # 如 15° → 30° 楔形; 180° → 完整 360° 圆
    sector_angle: float = 15.0

    # ── 键盘调节速度 ──
    # STD: move_speed_x = 米/秒 (W/S 调距离)
    # SPG: move_speed_mil = 密位/秒 (W/S 调密位)
    move_speed_x: float = 10.0
    move_speed_mil: float = 10.0
    move_speed_ang: float = 1.0
    move_speed_heading: float = 1.0   # Q/E 旋转 heading, °/秒 (仅 SPG)
    tilt_speed: float = 5.0           # Shift+滚轮 tilt 步长, MIL

    # ── SPG: 游戏内密位机械限制 (mil_flat 的合法范围) ──
    spg_mil_min: float = -89.0
    spg_mil_max: float = 466.0

    # ── SPG 扩展射程查表 ──
    # (有效密位, 距离) 对, 按密位升序排列。
    # 首项是线性公式与扩展段的边界。
    # 空元组 → 全线使用线性公式 (STD 模式)。
    extended_range: tuple = ()

    # ── MIL ↔ 距离 换算 (委托到 core/logic.py) ──

    def compute_mil(self, distance_m: float) -> float:
        """距离 (m) → 有效 MIL。"""
        return profile_compute_mil(self, distance_m)

    def inverse_mil(self, mil_value: float) -> float:
        """有效 MIL → 距离 (m)。"""
        return profile_inverse_mil(self, mil_value)

    def compute_effective_distance(self, distance_m: float, delta_mil: float) -> float:
        """用 delta_mil 偏移距离。 d_eff = d - mil_k * delta。"""
        return _effective_distance(self.mil_k, distance_m, delta_mil)


# ═══════════════════════════════════════════════════════════════════════
#  美国
# ═══════════════════════════════════════════════════════════════════════

USA_STD = ArtilleryProfile(
    country="USA", mode="STD",
    mil_base=MIL_BASE_DEFAULT, mil_k=MIL_K_DEFAULT,
    min_distance=100.0, max_distance=1600.0,
    sector_angle=15.0,
    move_speed_x=10.0, move_speed_ang=1.0,
    tilt_speed=1.0,
)

USA_SPG = ArtilleryProfile(
    country="USA", mode="SPG",
    # SPG 公式: MIL = (d - 50) / 1.5  →  d = 1.5 * MIL + 50
    mil_base=-50.0 / 1.5, mil_k=-1.5,
    # 有效 MIL [100, 766] → 距离 [200m, 915m]
    min_distance=200.0, max_distance=915.0,
    sector_angle=180.0,
    move_speed_mil=10.0, move_speed_ang=10.0, move_speed_heading=10.0,
    tilt_speed=1.0,
    # 366 MIL / 600m 以上的扩展射程表
    extended_range=(
        (366, 600),
        (416, 666),
        (466, 732),
        (516, 776),
        (566, 814),
        (616, 852),
        (666, 879),
        (716, 905),
        (766, 915),
    ),
)

# ═══════════════════════════════════════════════════════════════════════
#  英国  (SPG 为占位值, 暂与 STD 相同)
# ═══════════════════════════════════════════════════════════════════════

UK_STD = ArtilleryProfile(
    country="UK", mode="STD",
    mil_base=MIL_BASE_DEFAULT, mil_k=MIL_K_DEFAULT,
    min_distance=100.0, max_distance=1600.0,
    sector_angle=15.0,
    move_speed_x=10.0, move_speed_ang=1.0,
    tilt_speed=1.0,
)

UK_SPG = ArtilleryProfile(
    country="UK", mode="SPG",
    # 占位值 — 目前与 USA_SPG 相同, 待填入英国实际数据
    mil_base=-50.0 / 1.5, mil_k=-1.5,
    min_distance=200.0, max_distance=915.0,
    sector_angle=180.0,
    move_speed_mil=10.0, move_speed_ang=10.0, move_speed_heading=10.0,
    tilt_speed=1.0,
    extended_range=(
        (366, 600),
        (416, 666),
        (466, 732),
        (516, 776),
        (566, 814),
        (616, 852),
        (666, 879),
        (716, 905),
        (766, 915),
    ),
)

# ═══════════════════════════════════════════════════════════════════════
#  苏联  (SPG 为占位值, 目前与 USA_SPG 相同)
# ═══════════════════════════════════════════════════════════════════════

USSR_STD = ArtilleryProfile(
    country="USSR", mode="STD",
    mil_base=MIL_BASE_DEFAULT, mil_k=MIL_K_DEFAULT,
    min_distance=100.0, max_distance=1600.0,
    sector_angle=15.0,
    move_speed_x=10.0, move_speed_ang=1.0,
    tilt_speed=1.0,
)

USSR_SPG = ArtilleryProfile(
    country="USSR", mode="SPG",
    # 占位值 — 目前与 USA_SPG 相同, 待填入苏联实际数据
    mil_base=-50.0 / 1.5, mil_k=-1.5,
    min_distance=200.0, max_distance=915.0,
    sector_angle=180.0,
    move_speed_mil=10.0, move_speed_ang=10.0, move_speed_heading=10.0,
    tilt_speed=1.0,
    extended_range=(
        (366, 600),
        (416, 666),
        (466, 732),
        (516, 776),
        (566, 814),
        (616, 852),
        (666, 879),
        (716, 905),
        (766, 915),
    ),
)

# ═══════════════════════════════════════════════════════════════════════
#  德国  (SPG 为占位值, 目前与 USA_SPG 相同)
# ═══════════════════════════════════════════════════════════════════════

DE_STD = ArtilleryProfile(
    country="DE", mode="STD",
    mil_base=MIL_BASE_DEFAULT, mil_k=MIL_K_DEFAULT,
    min_distance=100.0, max_distance=1600.0,
    sector_angle=15.0,
    move_speed_x=10.0, move_speed_ang=1.0,
    tilt_speed=1.0,
)

DE_SPG = ArtilleryProfile(
    country="DE", mode="SPG",
    # 占位值 — 目前与 USA_SPG 相同, 待填入德国实际数据
    mil_base=-50.0 / 1.5, mil_k=-1.5,
    min_distance=200.0, max_distance=915.0,
    sector_angle=180.0,
    move_speed_mil=10.0, move_speed_ang=10.0, move_speed_heading=10.0,
    tilt_speed=1.0,
    extended_range=(
        (366, 600),
        (416, 666),
        (466, 732),
        (516, 776),
        (566, 814),
        (616, 852),
        (666, 879),
        (716, 905),
        (766, 915),
    ),
)

# ── 注册表 ──

PROFILES = {
    "USA_STD": USA_STD,
    "USA_SPG": USA_SPG,
    "UK_STD": UK_STD,
    "UK_SPG": UK_SPG,
    "USSR_STD": USSR_STD,
    "USSR_SPG": USSR_SPG,
    "DE_STD": DE_STD,
    "DE_SPG": DE_SPG,
}

COUNTRIES = ("USA", "UK", "USSR", "DE")
DEFAULT_COUNTRY = "USA"


def get_profile(country: str, mode: str) -> ArtilleryProfile:
    """按国家和射击模式查找 ArtilleryProfile。"""
    return PROFILES[f"{country}_{mode}"]


def get_default_profile() -> ArtilleryProfile:
    """返回应用启动时的默认 profile。"""
    return USA_STD
