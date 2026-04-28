import math


CARDINAL_HEADINGS = (0, 90, 180, 270)


def pixels_per_meter(map_pixel_width, map_width_m):
    return map_pixel_width / map_width_m


def nearest_cardinal_heading(point_x, point_y, map_width, map_height):
    center_x = map_width / 2
    center_y = map_height / 2
    angle = math.degrees(math.atan2(center_x - point_x, point_y - center_y)) % 360
    return min(
        CARDINAL_HEADINGS,
        key=lambda heading: abs((angle - heading + 180) % 360 - 180),
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


def relative_angle(angle_deg, heading_deg):
    if heading_deg is None:
        return 0.0
    return (angle_deg - heading_deg + 540) % 360 - 180


def compute_mil(distance_m):
    return 1002.0 - distance_m / (1500.0 / 356.0)
