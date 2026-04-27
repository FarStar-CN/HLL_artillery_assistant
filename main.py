import os
import math, sys

import PySide6.QtGui
from PySide6.QtCore   import Qt, QPoint, QPointF, QRectF, QTimer, QElapsedTimer, QDateTime
from PySide6.QtGui    import QAction, QBrush, QPixmap, QPainterPath, QPen, QPainter
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QGraphicsEllipseItem, QGraphicsPixmapItem,
    QGraphicsScene, QGraphicsView, QMainWindow, QMessageBox, QWidget,
    QVBoxLayout, QLabel, QHBoxLayout, QFrame, QPushButton, QGraphicsLineItem
)

from config import CFG, VK, key_pressed

# -------------------------- 视图类 --------------------------
class MapView(QGraphicsView):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setStyleSheet("background: transparent;")
        self.viewport().setStyleSheet("background: transparent;")

        self.pix_item = None
        self.overlay_item = None  # 半透明叠加图层
        self.A = self.B = self.line = self.sector = None
        self.pos_a = None
        self.hdg0 = None
        self.sector_ok = False

        self.X, self.Y = 1600.0, 0.0
        self.wait_point, self.panning = False, False
        self.pan_start = QPoint()

    def load_img(self, path):
        PySide6.QtGui.QImageReader.setAllocationLimit(0)
        pix = QPixmap(path)
        if pix.isNull():
            print("cant load")
            return QMessageBox.warning(self, "错误", f"无法加载：{path}")
        scn = self.scene(); scn.clear()
        self.pix_item = QGraphicsPixmapItem(pix); scn.addItem(self.pix_item)
        self.pix_item.setOpacity(1.0)
        scn.setSceneRect(QRectF(pix.rect()))
        self._reset()
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def _reset(self):
        self.clear_overlay()
        self.A = self.B = self.line = self.sector = None
        self.pos_a = None
        self.hdg0 = None
        self.sector_ok = False
        self.X, self.Y = 1600.0, 0.0
        self.main.up_sidebar(self.X, self.Y, self._mil(), 0.0)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.wait_point:
                if not self.pix_item:
                    return QMessageBox.information(self, "提示", "请先加载地图")
                self._set_A(self.mapToScene(e.position().toPoint()))
                self.wait_point = False
                return
            self.panning = True
            self.pan_start = e.position().toPoint()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.panning:
            d = e.position().toPoint() - self.pan_start
            self.pan_start = e.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.panning:
            self.panning = False
            self.viewport().setCursor(Qt.ArrowCursor)
            return
        super().mouseReleaseEvent(e)

    def _ppm(self):
        return self.pix_item.pixmap().width() / CFG["MAP_WIDTH_M"]

    def _set_A(self, pos):
        scn = self.scene()
        if self.A: scn.removeItem(self.A)
        r = CFG["R_A"]
        self.A = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
        self.A.setBrush(CFG["COLOR_A"])
        self.A.setPen(Qt.NoPen)
        self.A.setPos(pos)
        self.A.setZValue(2)
        scn.addItem(self.A)
        self.pos_a = pos

        center = QPointF(self.pix_item.pixmap().width() / 2, self.pix_item.pixmap().height() / 2)
        ang = math.degrees(math.atan2(center.x() - pos.x(), pos.y() - center.y())) % 360
        self.hdg0 = min((0, 90, 180, 270), key=lambda a: abs((ang - a + 180) % 360 - 180))
        self.Y = self.hdg0

        self.X = CFG["MAX_X"]

        self._mk_sector(create=not self.sector_ok)
        self._update_B()
        self.main.up_sidebar(self.X, self.Y, self._mil(), self._rel())

    def _rel(self):
        return (self.Y - self.hdg0 + 540) % 360 - 180 if self.hdg0 is not None else 0.0

    def _mk_sector(self, create=False):
        path = self._sector_path()
        if create:
            self.sector = self.scene().addPath(path, QPen(Qt.NoPen), QBrush(CFG["SECTOR_COLOR"]))
            self.sector.setZValue(1)
            self.sector_ok = True
        else:
            self.sector.setPath(path)

    def _sector_path(self):
        r_px = CFG["SECTOR_R_M"] * self._ppm()
        sa, ea = self.hdg0 - CFG["SECTOR_ANG"], self.hdg0 + CFG["SECTOR_ANG"]
        path = QPainterPath(self.pos_a)
        steps = 60
        for i in range(steps + 1):
            a = math.radians(sa + (ea - sa) * i / steps)
            dx, dy = math.sin(a) * r_px, -math.cos(a) * r_px
            path.lineTo(self.pos_a + QPointF(dx, dy))
        path.closeSubpath()
        return path

    def _update_B(self):
        if not self.pos_a:
            return

        # 保持Y在扇区内
        if self.hdg0 is not None:
            delta = (self.Y - self.hdg0 + 360) % 360
            delta = delta - 360 if delta > 180 else delta
            if delta < -CFG["SECTOR_ANG"]:
                self.Y = (self.hdg0 - CFG["SECTOR_ANG"]) % 360
            elif delta > CFG["SECTOR_ANG"]:
                self.Y = (self.hdg0 + CFG["SECTOR_ANG"]) % 360

        d_px = self.X * self._ppm()
        rad = math.radians(self.Y)
        dx, dy = math.sin(rad) * d_px, -math.cos(rad) * d_px
        pos_b = self.pos_a + QPointF(dx, dy)

        scn = self.scene()

        # B 点处理（逻辑不变）
        if self.B:
            self.B.setPos(pos_b)
        else:
            r = CFG["R_B"]
            self.B = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
            self.B.setBrush(CFG["COLOR_B"])
            self.B.setPen(Qt.NoPen)
            self.B.setZValue(2)
            self.B.setPos(pos_b)
            scn.addItem(self.B)

        # ---- 优化后的线条处理 ----
        if self.line is None:
            # 首次创建，使用 addLine 也可以，但为了统一管理，直接构造 QGraphicsLineItem
            self.line = QGraphicsLineItem()
            self.line.setPen(QPen(CFG["LINE_COLOR"], 2))
            self.line.setZValue(1.5)
            scn.addItem(self.line)

        # 直接更新线段端点，无需移除/添加
        self.line.setLine(self.pos_a.x(), self.pos_a.y(), pos_b.x(), pos_b.y())

    def adjust_xy(self, dx, dy):
        if not self.pos_a:
            return
        if self.main.mode == 'F1':  # Gunner 模式：调整距离/方位
            self.X = max(CFG["MIN_X"], min(CFG["MAX_X"], self.X + dx))
            self.Y = (self.Y + dy) % 360
        else:  # F2 / Loader 模式：旋转炮架
            self.hdg0 = (self.hdg0 + dy) % 360
            self.Y = (self.Y + dy) % 360
        self._mk_sector()
        self._update_B()
        self.main.up_sidebar(self.X, self.Y, self._mil(), self._rel())

    def wheelEvent(self, e):
        scale_factor = 1.25 if e.angleDelta().y() > 0 else 0.8
        self.scale(scale_factor, scale_factor)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def _mil(self):
        return 1002.0 - self.X / (1500.0 / 356.0)

    def set_overlay(self, pixmap, opacity=0.5):
        if self.pix_item is None:
            QMessageBox.warning(self, "提示", "请先加载底图")
            return

        # 移除旧叠加
        self.clear_overlay()

        base_pix = self.pix_item.pixmap()
        base_size = base_pix.size()  # 物理像素尺寸
        base_ratio = base_pix.devicePixelRatio()  # 一般可能是 1.0

        # 强制将叠加图缩放到与底图相同的物理像素尺寸
        pixmap = pixmap.scaled(base_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        pixmap.setDevicePixelRatio(base_ratio)

        self.overlay_item = QGraphicsPixmapItem(pixmap)
        self.overlay_item.setPos(self.pix_item.pos())
        self.overlay_item.setOffset(self.pix_item.offset())
        self.overlay_item.setZValue(0.5)
        self.overlay_item.setOpacity(opacity)
        self.scene().addItem(self.overlay_item)

    def clear_overlay(self):
        """移除叠加层"""
        if self.overlay_item:
            self.scene().removeItem(self.overlay_item)
            self.overlay_item = None

# ------------------------- 主窗 -------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.time = QElapsedTimer()
        self.time.start()
        self.setWindowTitle("离线地图查看器")
        self.resize(1050, 680)
        self.mode = 'F1'
        self.view = MapView(self)
        self._ui()
        self._menu()
        self._timer()
        self.last_screenshot_path = None

    def _ui(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view, 3)

        side = QFrame()
        side.setFixedWidth(240)
        side.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-left: 1px solid #ccc;
            }
        """)
        vb = QVBoxLayout(side)

        self.labs = {k: QLabel() for k in "x y mil ang mode".split()}
        for k, lab in self.labs.items():
            lab.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    padding: 6px;
                    color: #333;
                }
            """)
            vb.addWidget(lab)

        title = QLabel("地图操作")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 8px 6px;
                color: #222;
            }
        """)
        vb.addWidget(title)

        btnA = QPushButton("设置 A 点")
        btnA.setStyleSheet("QPushButton { padding: 8px; font-size: 14px; }")
        btnA.clicked.connect(lambda: setattr(self.view, 'wait_point', True))
        vb.addWidget(btnA)

        btnTop = QPushButton("窗口置顶", checkable=True)
        btnTop.setStyleSheet("""
            QPushButton {
                padding: 8px; font-size: 14px;
            }
            QPushButton:checked {
                background-color: #d0f0ff;
                border: 1px solid #66ccff;
            }
        """)
        btnTop.toggled.connect(self._top)
        vb.addWidget(btnTop)

        # 截取地图按钮
        self.btnCrop = QPushButton("截取地图")
        self.btnCrop.setStyleSheet("QPushButton { padding: 8px; font-size: 14px; }")
        self.btnCrop.clicked.connect(self._capture_and_overlay)
        vb.addWidget(self.btnCrop)

        # 清除叠加按钮
        self.btnClear = QPushButton("清除叠加")
        self.btnClear.setStyleSheet("QPushButton { padding: 8px; font-size: 14px; }")
        self.btnClear.clicked.connect(self.view.clear_overlay)
        vb.addWidget(self.btnClear)

        vb.addStretch(1)
        layout.addWidget(side)
        self.setCentralWidget(container)
        self.up_sidebar(1600.0, 0.0, self.view._mil(), 0.0)

    def _menu(self):
        m = self.menuBar().addMenu("文件")
        m.addAction(QAction("打开...", self, shortcut="Ctrl+O", triggered=self._open))
        m.addSeparator()
        m.addAction(QAction("退出", self, shortcut="Ctrl+Q", triggered=self.close))

    def _timer(self):
        t = QTimer(self)
        t.timeout.connect(self._poll)
        t.start(CFG["POLL_MS"])
        self.timer = t

    def _poll(self):
        dt = self.time.elapsed() / 1000.0
        self.time.restart()

        if key_pressed(VK["F1"]):
            self.mode = 'F1'
        elif key_pressed(VK["F2"]):
            self.mode = 'F2'

        if self.mode == 'F1':
            # Gunner 模式
            dx = 0.0
            dy = 0.0
            if key_pressed(VK["W"]):
                dx -= CFG["MOVE_SPEED_X"] * dt  # 减小距离
            if key_pressed(VK["S"]):
                dx += CFG["MOVE_SPEED_X"] * dt  # 增大距离
            if key_pressed(VK["A"]):
                dy -= CFG["MOVE_SPEED_Y"] * dt  # 减小方位
            if key_pressed(VK["D"]):
                dy += CFG["MOVE_SPEED_Y"] * dt  # 增大方位
            if dx != 0.0 or dy != 0.0:
                self.view.adjust_xy(dx, dy)
        else:
            # Loader 模式
            dy = 0.0
            if key_pressed(VK["A"]):
                dy -= CFG["MOVE_SPEED_Y"] * dt
            if key_pressed(VK["D"]):
                dy += CFG["MOVE_SPEED_Y"] * dt
            if dy != 0.0:
                self.view.adjust_xy(0.0, dy)

    def _top(self, on):
        f = self.windowFlags()
        self.setWindowFlags(f | Qt.WindowStaysOnTopHint if on else f & ~Qt.WindowStaysOnTopHint)
        self.show()

    def _open(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择地图", "", "图像 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)")
        if path:
            self.view.load_img(path)

    def _capture_and_overlay(self):
        # 1. 截取全屏
        screen = QApplication.primaryScreen()
        if not screen:
            QMessageBox.warning(self, "错误", "无法获取屏幕")
            return
        pix = screen.grabWindow(0)

        if self.last_screenshot_path:
            try:
                os.remove(self.last_screenshot_path)
            except Exception as e:
                print(f"删除旧截图失败: {e}")

        # 2. 保存到程序所在目录
        save_dir = os.path.dirname(os.path.abspath(__file__))
        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
        filename = f"screenshot_{timestamp}.png"
        save_path = os.path.join(save_dir, filename)
        pix.save(save_path, "PNG")
        self.last_screenshot_path = save_path

        # 3. 裁剪地图区域
        left = CFG["LEFT"] #左
        top = CFG["TOP"] #上
        right = CFG["RIGHT"] #右
        bottom = CFG["BOTTOM"] #下
        crop_w = right - left
        crop_h = bottom - top

        if crop_w <= 0 or crop_h <= 0:
            QMessageBox.warning(self, "裁剪错误", "裁剪区域无效，请检查")
            return

        cropped = pix.copy(left, top, crop_w, crop_h)

        self.view.set_overlay(cropped, opacity=CFG["OPACITY"])

    def up_sidebar(self, x, y, mil, ang):
        if self.mode == "F1":
            MODE = "炮手"
        elif self.mode == "F2":
            MODE = "装填手"
        self.labs["mode"].setText(f"当前模式: {MODE}")
        self.labs["x"].setText(f"距离: {x:.1f} m")
        self.labs["y"].setText(f"方位: {y:.1f} °")
        self.labs["mil"].setText(f"MIL 值: {mil:.2f}")
        self.labs["ang"].setText(f"相对角度: {ang:.1f} °")

    def closeEvent(self, event):
        if self.last_screenshot_path:
            try:
                os.remove(self.last_screenshot_path)
            except Exception as e:
                print(f"删除截图失败: {e}")
        event.accept()
# ------------------------- 入口 -------------------------
if __name__ == "__main__":
    QApplication(sys.argv + [''])
    win = MainWindow()
    win.show()
    sys.exit(QApplication.instance().exec())
