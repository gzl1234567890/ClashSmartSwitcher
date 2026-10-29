"""Exercise the real Qt event loop with synthetic data, without network access."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontInfo
from PySide6.QtWidgets import QApplication

from smart_switcher.config import ConfigStore, Settings
from smart_switcher.core import Measurement, RoundResult
from smart_switcher.logging_service import setup_logging
from smart_switcher.status import TrafficState
from smart_switcher.ui import MainWindow
from tests.fakes import FakeClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "verification" / "runtime")
    args = parser.parse_args()
    app = QApplication([])
    store = ConfigStore(args.output_dir)
    logger, redactor = setup_logging(store.directory / "logs")
    window = MainWindow(store, Settings(group="组"), logger, redactor)
    window.controller.client = FakeClient()
    window._connected({"proxies": window.controller.client.proxies(), "groups": ["组"],
                       "version": "QA synthetic", "traffic": TrafficState(True, False)})
    window.show()
    timer = QTimer(window)
    count = 0

    def step():
        nonlocal count
        count += 1
        name = "德国 Tokyo Singapore → ✓ " + "超长节点名称" * 18
        window._result(RoundResult("组", name, [Measurement(name, 80 + count)], "模拟数据 · QA"))
        window.navigate(count % 6)
        window.resize(850 if count % 2 else 1440, 630 if count % 2 else 900)
        if count < 100:
            return
        timer.stop()
        window.grab().save(str(args.output_dir / "runtime.png"))
        report = {"updates": count, "pages": 6, "network_requests": 0,
                  "font": QFontInfo(window.node.font()).family(),
                  "dpr": window.devicePixelRatioF()}
        (args.output_dir / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        window.motion.shutdown()
        window.tray.hide()
        window.exiting = True
        window.close()
        app.quit()

    timer.timeout.connect(step)
    timer.start(40)
    code = app.exec()
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    if count != 100:
        return 1
    print(f"Runtime check: {count} updates, 6 pages, no network requests")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
