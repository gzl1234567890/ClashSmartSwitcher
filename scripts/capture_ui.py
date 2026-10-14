"""Synthetic UI QA captures, never included in the runtime package."""
import os
from pathlib import Path
import sys
import threading

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from PySide6.QtWidgets import QApplication
from smart_switcher.config import ConfigStore, Settings
from smart_switcher.core import SwitchEngine
from smart_switcher.logging_service import setup_logging
from smart_switcher.status import TrafficState
from smart_switcher.ui import MainWindow
from tests.fakes import FakeClient

app = QApplication([])
store = ConfigStore(root / "verification" / "capture-data")
logger, redactor = setup_logging(store.directory / "logs")
window = MainWindow(store, Settings(group="组"), logger, redactor)
directory = root / ".impeccable" / "review"
directory.mkdir(parents=True, exist_ok=True)
window.show()
app.processEvents()
window.grab().save(str(directory / "empty.png"))
client = FakeClient()
window.controller.client = client
window._connected({"proxies": client.proxies(), "groups": ["组"], "version": "mock-test",
                   "traffic": TrafficState(True, False)})
result = SwitchEngine(lambda c: TrafficState(True, False)).run(client, Settings(group="组"), threading.Event(), False)
window._result(result)
window.notice.setText("模拟接口 QA 截图 · 不属于正式运行数据")
window.resize(1120, 820)
app.processEvents()
window.grab().save(str(directory / "desktop.png"))
window.resize(920, 680)
app.processEvents()
window.grab().save(str(directory / "compact.png"))
window.tabs.setCurrentIndex(1)
app.processEvents()
window.grab().save(str(directory / "settings.png"))
print("Captured: empty, desktop, compact, settings")
window.settings.close_to_tray = False
window.exiting = True
window.tray.hide()
window.close()
