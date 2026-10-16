"""Small Qt building blocks shared by the control panel and region selector."""
from functools import lru_cache
from pathlib import Path
import sys

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QStyle, QStyleOption

from .theme import COLORS


def resource_path(relative):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / relative


@lru_cache(maxsize=96)
def icon(name, color=COLORS["muted"]):
    """Render pinned local SVGs at multiple densities, with an explicit disabled mode."""
    source = resource_path(f"resources/icons/lucide/{name}.svg").read_text(encoding="utf-8")
    result = QIcon()
    for mode, tint in ((QIcon.Normal, color), (QIcon.Disabled, "#96a59d")):
        renderer = QSvgRenderer(QByteArray(source.replace("currentColor", tint).encode()))
        for size in (16, 20, 24, 32, 40, 48, 64):
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            result.addPixmap(pixmap, mode)
    return result


def set_tone(widget, tone):
    if widget.property("tone") != tone:
        widget.setProperty("tone", tone)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()


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


class NoticePanel(QFrame):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setObjectName("noticePanel")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(9)
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
        self.setAccessibleName(text)
        set_tone(self, tone)
        color = COLORS["error"] if tone == "error" else COLORS["warning"] if tone == "warning" else COLORS["accent"]
        name = "circle-alert" if tone in ("error", "warning") else "circle-check"
        self.symbol.setPixmap(icon(name, color).pixmap(18, 18))

    def text(self):
        return self.message.text()
