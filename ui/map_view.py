from PySide6.QtCore import QBuffer, QByteArray, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImageReader,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QMessageBox,
)

from core.config import CFG, VK, key_pressed
from core.country import get_default_profile
from core.logic import (
    angle_from_points,
    clamp_distance,
    clamp_to_sector,
    compute_target_position,
    pixels_per_meter,
    point_distance,
    project_point_to_ray,
    relative_angle,
    snap_to_cardinal,
)


class MapView(QGraphicsView):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setStyleSheet("background: transparent;")
        self.viewport().setStyleSheet("background: transparent;")

        self.pix_item = None
        self.overlay_item = None
        self.a_item = None
        self.b_item = None
        self.line_item = None
        self.sector_item = None
        self.heading_line_item = None

        self.preview_line_item = None
        self.preview_sector_item = None
        self.preview_arrow_item = None

        self.active_profile = get_default_profile()

        self.pos_a = None
        self.heading_deg = None
        self.distance_m = self.active_profile.max_distance
        self.azimuth_deg = 0.0
        self.tilt_angle = 0.0

        self._calc_mode = "STD"

        self.set_a_mode = False
        self.drawing_ray = False
        self.panning = False
        self.pan_start = QPoint()

        self.preview_mouse_pos = None
        self.preview_angle_deg = None
        self.shift_locked = False
        self.snapped_angle_deg = None
        self.saved_state = None

    def load_img(self, path):
        QImageReader.setAllocationLimit(0)
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return QMessageBox.warning(self, "Error", f"Unable to load: {path}")

        scene = self.scene()
        scene.clear()
        self.pix_item = QGraphicsPixmapItem(pixmap)
        self.pix_item.setOpacity(1.0)
        scene.addItem(self.pix_item)
        scene.setSceneRect(QRectF(pixmap.rect()))

        self._reset_state()
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def _reset_state(self):
        self.overlay_item = None
        self.a_item = None
        self.b_item = None
        self.line_item = None
        self.sector_item = None
        self.heading_line_item = None
        self.preview_line_item = None
        self.preview_sector_item = None
        self.preview_arrow_item = None

        self.pos_a = None
        self.heading_deg = None
        self.distance_m = self.active_profile.max_distance
        self.azimuth_deg = 0.0
        self.tilt_angle = 0.0

        self._calc_mode = "STD"

        self.set_a_mode = False
        self.drawing_ray = False
        self.preview_mouse_pos = None
        self.preview_angle_deg = None
        self.shift_locked = False
        self.snapped_angle_deg = None
        self.saved_state = None

        self.viewport().setCursor(Qt.ArrowCursor)
        self.main_window.clear_status_message()
        self._notify_sidebar()

    @property
    def calc_mode(self):
        return self._calc_mode

    def set_active_profile(self, profile):
        self.active_profile = profile
        self._clear_targeting()

    def switch_calc_mode(self, new_mode):
        if new_mode == self._calc_mode:
            return
        self._calc_mode = new_mode
        self._clear_targeting()

    def begin_set_a_mode(self):
        if self.drawing_ray:
            self._cancel_ray_setup()

        self.set_a_mode = True
        self.viewport().setCursor(Qt.CrossCursor)
        self.main_window.set_status_message(
            "Click and drag to set A point. Hold Shift to snap. Press Esc to cancel."
        )

    def handle_interaction_shortcuts(self):
        if self.drawing_ray:
            if key_pressed(VK["ESC"]):
                self._cancel_ray_setup()
                return True

            if self.preview_mouse_pos is not None:
                shift_pressed = key_pressed(VK["SHIFT"])
                should_refresh = shift_pressed != self.shift_locked
                if shift_pressed and self.snapped_angle_deg is None:
                    should_refresh = True
                if should_refresh:
                    self._update_preview(self.preview_mouse_pos)
            return True

        if self.set_a_mode:
            if key_pressed(VK["ESC"]):
                self._finish_set_a_mode()
            return True

        return False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.set_a_mode:
                if not self.pix_item:
                    return QMessageBox.information(self, "Info", "Load a map image first.")
                self._start_ray_setup(self.mapToScene(event.position().toPoint()))
                return

            self.panning = True
            self.pan_start = event.position().toPoint()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drawing_ray:
            self._update_preview(self.mapToScene(event.position().toPoint()))
            return

        if self.panning:
            delta = event.position().toPoint() - self.pan_start
            self.pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing_ray:
            self._finish_ray_setup(self.mapToScene(event.position().toPoint()))
            return

        if event.button() == Qt.LeftButton and self.panning:
            self.panning = False
            self.viewport().setCursor(Qt.ArrowCursor)
            return

        super().mouseReleaseEvent(event)

    def _start_ray_setup(self, pos):
        self.saved_state = self._snapshot_state()
        self.drawing_ray = True
        self.preview_mouse_pos = pos
        self.preview_angle_deg = None
        self.shift_locked = False
        self.snapped_angle_deg = None

        self._clear_committed_target_items()
        self._render_a_item(pos)
        self.pos_a = QPointF(pos)

        self._clear_preview_items()
        self.main_window.set_status_message("Drag to aim. Hold Shift to snap. Press Esc to cancel.")

    def _finish_ray_setup(self, release_pos):
        self.preview_mouse_pos = QPointF(release_pos)

        if point_distance(
            self.pos_a.x(),
            self.pos_a.y(),
            release_pos.x(),
            release_pos.y(),
        ) < CFG["SET_A_MIN_DRAG_PX"]:
            self._restore_saved_state()
            self._finish_set_a_mode()
            return

        final_angle = angle_from_points(
            self.pos_a.x(),
            self.pos_a.y(),
            release_pos.x(),
            release_pos.y(),
        )
        if key_pressed(VK["SHIFT"]):
            final_angle = self.snapped_angle_deg or snap_to_cardinal(final_angle)

        self.heading_deg = final_angle
        self.azimuth_deg = final_angle
        self._clear_preview_items()
        self._update_sector(create=True)
        self._update_target()
        self._notify_sidebar()
        self._finish_set_a_mode()

    def _cancel_ray_setup(self):
        self._restore_saved_state()
        self._finish_set_a_mode()

    def _finish_set_a_mode(self):
        self.set_a_mode = False
        self.drawing_ray = False
        self.preview_mouse_pos = None
        self.preview_angle_deg = None
        self.shift_locked = False
        self.snapped_angle_deg = None
        self.saved_state = None
        self._clear_preview_items()
        self.viewport().setCursor(Qt.ArrowCursor)
        self.main_window.clear_status_message()

    def _snapshot_state(self):
        if self.pos_a is None:
            return {
                "pos_a": None,
                "heading_deg": None,
                "azimuth_deg": self.azimuth_deg,
                "distance_m": self.distance_m,
            }

        return {
            "pos_a": QPointF(self.pos_a),
            "heading_deg": self.heading_deg,
            "azimuth_deg": self.azimuth_deg,
            "distance_m": self.distance_m,
        }

    def _restore_saved_state(self):
        state = self.saved_state
        if state is None:
            return

        self.distance_m = state["distance_m"]
        self.azimuth_deg = state["azimuth_deg"]
        self.heading_deg = state["heading_deg"]

        self._clear_committed_target_items()
        self._clear_preview_items()

        if state["pos_a"] is None:
            self.pos_a = None
            self._remove_item("a_item")
            self._notify_sidebar()
            return

        self.pos_a = QPointF(state["pos_a"])
        self._render_a_item(self.pos_a)
        self._update_sector(create=True)
        self._update_target()
        self._notify_sidebar()

    def _update_preview(self, mouse_pos):
        if not self.drawing_ray or self.pos_a is None:
            return

        self.preview_mouse_pos = QPointF(mouse_pos)
        raw_angle = angle_from_points(
            self.pos_a.x(),
            self.pos_a.y(),
            mouse_pos.x(),
            mouse_pos.y(),
        )

        if key_pressed(VK["SHIFT"]):
            self.snapped_angle_deg = snap_to_cardinal(raw_angle)
            self.shift_locked = True
            angle = self.snapped_angle_deg
            preview_x, preview_y = project_point_to_ray(
                self.pos_a.x(),
                self.pos_a.y(),
                mouse_pos.x(),
                mouse_pos.y(),
                angle,
            )
            preview_end = QPointF(preview_x, preview_y)
        else:
            self.shift_locked = False
            self.snapped_angle_deg = None
            angle = raw_angle
            preview_end = QPointF(mouse_pos)

        self.preview_angle_deg = angle
        self._update_preview_line(preview_end)
        self._update_preview_arrow(preview_end, angle)
        self._update_preview_sector(angle)
        d_eff = self._effective_distance()
        self.main_window.update_sidebar(
            self.distance_m,
            angle,
            self.active_profile.compute_mil(d_eff),
            0.0,
            getattr(self, "tilt_angle", 0.0),
        )

        status_suffix = " (snapped)" if self.shift_locked else ""
        self.main_window.set_status_message(f"Preview angle: {angle:.1f} deg{status_suffix}")

    def _effective_distance(self):
        if self._calc_mode == "SPG":
            return self.active_profile.compute_effective_distance(self.distance_m, self.tilt_angle)
        return self.distance_m

    def _pixels_per_meter(self):
        return pixels_per_meter(self.pix_item.pixmap().width(), CFG["MAP_WIDTH_M"])

    def _render_a_item(self, pos):
        self._remove_item("a_item")
        radius = CFG["R_A"]
        self.a_item = QGraphicsEllipseItem(-radius, -radius, 2 * radius, 2 * radius)
        self.a_item.setBrush(CFG["COLOR_A"])
        self.a_item.setPen(Qt.NoPen)
        self.a_item.setPos(pos)
        self.a_item.setZValue(2)
        self.scene().addItem(self.a_item)

    def _notify_sidebar(self):
        d_eff = self._effective_distance()
        self.main_window.update_sidebar(
            self.distance_m,
            self.azimuth_deg,
            self.active_profile.compute_mil(d_eff),
            relative_angle(self.azimuth_deg, self.heading_deg),
            getattr(self, "tilt_angle", 0.0),
        )

    def export_sync_state(self, role, calc_mode):
        map_width = 0
        map_height = 0
        if self.pix_item is not None:
            map_width = self.pix_item.pixmap().width()
            map_height = self.pix_item.pixmap().height()

        a_point = self._normalize_scene_point(self.pos_a, map_width, map_height)
        b_point = None
        if self.b_item is not None:
            b_point = self._normalize_scene_point(self.b_item.pos(), map_width, map_height)

        d_eff = self._effective_distance()
        result = {
            "mode": f"{calc_mode} · {'Gunner' if role == 'F1' else 'Loader'}" if calc_mode == "STD" else calc_mode,
            "calcMode": calc_mode,
            "country": self.active_profile.country,
            "map": {
                "widthPx": map_width,
                "heightPx": map_height,
            },
            "view": {
                "distanceM": self.distance_m,
                "azimuthDeg": self.azimuth_deg,
                "headingDeg": self.heading_deg,
                "mil": self.active_profile.compute_mil(d_eff),
                "relativeAngleDeg": relative_angle(self.azimuth_deg, self.heading_deg),
                "sectorAngleDeg": self.active_profile.sector_angle,
                "sectorRadiusNorm": self.active_profile.sector_radius / CFG["MAP_WIDTH_M"],
                "overlayOpacity": CFG["OPACITY"],
                "tiltAngleDeg": getattr(self, "tilt_angle", 0.0),
            },
            "entities": {
                "a": a_point,
                "b": b_point,
            },
        }
        return result

    def export_sync_assets(self):
        assets = {
            "base_map": None,
            "overlay": None,
        }

        if self.pix_item is not None:
            assets["base_map"] = self._pixmap_payload(self.pix_item.pixmap())
        if self.overlay_item is not None:
            assets["overlay"] = self._pixmap_payload(self.overlay_item.pixmap())
        return assets

    def _pixmap_payload(self, pixmap):
        image_bytes = self._pixmap_to_image_bytes(pixmap)
        return {
            "image_bytes": image_bytes,
            "width_px": pixmap.width(),
            "height_px": pixmap.height(),
            "mime_type": "image/jpeg",
        }

    def _pixmap_to_image_bytes(self, pixmap, fmt="JPEG", quality=None):
        if quality is None:
            quality = CFG.get("SYNC_IMAGE_JPEG_QUALITY", 80)
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QBuffer.WriteOnly)
        pixmap.save(buffer, fmt, quality=quality)
        return bytes(byte_array)

    def _normalize_scene_point(self, point, map_width, map_height):
        if point is None or map_width <= 0 or map_height <= 0:
            return None
        return {
            "x": point.x() / map_width,
            "y": point.y() / map_height,
        }

    def _update_sector(self, create=False):
        if self.pos_a is None or self.heading_deg is None:
            return

        path = self._sector_path(self.pos_a, self.heading_deg)
        if create or self.sector_item is None:
            self._remove_item("sector_item")
            self.sector_item = self.scene().addPath(
                path,
                QPen(Qt.NoPen),
                QBrush(CFG["SECTOR_COLOR"]),
            )
            self.sector_item.setZValue(1)
            return

        self.sector_item.setPath(path)

        self._update_heading_line()

    def _update_heading_line(self):
        radius_px = self.active_profile.sector_radius * self._pixels_per_meter()
        end_x, end_y = compute_target_position(
            self.pos_a.x(), self.pos_a.y(), radius_px, self.heading_deg, 1.0,
        )

        if self.heading_line_item is None:
            pen = QPen(CFG["DASH_LINE_COLOR"], CFG["DASH_LINE_WIDTH"], Qt.DashLine)
            self.heading_line_item = QGraphicsLineItem(
                self.pos_a.x(), self.pos_a.y(), end_x, end_y,
            )
            self.heading_line_item.setPen(pen)
            self.heading_line_item.setZValue(1.2)
            self.scene().addItem(self.heading_line_item)
            return

        self.heading_line_item.setLine(
            self.pos_a.x(), self.pos_a.y(), end_x, end_y,
        )

    def _sector_path(self, origin, center_angle_deg):
        radius_px = self.active_profile.sector_radius * self._pixels_per_meter()
        start_angle = center_angle_deg - self.active_profile.sector_angle
        end_angle = center_angle_deg + self.active_profile.sector_angle

        path = QPainterPath(origin)
        steps = 60
        for index in range(steps + 1):
            angle = start_angle + (end_angle - start_angle) * index / steps
            x, y = compute_target_position(origin.x(), origin.y(), radius_px, angle, 1.0)
            path.lineTo(QPointF(x, y))

        path.closeSubpath()
        return path

    def _update_target(self):
        if self.pos_a is None or self.heading_deg is None:
            return

        self.azimuth_deg = clamp_to_sector(
            self.azimuth_deg,
            self.heading_deg,
            self.active_profile.sector_angle,
        )
        pos_b_x, pos_b_y = compute_target_position(
            self.pos_a.x(),
            self.pos_a.y(),
            self._effective_distance(),
            self.azimuth_deg,
            self._pixels_per_meter(),
        )
        pos_b = QPointF(pos_b_x, pos_b_y)

        if self.b_item is None:
            radius = CFG["R_B"]
            self.b_item = QGraphicsEllipseItem(-radius, -radius, 2 * radius, 2 * radius)
            self.b_item.setBrush(CFG["COLOR_B"])
            self.b_item.setPen(Qt.NoPen)
            self.b_item.setZValue(2)
            self.scene().addItem(self.b_item)
        self.b_item.setPos(pos_b)

        if self.line_item is None:
            self.line_item = QGraphicsLineItem()
            self.line_item.setPen(QPen(CFG["LINE_COLOR"], CFG["LINE_WIDTH"]))
            self.line_item.setZValue(1.5)
            self.scene().addItem(self.line_item)

        self.line_item.setLine(self.pos_a.x(), self.pos_a.y(), pos_b.x(), pos_b.y())

    def _update_preview_line(self, preview_end):
        if self.preview_line_item is None:
            self.preview_line_item = QGraphicsLineItem()
            self.preview_line_item.setPen(QPen(CFG["LINE_COLOR"], CFG["LINE_WIDTH"]))
            self.preview_line_item.setZValue(1.6)
            self.scene().addItem(self.preview_line_item)

        self.preview_line_item.setLine(
            self.pos_a.x(),
            self.pos_a.y(),
            preview_end.x(),
            preview_end.y(),
        )

    def _update_preview_arrow(self, preview_end, angle_deg):
        arrow_size = CFG["PREVIEW_ARROW_SIZE_PX"]
        left_wing = self._point_from_angle(preview_end, arrow_size, (angle_deg + 210) % 360)
        right_wing = self._point_from_angle(preview_end, arrow_size, (angle_deg + 150) % 360)

        path = QPainterPath(left_wing)
        path.lineTo(preview_end)
        path.lineTo(right_wing)

        if self.preview_arrow_item is None:
            self.preview_arrow_item = self.scene().addPath(
                path,
                QPen(CFG["LINE_COLOR"], CFG["LINE_WIDTH"]),
            )
            self.preview_arrow_item.setZValue(1.7)
            return

        self.preview_arrow_item.setPath(path)

    def _point_from_angle(self, origin, distance_px, angle_deg):
        x, y = compute_target_position(origin.x(), origin.y(), distance_px, angle_deg, 1.0)
        return QPointF(x, y)

    def _update_preview_sector(self, angle_deg):
        preview_color = QColor(CFG["SECTOR_COLOR"])
        preview_color.setAlpha(CFG["PREVIEW_SECTOR_ALPHA"])
        path = self._sector_path(self.pos_a, angle_deg)

        if self.preview_sector_item is None:
            self.preview_sector_item = self.scene().addPath(
                path,
                QPen(Qt.NoPen),
                QBrush(preview_color),
            )
            self.preview_sector_item.setZValue(1.1)
            return

        self.preview_sector_item.setBrush(QBrush(preview_color))
        self.preview_sector_item.setPath(path)

    def _clear_targeting(self):
        self._clear_committed_target_items()
        self._clear_preview_items()
        self._remove_item("a_item")
        self.pos_a = None
        self.heading_deg = None
        self.distance_m = self.active_profile.max_distance
        self.azimuth_deg = 0.0
        self.tilt_angle = 0.0
        self._notify_sidebar()

    def _clear_committed_target_items(self):
        self._remove_item("sector_item")
        self._remove_item("b_item")
        self._remove_item("line_item")
        self._remove_item("heading_line_item")

    def _clear_preview_items(self):
        self._remove_item("preview_line_item")
        self._remove_item("preview_sector_item")
        self._remove_item("preview_arrow_item")

    def _remove_item(self, attr_name):
        item = getattr(self, attr_name)
        setattr(self, attr_name, None)
        if item is None:
            return

        try:
            self.scene().removeItem(item)
        except RuntimeError:
            pass

    def adjust_xy(self, dx, dy, mode):
        if self.pos_a is None or self.drawing_ray or self.set_a_mode:
            return

        if mode == "F1":
            self.distance_m = clamp_distance(
                self.distance_m + dx,
                self.active_profile.min_distance,
                self.active_profile.max_distance,
            )
            self.azimuth_deg = (self.azimuth_deg + dy) % 360
        else:
            self.heading_deg = (self.heading_deg + dy) % 360
            self.azimuth_deg = (self.azimuth_deg + dy) % 360

        self._update_sector()
        self._update_target()
        self._notify_sidebar()

    def adjust_tilt(self, delta):
        if self._calc_mode != "SPG":
            return
        self.tilt_angle += delta
        self._update_target()
        self._notify_sidebar()

    def wheelEvent(self, event):
        if self._calc_mode == "SPG" and key_pressed(VK["SHIFT"]):
            delta = event.angleDelta().y()
            if delta != 0:
                tilt_step = self.active_profile.tilt_speed
                self.adjust_tilt(tilt_step if delta > 0 else -tilt_step)
            return
        scale_factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.scale(scale_factor, scale_factor)

    def set_overlay(self, pixmap, opacity=0.5):
        if self.pix_item is None:
            QMessageBox.warning(self, "Info", "Load a base map first.")
            return

        self.clear_overlay()

        base_pixmap = self.pix_item.pixmap()
        pixmap = pixmap.scaled(
            base_pixmap.size(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        pixmap.setDevicePixelRatio(base_pixmap.devicePixelRatio())

        self.overlay_item = QGraphicsPixmapItem(pixmap)
        self.overlay_item.setPos(self.pix_item.pos())
        self.overlay_item.setOffset(self.pix_item.offset())
        self.overlay_item.setZValue(0.5)
        self.overlay_item.setOpacity(opacity)
        self.scene().addItem(self.overlay_item)

    def clear_overlay(self):
        self._remove_item("overlay_item")
