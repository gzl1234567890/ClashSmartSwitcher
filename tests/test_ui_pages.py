"""Page isolation, shared state and non-interrupting background feedback."""
import threading
from pathlib import Path
import tomllib
from functools import partial

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontMetrics, QHelpEvent, QIcon, QImage, QPainter, QRawFont, QTextDocument, QTextLayout
from PySide6.QtWidgets import QApplication, QMessageBox, QToolTip
from PySide6.QtTest import QTest

from smart_switcher.config import ConfigStore, Settings
from smart_switcher.api import ApiError
from smart_switcher.core import Measurement, RoundResult, SwitchEngine
from smart_switcher.logging_service import setup_logging
from smart_switcher.monitor import MonitorController
from smart_switcher.status import TrafficState
from smart_switcher.ui import MainWindow
from tests.fakes import FakeClient
from smart_switcher import motion
from smart_switcher.theme import COLORS, CONTROL_HEIGHT, FONT_FAMILY, TABLE_ROW_HEIGHT, configure_document_typography, font_families, load_app_fonts
from smart_switcher.ui_components import icon, set_tone


@pytest.fixture
def window(qtbot, tmp_path):
    settings = Settings(group="组")
    logger, redactor = setup_logging(tmp_path / "logs")
    controller = MonitorController(settings, engine=SwitchEngine(lambda c: TrafficState(True, False)))
    controller.client = FakeClient()
    subject = MainWindow(ConfigStore(tmp_path), settings, logger, redactor, controller)
    controller.setParent(subject)
    subject.closeEvent = lambda event: event.accept()
    subject.tray.hide()
    qtbot.addWidget(subject)
    subject.show()
    yield subject
    controller.shutdown()
    qtbot.waitUntil(lambda: not controller.busy, timeout=5000)
    subject.close()
    subject.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


def connect(window):
    client = window.controller.client
    window._connected({"proxies": client.proxies(), "groups": ["组"], "version": "test",
                       "traffic": TrafficState(True, False)})
    return client


def test_release_version_matches_project_and_app_bar(window):
    from smart_switcher import __version__
    root = Path(__file__).resolve().parent.parent
    metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == __version__
    assert window.sidebar_version.text() == f"v{__version__}"
    connect(window)
    assert window.sidebar_version.text() == f"v{__version__}"


def test_navigation_icons_have_visible_inset_in_all_navigation_states(window):
    for index, button in enumerate(window.nav_buttons):
        window.navigate(index)
        button.setFocus()
        QTest.qWait(180)
        assert button.height() == 48
        image = button.grab().toImage()
        dpr = image.devicePixelRatio()
        ink = [(x, y) for y in range(image.height()) for x in range(image.width())
               if image.pixelColor(x, y).alpha() > 240 and
               image.pixelColor(x, y).blue() < 195 and
               image.pixelColor(x, y).blue() > image.pixelColor(x, y).green() + 8 and
               image.pixelColor(x, y).green() > image.pixelColor(x, y).red() + 8]
        assert ink, button.text()
        assert min(x for x, y in ink) >= 12 * dpr, button.text()
        assert max(y for x, y in ink) - min(y for x, y in ink) >= 8 * dpr


def test_unmeasured_cells_and_tooltip_are_centered(window):
    connect(window)
    window.navigate(1)
    QTest.qWait(180)
    assert window.table.item(0, 1).textAlignment() == Qt.AlignCenter
    assert window.table.item(0, 2).textAlignment() == Qt.AlignCenter
    position = window.table.visualItemRect(window.table.item(0, 1)).center()
    QApplication.sendEvent(window.table.viewport(), QHelpEvent(
        QEvent.ToolTip, position, window.table.viewport().mapToGlobal(position)))
    QTest.qWait(30)
    try:
        tooltip = next(widget for widget in QApplication.topLevelWidgets()
                       if widget.objectName() == "qtooltip_label" and widget.isVisible())
        image = tooltip.grab().toImage()
        image.save(str(window.store.directory / "tooltip.png"))
        ink = [(x, y) for y in range(image.height()) for x in range(image.width())
               if min(image.pixelColor(x, y).red(), image.pixelColor(x, y).green(),
                      image.pixelColor(x, y).blue()) > 210]
        assert ink
        for axis, size in ((0, image.width()), (1, image.height())):
            low, high = min(p[axis] for p in ink), max(p[axis] for p in ink)
            assert low >= 6 * image.devicePixelRatio()
            assert abs((low + high) / 2 - (size - 1) / 2) <= 2 * image.devicePixelRatio()
    finally:
        QToolTip.hideText()
    window._result(RoundResult("组", "美国", [Measurement("美国", 87)], "完成"))
    assert window.table.item(0, 1).textAlignment() == Qt.AlignRight | Qt.AlignVCenter
    assert window.overview_table.item(0, 2).textAlignment() == Qt.AlignCenter


def test_shared_control_and_table_dimensions_are_consistent(window):
    connect(window)
    for field in (window.group, window.node_search, window.address, window.secret,
                  window.threshold, window.interval, window.timeout, window.minimum_switch):
        assert field.height() == CONTROL_HEIGHT, field.accessibleName()
    assert window.header_status.alignment() == Qt.AlignCenter
    assert window.table.rowHeight(0) == window.overview_table.rowHeight(0) == TABLE_ROW_HEIGHT
    assert window.table.horizontalHeader().height() == TABLE_ROW_HEIGHT


def test_compact_workspace_preserves_results_space_and_complete_status(window):
    connect(window)
    window.resize(850, 630)
    window.navigate(1)
    QTest.qWait(180)
    assert window.size() == window.minimumSize()
    assert window.table.viewport().height() >= TABLE_ROW_HEIGHT * 2
    window._busy(True)
    QTest.qWait(80)
    assert window.table.viewport().height() >= TABLE_ROW_HEIGHT * 2
    window._busy(False)
    message = "连接异常，当前控制接口无法访问，请检查 Clash Verge 的本机控制地址和密钥后重新检测"
    window._status(message)
    QTest.qWait(180)
    badge = window.header_status
    assert window.width() == 850
    assert badge.toolTip() == badge.accessibleName() == message
    assert badge.fontMetrics().horizontalAdvance(message) > badge.contentsRect().width()
    assert window.navigation_bar.width() <= window.width()


def test_settings_are_editable_while_automation_waits_and_runs(window, qtbot):
    client = connect(window)
    client.latency = 0.1
    window.controller.active = True
    window._busy(False)
    window.navigate(4)
    assert window.address.isEnabled() and window.threshold.isEnabled() and window.save_button.isEnabled()
    old_threshold = window.settings.threshold_ms
    window.threshold.setValue(90)
    window.concurrency.setValue(2)
    assert window.settings.threshold_ms == old_threshold
    assert window.settings.concurrency_auto
    assert str(old_threshold) in window.rule_threshold.text()
    window.controller.run_round()
    worker = window.controller.worker
    assert window.threshold.isEnabled() and window.save_button.isEnabled()
    window.save_button.click()
    assert window.controller.worker is worker and window.controller.active
    assert window.settings.threshold_ms == 90 and not window.settings.concurrency_auto
    assert window.store.load().threshold_ms == 90
    window.threshold.setValue(100)
    qtbot.waitUntil(lambda: not window.controller.busy, timeout=5000)
    assert window.threshold.value() == 100
    assert window.settings.threshold_ms == 90
    assert "未保存" in window.settings_feedback.text()
    assert "90" in window.rule_threshold.text()


def test_rule_save_affects_next_round_and_preserves_current_snapshot(window, qtbot, monkeypatch):
    connect(window)
    entered, release = threading.Event(), threading.Event()
    seen = []

    def run(client, settings, cancel, automatic, log):
        seen.append(settings.threshold_ms)
        entered.set()
        release.wait(3)
        return RoundResult("组", "美国", [Measurement("美国", 185)], "测速完成")

    monkeypatch.setattr(window.controller.engine, "run", run)
    window.controller.active = True
    window.controller.run_round()
    try:
        qtbot.waitUntil(entered.is_set)
        window.threshold.setValue(95)
        window.save_settings()
        assert seen == [120]
        assert window.controller.active
    finally:
        release.set()
    qtbot.waitUntil(lambda: not window.controller.busy)
    window.controller.run_round()
    qtbot.waitUntil(lambda: not window.controller.busy)
    assert seen == [120, 95]


@pytest.mark.parametrize("failure", ["invalid", "disk"])
def test_failed_save_keeps_runtime_and_worker_unchanged(window, monkeypatch, failure):
    connect(window)
    window.controller.active = True
    original = window.settings
    window.threshold.setValue(99)
    if failure == "invalid":
        window.test_url.setText("invalid")
    else:
        def fail(settings):
            raise OSError("模拟保存失败")
        monkeypatch.setattr(window.store, "save", fail)
    window.save_settings()
    assert window.settings is original and window.controller.settings is original
    assert window.settings.threshold_ms == 120 and window.controller.active
    assert window.threshold.value() == 99
    assert window.notice.property("tone") == "error"


@pytest.mark.parametrize("pause", [False, True])
def test_connection_save_waits_for_worker_then_reconnects_with_latest_settings(window, qtbot, monkeypatch, pause):
    client = connect(window)
    client.latency = 0.1
    calls = []
    replacement = FakeClient()
    monkeypatch.setattr("smart_switcher.monitor.discover", lambda: [])
    monkeypatch.setattr("smart_switcher.monitor.detect_traffic", lambda configs: TrafficState(True, False))
    def factory(address, secret):
        calls.append((address, secret))
        return replacement
    window.controller.client_factory = factory
    window.controller.active = True
    window.controller.run_round()
    worker = window.controller.worker
    window.address.setText("http://127.0.0.1:19999")
    window.secret.setText("new-secret")
    window.save_secret.setChecked(False)
    window.save_settings()
    assert calls == [] and window.controller.worker is worker
    assert not window.controller.active and window.controller.cancel.is_set()
    window.secret.setText("latest-secret")
    window.save_settings()
    if pause:
        window.pause_auto()
    qtbot.waitUntil(lambda: bool(calls) and not window.controller.busy, timeout=5000)
    assert calls == [("http://127.0.0.1:19999", "latest-secret")]
    assert window.controller.client is replacement
    assert window.controller.active is (not pause)
    assert not client.writes
    assert not window._reconnect_pending


def test_connection_result_preserves_unsaved_draft(window):
    window.address.setText("http://127.0.0.1:19998")
    window.secret.setText("draft-secret")
    window.threshold.setValue(88)
    window.concurrency.setValue(2)
    window.controller.settings.controller = "http://127.0.0.1:19999"
    connect(window)
    assert window.address.text() == "http://127.0.0.1:19998"
    assert window.secret.text() == "draft-secret"
    assert window.threshold.value() == 88 and window.concurrency.value() == 2
    assert window.settings.threshold_ms == 120 and window.settings.concurrency_auto
    assert "未保存" in window.settings_feedback.text()


@pytest.mark.parametrize("action", ["retry", "discover"])
@pytest.mark.parametrize("active", [False, True])
def test_recheck_preserves_previous_automation_state(window, qtbot, monkeypatch, action, active):
    connect(window)
    replacement = FakeClient()
    window.controller.client_factory = lambda address, secret: replacement
    from smart_switcher.discovery import Endpoint
    monkeypatch.setattr("smart_switcher.monitor.discover", lambda: [Endpoint("http://127.0.0.1:19999", "", "test")])
    monkeypatch.setattr("smart_switcher.monitor.detect_traffic", lambda configs: TrafficState(True, False))
    window.address.setText("尚未保存的无效地址")
    window.threshold.setValue(99)
    window.controller.active = active
    window._busy(False)
    if action == "retry":
        window.notice_retry.click()
    else:
        window.discover_button.click()
    qtbot.waitUntil(lambda: window.controller.client is replacement and not window.controller.busy, timeout=5000)
    assert window.controller.active is active
    assert window.controller.timer.isActive() is active
    assert window.settings.threshold_ms == 120
    assert window.address.text() == "尚未保存的无效地址" and window.threshold.value() == 99


@pytest.mark.parametrize("failure", ["connection", "traffic", "pause", "replace"])
def test_recheck_does_not_resume_on_failure_or_explicit_pause(window, qtbot, monkeypatch, failure):
    connect(window)
    entered, release = threading.Event(), threading.Event()
    client = FakeClient()
    def factory(address, secret):
        entered.set()
        release.wait(3)
        if failure == "connection":
            raise ApiError("模拟接口断开")
        return client
    window.controller.client_factory = factory
    from smart_switcher.discovery import Endpoint
    monkeypatch.setattr("smart_switcher.monitor.discover", lambda: [Endpoint("http://127.0.0.1:19999", "", "test")])
    monkeypatch.setattr("smart_switcher.monitor.detect_traffic", lambda configs: TrafficState(failure != "traffic", False))
    window.controller.active = True
    window.connect_api()
    try:
        qtbot.waitUntil(entered.is_set)
        if failure == "pause":
            window.pause_auto()
        elif failure == "replace":
            window.address.setText("http://127.0.0.1:19998")
            window.save_settings()
    finally:
        release.set()
    qtbot.waitUntil(lambda: not window.controller.busy, timeout=5000)
    assert window.controller.active is (failure == "replace")
    assert window.controller.timer.isActive() is (failure == "replace")
    assert window.store.load().auto_enabled is (failure == "replace")
    if failure == "replace":
        assert window.controller.settings.controller == "http://127.0.0.1:19998"
        assert window.controller.client is client
    elif failure != "pause":
        assert window.notice.property("tone") == "error"


def test_navigation_is_independent_and_does_not_run_network_work(window):
    client = connect(window)
    before = client.reads
    pages = set()
    for index, button in enumerate(window.nav_buttons):
        button.click()
        assert window.tabs.currentIndex() == index
        assert window.page_title.text() == window.PAGE_TITLES[index][0]
        assert [item.isChecked() for item in window.nav_buttons] == [i == index for i in range(5)]
        assert window.group_row.isVisible() == (index < 3)
        pages.add(window.tabs.currentWidget())
    assert len(pages) == 5
    assert client.reads == before and client.tests == [] and client.writes == []
    window.navigate(2)
    assert window.start_button.isVisible() and not window.table.isVisible()
    window.navigate(1)
    assert window.table.isVisible() and not window.start_button.isVisible()
    window.navigate(0)
    assert window.summary.isVisible() and not window.table.isVisible()


def test_background_switch_and_errors_never_show_dialog_or_notification(window, monkeypatch):
    client = connect(window)
    interruptions = []
    monkeypatch.setattr(window.tray, "showMessage", lambda *args: interruptions.append("notification"))
    monkeypatch.setattr(QMessageBox, "exec", lambda *args: interruptions.append("dialog"))
    monkeypatch.setattr(window, "show_window", lambda: interruptions.append("window"))
    window.hide()
    result = window.controller.engine.run(client, window.settings, threading.Event(), True)
    assert result.switched
    window._result(result)
    window._error("系统代理或 TUN 已关闭，请重新检测")
    assert interruptions == [] and not window.isVisible()
    assert window.node.text() == "德国"
    assert "德国" in window.automation_node.text()
    assert "德国" in window.switch_history.toPlainText()
    assert "TUN" in window.logs.toPlainText()
    assert window.notice.property("tone") == "error"
    assert window.notice_retry.isEnabled()


def test_proxy_failure_still_pauses_automation_without_popup(window, qtbot, monkeypatch):
    connect(window)
    monkeypatch.setattr(QMessageBox, "exec", lambda *args: pytest.fail("background modal"))
    window.controller.engine = SwitchEngine(lambda c: TrafficState(False, False))
    window.controller.active = True
    window.controller.run_round()
    qtbot.waitUntil(lambda: not window.controller.busy, timeout=5000)
    assert not window.controller.active and not window.controller.timer.isActive()
    assert window.notice.property("tone") == "error"
    assert "系统代理" in window.logs.toPlainText()


def test_preview_is_limited_and_results_preserve_view_state(window, qtbot):
    connect(window)
    result = RoundResult("组", "美国", [Measurement("美国", 185)] +
                         [Measurement(f"节点 {i:02d}", i + 50) for i in range(60)], "完成测速")
    window._result(result)
    assert window.overview_table.rowCount() == 5
    window.resize(850, 630)
    window.navigate(1)
    QTest.qWait(30)
    window.table.setCurrentCell(40, 3)
    window.table.scrollToItem(window.table.item(40, 0))
    previous = window.table.verticalScrollBar().value()
    window._result(result)
    assert window.table.currentRow() == 40
    assert window.table.verticalScrollBar().value() == previous
    window.node_search.setText("节点 40")
    window._result(result)
    assert window.node_search.text() == "节点 40"
    assert sum(not window.table.isRowHidden(i) for i in range(window.table.rowCount())) == 1
    for index in (0, 2, 3, 4, 1):
        window.navigate(index)
    assert window.node_search.text() == "节点 40"
    assert window.table.currentRow() == 40
    stale = RoundResult("其他组", "不应出现", [Measurement("不应出现", 1)])
    window._result(stale)
    assert window.node.text() == "美国"


def test_repeated_results_reuse_items_and_clear_previous_state(window):
    connect(window)
    first = RoundResult("组", "美国", [Measurement("美国", 80),
                        Measurement("德国", None, "超时", "德国")], "第一次")
    window._result(first)
    cells = [[window.table.item(row, col) for col in range(4)] for row in range(2)]
    preview = [[window.overview_table.item(row, col) for col in range(3)] for row in range(2)]
    second = RoundResult("组", "德国", [Measurement("美国", 180), Measurement("德国", 70)], "第二次")
    for _ in range(100):
        window._result(second)
    for row in range(2):
        assert all(window.table.item(row, col) is cells[row][col] for col in range(4))
        assert all(window.overview_table.item(row, col) is preview[row][col] for col in range(3))
    assert window.table.item(0, 0).data(Qt.BackgroundRole) is None
    assert window.table.item(1, 0).data(Qt.BackgroundRole) is not None
    assert window.table.item(1, 2).toolTip() == "正常"
    assert window.overview_table.item(0, 2).text() == "延迟偏高"
    assert window.overview_table.item(1, 2).text() == "当前使用"
    window.table.setCurrentCell(0, 0)
    window._result(RoundResult("组", "德国", [Measurement("德国", 90)], "缩减"))
    assert window.table.rowCount() == window.overview_table.rowCount() == 1
    assert window.table.currentRow() == -1 and not window.table.selectedItems()
    window._result(RoundResult("组", "", [], "空结果"))
    assert window.table.rowCount() == window.overview_table.rowCount() == 0


def test_history_exclusions_and_compact_timestamp(window):
    client = connect(window)
    result = window.controller.engine.run(client, window.settings, threading.Event(), False)
    window._result(result)
    assert window._latency_history
    assert "最近检测于" in window.result_summary.text()
    for row in range(window.overview_table.rowCount()):
        if window.overview_table.item(row, 0).text() == "香港 HK":
            assert window.overview_table.item(row, 2).text() == "已排除"
    window.resize(850, 630)
    window.navigate(1)
    assert window.result_summary.isVisible()
    connect(window)
    assert window._latency_history == []
    window._result(result)
    window.group.setCurrentIndex(0)
    assert window._latency_history == []


@pytest.mark.parametrize("measurements", [[], [Measurement("美国", None, "超时")],
                                        [Measurement("美国", 180, excluded="美国")]])
def test_empty_failed_and_excluded_results_remain_browsable(window, measurements):
    connect(window)
    result = RoundResult("组", "美国", measurements, "没有可切换的合格节点")
    window._result(result)
    assert window.table.rowCount() == len(measurements)
    assert "没有可切换" in window.notice.text()
    window.navigate(2)
    assert window.start_button.isEnabled()


def test_rule_link_numeric_font_and_minimum_window(window, qtbot):
    connect(window)
    window.resize(850, 630)
    for index in range(5):
        window.navigate(index)
        QTest.qWait(10)
        assert window.width() == 850 and window.height() == 630
        for control in (window.start_button, window.pause_button, window.stop_button,
                        window.measure_button, window.group, window.save_button):
            if control.isVisible():
                assert control.width() >= control.minimumSizeHint().width()
                assert 36 <= control.height() <= 40
    window._open_rules()
    assert window.tabs.currentIndex() == 4 and window.threshold.hasFocus()
    assert window.delay.font().featureValue(QFont.Tag.fromString("tnum")) == 1
    metrics = QFontMetrics(window.delay.font())
    assert metrics.horizontalAdvance("111") == metrics.horizontalAdvance("888")


def test_log_history_does_not_jump_when_new_messages_arrive(window, qtbot):
    window.navigate(3)
    for index in range(80):
        window.append_log(f"历史记录 {index}")
    QTest.qWait(10)
    bar = window.logs.verticalScrollBar()
    bar.setValue(10)
    assert not window.follow_logs.isChecked()
    window.append_log("新增记录")
    assert bar.value() == 10
    assert window.recent_logs.document().blockCount() <= 5
    window._clear_logs()
    assert window.logs.toPlainText() == "" and window.recent_logs.toPlainText() == ""


def test_static_faces_render_increasing_stroke_weight(window):
    coverage = []
    for weight in (400, 500, 600):
        font = QFont(FONT_FAMILY)
        font.setPixelSize(40)
        font.setWeight(QFont.Weight(weight))
        raw = QRawFont.fromFont(font)
        assert not raw.fontTable("fvar")
        assert raw.familyName() == FONT_FAMILY
        assert int.from_bytes(bytes(raw.fontTable("OS/2"))[4:6], "big") == weight
        image = QImage(600, 80, QImage.Format_RGB32)
        image.fill(Qt.white)
        painter = QPainter(image)
        painter.setPen(Qt.black)
        painter.setFont(font)
        painter.drawText(10, 55, "运行总览节点延迟 87 ms")
        painter.end()
        gray = image.convertToFormat(QImage.Format_Grayscale8)
        coverage.append(sum(255 - pixel for pixel in bytes(gray.constBits())))
    assert coverage[0] < coverage[1] < coverage[2]
    assert coverage[2] > coverage[0] * 1.2
    for label in (window.page_title, window.delay):
        assert label.font().weight() == 600
        assert QRawFont.fromFont(label.font()).weight() >= 600
        assert not QRawFont.fromFont(label.font()).fontTable("fvar")


def test_shared_font_chain_and_mixed_script_glyphs(window):
    controls = (window.page_title, window.delay, window.node, window.table,
                window.save_button, window.logs, window.region_selector.editor,
                window.header_status, window.tray.contextMenu())
    for control in controls:
        control.ensurePolished()
        assert control.font().families() == font_families()
        assert control.font().hintingPreference() == QFont.PreferNoHinting
        assert control.font().styleStrategy() & QFont.PreferAntialias
        assert control.font().styleStrategy() & QFont.PreferOutline
        assert QRawFont.fromFont(control.font()).familyName() == FONT_FAMILY
    layout = QTextLayout("节点 Tokyo Singapore 103 ms → ✓ … —", window.node.font())
    layout.beginLayout()
    line = layout.createLine()
    line.setLineWidth(1200)
    layout.endLayout()
    assert layout.glyphRuns()
    assert all(0 not in run.glyphIndexes() for run in layout.glyphRuns())
    set_tone(window.page_title, "warning")
    assert window.page_title.font().weight() == 600
    assert window.page_title.font().families() == font_families()
    assert window.page_title.font().hintingPreference() == QFont.PreferNoHinting
    for weight in (400, 500, 600):
        font = QFont(window.node.font())
        font.setWeight(QFont.Weight(weight))
        assert QRawFont.fromFont(font).weight() == weight


def test_rich_text_uses_real_ui_emphasis_and_keeps_content(window):
    document = QTextDocument()
    document.setMarkdown("连接设置 **保存后应用**，控制地址 `http://127.0.0.1:9090`。")
    content = document.toPlainText()
    configure_document_typography(document, pixel_size=15)
    assert document.toPlainText() == content
    assert document.defaultFont().families() == font_families()
    assert document.defaultFont().hintingPreference() == QFont.PreferNoHinting
    assert document.useDesignMetrics()
    weights = []
    block = document.begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            if fragment.isValid() and "保存后应用" in fragment.text():
                weights.append(fragment.charFormat().fontWeight())
            iterator += 1
        block = block.next()
    assert weights == [QFont.DemiBold]


def test_missing_packaged_fonts_are_reported(window, monkeypatch, tmp_path):
    import sys
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    with pytest.raises(RuntimeError, match="Missing bundled font"):
        load_app_fonts.__wrapped__()


def test_help_chapters_remain_reachable_in_compact_layout(window, qtbot):
    window.navigate(5)
    guide = window.help
    assert [title for title, _ in guide.sections] == [
        "快速开始", "连接设置", "自动切换", "测速与候选", "常见问题", "日常使用"]
    assert guide.topic_panel.isVisible() and not guide.compact_selector.isVisible()
    qtbot.mouseClick(guide.topic_buttons[1], Qt.LeftButton)
    assert guide.chapter_title.text() == "连接设置"
    assert "127.0.0.1:9090" in guide.browser.toPlainText()
    window.resize(850, 630)
    QTest.qWait(180)
    assert not guide.topic_panel.isVisible() and guide.compact_selector.isVisible()
    guide.topic_picker.setCurrentIndex(4)
    assert guide.chapter_title.text() == "常见问题"
    assert "没有发生自动切换" in guide.browser.toPlainText()
    assert window.width() == 850 and window.height() == 630
    assert guide.browser.horizontalScrollBar().maximum() == 0


def test_help_reading_uses_shared_font_and_paragraph_spacing(window):
    window.navigate(5)
    document = window.help.browser.document()
    assert document.defaultFont().families() == font_families()
    assert document.defaultFont().pixelSize() == 15
    window.help.select_topic(1)
    code_fonts = []
    block = window.help.browser.document().begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            if fragment.isValid() and "external-controller" in fragment.text():
                code_fonts.append(fragment.charFormat().font())
            iterator += 1
        block = block.next()
    assert code_fonts
    assert all(font.families()[0] == "Consolas" and font.pixelSize() == 14 for font in code_fonts)
    window.help.select_topic(4)
    assert window.help.browser.document().defaultFont().hintingPreference() == QFont.PreferNoHinting


@pytest.fixture
def animated_window(window, monkeypatch):
    monkeypatch.setattr(motion, "system_motion_enabled", lambda: True)
    window.motion.refresh_preferences()
    return window


def test_rapid_navigation_finishes_at_latest_page(animated_window, qtbot):
    window = animated_window
    client = connect(window)
    reads = client.reads
    for index in (4, 1, 0, 2, 3, 1, 1):
        window.navigate(index)
        assert window.tabs.currentIndex() == index
        assert window.page_title.text() == window.PAGE_TITLES[index][0]
    assert window.motion.veil.testAttribute(Qt.WA_TransparentForMouseEvents)
    QTest.qWait(240)
    assert not window.motion.veil.isVisible()
    button = window.nav_buttons[1]
    expected = button.mapTo(window.navigation_bar, QPoint((button.width() - 24) // 2, button.height() - 5))
    assert window.motion.indicator.pos() == expected
    window.resize(850, 630)
    QTest.qWait(180)
    expected = button.mapTo(window.navigation_bar, QPoint((button.width() - 24) // 2, button.height() - 5))
    assert window.motion.indicator.pos() == expected
    assert client.reads == reads and not client.tests and not client.writes


def test_button_feedback_does_not_resize_or_delay_click(animated_window, qtbot):
    window = animated_window
    button = window.nav_buttons[2]
    before = button.geometry()
    qtbot.mouseMove(button, button.rect().center())
    qtbot.mousePress(button, Qt.LeftButton)
    QTest.qWait(35)
    assert button._feedback_values["press"] > 0
    qtbot.mouseRelease(button, Qt.LeftButton)
    assert window.tabs.currentIndex() == 2
    QTest.qWait(180)
    assert button.geometry() == before
    assert button._feedback_values["press"] == 0


def test_busy_animation_stops_hidden_and_resumes_without_requests(animated_window, qtbot):
    window = animated_window
    client = connect(window)
    reads = client.reads
    window._busy(True)
    assert window.motion.spinner.state() == QVariantAnimation.Running
    QTest.qWait(40)
    assert window.header_refresh.busy_angle is not None
    window.hide()
    assert window.motion.spinner.state() == QVariantAnimation.Stopped
    assert window.task_progress.maximum() == 1
    assert all(channel.state() == QVariantAnimation.Stopped for channel in window.motion._channels)
    window.show()
    QTest.qWait(20)
    assert window.motion.spinner.state() == QVariantAnimation.Running
    window.showMinimized()
    QTest.qWait(20)
    assert window.motion.spinner.state() == QVariantAnimation.Stopped
    assert window.task_progress.maximum() == 1
    window.showNormal()
    QTest.qWait(20)
    assert window.motion.spinner.state() == QVariantAnimation.Running
    window._busy(False)
    assert window.motion.spinner.state() == QVariantAnimation.Stopped
    assert window.header_refresh.busy_angle is None
    assert client.reads == reads and not client.tests and not client.writes


def test_reduced_motion_has_instant_states_and_no_running_animation(animated_window, qtbot, monkeypatch):
    window = animated_window
    window.navigate(1)
    window._busy(True)
    monkeypatch.setattr(motion, "system_motion_enabled", lambda: False)
    window.motion.refresh_preferences()
    window.navigate(4)
    set_tone(window.header_status, "error")
    QTest.qWait(20)
    assert not window.motion.veil.isVisible()
    assert window.motion.spinner.state() == QVariantAnimation.Stopped
    assert all(channel.state() == QVariantAnimation.Stopped for channel in window.motion._channels)
    assert window.header_status.surface_color == QColor(COLORS["error_bg"])
    assert window.header_refresh.busy_angle is None
    assert window.task_progress.maximum() == 1 and window.task_progress.value() == 1
    assert window.header_status.text()
    window._busy(False)


def test_tone_transition_keeps_text_and_finishes_after_latest_status(animated_window, qtbot):
    window = animated_window
    window.header_status.setText("连接异常，请重新检测")
    set_tone(window.header_status, "error")
    QTest.qWait(30)
    set_tone(window.header_status, "success")
    QTest.qWait(230)
    assert window.header_status.text() == "连接异常，请重新检测"
    assert window.header_status.surface_color == QColor(COLORS["tint"])
    assert window.page_title.font().weight() == 600
    assert QRawFont.fromFont(window.page_title.font()).weight() >= 600


def test_keyboard_focus_survives_page_transition(animated_window, qtbot):
    window = animated_window
    window.activateWindow()
    window._open_rules()
    QTest.qWait(240)
    assert window.threshold.hasFocus()
    assert window.motion._outlines[window.threshold].amount == 1
    assert not window.motion.veil.isVisible()
    assert window.threshold.graphicsEffect() is None


def test_motion_shutdown_clears_visual_work(animated_window):
    window = animated_window
    window.navigate(3)
    window._busy(True)
    window.motion.shutdown()
    assert window.motion.spinner.state() == QVariantAnimation.Stopped
    assert all(channel.state() == QVariantAnimation.Stopped for channel in window.motion._channels)
    assert not window.motion.veil.isVisible()
    assert window.header_refresh.busy_angle is None


def test_dynamic_control_deletion_during_feedback_is_safe(animated_window, qtbot):
    from smart_switcher.region_select import RegionChip
    window = animated_window
    window.navigate(4)
    chip = window.region_selector.findChildren(RegionChip)[0]
    button = chip.remove_button
    window.motion.transition(button, "hover", 0.0, 1.0,
                             partial(button._set_feedback, "hover"), 120)
    window.region_selector.clear()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    window.motion.finish_transitions()
    QTest.qWait(150)
    assert window.region_selector.selected_regions() == []


def test_error_icon_reader_produces_tinted_pixels_at_all_densities(window):
    icon.cache_clear()
    symbol = icon("circle-alert", "#b23f38")
    for size in (16, 20, 24, 32, 40, 48, 64):
        for mode, expected in ((QIcon.Normal, QColor("#b23f38")),
                               (QIcon.Disabled, QColor("#96a59d"))):
            image = symbol.pixmap(size, size, mode).toImage()
            assert not image.isNull()
            solid = [image.pixelColor(x, y) for y in range(image.height())
                     for x in range(image.width()) if image.pixelColor(x, y).alpha() > 245]
            assert solid
            assert any(abs(pixel.red() - expected.red()) <= 1 and
                       abs(pixel.green() - expected.green()) <= 1 and
                       abs(pixel.blue() - expected.blue()) <= 1 for pixel in solid)


def test_long_node_name_keeps_full_tooltip_and_compact_geometry(window, qtbot):
    connect(window)
    name = "德国高速专线-" + "超长节点名称" * 18
    window.resize(850, 630)
    window._result(RoundResult("组", name, [Measurement(name, 87)], "完成测速"))
    QTest.qWait(220)
    assert window.node.text() == window.node.toolTip() == name
    assert window.node.fontMetrics().horizontalAdvance(name) > window.node.width()
    assert window.width() == 850
    window.navigate(1)
    QTest.qWait(220)
    assert window.table.item(0, 0).toolTip() == name
    assert window.width() == 850
