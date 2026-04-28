import math

import PySide6.QtGui
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QMessageBox,
)

from config import CFG
from logic import (
    clamp_distance,
    clamp_to_sector,
    compute_mil,
    compute_target_position,
    nearest_cardinal_heading,
    pixels_per_meter,
    relative_angle,
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

        self.pos_a = None
        self.heading_deg = None
        self.sector_ready = False
        self.distance_m = CFG["MAX_X"]
        self.azimuth_deg = 0.0

        self.wait_point = False
        self.panning = False
        self.pan_start = QPoint()

    def load_img(self, path):
        PySide6.QtGui.QImageReader.setAllocationLimit(0)
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
        self.clear_overlay()
        self.a_item = None
        self.b_item = None
        self.line_item = None
        self.sector_item = None
        self.pos_a = None
        self.heading_deg = None
        self.sector_ready = False
        self.distance_m = CFG["MAX_X"]
        self.azimuth_deg = 0.0
        self._notify_sidebar()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.wait_point:
                if not self.pix_item:
                    return QMessageBox.information(self, "Info", "Load a map image first.")
                self._set_a_point(self.mapToScene(event.position().toPoint()))
                self.wait_point = False
                return

            self.panning = True
            self.pan_start = event.position().toPoint()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.panning:
            delta = event.position().toPoint() - self.pan_start
            self.pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.panning:
            self.panning = False
            self.viewport().setCursor(Qt.ArrowCursor)
            return

        super().mouseReleaseEvent(event)

    def _pixels_per_meter(self):
        return pixels_per_meter(self.pix_item.pixmap().width(), CFG["MAP_WIDTH_M"])

    def _set_a_point(self, pos):
        scene = self.scene()
        if self.a_item:
            scene.removeItem(self.a_item)

        radius = CFG["R_A"]
        self.a_item = QGraphicsEllipseItem(-radius, -radius, 2 * radius, 2 * radius)
        self.a_item.setBrush(CFG["COLOR_A"])
        self.a_item.setPen(Qt.NoPen)
        self.a_item.setPos(pos)
        self.a_item.setZValue(2)
        scene.addItem(self.a_item)
        self.pos_a = pos

        map_width = self.pix_item.pixmap().width()
        map_height = self.pix_item.pixmap().height()
        self.heading_deg = nearest_cardinal_heading(pos.x(), pos.y(), map_width, map_height)
        self.azimuth_deg = self.heading_deg
        self.distance_m = CFG["MAX_X"]

        self._update_sector(create=not self.sector_ready)
        self._update_target()
        self._notify_sidebar()

    def _notify_sidebar(self):
        self.main_window.update_sidebar(
            self.distance_m,
            self.azimuth_deg,
            compute_mil(self.distance_m),
            relative_angle(self.azimuth_deg, self.heading_deg),
        )

    def _update_sector(self, create=False):
        path = self._sector_path()
        if create:
            self.sector_item = self.scene().addPath(
                path,
                QPen(Qt.NoPen),
                QBrush(CFG["SECTOR_COLOR"]),
            )
            self.sector_item.setZValue(1)
            self.sector_ready = True
            return

        self.sector_item.setPath(path)

    def _sector_path(self):
        radius_px = CFG["SECTOR_R_M"] * self._pixels_per_meter()
        start_angle = self.heading_deg - CFG["SECTOR_ANG"]
        end_angle = self.heading_deg + CFG["SECTOR_ANG"]

        path = QPainterPath(self.pos_a)
        steps = 60
        for index in range(steps + 1):
            radians_value = math.radians(start_angle + (end_angle - start_angle) * index / steps)
            dx = math.sin(radians_value) * radius_px
            dy = -math.cos(radians_value) * radius_px
            path.lineTo(self.pos_a + QPointF(dx, dy))

        path.closeSubpath()
        return path

    def _update_target(self):
        if not self.pos_a:
            return

        self.azimuth_deg = clamp_to_sector(
            self.azimuth_deg,
            self.heading_deg,
            CFG["SECTOR_ANG"],
        )
        pos_b_x, pos_b_y = compute_target_position(
            self.pos_a.x(),
            self.pos_a.y(),
            self.distance_m,
            self.azimuth_deg,
            self._pixels_per_meter(),
        )
        pos_b = QPointF(pos_b_x, pos_b_y)
        scene = self.scene()

        if self.b_item:
            self.b_item.setPos(pos_b)
        else:
            radius = CFG["R_B"]
            self.b_item = QGraphicsEllipseItem(-radius, -radius, 2 * radius, 2 * radius)
            self.b_item.setBrush(CFG["COLOR_B"])
            self.b_item.setPen(Qt.NoPen)
            self.b_item.setZValue(2)
            self.b_item.setPos(pos_b)
            scene.addItem(self.b_item)

        if self.line_item is None:
            self.line_item = QGraphicsLineItem()
            self.line_item.setPen(QPen(CFG["LINE_COLOR"], 2))
            self.line_item.setZValue(1.5)
            scene.addItem(self.line_item)

        self.line_item.setLine(self.pos_a.x(), self.pos_a.y(), pos_b.x(), pos_b.y())

    def adjust_xy(self, dx, dy, mode):
        if not self.pos_a:
            return

        if mode == "F1":
            self.distance_m = clamp_distance(
                self.distance_m + dx,
                CFG["MIN_X"],
                CFG["MAX_X"],
            )
            self.azimuth_deg = (self.azimuth_deg + dy) % 360
        else:
            self.heading_deg = (self.heading_deg + dy) % 360
            self.azimuth_deg = (self.azimuth_deg + dy) % 360

        self._update_sector()
        self._update_target()
        self._notify_sidebar()

    def wheelEvent(self, event):
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
        overlay_item = self.overlay_item
        self.overlay_item = None
        if overlay_item is None:
            return

        try:
            self.scene().removeItem(overlay_item)
        except RuntimeError:
            pass
