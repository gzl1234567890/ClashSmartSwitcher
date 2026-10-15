from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
import sys

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFormLayout, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSpinBox, QSplitter, QStyle, QSystemTrayIcon,
    QToolButton, QGraphicsOpacityEffect, QLayout,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from .config import MAX_CONCURRENCY
from .core import group_members, is_node
from .api import ApiError
from .monitor import MonitorController
from .regions import excluded_region
from .status import TrafficState


STYLE = """
QWidget { font-family: 'Microsoft YaHei UI', 'Segoe UI'; font-size: 13px; color: #24272e; }
QMainWindow, QWidget#root { background: #f5f6f8; }
QWidget#header { background: #242c3b; }
QWidget#header QLabel { color: #f9fafc; background: transparent; }
QLabel#title { font-size: 22px; font-weight: 600; }
QLabel#muted { color: #616977; }
QLabel#node { font-size: 18px; font-weight: 600; }
QLabel#delay { font-size: 26px; font-weight: 600; color: #087f69; }
QLabel#section { font-size: 14px; font-weight: 600; }
QWidget#summary { background: white; border-bottom: 1px solid #dce0e7; }
QTabWidget::pane { border: 1px solid #dce0e7; background: white; }
QTabBar::tab { padding: 10px 20px; background: #e9ecf1; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { background: white; color: #087f69; border-bottom: 2px solid #087f69; }
QPushButton { border: 1px solid #c6ccd5; border-radius: 5px; background: white; padding: 7px 13px; min-height: 21px; }
QPushButton:hover { background: #eef4f2; border-color: #087f69; }
QPushButton:pressed { background: #dceae5; }
QPushButton:focus, QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 2px solid #087f69; }
QPushButton#primary { background: #087f69; color: white; border-color: #087f69; }
QPushButton#primary:hover { background: #096b5b; }
QPushButton:disabled { background: #f0f1f4; color: #808692; border-color: #e0e3e8; }
QLineEdit, QSpinBox, QComboBox { background: white; border: 1px solid #c6ccd5; border-radius: 4px; padding: 6px; min-height: 22px; }
QComboBox::drop-down { width: 23px; border: none; }
QCheckBox { spacing: 8px; }
QTableWidget { background: white; border: none; alternate-background-color: #f6f8fa; gridline-color: #ebedf1; }
QHeaderView::section { background: #f0f3f6; border: none; border-bottom: 1px solid #dce0e7; padding: 9px; font-weight: 600; }
QTableWidget::item { padding: 5px; }
QTableWidget::item:selected { background: #e2f2ed; color: #24272e; }
QPlainTextEdit { border: 1px solid #dce0e7; background: #fafbfc; padding: 7px; }
QTextBrowser { border: none; background: white; padding: 15px; }
QLabel#notice { padding: 9px 12px; background: #eef4f2; color: #285248; border-radius: 4px; }
QLabel#settingHint { color: #616977; padding-left: 8px; }
QWidget#regionChip { background: #e2f2ed; border: 1px solid #a9d7c9; border-radius: 14px; }
QWidget#regionChip QLabel { color: #285248; padding-left: 10px; }
QToolButton#regionRemove { border: none; border-radius: 10px; padding: 2px; }
QToolButton#regionRemove:hover { background: #c6e8dc; }
QStatusBar { background: #edf0f4; }
"""


def resource_path(relative):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / relative


class NoWheelSpinBox(QSpinBox):
    """Keep the settings stable while the surrounding scroll area is wheeled."""

    def wheelEvent(self, event):
        event.ignore()


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=8):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
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
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _do_layout(self, rect, test_only):
        margins = self.contentsMargins()
        area = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x, y, line_height = area.x(), area.y(), 0
        for item in self._items:
            space_x = self._spacing
            space_y = self._spacing
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > area.right() and line_height > 0:
                x = area.x()
                y += line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, item.sizeHint().width(), item.sizeHint().height()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y() + margins.bottom()


class RegionChip(QWidget):
    remove_requested = Signal(str)

    def __init__(self, region, parent=None):
        super().__init__(parent)
        self.region = region
        self.setObjectName("regionChip")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 2, 0)
        layout.setSpacing(2)
        label = QLabel(region)
        close = QToolButton()
        close.setObjectName("regionRemove")
        close.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton))
        close.setToolTip(f"删除排除地区：{region}")
        close.setAccessibleName(f"删除排除地区：{region}")
        close.setAutoRaise(True)
        close.clicked.connect(lambda: self.remove_requested.emit(self.region))
        layout.addWidget(label)
        layout.addWidget(close)


class MainWindow(QMainWindow):
    def __init__(self, store, settings, logger, redactor, controller=None):
        super().__init__()
        self.store, self.settings = store, settings
        self.logger, self.redactor = logger, redactor
        self.controller = controller or MonitorController(settings, parent=self)
        self.proxies = {}
        self.exiting = False
        self.pending_start = False
        self._concurrency_internal = False
        self._excluded_regions = []
        self.setWindowTitle("Clash 智能节点管家")
        self.resize(1120, 820)
        self.setMinimumSize(850, 630)
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.setStyleSheet(STYLE)
        self._build()
        self._tray()
        self.controller.connection.connect(self._connected)
        self.controller.result.connect(self._result)
        self.controller.message.connect(self.append_log)
        self.controller.error.connect(self._error)
        self.controller.status.connect(self._status)
        self.controller.busy_changed.connect(self._busy)
        self.controller.idle.connect(self._idle)
        self._fill_settings()
        self.append_log("程序启动；自动操作将在连接与代理状态检查通过后执行")
        if store.warning:
            self.append_log(store.warning)
            self.notice.setText(store.warning)

    def button(self, text, icon, callback, primary=False):
        button = QPushButton(text)
        button.setIcon(self.style().standardIcon(icon))
        button.setToolTip(text)
        if primary:
            button.setObjectName("primary")
        button.clicked.connect(callback)
        return button

    def _build(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QWidget()
        header.setObjectName("header")
        bar = QHBoxLayout(header)
        bar.setContentsMargins(24, 19, 24, 19)
        title = QLabel("Clash 智能节点管家")
        title.setObjectName("title")
        bar.addWidget(title)
        bar.addStretch()
        self.header_status = QLabel("接口未连接")
        bar.addWidget(self.header_status)
        layout.addWidget(header)

        summary = QWidget()
        summary.setObjectName("summary")
        grid = QGridLayout(summary)
        grid.setContentsMargins(24, 17, 24, 17)
        grid.setHorizontalSpacing(26)
        grid.setVerticalSpacing(8)
        self.node = QLabel("等待连接")
        self.node.setObjectName("node")
        self.node.setWordWrap(True)
        self.delay = QLabel("未测速")
        self.delay.setObjectName("delay")
        self.auto_state = QLabel("已关闭")
        self.auto_state.setObjectName("node")
        for column, title in enumerate(("当前节点", "本轮延迟", "自动切换")):
            label = QLabel(title)
            label.setObjectName("muted")
            grid.addWidget(label, 0, column)
        grid.addWidget(self.node, 1, 0)
        grid.addWidget(self.delay, 1, 1)
        grid.addWidget(self.auto_state, 1, 2)
        grid.setColumnStretch(0, 5)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 2)
        self.traffic_label = QLabel("系统代理：状态无法确认    TUN：状态无法确认")
        self.traffic_label.setObjectName("muted")
        self.traffic_label.setWordWrap(True)
        grid.addWidget(self.traffic_label, 2, 0, 1, 3)
        layout.addWidget(summary)

        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(24, 17, 24, 14)
        body.setSpacing(12)
        actions = QHBoxLayout()
        self.group = QComboBox()
        self.group.setMinimumWidth(210)
        self.group.addItem("请选择代理组", "")
        self.group.currentIndexChanged.connect(self._group_changed)
        actions.addWidget(QLabel("代理组"))
        actions.addWidget(self.group, 1)
        self.start_button = self.button("开启自动切换", QStyle.SP_MediaPlay, self.start_auto, True)
        self.pause_button = self.button("暂停", QStyle.SP_MediaPause, self.pause_auto)
        self.stop_button = self.button("关闭", QStyle.SP_MediaStop, self.stop_auto)
        self.measure_button = self.button("立即测速", QStyle.SP_BrowserReload, self.measure)
        actions.addWidget(self.start_button)
        actions.addWidget(self.pause_button)
        actions.addWidget(self.stop_button)
        actions.addWidget(self.measure_button)
        body.addLayout(actions)
        self.notice = QLabel("尚未连接本机控制接口")
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        self.notice.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.addWidget(self.notice)

        self.tabs = QTabWidget()
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        self.table_caption = QLabel("节点测速结果")
        self.table_caption.setObjectName("section")
        panel_layout.addWidget(self.table_caption)
        splitter = QSplitter(Qt.Vertical)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["节点名称", "延迟", "测速状态", "备注"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column, width in ((1, 110), (2, 115), (3, 230)):
            self.table.setColumnWidth(column, width)
        self.table.setMinimumHeight(140)
        splitter.addWidget(self.table)
        log_area = QWidget()
        logs = QVBoxLayout(log_area)
        logs.setContentsMargins(0, 8, 0, 0)
        line = QHBoxLayout()
        label = QLabel("运行日志")
        label.setObjectName("section")
        line.addWidget(label)
        line.addStretch()
        self.last_checked = QLabel("最近检测：尚未检测")
        self.last_checked.setObjectName("muted")
        line.addWidget(self.last_checked)
        line.addWidget(self.button("日志目录", QStyle.SP_DirOpenIcon, self.open_logs))
        line.addWidget(self.button("清空显示", QStyle.SP_TrashIcon, lambda: self.logs.clear()))
        logs.addLayout(line)
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setMaximumBlockCount(2000)
        self.logs.setMinimumHeight(90)
        logs.addWidget(self.logs)
        splitter.addWidget(log_area)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        panel_layout.addWidget(splitter)
        self.tabs.addTab(panel, "控制面板")
        self._settings_page()
        self.help = QTextBrowser()
        self.help.setOpenExternalLinks(True)
        help_path = resource_path("docs/HELP.md")
        self.help.setMarkdown(help_path.read_text(encoding="utf-8") if help_path.exists() else "请查看分发包内的中文 README.md。")
        self.tabs.addTab(self.help, "帮助与排查")
        body.addWidget(self.tabs, 1)
        footer = QHBoxLayout()
        self.connect_button = self.button("重新检测连接", QStyle.SP_BrowserReload, self.connect_api)
        self.discover_button = self.button("自动发现", QStyle.SP_FileDialogContentsView, self.discover_api)
        footer.addWidget(self.connect_button)
        footer.addWidget(self.discover_button)
        footer.addStretch()
        self.version_label = QLabel("本机控制接口 · 等待检测")
        self.version_label.setObjectName("muted")
        self.version_label.setMaximumWidth(300)
        footer.addWidget(self.version_label)
        footer.addWidget(self.button("退出", QStyle.SP_DialogCloseButton, self.request_exit))
        body.addLayout(footer)
        layout.addWidget(content, 1)
        self.statusBar().showMessage("就绪")

    def _settings_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        widget = QWidget()
        form = QFormLayout(widget)
        form.setContentsMargins(24, 20, 24, 20)
        form.setVerticalSpacing(12)
        self.settings_widget = widget
        self.address = QLineEdit()
        self.address.setPlaceholderText("自动发现，或填写 http://127.0.0.1:控制端口")
        self.address.setToolTip("仅支持本机 HTTP/HTTPS 控制地址或 Mihomo 官方命名管道")
        self.secret = QLineEdit()
        self.secret.setEchoMode(QLineEdit.Password)
        self.secret.setPlaceholderText("控制接口需要认证时填写")
        form.addRow("控制接口地址", self.address)
        form.addRow("控制密钥", self.secret)
        self.threshold = self.spin(1, 60000, " ms")
        self.interval = self.spin(5, 86400, " 秒")
        self.timeout = self.spin(500, 30000, " ms")
        self.concurrency = self.spin(1, MAX_CONCURRENCY, " 个")
        self.minimum_switch = self.spin(0, 86400, " 秒")
        self.concurrency.valueChanged.connect(self._concurrency_edited)
        for label, control, low, high in (
                ("延迟阈值", self.threshold, 1, 60000),
                ("检测间隔", self.interval, 5, 86400),
                ("单节点测速超时", self.timeout, 500, 30000),
                ("并发测速数量", self.concurrency, 1, MAX_CONCURRENCY),
                ("最小切换间隔", self.minimum_switch, 0, 86400)):
            row = self.numeric_row(control, low, high)
            if control is self.concurrency:
                self.concurrency_hint = row.findChild(QLabel, "settingHint")
            form.addRow(label, row)
        self.test_url = QLineEdit()
        form.addRow("测速地址", self.test_url)
        regions = QWidget()
        region_layout = QVBoxLayout(regions)
        region_layout.setContentsMargins(0, 0, 0, 0)
        region_layout.setSpacing(8)
        region_input = QHBoxLayout()
        self.region_selector = QComboBox()
        self.region_selector.setEditable(True)
        self.region_selector.setInsertPolicy(QComboBox.NoInsert)
        self.region_selector.addItems(["香港", "新加坡", "日本", "美国", "德国", "英国", "韩国", "台湾"])
        self.region_selector.setPlaceholderText("选择或输入地区")
        self.region_selector.lineEdit().setPlaceholderText("选择或输入地区")
        self.region_selector.setToolTip("选择预设地区，或输入自定义地区")
        self.region_selector.lineEdit().returnPressed.connect(self._add_region_from_editor)
        add_region = self.button("添加地区", QStyle.SP_FileDialogNewFolder, self._add_region_from_editor)
        region_input.addWidget(self.region_selector, 1)
        region_input.addWidget(add_region)
        region_layout.addLayout(region_input)
        self.region_chips_widget = QWidget()
        self.region_chips_layout = FlowLayout(self.region_chips_widget, spacing=7)
        self.region_chips_widget.setMinimumHeight(36)
        region_layout.addWidget(self.region_chips_widget)
        form.addRow("排除地区", regions)
        self.close_to_tray = QCheckBox("关闭窗口时最小化到托盘")
        self.save_secret = QCheckBox("使用 Windows 账户加密保存密钥")
        form.addRow("窗口行为", self.close_to_tray)
        form.addRow("密钥保存", self.save_secret)
        self.save_button = self.button("保存设置", QStyle.SP_DialogSaveButton, self.save_settings, True)
        form.addRow("", self.save_button)
        scroll.setWidget(widget)
        self.tabs.addTab(scroll, "连接与设置")

    @staticmethod
    def spin(low, high, suffix):
        control = NoWheelSpinBox()
        control.setRange(low, high)
        control.setSuffix(suffix)
        control.setToolTip(f"可直接输入，或使用右侧箭头调整。允许范围：{low}–{high}")
        return control

    @staticmethod
    def numeric_row(control, low, high):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(control, 1)
        hint = QLabel(f"范围：{low}–{high}")
        hint.setObjectName("settingHint")
        hint.setMinimumWidth(110)
        layout.addWidget(hint)
        return row

    def _tray(self):
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip("Clash 智能节点管家 · 已关闭")
        menu = QMenu(self)
        for title, callback in (("打开主窗口", self.show_window), ("开启自动切换", self.start_auto),
                                ("暂停自动切换", self.pause_auto), ("关闭自动切换", self.stop_auto),
                                ("退出程序", self.request_exit)):
            action = QAction(title, menu)
            action.triggered.connect(callback)
            menu.addAction(action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()
        elif reason == QSystemTrayIcon.Trigger:
            self.tray.showMessage("Clash 智能节点管家", self.header_status.text() + "\n当前节点：" + self.node.text(), QSystemTrayIcon.Information, 3000)

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _fill_settings(self):
        s = self.settings
        self.address.setText(s.controller)
        self.secret.setText(s.secret)
        self.threshold.setValue(s.threshold_ms)
        self.interval.setValue(s.interval_seconds)
        self.timeout.setValue(s.timeout_ms)
        self._concurrency_internal = True
        self.concurrency.setValue(s.concurrency)
        self._concurrency_internal = False
        self.minimum_switch.setValue(s.minimum_switch_seconds)
        self.test_url.setText(s.test_url)
        self._set_excluded_regions(s.excluded_regions)
        self.close_to_tray.setChecked(s.close_to_tray)
        self.save_secret.setChecked(s.save_secret)
        self.redactor.secrets.add(s.secret)

    def _read_settings(self):
        settings = replace(self.settings, controller=self.address.text().strip(), secret=self.secret.text(),
                           group=(self.group.currentData() or "") if self.proxies else self.settings.group, threshold_ms=self.threshold.value(),
                           interval_seconds=self.interval.value(), timeout_ms=self.timeout.value(),
                           test_url=self.test_url.text().strip(), concurrency=self.concurrency.value(),
                           concurrency_auto=self.settings.concurrency_auto,
                           minimum_switch_seconds=self.minimum_switch.value(), excluded_regions=list(self._excluded_regions),
                           close_to_tray=self.close_to_tray.isChecked(), save_secret=self.save_secret.isChecked(),
                           auto_enabled=self.controller.active)
        settings.validate()
        self.redactor.secrets.add(settings.secret)
        self.settings = settings
        self.controller.settings = settings
        return settings

    def _set_excluded_regions(self, regions):
        self._excluded_regions = []
        for region in regions:
            self._append_region(region, render=False)
        self._render_region_chips()

    def _add_region_from_editor(self):
        region = self.region_selector.currentText().strip()
        if not region:
            return
        self._append_region(region)
        self.region_selector.setCurrentText("")
        self.region_selector.lineEdit().setFocus()

    def _append_region(self, region, render=True):
        if region and region not in self._excluded_regions:
            self._excluded_regions.append(region)
            if render:
                self._render_region_chips()

    def _render_region_chips(self):
        while self.region_chips_layout.count():
            item = self.region_chips_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        for region in self._excluded_regions:
            chip = RegionChip(region, self.region_chips_widget)
            chip.remove_requested.connect(self._remove_region)
            self.region_chips_layout.addWidget(chip)
        self.region_chips_widget.updateGeometry()

    def _remove_region(self, region):
        if region not in self._excluded_regions:
            return
        self._excluded_regions.remove(region)
        for index in range(self.region_chips_layout.count()):
            item = self.region_chips_layout.itemAt(index)
            chip = item.widget()
            if chip and getattr(chip, "region", None) == region:
                effect = QGraphicsOpacityEffect(chip)
                chip.setGraphicsEffect(effect)
                animation = QPropertyAnimation(effect, b"opacity", chip)
                animation.setDuration(150)
                animation.setStartValue(1.0)
                animation.setEndValue(0.0)
                animation.setEasingCurve(QEasingCurve.OutCubic)
                animation.finished.connect(lambda c=chip: self._remove_chip_widget(c))
                chip._remove_animation = animation
                animation.start()
                break

    def _remove_chip_widget(self, chip):
        self.region_chips_layout.removeWidget(chip)
        chip.deleteLater()
        self.region_chips_widget.updateGeometry()

    def _concurrency_edited(self):
        if not self._concurrency_internal:
            self.settings.concurrency_auto = False

    def _sync_concurrency_limit(self, reset_to_node_count=False):
        count = 0
        if self.settings.group and self.proxies:
            try:
                count = len(group_members(self.settings.group, self.proxies))
            except (ApiError, ValueError):
                count = 0
        maximum = count or MAX_CONCURRENCY
        self._concurrency_internal = True
        self.concurrency.setRange(1, maximum)
        if count and (reset_to_node_count or self.settings.concurrency_auto):
            self.concurrency.setValue(count)
        else:
            self.concurrency.setValue(min(self.concurrency.value(), maximum))
        self._concurrency_internal = False
        if count:
            self.concurrency_hint.setText(f"当前代理组 {count} 个节点；范围：1–{count}")
            self.concurrency.setToolTip(f"可直接输入，或使用右侧箭头调整。当前代理组有 {count} 个节点，允许范围：1–{count}")
        else:
            self.concurrency_hint.setText("选择代理组后自动限制到节点数")
            self.concurrency.setToolTip("可直接输入，或使用右侧箭头调整。选择代理组后，最大值会自动限制为节点数")

    def save_settings(self):
        try:
            self.store.save(self._read_settings())
            self.append_log("设置已保存；密钥使用 Windows 账户保护（如启用保存）")
            self.notice.setText("设置已保存")
        except (OSError, ValueError) as exc:
            self._error(str(exc))

    def connect_api(self):
        if self.controller.busy:
            return
        try:
            self._read_settings()
            self.controller.connect_api()
        except ValueError as exc:
            self._error(str(exc))

    def discover_api(self):
        if self.controller.busy:
            return
        self.controller.connect_api(force_discovery=True)

    def start_auto(self):
        if self.controller.busy or self.controller.active:
            return
        try:
            self._read_settings()
            self.controller.connect_api(start_after=True)
        except ValueError as exc:
            self._error(str(exc))

    def pause_auto(self):
        self.controller.pause()
        self.settings.auto_enabled = False
        self.append_log("自动切换已暂停；已发出的请求会结束，不再继续切换。节点和代理配置保持当前状态。")
        self._busy(self.controller.busy)
        self._persist_runtime()

    def stop_auto(self):
        self.pause_auto()
        self._status("自动切换已关闭")
        self._persist_runtime()

    def measure(self):
        if self.controller.busy:
            return
        try:
            self._read_settings()
            self.controller.run_round(automatic=False)
        except ValueError as exc:
            self._error(str(exc))

    def _group_changed(self):
        selected = self.group.currentData() or ""
        if selected == self.settings.group:
            return
        self.controller.pause()
        if selected:
            try:
                if not group_members(selected, self.proxies):
                    raise ValueError("该组没有直接服务器节点，请选择其内部可控代理组")
            except (ValueError, ApiError) as exc:
                self.notice.setText(str(exc))
                self.group.blockSignals(True)
                self.group.setCurrentIndex(max(0, self.group.findData(self.settings.group)))
                self.group.blockSignals(False)
                return
        self.settings.group = selected
        self.settings.concurrency_auto = True
        self.table.setRowCount(0)
        self.delay.setText("未测速")
        self.node.setText(self.proxies.get(selected, {}).get("now", "未选择"))
        self._populate_members()
        self._sync_concurrency_limit(reset_to_node_count=bool(selected))
        self._busy(False)

    def _populate_members(self):
        group = self.proxies.get(self.settings.group, {})
        self.table.setRowCount(0)
        for name in group.get("all", []):
            if not isinstance(name, str):
                continue
            excluded = excluded_region(name, self.settings.excluded_regions)
            remark = "策略 / 代理组容器" if not is_node(name, self.proxies) else (
                f"已排除：{excluded}" if excluded else "候选节点")
            self._table_row(name, "未测速", "等待检测", ("当前使用；" if name == group.get("now") else "") + remark)

    def _connected(self, data):
        self.settings = self.controller.settings
        self.proxies = data["proxies"]
        self.group.blockSignals(True)
        self.group.clear()
        self.group.addItem("请选择代理组", "")
        for name in data["groups"]:
            self.group.addItem(name, name)
        self.group.setCurrentIndex(max(0, self.group.findData(self.settings.group)))
        self.group.blockSignals(False)
        self.address.setText(self.settings.controller)
        self.secret.setText(self.settings.secret)
        self.redactor.secrets.add(self.settings.secret)
        self.node.setText(self.proxies.get(self.settings.group, {}).get("now", "未选择代理组"))
        self.delay.setText("未测速")
        self.version_label.setText("Mihomo " + data["version"])
        self.version_label.setToolTip(self.settings.controller)
        self._traffic(data["traffic"])
        self.notice.setText("接口连接成功" if self.settings.group else "接口连接成功；请选择需要管理的代理组")
        self._populate_members()
        self._sync_concurrency_limit()
        self._persist_runtime()

    def _traffic(self, traffic):
        self.traffic_label.setText(f"系统代理：{TrafficState.label(traffic.system_proxy)}    TUN：{TrafficState.label(traffic.tun)}")
        self.traffic_label.setToolTip(traffic.detail)

    def _result(self, result):
        self.table.setRowCount(0)
        self.node.setText(result.current or "状态无法确认")
        active = next((x for x in result.measurements if x.name == result.current), None)
        self.delay.setText(f"{active.delay} ms" if active and active.delay is not None else "测速失败 / 未知")
        self.delay.setStyleSheet("color: " + ("#087f69" if active and active.delay is not None and active.delay <= self.settings.threshold_ms else "#a76508"))
        for item in result.measurements:
            remark = ("当前使用；" if item.name == result.current else "") + (f"已排除：{item.excluded}" if item.excluded else "候选节点")
            self._table_row(item.name, f"{item.delay} ms" if item.delay is not None else "无有效数据",
                            "正常" if item.delay is not None and item.delay <= self.settings.threshold_ms else ("延迟偏高" if item.delay else "测速失败"),
                            remark, item.error)
        self.table_caption.setText(f"节点测速结果 · {len(result.measurements)} 个节点 · {result.group}")
        self.last_checked.setText("最近检测：" + datetime.now().strftime("%H:%M:%S"))
        self.notice.setText(result.message)
        if result.traffic:
            self._traffic(result.traffic)
        if result.switched:
            self.tray.showMessage("节点已切换", result.message, QSystemTrayIcon.Information, 4000)

    def _table_row(self, name, delay, status, remark, error=""):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 37)
        for col, text in enumerate((name, delay, status, remark)):
            item = QTableWidgetItem(text)
            item.setToolTip(error if col == 2 and error else text)
            if col == 1:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if "当前使用" in remark:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setBackground(QColor("#edf8f3"))
            if col == 2:
                item.setForeground(QColor("#087f69" if status == "正常" else "#a76508" if status == "延迟偏高" else "#616977"))
            self.table.setItem(row, col, item)

    def _error(self, message):
        self.notice.setText(message)
        self.header_status.setText("需要处理")
        self.statusBar().showMessage(message)
        if "系统代理" in message or "TUN" in message:
            dialog = QMessageBox(QMessageBox.Warning, "请先启用代理模式", message, parent=self)
            retry = dialog.addButton("重新检测", QMessageBox.AcceptRole)
            dialog.addButton("取消", QMessageBox.RejectRole)
            dialog.exec()
            if dialog.clickedButton() == retry:
                QTimer.singleShot(0, self.connect_api)

    def _status(self, text):
        self.header_status.setText(text)
        self.auto_state.setText("运行中" if self.controller.active else ("已暂停" if "暂停" in text else "已关闭"))
        self.tray.setToolTip("Clash 智能节点管家 · " + text)
        self.statusBar().showMessage(text)
        self._busy(self.controller.busy)

    def _busy(self, busy):
        active = self.controller.active
        for button in (self.connect_button, self.discover_button, self.measure_button):
            button.setEnabled(not busy and not self.exiting)
        self.start_button.setEnabled(not busy and not active and not self.exiting)
        self.pause_button.setEnabled((active or busy) and not self.exiting)
        self.stop_button.setEnabled((active or busy) and not self.exiting)
        self.group.setEnabled(not busy and not self.exiting)
        self.settings_widget.setEnabled(not busy and not active and not self.exiting)

    def append_log(self, message):
        for secret in self.redactor.secrets:
            if secret:
                message = message.replace(secret, "[密钥已隐藏]")
        self.logger.info(message)
        self.logs.appendPlainText(datetime.now().strftime("%H:%M:%S") + "  " + message)

    def open_logs(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.directory / "logs")))

    def _persist_runtime(self):
        try:
            self.settings.auto_enabled = self.controller.active
            self.store.save(self.settings)
        except (OSError, ValueError) as exc:
            self.append_log("保存运行状态失败：" + str(exc))

    def _idle(self):
        if self.exiting:
            self._finish_exit()
        elif self.controller.active:
            self._persist_runtime()

    def request_exit(self):
        if self.exiting:
            return
        if self.controller.active:
            choice = QMessageBox.question(self, "退出程序", "自动切换仍在运行。退出后将停止检测，是否退出？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if choice != QMessageBox.Yes:
                return
        self.exiting = True
        self.controller.shutdown()
        self._persist_runtime()
        self._busy(self.controller.busy)
        self.notice.setText("正在结束后台请求，请稍候…")
        if not self.controller.busy:
            self._finish_exit()

    def _finish_exit(self):
        self.append_log("后台任务已结束，程序退出")
        self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        if self.exiting and not self.controller.busy:
            event.accept()
            return
        event.ignore()
        if self.settings.close_to_tray and self.tray.isVisible() and not self.exiting:
            self.hide()
            self.tray.showMessage("已最小化到托盘", self.header_status.text(), QSystemTrayIcon.Information, 2000)
        else:
            self.request_exit()
