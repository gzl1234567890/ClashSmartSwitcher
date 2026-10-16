from pathlib import Path
import time

from PySide6.QtCore import QCoreApplication, QEvent, QThread, QTimer
import pytest

from smart_switcher.config import ConfigStore, Settings
from smart_switcher.core import SwitchEngine
from smart_switcher.instance import SingleInstance
from smart_switcher.logging_service import setup_logging
from smart_switcher.monitor import MonitorController
from smart_switcher.status import TrafficState
from smart_switcher.ui import MainWindow
from tests.fakes import FakeClient


def controller(qtbot, client=None):
    subject = MonitorController(Settings(group="组", interval_seconds=5),
                                engine=SwitchEngine(lambda c: TrafficState(True, False)))
    subject.client = client or FakeClient()
    return subject


def test_gui_event_loop_responsive_during_network_work(qtbot):
    subject = controller(qtbot, FakeClient(latency=0.15))
    ticks = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    subject.run_round(automatic=False)
    qtbot.waitUntil(lambda: not subject.busy, timeout=5000)
    timer.stop()
    assert len(ticks) >= 5


def test_pause_stops_timer_and_queued_auto_work(qtbot):
    subject = controller(qtbot)
    subject.active = True
    subject.timer.start(0)
    subject.pause()
    qtbot.wait(100)
    assert not subject.busy and not subject.client.tests and not subject.timer.isActive()


def test_pause_during_round_prevents_write_and_future_tasks(qtbot):
    client = FakeClient(latency=0.15)
    subject = controller(qtbot, client)
    subject.active = True
    subject.run_round()
    subject.pause()
    qtbot.waitUntil(lambda: not subject.busy, timeout=5000)
    assert not client.writes and not subject.timer.isActive()


def test_shutdown_joins_work_and_no_timer_remains(qtbot):
    subject = controller(qtbot, FakeClient(latency=0.1))
    subject.active = True
    subject.run_round()
    subject.shutdown()
    qtbot.waitUntil(lambda: not subject.busy, timeout=5000)
    assert not subject.timer.isActive() and not subject.active


def test_interface_disconnect_does_not_freeze_and_can_recover(qtbot):
    client = FakeClient()
    client.connected = False
    subject = controller(qtbot, client)
    failures = []
    subject.error.connect(failures.append)
    subject.run_round(automatic=False)
    qtbot.waitUntil(lambda: not subject.busy, timeout=5000)
    assert failures
    client.connected = True
    results = []
    subject.result.connect(results.append)
    subject.run_round(automatic=False)
    qtbot.waitUntil(lambda: not subject.busy, timeout=5000)
    assert results


def test_duplicate_instance_not_acquired_and_existing_window_notified(qtbot, tmp_path):
    first = SingleInstance(tmp_path)
    second = SingleInstance(tmp_path)
    messages = []
    first.show_requested.connect(lambda: messages.append(1))
    assert first.acquire()
    assert not second.acquire()
    qtbot.waitUntil(lambda: bool(messages), timeout=3000)
    first.release()
    assert second.acquire()
    second.release()


def test_worker_completion_and_deletion_stay_on_controller_thread(qtbot):
    from smart_switcher.monitor import TaskThread
    subject = controller(qtbot)
    callback_threads = []
    subject.result.connect(lambda _: callback_threads.append(QThread.currentThread()))
    for _ in range(20):
        subject.run_round(automatic=False)
        qtbot.waitUntil(lambda: not subject.busy)
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        assert subject.findChildren(TaskThread) == []
    assert len(callback_threads) == 20
    assert all(thread == subject.thread() for thread in callback_threads)


def test_ui_has_no_fake_nodes_and_accepts_real_results(qtbot, tmp_path):
    store = ConfigStore(tmp_path)
    logger, redactor = setup_logging(tmp_path / "logs")
    settings = Settings(group="组")
    subject = controller(qtbot)
    window = MainWindow(store, settings, logger, redactor, subject)
    qtbot.addWidget(window)
    window.show()
    assert window.table.rowCount() == 0 and window.delay.text() == "未测速"
    window._connected({"client": subject.client, "proxies": subject.client.proxies(), "groups": ["组"],
                       "version": "mock-test", "traffic": TrafficState(True, False)})
    subject.run_round(automatic=False)
    qtbot.waitUntil(lambda: not subject.busy, timeout=5000)
    assert window.table.rowCount() == 4 and window.delay.text() == "185 ms"
    assert window.start_button.isEnabled()
    window.tray.hide()
    window.settings.close_to_tray = False
    # Close only this test window; avoid quitting the shared pytest QApplication.
    window.closeEvent = lambda event: event.accept()
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


def test_settings_controls_follow_group_size_and_region_chips(qtbot, tmp_path):
    store = ConfigStore(tmp_path)
    logger, redactor = setup_logging(tmp_path / "logs")
    subject = controller(qtbot)
    window = MainWindow(store, Settings(), logger, redactor, subject)
    qtbot.addWidget(window)
    client = subject.client
    window._connected({"client": client, "proxies": client.proxies(), "groups": ["组"],
                       "version": "mock-test", "traffic": TrafficState(True, False)})
    window.group.setCurrentIndex(window.group.findData("组"))
    assert window.concurrency.maximum() == len(client.delays)
    assert window.concurrency.value() == len(client.delays)
    window.concurrency.setValue(2)
    assert window.settings.concurrency_auto
    assert not window._read_settings().concurrency_auto
    window.region_selector.set_selected_regions(["香港", "新加坡", "日本"])
    assert "日本" in window._read_settings().excluded_regions
    window.region_selector.remove_region("日本")
    assert "日本" not in window._read_settings().excluded_regions
    assert [window.region_selector.options.item(i).text()
            for i in range(window.region_selector.options.count())] == ["美国", "德国", "香港", "新加坡"]
    window.proxies.update({"JP01": {"type": "Shadowsocks"}, "TW01": {"type": "Shadowsocks"},
                           "第二组": {"type": "Selector", "all": ["JP01", "TW01", "子组", "DIRECT"]}})
    window.group.addItem("第二组", "第二组")
    window.group.setCurrentIndex(window.group.findData("第二组"))
    assert [window.region_selector.options.item(i).text()
            for i in range(window.region_selector.options.count())] == ["日本", "台湾", "香港", "新加坡"]
    assert window.region_selector.selected_regions() == ["香港", "新加坡"]
    window.region_selector.set_selected_regions(["台湾", "日本", "自定义地区"])
    window.save_settings()
    assert store.load().excluded_regions == ["台湾", "日本", "自定义地区"]
    assert subject.settings.excluded_regions == ["台湾", "日本", "自定义地区"]
    window._fill_settings()
    assert window.region_selector.selected_regions() == store.load().excluded_regions
    window.region_selector.remove_region("日本")
    window.save_settings()
    assert store.load().excluded_regions == ["台湾", "自定义地区"]
    window.region_selector.clear()
    window.save_settings()
    assert store.load().excluded_regions == []
    assert window.threshold.toolTip().endswith("1–60000")
    window.tray.hide()
    window.closeEvent = lambda event: event.accept()
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
