from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QSignalBlocker, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLayout,
    QLineEdit, QListWidget, QListWidgetItem, QSizePolicy, QStyle, QToolButton,
    QVBoxLayout, QWidget,
)

from .regions import ALIASES
from .theme import REGION_STYLE



class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing=6):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self._items = []
        self._spacing = spacing

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize(0, 0)
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _do_layout(self, rect, test_only):
        x, y, line_height = rect.x(), rect.y(), 0
        for item in self._items:
            width = min(item.sizeHint().width(), max(0, rect.width()))
            height = item.sizeHint().height()
            if x + width > rect.x() + rect.width() and line_height:
                x = rect.x()
                y += line_height + self._spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, width, height))
            x += width + self._spacing
            line_height = max(line_height, height)
        return y + line_height - rect.y()


class RegionChip(QWidget):
    remove_requested = Signal(str)

    def __init__(self, region, parent=None):
        super().__init__(parent)
        self.region = region
        self.setObjectName("regionChip")
        self.setAttribute(Qt.WA_StyledBackground)
        self.setToolTip(region)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 2, 3, 2)
        layout.setSpacing(3)
        label = QLabel(self.fontMetrics().elidedText(region, Qt.ElideRight, 170))
        label.setMinimumWidth(0)
        self.remove_button = QToolButton()
        self.remove_button.setObjectName("regionRemove")
        self.remove_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton))
        self.remove_button.setFixedSize(24, 24)
        self.remove_button.setToolTip(f"删除排除地区：{region}")
        self.remove_button.setAccessibleName(f"删除排除地区：{region}")
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self.region))
        layout.addWidget(label)
        layout.addWidget(self.remove_button)


class RegionSearchEdit(QLineEdit):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class RegionMultiSelect(QFrame):
    selection_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected = []
        self._options = []
        self._popup_filter_installed = False
        self.setObjectName("regionSelect")
        self.setAccessibleName("排除地区")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumHeight(44)
        self.setStyleSheet(REGION_STYLE)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 6, 6)
        layout.setSpacing(6)
        self.content = QWidget()
        self.flow = FlowLayout(self.content)
        self.editor = RegionSearchEdit()
        self.editor.setObjectName("regionSearch")
        self.editor.setMinimumWidth(130)
        self.editor.setPlaceholderText("请选择或搜索地区")
        self.editor.setAccessibleName("排除地区，搜索或选择多个地区")
        self.editor.setToolTip("搜索地区；也可输入自定义地区后选择添加")
        self.flow.addWidget(self.editor)
        layout.addWidget(self.content, 1)
        self.clear_button = QToolButton()
        self.clear_button.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        self.clear_button.setToolTip("清空排除地区")
        self.clear_button.setAccessibleName("清空排除地区")
        self.clear_button.setFixedSize(28, 30)
        self.clear_button.clicked.connect(self.clear)
        layout.addWidget(self.clear_button, 0, Qt.AlignTop)
        self.toggle_button = QToolButton()
        self.toggle_button.setArrowType(Qt.DownArrow)
        self.toggle_button.setToolTip("展开或收起地区选项")
        self.toggle_button.setAccessibleName("展开或收起地区选项")
        self.toggle_button.setFixedSize(28, 30)
        self.toggle_button.clicked.connect(self._toggle_popup)
        layout.addWidget(self.toggle_button, 0, Qt.AlignTop)
        self.setFocusProxy(self.editor)

        # A non-activating window keeps typing in the field and escapes scroll clipping.
        self.popup = QWidget(self, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
        self.popup.setAttribute(Qt.WA_ShowWithoutActivating)
        self.popup.setAttribute(Qt.WA_TranslucentBackground)
        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(8, 8, 8, 10)
        frame = QFrame()
        frame.setObjectName("regionMenu")
        shadow = QGraphicsDropShadowEffect(frame)
        shadow.setBlurRadius(14)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(36, 39, 46, 45))
        frame.setGraphicsEffect(shadow)
        popup_layout.addWidget(frame)
        menu = QVBoxLayout(frame)
        menu.setContentsMargins(5, 5, 5, 5)
        menu.setSpacing(2)
        self.options = QListWidget()
        self.options.setAccessibleName("地区选项（可多选）")
        self.options.setFocusPolicy(Qt.NoFocus)
        self.options.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.options.itemClicked.connect(self._choose_item)
        menu.addWidget(self.options)
        self.empty_label = QLabel("未找到匹配地区")
        self.empty_label.setObjectName("regionEmpty")
        menu.addWidget(self.empty_label)
        self.editor.textChanged.connect(self._search_changed)
        self.editor.clicked.connect(self._toggle_popup)
        self.editor.installEventFilter(self)
        self.content.installEventFilter(self)
        self._render_selection()

    def selected_regions(self):
        return list(self._selected)

    def set_selected_regions(self, regions):
        selected = list(dict.fromkeys(region for region in regions if region))
        if selected == self._selected:
            return
        self._selected = selected
        self._render_selection()
        self.selection_changed.emit(self.selected_regions())

    def set_available_regions(self, regions):
        self._options = list(dict.fromkeys(regions))
        self._filter_options()
        self._position_popup()

    def remove_region(self, region):
        self.set_selected_regions([value for value in self._selected if value != region])

    def clear(self):
        with QSignalBlocker(self.editor):
            self.editor.clear()
        self.set_selected_regions([])
        self._filter_options()
        self._position_popup()

    def _render_selection(self):
        self.flow.removeWidget(self.editor)
        while self.flow.count():
            chip = self.flow.takeAt(0).widget()
            chip.hide()
            chip.deleteLater()
        for region in self._selected:
            chip = RegionChip(region)
            chip.remove_requested.connect(self.remove_region)
            chip.installEventFilter(self)
            for label in chip.findChildren(QLabel):
                label.installEventFilter(self)
            self.flow.addWidget(chip)
        self.flow.addWidget(self.editor)
        self.clear_button.setVisible(bool(self._selected))
        self.editor.setPlaceholderText("搜索地区" if self._selected else "请选择或搜索地区")
        self.flow.invalidate()
        self.content.updateGeometry()
        self.updateGeometry()
        self._filter_options()
        QTimer.singleShot(0, self._position_popup)

    def _filter_options(self):
        current = self.options.currentItem()
        current_data = current.data(Qt.UserRole) if current else None
        query = self.editor.text().strip()
        self.options.clear()
        candidates = list(dict.fromkeys([*self._options, *self._selected]))
        matches = [region for region in candidates
                   if any(query.casefold() in alias.casefold()
                          for alias in ALIASES.get(region, (region,)))]
        for region in matches:
            item = QListWidgetItem(region, self.options)
            item.setData(Qt.UserRole, region)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Checked if region in self._selected else Qt.Unchecked)
        self.empty_label.setVisible(not matches)
        if query and query not in candidates and not matches:
            item = QListWidgetItem(f'添加“{query}”', self.options)
            item.setData(Qt.UserRole, query)
            item.setToolTip("添加自定义地区，沿用原有名称匹配规则")
        self.options.setVisible(bool(self.options.count()))
        self.options.setCurrentRow(next((i for i in range(self.options.count())
                                        if self.options.item(i).data(Qt.UserRole) == current_data), 0))
        self.options.setFixedHeight(min(8, self.options.count()) * 34 + 4)

    def _choose_item(self, item):
        region = item.data(Qt.UserRole)
        if region in self._selected:
            self.remove_region(region)
        else:
            self.set_selected_regions([*self._selected, region])
        self.editor.setFocus()

    def _search_changed(self):
        self._filter_options()
        if self.editor.hasFocus() and self.isVisible():
            self.show_popup()
        self._position_popup()

    def show_popup(self):
        if not self.isEnabled():
            return
        self.popup.show()
        self._position_popup()
        self.toggle_button.setArrowType(Qt.UpArrow)
        if not self._popup_filter_installed:
            QApplication.instance().installEventFilter(self)
            self._popup_filter_installed = True
        self.editor.setFocus()

    def hide_popup(self):
        self.popup.hide()
        self.toggle_button.setArrowType(Qt.DownArrow)
        if self._popup_filter_installed:
            QApplication.instance().removeEventFilter(self)
            self._popup_filter_installed = False

    def _toggle_popup(self):
        if self.popup.isVisible():
            self.hide_popup()
        else:
            self.show_popup()

    def _position_popup(self):
        if not self.popup.isVisible():
            return
        screen = self.screen().availableGeometry()
        window = self.window()
        bounds = QRect(window.mapToGlobal(QPoint(0, 0)), window.size()).intersected(screen)
        width = min(self.width() + 16, screen.width())
        below = self.mapToGlobal(QPoint(0, self.height()))
        above = self.mapToGlobal(QPoint(0, 0))
        self.options.setFixedHeight(min(8, self.options.count()) * 34 + 4)
        height = self.popup.sizeHint().height()
        below_space = bounds.bottom() - below.y() - 4
        above_space = above.y() - bounds.top() - 4
        opens_above = height > below_space and above_space > below_space
        space = above_space if opens_above else below_space
        if height > space:
            self.options.setFixedHeight(max(36, self.options.height() - (height - space)))
        self.popup.adjustSize()
        height = min(self.popup.sizeHint().height(), screen.height())
        y = above.y() - height + 4 if opens_above else below.y() - 4
        x = max(screen.left(), min(below.x() - 8, screen.right() - width + 1))
        self.popup.setGeometry(x, max(screen.top(), y), width, height)

    def _contains(self, widget):
        return isinstance(widget, QWidget) and (
            widget is self or self.isAncestorOf(widget) or widget is self.popup
            or self.popup.isAncestorOf(widget))

    def eventFilter(self, watched, event):
        kind = event.type()
        if self.popup.isVisible():
            if kind == QEvent.MouseButtonPress:
                position = event.globalPosition().toPoint()
                if not (self.rect().contains(self.mapFromGlobal(position))
                        or self.popup.rect().contains(self.popup.mapFromGlobal(position))):
                    self.hide_popup()
            elif kind == QEvent.FocusIn and isinstance(watched, QWidget) and not self._contains(watched):
                self.hide_popup()
            elif kind == QEvent.ApplicationDeactivate:
                self.hide_popup()
            elif kind in (QEvent.Move, QEvent.Resize) and watched is self.window():
                self._position_popup()
            elif kind == QEvent.Wheel:
                # Native wheel delivery starts at QWindow, before reaching the viewport.
                position = event.globalPosition().toPoint()
                if not self.popup.rect().contains(self.popup.mapFromGlobal(position)):
                    self.hide_popup()
                elif watched is self.popup:
                    # Only stop unhandled boundary/margin wheels after the list had its turn.
                    event.accept()
                    return True
        if kind == QEvent.KeyPress and self._contains(watched):
            key = event.key()
            if key == Qt.Key_Escape and self.popup.isVisible():
                self.hide_popup()
                return True
            if watched is self.editor and key in (Qt.Key_Down, Qt.Key_Up):
                was_open = self.popup.isVisible()
                self.show_popup()
                row = self.options.currentRow()
                if was_open:
                    row += 1 if key == Qt.Key_Down else -1
                elif key == Qt.Key_Up:
                    row = self.options.count() - 1
                self.options.setCurrentRow(max(0, min(row, self.options.count() - 1)))
                return True
            if watched is self.editor and key in (Qt.Key_Return, Qt.Key_Enter):
                if self.popup.isVisible() and self.options.currentItem():
                    self._choose_item(self.options.currentItem())
                else:
                    self.show_popup()
                return True
            if key in (Qt.Key_Tab, Qt.Key_Backtab):
                self.hide_popup()
        if watched is self.editor and kind in (QEvent.FocusIn, QEvent.FocusOut):
            self.setProperty("focused", kind == QEvent.FocusIn)
            self.style().unpolish(self)
            self.style().polish(self)
        if (kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton
                and isinstance(watched, QWidget) and watched is not self.editor
                and not isinstance(watched, QToolButton)):
            if watched is self.content or self.content.isAncestorOf(watched):
                self._toggle_popup()
                return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_popup()
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_popup()

    def hideEvent(self, event):
        self.hide_popup()
        super().hideEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.EnabledChange and not self.isEnabled():
            self.hide_popup()
        super().changeEvent(event)
