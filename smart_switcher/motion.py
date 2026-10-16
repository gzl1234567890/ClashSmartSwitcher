"""Bounded native feedback. Text and layout geometry are never animated."""
import ctypes
from functools import partial
import sys
import weakref
from shiboken6 import isValid

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QRect, QRectF, Qt, QVariantAnimation, Slot
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox, QLineEdit, QPushButton, QSpinBox, QStyle, QStyleOptionButton,
    QStyleOptionToolButton, QStylePainter, QToolButton, QWidget,
)

from .theme import COLORS


DURATIONS = {"hover": 120, "press": 80, "focus": 120, "navigation": 160,
             "page": 140, "tone": 180}


def system_motion_enabled():
    if sys.platform != "win32":
        return True
    enabled = ctypes.c_int(1)
    if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0):
        return bool(enabled.value)
    return False


def controller_for(widget):
    while widget is not None:
        controller = getattr(widget, "motion", None)
        if controller is not None:
            return controller
        widget = widget.parentWidget()
    return None


def is_settings_message(message):
    if sys.platform != "win32":
        return False
    from ctypes.wintypes import MSG
    return ctypes.cast(int(message), ctypes.POINTER(MSG)).contents.message == 0x001A


class Channel(QVariantAnimation):
    def __init__(self, target, setter):
        super().__init__(target)
        self._target = weakref.ref(target)
        self._args = setter.args if isinstance(setter, partial) else ()
        method = setter.func if isinstance(setter, partial) else setter
        self._method = method.__name__
        self.valueChanged.connect(self.apply_value)
        self.setEasingCurve(QEasingCurve.OutCubic)

    @Slot(object)
    def apply_value(self, value):
        target = self._target()
        if target is not None and isValid(target):
            getattr(target, self._method)(*self._args, value)

    def finish(self):
        self.stop()
        if self.endValue() is not None:
            self.apply_value(self.endValue())


class SurfaceVeil(QWidget):
    def __init__(self, parent, color, outline=False):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.color = QColor(color)
        self.amount = 0.0
        self.outline = outline
        self.setGeometry(parent.rect())
        self.hide()

    def set_amount(self, value):
        self.amount = float(value)
        self.setVisible(self.amount > 0)
        self.raise_()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(self.color)
        color.setAlphaF(max(0, min(1, self.amount)))
        if self.outline:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(color, 1.4))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.8, 0.8, -0.8, -0.8), 6, 6)
        else:
            painter.fillRect(self.rect(), color)


class FeedbackMixin:
    def _init_feedback(self):
        self._feedback_values = {"hover": 0.0, "press": 0.0, "focus": 0.0}
        self.busy_angle = None

    def _set_feedback(self, name, value):
        self._feedback_values[name] = float(value)
        self.update()

    def _sync_feedback(self):
        controller = controller_for(self)
        if controller is None or controller.disposed:
            return
        for name, state in (("hover", self.underMouse()), ("press", self.isDown()),
                            ("focus", self.hasFocus())):
            target = float(state and self.isEnabled())
            controller.transition(self, name, self._feedback_values[name], target,
                                  partial(self._set_feedback, name), DURATIONS[name])

    def _feedback_event(self, event, native_event):
        result = native_event(event)
        if hasattr(self, "_feedback_values") and event.type() in (
            QEvent.Enter, QEvent.Leave, QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
            QEvent.FocusIn, QEvent.FocusOut, QEvent.EnabledChange, QEvent.KeyPress, QEvent.KeyRelease,
        ):
            self._sync_feedback()
        return result

    def _paint_feedback(self, painter):
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        values = self._feedback_values
        primary = self.objectName() == "primary"
        tint = QColor("#ffffff" if primary else COLORS["accent"])
        tint.setAlphaF(values["hover"] * (0.09 if primary else 0.055))
        painter.setPen(Qt.NoPen)
        painter.setBrush(tint)
        painter.drawRoundedRect(rect, 6, 6)
        pressed = QColor("#000000" if primary else COLORS["accent"])
        pressed.setAlphaF(values["press"] * 0.10)
        painter.setBrush(pressed)
        painter.drawRoundedRect(rect, 6, 6)
        if values["focus"]:
            focus = QColor("#ffffff" if primary else COLORS["accent"])
            focus.setAlphaF(values["focus"] * 0.85)
            painter.setPen(QPen(focus, 1.2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 6, 6)


class MotionButton(QPushButton, FeedbackMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_feedback()

    def event(self, event):
        return self._feedback_event(event, super().event)

    def set_busy_angle(self, value):
        self.busy_angle = value
        self.update()

    def paintEvent(self, event):
        if controller_for(self) is None:
            return super().paintEvent(event)
        painter = QStylePainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.state &= ~(QStyle.State_MouseOver | QStyle.State_Sunken | QStyle.State_HasFocus)
        painter.drawControl(QStyle.CE_PushButtonBevel, option)
        self._paint_feedback(painter)
        if self.busy_angle is not None:
            option.icon = QIcon()
        option.rect = self.style().subElementRect(QStyle.SE_PushButtonContents, option, self)
        painter.drawControl(QStyle.CE_PushButtonLabel, option)
        if self.busy_angle is not None:
            painter.save()
            painter.translate(self.rect().center())
            painter.rotate(float(self.busy_angle))
            size = self.iconSize()
            pixmap = self.icon().pixmap(size * self.devicePixelRatioF())
            painter.drawPixmap(QRect(-size.width() // 2, -size.height() // 2,
                                    size.width(), size.height()), pixmap)
            painter.restore()


class MotionToolButton(QToolButton, FeedbackMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_feedback()

    def event(self, event):
        return self._feedback_event(event, super().event)

    def paintEvent(self, event):
        if controller_for(self) is None:
            return super().paintEvent(event)
        painter = QStylePainter(self)
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        option.state &= ~(QStyle.State_MouseOver | QStyle.State_Sunken | QStyle.State_HasFocus)
        background = QStyleOptionToolButton(option)
        background.icon, background.text, background.arrowType = QIcon(), "", Qt.NoArrow
        painter.drawComplexControl(QStyle.CC_ToolButton, background)
        self._paint_feedback(painter)
        painter.drawControl(QStyle.CE_ToolButtonLabel, option)


class MotionController(QObject):
    def __init__(self, window, sidebar):
        super().__init__(window)
        self.window = window
        self.disposed = False
        self.stopping = False
        self.enabled = system_motion_enabled()
        self._channels = weakref.WeakSet()
        self._outlines = {}
        self._focus_targets = {}
        self._busy = False
        self._current_page = window.tabs.currentIndex()
        self.indicator = QWidget(sidebar)
        self.indicator.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.indicator.setStyleSheet("background: #087f69; border-radius: 2px;")
        self.indicator.setFixedSize(3, 24)
        self.veil = SurfaceVeil(window.tabs.currentWidget(), COLORS["background"])
        self.spinner = QVariantAnimation(self)
        self.spinner.setStartValue(0.0)
        self.spinner.setEndValue(360.0)
        self.spinner.setDuration(1200)
        self.spinner.setLoopCount(-1)
        self.spinner.valueChanged.connect(window.header_refresh.set_busy_angle)
        window.installEventFilter(self)
        window.destroyed.connect(self.dispose)
        for widget in window.findChildren(QWidget):
            if isinstance(widget, (QLineEdit, QComboBox, QSpinBox)) or widget.objectName() == "regionSelect":
                if isinstance(widget.parentWidget(), QSpinBox):
                    continue
                if widget.objectName() == "regionSearch":
                    continue
                widget.setAttribute(Qt.WA_Hover)
                widget.setProperty("motionFocus", True)
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                self._outlines[widget] = SurfaceVeil(widget, COLORS["accent"], outline=True)
                widget.installEventFilter(self)
                if widget.focusProxy() is not None:
                    proxy = widget.focusProxy()
                    self._focus_targets[proxy] = widget
                    proxy.installEventFilter(self)
        self.navigate(self._current_page, initial=True)

    @property
    def visible(self):
        return self.window.isVisible() and not self.window.isMinimized()

    def transition(self, target, name, start, end, setter, duration):
        channels = getattr(target, "_motion_channels", None)
        if channels is None:
            channels = target._motion_channels = {}
        channel = channels.get(name)
        if channel is None:
            channel = channels[name] = Channel(target, setter)
            self._channels.add(channel)
        if channel.state() == QVariantAnimation.Running and channel.endValue() == end:
            return channel
        channel.stop()
        channel.setStartValue(start)
        channel.setEndValue(end)
        channel.setDuration(duration)
        if self.enabled and self.visible and target.isVisible() and start != end:
            channel.start()
        else:
            setter(end)
        return channel

    def navigate(self, index, initial=False):
        changed = index != self._current_page
        self._current_page = index
        if index < len(self.window.nav_buttons):
            button = self.window.nav_buttons[index]
            target = button.mapTo(self.indicator.parentWidget(), button.rect().topLeft())
            target.setX(6)
            target.setY(target.y() + (button.height() - 24) // 2)
            self.indicator.show()
            self.indicator.raise_()
            if initial or not self.visible:
                self.indicator.move(target)
            else:
                self.transition(self.indicator, "navigation", self.indicator.pos(), target,
                                self.indicator.move, DURATIONS["navigation"])
        else:
            channel = getattr(self.indicator, "_motion_channels", {}).get("navigation")
            if channel is not None:
                channel.stop()
            self.indicator.hide()
        if changed:
            self.veil.setParent(self.window.tabs.currentWidget())
            self.veil.setGeometry(self.veil.parentWidget().rect())
            self.veil.set_amount(0.13 if self.enabled and self.visible else 0)
            self.transition(self.veil, "page", self.veil.amount, 0.0,
                            self.veil.set_amount, DURATIONS["page"])

    def tone_changed(self, widget, previous):
        if not hasattr(widget, "set_surface_color"):
            return
        colors = {"error": COLORS["error_bg"], "warning": COLORS["warning_bg"],
                  "success": COLORS["tint"], "": "#eef2f0", "info": "#edf4f0"}
        target = QColor(colors.get(widget.property("tone"), colors[""]))
        start = widget.surface_color or QColor(colors.get(previous, colors[""]))
        self.transition(widget, "tone", start, target,
                        widget.set_surface_color, DURATIONS["tone"])

    def set_busy(self, busy):
        self._busy = busy and not self.stopping
        self._sync_spinner()

    def _sync_spinner(self):
        animate = self._busy and self.enabled and self.visible
        self.window.task_progress.setRange(0, 0 if animate else 1)
        if not animate:
            self.window.task_progress.setValue(1 if self._busy else 0)
        if animate:
            if self.spinner.state() != QVariantAnimation.Running:
                self.window.header_refresh.set_busy_angle(0.0)
                self.spinner.start()
        else:
            self.spinner.stop()
            self.window.header_refresh.set_busy_angle(None)

    def refresh_preferences(self):
        self.enabled = system_motion_enabled()
        if not self.enabled:
            self.finish_transitions()
        self._sync_spinner()

    def finish_transitions(self):
        for channel in list(self._channels):
            if isValid(channel):
                channel.finish()
        self.veil.set_amount(0)

    def shutdown(self):
        self.stopping = True
        self._busy = False
        self._sync_spinner()
        self.finish_transitions()
        self.window.header_refresh.set_busy_angle(None)

    def dispose(self):
        # QObject emits destroyed before deleting children. Stop callbacks here,
        # before controls and their Python wrappers can be torn down in any order.
        self.disposed = True
        self.spinner.stop()
        for channel in list(self._channels):
            if isValid(channel):
                channel.stop()
                channel.valueChanged.disconnect()
        self._outlines.clear()
        self._focus_targets.clear()
        self.window = None

    def eventFilter(self, watched, event):
        if self.disposed:
            return False
        kind = event.type()
        if watched is self.window:
            if kind in (QEvent.Show, QEvent.WindowStateChange, QEvent.ActivationChange):
                self.refresh_preferences()
                if not self.visible:
                    self.finish_transitions()
                self.navigate(self._current_page, initial=True)
            elif kind in (QEvent.Hide, QEvent.Close):
                self.spinner.stop()
                self.window.task_progress.setRange(0, 1)
                self.window.task_progress.setValue(1 if self._busy else 0)
                self.window.header_refresh.set_busy_angle(None)
                self.finish_transitions()
        else:
            target_widget = self._focus_targets.get(watched, watched)
            outline = self._outlines.get(target_widget)
            if outline is None:
                return False
            if kind == QEvent.Resize:
                outline.setGeometry(target_widget.rect())
            elif kind in (QEvent.FocusIn, QEvent.FocusOut, QEvent.Enter, QEvent.Leave,
                          QEvent.EnabledChange):
                focused = target_widget.hasFocus() or bool(
                    target_widget.focusProxy() and target_widget.focusProxy().hasFocus())
                target = (1.0 if focused else 0.4 if target_widget.underMouse() else 0.0)
                if not target_widget.isEnabled():
                    target = 0.0
                self.transition(outline, "focus", outline.amount, target,
                                outline.set_amount, DURATIONS["focus"])
        if kind == QEvent.Resize:
            if watched is self.window:
                self.veil.setGeometry(self.veil.parentWidget().rect())
        return False
