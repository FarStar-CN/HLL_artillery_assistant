import math


CARDINAL_HEADINGS = (0, 90, 180, 270)


def pixels_per_meter(map_pixel_width, map_width_m):
    return map_pixel_width / map_width_m


def angle_from_points(origin_x, origin_y, target_x, target_y):
    return math.degrees(math.atan2(target_x - origin_x, origin_y - target_y)) % 360


def snap_to_cardinal(angle_deg):
    return min(
        CARDINAL_HEADINGS,
        key=lambda heading: abs((angle_deg - heading + 180) % 360 - 180),
    )


def clamp_distance(distance_m, min_distance_m, max_distance_m):
    return max(min_distance_m, min(max_distance_m, distance_m))


def clamp_to_sector(angle_deg, heading_deg, sector_angle_deg):
    delta = (angle_deg - heading_deg + 360) % 360
    delta = delta - 360 if delta > 180 else delta

    if delta < -sector_angle_deg:
        return (heading_deg - sector_angle_deg) % 360
    if delta > sector_angle_deg:
        return (heading_deg + sector_angle_deg) % 360
    return angle_deg % 360


def compute_target_position(origin_x, origin_y, distance_m, azimuth_deg, ppm):
    distance_px = distance_m * ppm
    radians_value = math.radians(azimuth_deg)
    dx = math.sin(radians_value) * distance_px
    dy = -math.cos(radians_value) * distance_px
    return origin_x + dx, origin_y + dy


def project_point_to_ray(origin_x, origin_y, target_x, target_y, angle_deg):
    radians_value = math.radians(angle_deg)
    direction_x = math.sin(radians_value)
    direction_y = -math.cos(radians_value)

    offset_x = target_x - origin_x
    offset_y = target_y - origin_y
    projection = max(0.0, offset_x * direction_x + offset_y * direction_y)
    return (
        origin_x + direction_x * projection,
        origin_y + direction_y * projection,
    )


def point_distance(point_a_x, point_a_y, point_b_x, point_b_y):
    return math.hypot(point_b_x - point_a_x, point_b_y - point_a_y)


def relative_angle(angle_deg, heading_deg):
    if heading_deg is None:
        return 0.0
    return (angle_deg - heading_deg + 540) % 360 - 180


# ═══════════════════════════════════════════════════════════════════════
#  MIL ↔ 距离 线性公式
# ═══════════════════════════════════════════════════════════════════════

def mil_from_distance(mil_base, mil_k, distance_m):
    """mil = mil_base - d / mil_k"""
    return mil_base - distance_m / mil_k


def distance_from_mil(mil_base, mil_k, mil_value):
    """d = mil_k * (mil_base - mil)"""
    return mil_k * (mil_base - mil_value)


def effective_distance(mil_k, distance_m, delta_mil):
    """d_eff = d - mil_k * delta"""
    return distance_m - mil_k * delta_mil


# ═══════════════════════════════════════════════════════════════════════
#  SPG 扩展射程 分段线性插值
#  table: ((有效密位, 距离), ...) 按密位升序排列
# ═══════════════════════════════════════════════════════════════════════

def interp_mil_to_dist(table, mil_value):
    """扩展段 MIL → 距离。超出表范围 clamp 到端点。"""
    for i in range(len(table) - 1):
        m_lo, d_lo = table[i]
        m_hi, d_hi = table[i + 1]
        if m_lo <= mil_value <= m_hi:
            t = (mil_value - m_lo) / (m_hi - m_lo)
            return d_lo + t * (d_hi - d_lo)
    return table[-1][1]


def interp_dist_to_mil(table, distance_m):
    """扩展段 距离 → MIL。超出表范围 clamp 到端点。"""
    for i in range(len(table) - 1):
        m_lo, d_lo = table[i]
        m_hi, d_hi = table[i + 1]
        if d_lo <= distance_m <= d_hi:
            t = (distance_m - d_lo) / (d_hi - d_lo)
            return m_lo + t * (m_hi - m_lo)
    return table[-1][0]


# ═══════════════════════════════════════════════════════════════════════
#  Profile-aware 封装 (自动处理 extended_range 标准段/扩展段分派)
# ═══════════════════════════════════════════════════════════════════════

def profile_compute_mil(profile, distance_m):
    """距离 → 有效 MIL。自动处理标准段/扩展段。"""
    if profile.extended_range:
        std_dist_max = profile.extended_range[0][1]
        if distance_m < std_dist_max:
            return mil_from_distance(profile.mil_base, profile.mil_k, distance_m)
        return interp_dist_to_mil(profile.extended_range, distance_m)
    return mil_from_distance(profile.mil_base, profile.mil_k, distance_m)


def profile_inverse_mil(profile, mil_value):
    """有效 MIL → 距离。自动处理标准段/扩展段。"""
    if profile.extended_range:
        std_mil_max = profile.extended_range[0][0]
        if mil_value < std_mil_max:
            return distance_from_mil(profile.mil_base, profile.mil_k, mil_value)
        return interp_mil_to_dist(profile.extended_range, mil_value)
    return distance_from_mil(profile.mil_base, profile.mil_k, mil_value)

