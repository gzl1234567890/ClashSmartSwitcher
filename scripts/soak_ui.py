"""Run real worker/UI lifecycles with fake nodes only; never contact a controller."""
import argparse
import faulthandler
import gc
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication, QEvent, QThread, QTimer
from PySide6.QtWidgets import QApplication
import psutil

from smart_switcher.config import ConfigStore, Settings
from smart_switcher.core import SwitchEngine
from smart_switcher.logging_service import setup_logging
from smart_switcher.diagnostics import RuntimeDiagnostics
from smart_switcher.monitor import MonitorController, TaskThread
from smart_switcher.status import TrafficState
from smart_switcher.ui import MainWindow
from tests.fakes import FakeClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=300)
    parser.add_argument("--seconds", type=float, default=0, help="Minimum wall-clock duration")
    parser.add_argument("--interval-ms", type=int, default=10)
    parser.add_argument("--vary-members", action="store_true", help="Also exercise nodes being removed/added")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "verification/soak")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    crash = (args.output_dir / "native-crash.log").open("w", encoding="utf-8")
    faulthandler.enable(crash, all_threads=True)
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    store = ConfigStore(args.output_dir / "data")
    logger, redactor = setup_logging(store.directory / "logs")
    diagnostics = RuntimeDiagnostics(store.directory / "logs", logger, app)
    settings = Settings(group="组", minimum_switch_seconds=0)
    engine = SwitchEngine(lambda _: TrafficState(True, False))
    controller = MonitorController(settings, engine=engine)
    client = FakeClient({f"美国 QA node {i:03} 超长名称": 80 + i for i in range(64)},
                        current="美国 QA node 000 超长名称")
    controller.client = client
    window = MainWindow(store, settings, logger, redactor, controller)
    controller.setParent(window)
    diagnostics.controller = controller
    window._connected({"proxies": client.proxies(), "groups": ["组"],
                       "version": "synthetic soak", "traffic": TrafficState(True, False)})
    window.show()
    controller.active = True
    process = psutil.Process()
    started = time.monotonic()
    completed = 0
    errors = []
    samples = []
    failures = []
    next_round = QTimer(controller)
    next_round.setSingleShot(True)
    next_round.timeout.connect(controller.run_round)
    previous_hook = sys.excepthook

    def exception_hook(kind, value, traceback):
        failures.append(kind.__name__)
        previous_hook(kind, value, traceback)
        app.exit(1)

    sys.excepthook = exception_hook
    controller.error.connect(errors.append)

    def sample():
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        data = {"round": completed, "seconds": round(time.monotonic() - started, 2),
                "rss_mb": round(process.memory_info().rss / 1024**2, 2),
                "threads": process.num_threads(), "qt_workers": len(controller.findChildren(TaskThread)),
                "channels": len(window.motion._channels), "qt_children": len(window.findChildren(QThread))}
        if hasattr(process, "num_handles"):
            data["handles"] = process.num_handles()
        samples.append(data)
        (args.output_dir / "progress.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(json.dumps(data), flush=True)

    def idle():
        nonlocal completed
        controller.timer.stop()
        completed += 1
        if QThread.currentThread() != app.thread():
            failures.append("CompletionOutsideGuiThread")
            app.exit(1)
            return
        if args.vary_members and completed % 40 == 0:
            count = 48 if (completed // 40) % 2 else 80
            client.delays = {f"美国 QA node {i:03} 超长名称": 80 + i for i in range(count)}
        if completed % 10 == 0:
            if (completed // 10) % 2:
                window.hide()
            else:
                window.show()
                window.navigate((completed // 20) % 5)
        if completed % 25 == 0:
            gc.collect()
            sample()
        if completed >= args.rounds and time.monotonic() - started >= args.seconds:
            finish()
        else:
            next_round.start(args.interval_ms)

    def finish():
        sample()
        controller.idle.disconnect(idle)
        controller.pause()
        window.request_exit()

    controller.idle.connect(idle)
    next_round.start(0)
    code = app.exec()
    sys.excepthook = previous_hook
    diagnostics.close(code, requested=window.exiting)
    report = {"completed": completed, "elapsed_seconds": round(time.monotonic() - started, 2),
              "requested_seconds": args.seconds, "real_network_requests": 0,
              "python_exceptions": failures, "controller_errors": errors, "samples": samples,
              "normal_exit": window.exiting, "exit_code": code}
    (args.output_dir / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    faulthandler.disable()
    crash.close()
    return code if code else int(bool(errors or failures or completed < args.rounds))


if __name__ == "__main__":
    raise SystemExit(main())
