"""Static, app-local frosted material with crisp native child widgets.

The backdrop is already diffuse, so panels can sample it directly without a
per-frame blur, desktop capture, graphics effects, or rasterizing any text.
"""
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QFrame, QWidget

from .theme import COLORS, SURFACE_RADIUS


class GlassCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._backdrop = None
        self._backdrop_key = None

    def backdrop(self):
        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr)
        if self._backdrop_key != key:
            width, height = max(1, self.width()), max(1, self.height())
            pixmap = QPixmap(round(width * dpr), round(height * dpr))
            pixmap.setDevicePixelRatio(dpr)
            pixmap.fill(QColor(COLORS["background"]))
            painter = QPainter(pixmap)
            base = QLinearGradient(0, 0, width, height)
            base.setColorAt(0, QColor("#e6edfb"))
            base.setColorAt(.55, QColor("#f2f5fc"))
            base.setColorAt(1, QColor("#e9eff9"))
            painter.fillRect(0, 0, width, height, base)
            for x, y, radius, tint in (
                (.12, .06, .62, "#c3d8ff"),
                (.95, .30, .58, "#dad5f7"),
                (.45, 1.02, .62, "#cde7f6"),
            ):
                glow = QRadialGradient(width * x, height * y, max(width, height) * radius)
                color = QColor(tint)
                color.setAlpha(180)
                glow.setColorAt(0, color)
                color.setAlpha(0)
                glow.setColorAt(1, color)
                painter.fillRect(0, 0, width, height, glow)
            painter.end()
            self._backdrop, self._backdrop_key = pixmap, key
        return self._backdrop

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.backdrop())


class GlassSurface(QFrame):
    def __init__(self, parent=None, *, radius=SURFACE_RADIUS, opacity=178):
        super().__init__(parent)
        self.radius, self.opacity = radius, opacity
        self.setAutoFillBackground(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)
        painter.setClipPath(path)
        canvas = self.window().centralWidget()
        if isinstance(canvas, GlassCanvas):
            offset = self.mapTo(canvas, QPoint())
            dpr = canvas.devicePixelRatioF()
            source = QRectF(offset.x() * dpr, offset.y() * dpr,
                            self.width() * dpr, self.height() * dpr)
            painter.drawPixmap(QRectF(self.rect()), canvas.backdrop(), source)
        painter.fillPath(path, QColor(255, 255, 255, self.opacity))
        rim = QLinearGradient(0, 0, 0, self.height())
        rim.setColorAt(0, QColor(255, 255, 255, 245))
        rim.setColorAt(1, QColor(255, 255, 255, 110))
        painter.setClipping(False)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(rim, 1))
        painter.drawRoundedRect(rect, self.radius, self.radius)
