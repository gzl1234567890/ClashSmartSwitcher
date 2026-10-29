"""Small Qt building blocks shared by the control panel and region selector."""
from functools import lru_cache
from pathlib import Path
import sys

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImageReader, QLinearGradient, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QStyle, QStyleOption, QWidget

from .theme import COLORS, SPACE
from .motion import controller_for


def resource_path(relative):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / relative


@lru_cache(maxsize=96)
def icon(name, color=COLORS["muted"]):
    """Render pinned local SVGs at multiple densities, with an explicit disabled mode."""
    source = resource_path(f"resources/icons/lucide/{name}.svg").read_text(encoding="utf-8")
    result = QIcon()
    for mode, tint in ((QIcon.Normal, color), (QIcon.Disabled, "#96a59d")):
        data = QByteArray(source.replace("currentColor", tint).encode())
        for size in (16, 20, 24, 32, 40, 48, 64):
            # Keep SVG parser ownership inside Qt's image plugin. Transient Python
            # QSvgRenderer objects crashed during repeated window/error updates.
            buffer = QBuffer()
            buffer.setData(data)
            buffer.open(QIODevice.ReadOnly)
            reader = QImageReader(buffer, b"svg")
            reader.setScaledSize(QSize(size, size))
            image = reader.read()
            if image.isNull():
                raise RuntimeError(f"Unable to load UI icon {name}: {reader.errorString()}")
            result.addPixmap(QPixmap.fromImage(image), mode)
            del reader
            buffer.close()
    return result


def set_tone(widget, tone):
    if widget.property("tone") != tone:
        previous = widget.property("tone") or ""
        widget.setProperty("tone", tone)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
        motion = controller_for(widget)
        if motion is not None:
            motion.tone_changed(widget, previous)


class ElidedLabel(QLabel):
    """Keep the full, selectable value while long node names never expand the layout."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(0)
        self.setTextFormat(Qt.PlainText)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setToolTip(text)
        self.setAccessibleName(text)

    def setText(self, text):
        super().setText(text)
        self.setToolTip(text)
        self.setAccessibleName(text)

    def sizeHint(self):
        return QSize(180, self.fontMetrics().height() + 6)

    def paintEvent(self, event):
        # QLabel still owns copy/context-menu behavior and its full underlying value.
        if self.fontMetrics().horizontalAdvance(self.text()) <= self.contentsRect().width():
            return super().paintEvent(event)
        painter = QPainter(self)
        option = QStyleOption()
        option.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_Widget, option, painter, self)
        painter.setPen(self.palette().color(QPalette.WindowText))
        painter.drawText(self.contentsRect(), Qt.AlignVCenter | Qt.AlignLeft,
                         self.fontMetrics().elidedText(self.text(), Qt.ElideRight, self.contentsRect().width()))


class StatusBadge(QLabel):
    surface_color = None

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumWidth(0)
        self.setMaximumWidth(360)
        self.setToolTip(text)
        self.setAccessibleName(text)

    def setText(self, text):
        super().setText(text)
        self.setToolTip(text)
        self.setAccessibleName(text)

    def minimumSizeHint(self):
        return QSize(80, super().minimumSizeHint().height())

    def sizeHint(self):
        hint = super().sizeHint()
        return QSize(min(360, hint.width()), hint.height())

    def set_surface_color(self, color):
        self.surface_color = QColor(color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.surface_color is None:
            option = QStyleOption()
            option.initFrom(self)
            self.style().drawPrimitive(QStyle.PE_Widget, option, painter, self)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.surface_color)
            painter.drawRoundedRect(self.rect(), 12, 12)
        painter.setPen(self.palette().color(QPalette.WindowText))
        painter.setFont(self.font())
        rect = self.contentsRect()
        text = self.fontMetrics().elidedText(self.text(), Qt.ElideRight, max(0, rect.width()))
        alignment = self.alignment() if text == self.text() else Qt.AlignLeft | Qt.AlignVCenter
        painter.drawText(rect, alignment, text)


class NoticePanel(QFrame):
    surface_color = None

    def set_surface_color(self, color):
        self.surface_color = QColor(color)
        self.update()

    def paintEvent(self, event):
        if self.surface_color is None:
            return super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.surface_color)
        painter.drawRoundedRect(self.rect(), 12, 12)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setObjectName("noticePanel")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE["control"], SPACE["small"], SPACE["control"], SPACE["small"])
        layout.setSpacing(SPACE["small"])
        self.symbol = QLabel()
        self.symbol.setFixedSize(18, 18)
        self.message = QLabel()
        self.message.setTextFormat(Qt.PlainText)
        self.message.setWordWrap(True)
        self.message.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.symbol, 0, Qt.AlignTop)
        layout.addWidget(self.message, 1)
        self.setText(text)

    def setText(self, text, tone="info"):
        self.message.setText(text)
        self.setVisible(tone != "success")
        self.setAccessibleName(text)
        set_tone(self, tone)
        color = COLORS["error"] if tone == "error" else COLORS["warning"] if tone == "warning" else COLORS["accent"]
        name = "circle-alert" if tone in ("error", "warning") else "circle-check"
        self.symbol.setPixmap(icon(name, color).pixmap(18, 18))

    def text(self):
        return self.message.text()


class LatencyTrendWidget(QWidget):
    """Small native chart that only renders latency measurements received from Mihomo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history = []
        self._threshold = 120
        self.setMinimumHeight(126)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_history(self, history, threshold=None):
        self._history = list(history)[-5:]
        if threshold is not None:
            self._threshold = threshold
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = self.font()
        font.setPixelSize(12)
        painter.setFont(font)
        rect = self.rect().adjusted(66, 12, -18, -34)
        valid = [(stamp, value) for stamp, value in self._history if isinstance(value, int) and value > 0]
        if not valid:
            painter.setPen(QColor(COLORS["muted"]))
            painter.drawText(rect, Qt.AlignCenter, "完成测速后显示真实趋势")
            return

        top = max(max(value for _, value in valid), self._threshold, 50) * 1.18
        grid_pen = QPen(QColor("#dfe7f4"))
        grid_pen.setStyle(Qt.DashLine)
        painter.setPen(grid_pen)
        for fraction in (0.0, 0.5, 1.0):
            y = rect.bottom() - rect.height() * fraction
            painter.setPen(QColor(COLORS["muted"]))
            painter.drawText(0, int(y - 8), 56, 16, Qt.AlignRight | Qt.AlignVCenter,
                             f"{round(top * fraction)} ms")
            painter.setPen(grid_pen)
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))
        threshold_y = rect.bottom() - (self._threshold / top) * rect.height()
        threshold_pen = QPen(QColor("#9cb8e6"))
        threshold_pen.setStyle(Qt.DashLine)
        painter.setPen(threshold_pen)
        painter.drawLine(rect.left(), int(threshold_y), rect.right(), int(threshold_y))

        points = []
        for index, (_, value) in enumerate(valid):
            x = rect.left() if len(valid) == 1 else rect.left() + index * rect.width() / (len(valid) - 1)
            y = rect.bottom() - (value / top) * rect.height()
            points.append(QPointF(x, y))
        if len(points) > 1:
            area = QPainterPath(points[0])
            for point in points[1:]:
                area.lineTo(point)
            area.lineTo(points[-1].x(), rect.bottom())
            area.lineTo(points[0].x(), rect.bottom())
            area.closeSubpath()
            fill = QLinearGradient(0, rect.top(), 0, rect.bottom())
            fill.setColorAt(0, QColor(23, 98, 214, 35))
            fill.setColorAt(1, QColor(23, 98, 214, 0))
            painter.fillPath(area, fill)
        line_pen = QPen(QColor(COLORS["accent"]), 2)
        painter.setPen(line_pen)
        for first, second in zip(points, points[1:]):
            painter.drawLine(first, second)
        painter.setBrush(QColor(COLORS["accent"]))
        painter.setPen(Qt.NoPen)
        for point in points:
            painter.drawEllipse(point, 4, 4)
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(point, 1.7, 1.7)
            painter.setBrush(QColor(COLORS["accent"]))

        painter.setPen(QColor(COLORS["muted"]))
        for index, (stamp, value) in enumerate(valid):
            x = rect.left() if len(valid) == 1 else rect.left() + index * rect.width() / (len(valid) - 1)
            label = stamp.strftime("%H:%M") if hasattr(stamp, "strftime") else str(stamp)
            left = max(0, min(self.width() - 56, int(x - 28)))
            painter.drawText(left, rect.bottom() + 10, 56, 18, Qt.AlignHCenter, label)
