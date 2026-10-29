"""Synthetic UI QA captures, never included in the runtime package."""
import os
import argparse
from pathlib import Path
import sys
import threading
from datetime import datetime, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

parser = argparse.ArgumentParser()
parser.add_argument("--scale", default="100")
parser.add_argument("--base-scale", type=int, default=100, help="Windows system scale; offscreen uses 100")
parser.add_argument("--output-dir", type=Path)
args = parser.parse_args()
os.environ["QT_SCALE_FACTOR"] = str(int(args.scale) / args.base_scale)

from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QApplication, QToolTip
from PySide6.QtTest import QTest
from smart_switcher.config import ConfigStore, Settings
from smart_switcher.core import SwitchEngine
from smart_switcher.logging_service import setup_logging
from smart_switcher.status import TrafficState
from smart_switcher.ui import MainWindow
from tests.fakes import FakeClient

def capture(widget, filename):
    image = widget.grab().toImage()
    image.setText("Source", "Synthetic QA screenshot of Clash Smart Switcher; scripts/capture_ui.py; scale " + args.scale + "%.")
    image.save(str(filename))


app = QApplication([])
store = ConfigStore(root / "verification" / ("capture-data-" + args.scale))
logger, redactor = setup_logging(store.directory / "logs")
window = MainWindow(store, Settings(group="组"), logger, redactor)
assert abs(window.devicePixelRatioF() - int(args.scale) / 100) < 0.01
directory = args.output_dir or root / "verification" / ("ui-" + args.scale)
directory.mkdir(parents=True, exist_ok=True)
window.show()
QTest.qWait(220)
capture(window, directory / "empty.png")
client = FakeClient()
window.controller.client = client
window._connected({"proxies": client.proxies(), "groups": ["组"], "version": "mock-test",
                   "traffic": TrafficState(True, False)})
window.navigate(1)
QTest.qWait(220)
capture(window, directory / "unmeasured.png")
cell = window.table.visualItemRect(window.table.item(0, 1))
position = cell.center()
QTest.mouseMove(window.table.viewport(), position)
QApplication.sendEvent(window.table.viewport(), QHelpEvent(
    QEvent.ToolTip, position, window.table.viewport().mapToGlobal(position)))
QTest.qWait(80)
capture(window, directory / "unmeasured-hover.png")
for widget in QApplication.topLevelWidgets():
    if widget.objectName() == "qtooltip_label" and widget.isVisible():
        capture(widget, directory / "unmeasured-tooltip.png")
QToolTip.hideText()
QTest.mouseMove(window.navigation_bar, QPoint(100, 5))
engine = SwitchEngine(lambda c: TrafficState(True, False))
for delay in (125, 110, 87, 98, 103):
    client.delays["美国"] = delay
    result = engine.run(client, Settings(group="组"), threading.Event(), False)
    window._result(result)
window._latency_history = [(datetime.now() - timedelta(minutes=4 - i), delay)
                           for i, delay in enumerate((125, 110, 87, 98, 103))]
window._refresh_dashboard_rules()
window._status("已连接，自动切换已关闭")
window.header_status.setText("模拟数据 · QA")
for message in ("控制接口已连接", "完成节点测速", "当前节点 103 ms，保持当前节点"):
    window.append_log(message)
for size, dimensions in (("desktop", (1440, 900)), ("compact", (850, 630))):
    window.resize(*dimensions)
    for index, name in enumerate(("overview", "measurement", "automation", "logs", "settings", "help")):
        window.navigate(index)
        QTest.qWait(220)
        capture(window, directory / f"{size}-{name}.png")
        assert window.size().width() == dimensions[0], (name, window.size())
        assert window.size().height() == dimensions[1], (name, window.size())
    for topic in (1, 4):
        window.help.select_topic(topic)
        QTest.qWait(180)
        capture(window, directory / f"{size}-help-{topic}.png")
        if topic == 1:
            window.help.browser.verticalScrollBar().setValue(window.help.browser.verticalScrollBar().maximum())
            QTest.qWait(100)
            capture(window, directory / f"{size}-help-connection-code.png")
            window.help.browser.verticalScrollBar().setValue(0)
    window.help.select_topic(0)
window.resize(1440, 900)
window.navigate(1)
QTest.qWait(220)
window.motion.enabled = True
window.navigate(2)
app.processEvents()
capture(window, directory / "transition-start.png")
QTest.qWait(70)
capture(window, directory / "transition-middle.png")
QTest.qWait(170)
capture(window, directory / "transition-settled.png")
window.navigate(4)
window.threshold.setFocus()
QTest.qWait(220)
capture(window, directory / "interaction-focus.png")
window.navigate(1)
window._busy(True)
QTest.qWait(100)
capture(window, directory / "interaction-busy.png")
window._busy(False)
window.resize(850, 630)
window._busy(True)
QTest.qWait(100)
capture(window, directory / "compact-busy.png")
window._busy(False)
window._status("连接异常，当前控制接口无法访问，请检查 Clash Verge 的本机控制地址和密钥后重新检测")
QTest.qWait(220)
capture(window, directory / "compact-long-status.png")
print(f"Captured six pages, help topics and interactions, scale {args.scale}, DPR {window.devicePixelRatioF()}")
window.settings.close_to_tray = False
window.exiting = True
window.tray.hide()
window.close()
