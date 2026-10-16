from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
import sys

from PySide6.QtCore import QDir, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFormLayout, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSpinBox, QSplitter, QStyle, QSystemTrayIcon,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from .config import AUTO_CONCURRENCY_CAP, MAX_CONCURRENCY
from .core import group_members, is_node
from .api import ApiError
from .monitor import MonitorController
from .regions import available_regions, excluded_region
from .region_select import RegionMultiSelect
from .status import TrafficState


from .theme import COLORS, apply_interface_typography, interface_font, load_app_fonts, stylesheet
from .ui_components import icon, resource_path, set_tone
from .ui_layout import WindowLayout
from .motion import MotionController, is_settings_message


class MainWindow(QMainWindow, WindowLayout):
    def __init__(self, store, settings, logger, redactor, controller=None):
        super().__init__()
        self.store, self.settings = store, settings
        self.logger, self.redactor = logger, redactor
        self.controller = controller or MonitorController(settings, parent=self)
        self.proxies = {}
        self.exiting = False
        self._concurrency_internal = False
        self._draft_concurrency_auto = settings.concurrency_auto
        self._reconnect_pending = False
        self._resume_after_reconnect = False
        self.setWindowTitle("Clash 智能节点管家")
        self._settings_loading = True
        self._appending_log = False
        self._paused_by_user = False
        self._task_status = "就绪"
        self._last_result_time = None
        self._latency_history = []
        self.resize(1440, 900)
        self.setMinimumSize(850, 630)
        load_app_fonts()
        self.setFont(interface_font())
        self.setWindowIcon(QIcon(str(resource_path("resources/app.ico"))))
        QDir.addSearchPath("uiicons", str(resource_path("resources/icons/lucide")))
        self.setStyleSheet(stylesheet())
        self._build()
        apply_interface_typography(self, (
            self.delay, self.last_checked, self.table, self.overview_table,
            self.threshold, self.interval, self.timeout, self.minimum_switch,
            self.concurrency, self.rule_threshold, self.rule_interval,
            self.rule_timeout, self.rule_cooldown, self.logs, self.recent_logs,
            self.switch_history, self.result_summary, self.trend_caption,
        ))
        self.motion = MotionController(self, self.sidebar)
        self._tray()
        self.controller.connection.connect(self._connected)
        self.controller.result.connect(self._result)
        self.controller.message.connect(self.append_log)
        self.controller.error.connect(self._error)
        self.controller.status.connect(self._status)
        self.controller.busy_changed.connect(self._busy)
        self.controller.idle.connect(self._idle)
        self._fill_settings()
        self._refresh_dashboard_rules()
        self._refresh_node_preview()
        self._settings_loading = False
        self._saved_form = self._form_snapshot()
        self._busy(self.controller.busy)
        self.append_log("程序启动；自动操作将在连接与代理状态检查通过后执行")
        if store.warning:
            self.append_log(store.warning)
            self.notice.setText(store.warning)

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
        self._draft_concurrency_auto = s.concurrency_auto
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
        self.region_selector.set_selected_regions(s.excluded_regions)
        self.close_to_tray.setChecked(s.close_to_tray)
        self.save_secret.setChecked(s.save_secret)
        self.redactor.secrets.add(s.secret)

    def _refresh_dashboard_rules(self):
        if not hasattr(self, "rule_threshold"):
            return
        s = self.settings
        regions = "、".join(s.excluded_regions) or "无"
        self.rule_threshold.setText(f"延迟阈值    {s.threshold_ms} ms")
        self.rule_interval.setText(f"检测间隔    {s.interval_seconds} 秒")
        self.rule_regions.setText(f"排除地区    {regions}")
        self.rule_timeout.setText(f"测速超时    {s.timeout_ms / 1000:g} 秒")
        self.rule_cooldown.setText(f"最小切换间隔    {s.minimum_switch_seconds} 秒")
        self.trend_caption.setText(f"最近 5 次 · 阈值 {s.threshold_ms} ms")
        self.latency_trend.set_history(self._latency_history, s.threshold_ms)

    def _form_snapshot(self):
        return dict(address=self.address.text(), secret=self.secret.text(),
                    threshold=self.threshold.value(), interval=self.interval.value(),
                    timeout=self.timeout.value(), concurrency=self.concurrency.value(),
                    concurrency_auto=self._draft_concurrency_auto,
                    minimum_switch=self.minimum_switch.value(), test_url=self.test_url.text(),
                    regions=tuple(self.region_selector.selected_regions()),
                    close_to_tray=self.close_to_tray.isChecked(), save_secret=self.save_secret.isChecked())

    def _settings_edited(self, *_):
        if getattr(self, "_settings_loading", False):
            return
        self._refresh_dashboard_rules()
        changed = self._form_snapshot() != getattr(self, "_saved_form", ())
        self.settings_feedback.setText("有未保存的修改" if changed else "设置已保存")
        self.settings_feedback.setProperty("tone", "warning" if changed else "")
        self.settings_feedback.style().unpolish(self.settings_feedback)
        self.settings_feedback.style().polish(self.settings_feedback)

    def _filter_nodes(self, query):
        query = query.strip().casefold()
        for row in range(self.table.rowCount()):
            values = " ".join(
                self.table.item(row, col).text() if self.table.item(row, col) else ""
                for col in range(self.table.columnCount())
            ).casefold()
            self.table.setRowHidden(row, bool(query and query not in values))

    def _clear_logs(self):
        self.logs.clear()
        self.recent_logs.clear()
        self.statusBar().showMessage("已清空界面日志；文件日志未删除", 3000)

    def _follow_log_changed(self, checked):
        if checked:
            self.logs.verticalScrollBar().setValue(self.logs.verticalScrollBar().maximum())

    def _log_scrolled(self, value):
        bar = self.logs.verticalScrollBar()
        if not self._appending_log and value < bar.maximum() - 8 and self.follow_logs.isChecked():
            self.follow_logs.blockSignals(True)
            self.follow_logs.setChecked(False)
            self.follow_logs.blockSignals(False)

    def _read_settings(self):
        settings = replace(self.settings, controller=self.address.text().strip(), secret=self.secret.text(),
                           group=(self.group.currentData() or "") if self.proxies else self.settings.group, threshold_ms=self.threshold.value(),
                           interval_seconds=self.interval.value(), timeout_ms=self.timeout.value(),
                           test_url=self.test_url.text().strip(), concurrency=self.concurrency.value(),
                           concurrency_auto=self._draft_concurrency_auto,
                           minimum_switch_seconds=self.minimum_switch.value(),
                           excluded_regions=self.region_selector.selected_regions(),
                           close_to_tray=self.close_to_tray.isChecked(), save_secret=self.save_secret.isChecked(),
                           auto_enabled=self.controller.active)
        settings.validate()
        self.redactor.secrets.add(settings.secret)
        return settings

    def _commit_settings(self, settings):
        self.settings = settings
        self.controller.settings = settings
        self._refresh_dashboard_rules()

    def _concurrency_edited(self):
        if not self._concurrency_internal:
            self._draft_concurrency_auto = False

    def _sync_concurrency_limit(self, reset_to_node_count=False):
        count = 0
        if self.settings.group and self.proxies:
            try:
                count = len(group_members(self.settings.group, self.proxies))
            except (ApiError, ValueError):
                count = 0
        maximum = count or MAX_CONCURRENCY
        if count and self.settings.concurrency_auto:
            self.settings.concurrency = min(count, AUTO_CONCURRENCY_CAP)
        self._concurrency_internal = True
        self.concurrency.setRange(1, maximum)
        if count and (reset_to_node_count or self._draft_concurrency_auto):
            self.concurrency.setValue(min(count, AUTO_CONCURRENCY_CAP))
        else:
            self.concurrency.setValue(min(self.concurrency.value(), maximum))
        self._concurrency_internal = False
        if count:
            self.concurrency_hint.setText(f"当前代理组 {count} 个节点；自动模式最多 {AUTO_CONCURRENCY_CAP} 个并发")
            self.concurrency.setToolTip(f"自动模式最多 {AUTO_CONCURRENCY_CAP} 个并发；也可手动调整，当前代理组允许范围：1–{count}")
        else:
            self.concurrency_hint.setText("选择代理组后自动限制到节点数")
            self.concurrency.setToolTip("可直接输入，或使用右侧箭头调整。选择代理组后，最大值会自动限制为节点数")

    def save_settings(self):
        try:
            settings = self._read_settings()
            connection_changed = (settings.controller, settings.secret) != (self.settings.controller, self.settings.secret)
            self.store.save(settings)
            if connection_changed:
                self._resume_after_reconnect = self.controller.active or self._resume_after_reconnect
                self._reconnect_pending = True
                self.controller.pause()
            self._commit_settings(settings)
            self.append_log("设置已保存；密钥使用 Windows 账户保护（如启用保存）")
            self._saved_form = self._form_snapshot()
            self._settings_edited()
            message = ("设置已保存；当前任务结束后重新连接" if self._reconnect_pending else
                       "设置已保存；新规则从下一轮检测生效" if self.controller.active else "设置已保存")
            self.settings_feedback.setText(message)
            self.notice.setText(message, "success")
            if self._reconnect_pending and not self.controller.busy:
                self._reconnect_settings()
        except (OSError, ValueError) as exc:
            self._error(str(exc))

    def connect_api(self):
        if self.controller.busy:
            return
        self._resume_after_reconnect = self.controller.active
        self.controller.connect_api(start_after=self.controller.active)

    def discover_api(self):
        if self.controller.busy:
            return
        self._resume_after_reconnect = self.controller.active
        self.controller.connect_api(start_after=self.controller.active, force_discovery=True)

    def start_auto(self):
        if self.controller.busy or self.controller.active:
            return
        self._resume_after_reconnect = True
        self.controller.connect_api(start_after=True)

    def pause_auto(self):
        self._resume_after_reconnect = False
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
        self.controller.run_round(automatic=False)

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
                self.notice.setText(str(exc), "error")
                self.group.blockSignals(True)
                self.group.setCurrentIndex(max(0, self.group.findData(self.settings.group)))
                self.group.blockSignals(False)
                return
        self.settings.group = selected
        self._latency_history.clear()
        self._last_result_time = None
        self.last_checked.setText("尚未检测")
        self.measure_context.setText("尚无测速结果")
        self.settings.concurrency_auto = True
        self._draft_concurrency_auto = True
        self.table.setRowCount(0)
        self.delay.setText("未测速")
        self.delay.setStyleSheet("")
        self.node.setText(self.proxies.get(selected, {}).get("now", "未选择"))
        self._populate_members()
        self._sync_concurrency_limit(reset_to_node_count=bool(selected))
        self.results_stack.setCurrentIndex(0 if selected else 1)
        self.group_context.setText(selected or "选择一个代理组，开始管理节点")
        self._refresh_dashboard_rules()
        self._busy(False)

    def _populate_members(self):
        group = self.proxies.get(self.settings.group, {})
        try:
            members = group_members(self.settings.group, self.proxies)
        except ApiError:
            members = []
        self.region_selector.set_available_regions(available_regions(members))
        self.table.setRowCount(0)
        for name in group.get("all", []):
            if not isinstance(name, str):
                continue
            excluded = excluded_region(name, self.settings.excluded_regions)
            remark = "策略 / 代理组容器" if not is_node(name, self.proxies) else (
                f"已排除：{excluded}" if excluded else "候选节点")
            self._table_row(name, "未测速", "等待检测", ("当前使用；" if name == group.get("now") else "") + remark)
        self.results_stack.setCurrentIndex(0 if self.table.rowCount() else 1)
        self.table_caption.setText(f"{self.settings.group or '未选择代理组'} · {len(members)} 个节点")
        self.result_summary.setText("等待首次测速" if members else "当前代理组没有直接服务器节点")
        self.empty_title.setText("选择代理组" if not self.settings.group else "当前代理组没有可测速节点")
        self.empty_detail.setText("请选择需要管理的 Selector 代理组" if self.proxies else "尚未连接本机控制接口")
        self._refresh_node_preview()
        self._sync_view_state()

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
        # Discovery may resolve a new endpoint while the user is editing a draft.
        for name, value in (("address", self.settings.controller), ("secret", self.settings.secret)):
            control = getattr(self, name)
            if control.text() == self._saved_form[name]:
                control.setText(value)
                self._saved_form[name] = value
        self.redactor.secrets.add(self.settings.secret)
        self.node.setText(self.proxies.get(self.settings.group, {}).get("now", "未选择代理组"))
        self.delay.setText("未测速")
        self.delay.setStyleSheet("")
        self._latency_history.clear()
        self._last_result_time = None
        self.measure_context.setText("尚无测速结果")
        self.last_checked.setText("尚未检测")
        self.version_label.setText("Mihomo " + data["version"])
        self.version_label.setToolTip(self.settings.controller)
        self.sidebar_version.setToolTip("Mihomo " + data["version"])
        self.connection_detail.setText(self.settings.controller or "本机控制接口已连接")
        self._traffic(data["traffic"])
        self.notice.setText("接口连接成功" if self.settings.group else "接口连接成功；请选择需要管理的代理组", "success")
        self.group_context.setText(self.settings.group or "选择一个代理组，开始管理节点")
        self._populate_members()
        previous_concurrency = self.concurrency.value()
        self._sync_concurrency_limit()
        if previous_concurrency == self._saved_form["concurrency"]:
            self._saved_form["concurrency"] = self.concurrency.value()
        self._settings_edited()
        self._refresh_dashboard_rules()
        self._persist_runtime()

    def _traffic(self, traffic):
        self.traffic_label.setText(f"系统代理：{TrafficState.label(traffic.system_proxy)}    TUN：{TrafficState.label(traffic.tun)}")
        self.traffic_label.setToolTip(traffic.detail)
        for control, state in ((self.system_state, traffic.system_proxy), (self.tun_state, traffic.tun)):
            control.setText(TrafficState.label(state))
            set_tone(control, "success" if state is True else "warning" if state is None else "")
        connected = self.controller.client is not None
        self.sidebar_connection.setText("本机控制器 · 已连接" if connected else "本机控制器 · 未连接")
        set_tone(self.sidebar_connection, "success" if connected else "warning")

    def _result(self, result):
        if result.group != self.settings.group:
            return
        self.region_selector.set_available_regions(available_regions([item.name for item in result.measurements]))
        selected_row = self.table.currentRow()
        selected_name = self.table.item(selected_row, 0).text() if selected_row >= 0 else None
        scroll_value = self.table.verticalScrollBar().value()
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(result.measurements))
        self.node.setText(result.current or "状态无法确认")
        active = next((x for x in result.measurements if x.name == result.current), None)
        self.delay.setText(f"{active.delay} ms" if active and active.delay is not None else "未知")
        tone = "success" if active and active.delay is not None and active.delay <= self.settings.threshold_ms else "warning"
        self.delay.setStyleSheet("color: " + ("#087f69" if tone == "success" else "#936010"))
        for row, item in enumerate(result.measurements):
            remark = ("当前使用；" if item.name == result.current else "") + (f"已排除：{item.excluded}" if item.excluded else "候选节点")
            self._table_row(item.name, f"{item.delay} ms" if item.delay is not None else "无有效数据",
                            "正常" if item.delay is not None and item.delay <= self.settings.threshold_ms else ("延迟偏高" if item.delay else "测速失败"),
                            remark, item.error, row=row)
        self.table_caption.setText(f"{result.group} · {len(result.measurements)} 个节点")
        valid_count = sum(item.delay is not None for item in result.measurements)
        self.measure_context.setText(f"{valid_count} 个可用 · {len(result.measurements) - valid_count} 个测速失败")
        self._last_result_time = datetime.now()
        self.result_summary.setText("最近检测于 " + self._last_result_time.strftime("%H:%M:%S"))
        self.last_checked.setText("检测于 " + self._last_result_time.strftime("%H:%M:%S"))
        self.notice.setText(result.message, "success" if result.switched or tone == "success" else "warning")
        if active and active.delay is not None:
            self._latency_history.append((datetime.now(), active.delay))
            self._latency_history = self._latency_history[-5:]
        self._refresh_dashboard_rules()
        self.results_stack.setCurrentIndex(0)
        self._filter_nodes(self.node_search.text())
        if selected_name:
            for row in range(self.table.rowCount()):
                if self.table.item(row, 0) and self.table.item(row, 0).text() == selected_name:
                    self.table.selectRow(row)
                    break
            else:
                self.table.clearSelection()
                self.table.setCurrentCell(-1, -1)
        self.table.verticalScrollBar().setValue(min(scroll_value, self.table.verticalScrollBar().maximum()))
        self.table.setUpdatesEnabled(True)
        if result.traffic:
            self._traffic(result.traffic)
        if result.switched:
            record = f"{datetime.now():%H:%M:%S}  {result.group} · {result.previous} → {result.current}"
            for secret in self.redactor.secrets:
                if secret:
                    record = record.replace(secret, "[密钥已隐藏]")
            self.switch_history.appendPlainText(record)
        self._refresh_node_preview()
        self._sync_view_state()

    def _refresh_node_preview(self):
        node_rows = [row for row in range(self.table.rowCount())
                     if "策略 / 代理组容器" not in self.table.item(row, 3).text()]
        self.overview_table.setRowCount(min(5, len(node_rows)))
        for row, source in enumerate(node_rows[:5]):
            for col in range(3):
                original = self.table.item(source, col)
                item = self.overview_table.item(row, col)
                if item is None:
                    item = QTableWidgetItem()
                    self.overview_table.setItem(row, col, item)
                for role in (Qt.DisplayRole, Qt.ToolTipRole, Qt.ForegroundRole,
                             Qt.BackgroundRole, Qt.TextAlignmentRole):
                    item.setData(role, original.data(role))
                if col == 2 and "当前使用" in self.table.item(source, 3).text():
                    item.setText("当前使用")
                elif col == 2 and "已排除" in self.table.item(source, 3).text():
                    item.setText("已排除")
                    item.setForeground(QColor(COLORS["muted"]))
                if col == 2:
                    item.setToolTip(self.table.item(source, 3).text())
        self.preview_empty.setVisible(not node_rows)
        self.overview_table.setVisible(bool(node_rows))

    def _sync_view_state(self):
        self.auto_detail.setText(self.auto_state.text())
        self.automation_node.setText("当前节点 · " + self.node.text())
        self.auto_context.setText(f"管理代理组 · {self.settings.group}" if self.settings.group else "尚未选择代理组")

    def _table_row(self, name, delay, status, remark, error="", row=None):
        if row is None:
            row = self.table.rowCount()
            self.table.insertRow(row)
        self.table.setRowHeight(row, 44)
        for col, text in enumerate((name, delay, status, remark)):
            item = self.table.item(row, col)
            if item is None:
                item = QTableWidgetItem()
                self.table.setItem(row, col, item)
            item.setText(text)
            item.setToolTip(error if col == 2 and error else text)
            if col == 1:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if "当前使用" in remark:
                item.setBackground(QColor("#edf8f3"))
            else:
                item.setData(Qt.BackgroundRole, None)
            if col == 2:
                item.setForeground(QColor(COLORS["accent"] if status == "正常" else "#a76508" if status == "延迟偏高" else COLORS["muted"]))

    def _error(self, message):
        self.notice.setText(message, "error")
        self.header_status.setText("需要处理")
        set_tone(self.header_status, "error")
        self.statusBar().showMessage(message)
        self.append_log(message)

    def _status(self, text):
        self.header_status.setText(text)
        set_tone(self.header_status, "success" if "运行中" in text or text.startswith("已连接") else "warning" if "暂停" in text or "异常" in text else "")
        self.auto_state.setText("运行中" if self.controller.active else ("已暂停" if "暂停" in text else "已关闭"))
        self.tray.setToolTip("Clash 智能节点管家 · " + text)
        self.statusBar().showMessage(text)
        self.sidebar_connection.setText("本机控制器 · " + ("已连接" if self.controller.client else "未连接"))
        self._sync_view_state()
        self._busy(self.controller.busy)

    def _busy(self, busy):
        self.motion.set_busy(busy)
        active = self.controller.active
        for button in (self.connect_button, self.discover_button, self.measure_button,
                       self.empty_discover, self.notice_retry, self.header_refresh):
            button.setEnabled(not busy and not self.exiting)
        self.start_button.setEnabled(not busy and not active and not self.exiting)
        self.pause_button.setEnabled((active or busy) and not self.exiting)
        self.stop_button.setEnabled((active or busy) and not self.exiting)
        self.group.setEnabled(not busy and not self.exiting)
        self.settings_widget.setEnabled(not self.exiting)
        self.save_button.setEnabled(not self.exiting)
        self.task_progress.setVisible(busy)
        if busy:
            self.operation_hint.setText("后台任务进行中；界面仍可浏览")
            self.header_status.setText("处理中")
            set_tone(self.header_status, "warning")
        elif self._task_status:
            self.operation_hint.setText("立即测速只检测，不切换节点")
        self._task_status = "处理中" if busy else "就绪"
        self._sync_view_state()

    def append_log(self, message):
        for secret in self.redactor.secrets:
            if secret:
                message = message.replace(secret, "[密钥已隐藏]")
        self.logger.info(message)
        was_following = self.follow_logs.isChecked()
        bar = self.logs.verticalScrollBar()
        scroll_value = bar.value()
        self._appending_log = True
        self.logs.appendPlainText(datetime.now().strftime("%H:%M:%S") + "  " + message)
        self.recent_logs.appendPlainText(datetime.now().strftime("%H:%M:%S") + "  " + message)
        if was_following:
            bar.setValue(bar.maximum())
        else:
            bar.setValue(scroll_value)
        self._appending_log = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_actions()

    def nativeEvent(self, event_type, message):
        if hasattr(self, "motion") and is_settings_message(message):
            self.motion.refresh_preferences()
        return super().nativeEvent(event_type, message)

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
        elif self._reconnect_pending:
            self._reconnect_settings()
        else:
            self._resume_after_reconnect = False
            self._persist_runtime()

    def _reconnect_settings(self):
        resume = self._resume_after_reconnect
        self._reconnect_pending = False
        self.append_log("连接设置已更新，正在重新检测控制接口" + ("；验证通过后恢复自动切换" if resume else ""))
        self.controller.connect_api(start_after=resume)

    def request_exit(self):
        if self.exiting:
            return
        if self.controller.active:
            choice = QMessageBox.question(self, "退出程序", "自动切换仍在运行。退出后将停止检测，是否退出？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if choice != QMessageBox.Yes:
                return
        self.exiting = True
        self.motion.shutdown()
        self.controller.shutdown()
        self._persist_runtime()
        self._busy(self.controller.busy)
        self.notice.setText("正在结束后台请求，请稍候…", "warning")
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
        else:
            self.request_exit()
