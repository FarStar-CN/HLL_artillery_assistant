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

