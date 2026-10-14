from pathlib import Path
import time

from PySide6.QtCore import QTimer
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
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
