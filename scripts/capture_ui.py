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

app = QApplication([])
store = ConfigStore(root / "verification" / ("capture-data-" + args.scale))
logger, redactor = setup_logging(store.directory / "logs")
window = MainWindow(store, Settings(group="组"), logger, redactor)
assert abs(window.devicePixelRatioF() - int(args.scale) / 100) < 0.01
directory = args.output_dir or root / "verification" / ("ui-" + args.scale)
directory.mkdir(parents=True, exist_ok=True)
window.show()
QTest.qWait(220)
window.grab().save(str(directory / "empty.png"))
client = FakeClient()
window.controller.client = client
window._connected({"proxies": client.proxies(), "groups": ["组"], "version": "mock-test",
                   "traffic": TrafficState(True, False)})
window.navigate(1)
QTest.qWait(220)
window.grab().save(str(directory / "unmeasured.png"))
cell = window.table.visualItemRect(window.table.item(0, 1))
position = cell.center()
QTest.mouseMove(window.table.viewport(), position)
QApplication.sendEvent(window.table.viewport(), QHelpEvent(
    QEvent.ToolTip, position, window.table.viewport().mapToGlobal(position)))
QTest.qWait(80)
window.grab().save(str(directory / "unmeasured-hover.png"))
for widget in QApplication.topLevelWidgets():
    if widget.objectName() == "qtooltip_label" and widget.isVisible():
        widget.grab().save(str(directory / "unmeasured-tooltip.png"))
QToolTip.hideText()
QTest.mouseMove(window.sidebar, QPoint(100, 5))
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
    for index, name in enumerate(("overview", "measurement", "automation", "logs", "settings")):
        window.navigate(index)
        QTest.qWait(220)
        window.grab().save(str(directory / f"{size}-{name}.png"))
        assert window.size().width() == dimensions[0], (name, window.size())
        assert window.size().height() == dimensions[1], (name, window.size())
window.resize(1440, 900)
window.navigate(1)
QTest.qWait(220)
window.motion.enabled = True
window.navigate(2)
app.processEvents()
window.grab().save(str(directory / "transition-start.png"))
QTest.qWait(70)
window.grab().save(str(directory / "transition-middle.png"))
QTest.qWait(170)
window.grab().save(str(directory / "transition-settled.png"))
window.navigate(4)
window.threshold.setFocus()
QTest.qWait(220)
window.grab().save(str(directory / "interaction-focus.png"))
window.navigate(1)
window._busy(True)
QTest.qWait(100)
window.grab().save(str(directory / "interaction-busy.png"))
window._busy(False)
print(f"Captured five pages and interactions, scale {args.scale}, DPR {window.devicePixelRatioF()}")
window.settings.close_to_tray = False
window.exiting = True
window.tray.hide()
window.close()
