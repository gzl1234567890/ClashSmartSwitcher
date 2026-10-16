"""Local crash stacks and bounded runtime status, without controller/user data."""
from datetime import datetime, timezone
import faulthandler
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback

import psutil
from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QObject, QTimer, Slot, qVersion

from . import __version__


class RuntimeDiagnostics(QObject):
    def __init__(self, directory: Path, logger, parent=None):
        super().__init__(parent)
        self.directory, self.logger = directory, logger
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "runtime-status.json"
        self.controller = None
        self.started = time.monotonic()
        self.closed = False
        self.process = psutil.Process()
        self.native_file = None
        self.owns_faulthandler = False
        self.previous_hook = sys.excepthook
        self.installed_hook = self._exception
        previous = self._previous_status()
        self.status = {"application": __version__, "python": platform.python_version(),
                       "pyside": pyside_version, "qt": qVersion(), "windows": platform.version(),
                       "pid": os.getpid(), "started_utc": self._now(), "clean_exit": False}
        if previous and not previous.get("clean_exit", False):
            logger.warning("上次运行没有正常退出标记；请结合 native-crash.log 和 Windows 应用程序事件排查")
        try:
            native = directory / "native-crash.log"
            if not faulthandler.is_enabled():
                if native.exists() and native.stat().st_size:
                    native.replace(directory / "native-crash.previous.log")
                self.native_file = native.open("w", encoding="utf-8")
                faulthandler.enable(self.native_file, all_threads=True)
                self.owns_faulthandler = True
        except (OSError, RuntimeError):
            logger.warning("无法启用本地原生崩溃记录")
        sys.excepthook = self.installed_hook
        self.timer = QTimer(self)
        self.timer.setInterval(60_000)
        self.timer.timeout.connect(self.snapshot)
        self.snapshot()
        self.timer.start()
        logger.info("运行诊断已启动；应用 %s；Python %s；PySide %s；Qt %s；Windows %s",
                    __version__, self.status["python"], pyside_version, qVersion(), self.status["windows"])

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _previous_status(self):
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, ValueError):
            return None

    @Slot()
    def snapshot(self):
        if self.closed:
            return
        self.status.update(updated_utc=self._now(), elapsed_seconds=int(time.monotonic() - self.started))
        if self.controller is not None:
            self.status.update(automation_active=self.controller.active, worker_busy=self.controller.busy,
                               retry_failures=self.controller.failures)
        try:
            self.status.update(rss_mb=round(self.process.memory_info().rss / 1024**2, 1),
                               threads=self.process.num_threads())
            if hasattr(self.process, "num_handles"):
                self.status["handles"] = self.process.num_handles()
        except (psutil.Error, OSError):
            pass
        self._write()

    def _write(self):
        try:
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.status, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.path)
        except OSError:
            self.logger.warning("无法更新本地运行诊断")

    def _exception(self, kind, value, tb):
        # Exception values/locals may include credentials; retain type and call sites only.
        frames = "".join(traceback.format_list([
            traceback.FrameSummary(frame.filename, frame.lineno, frame.name, lookup_line=False, line="")
            for frame in traceback.extract_tb(tb)]))
        self.logger.error("未处理的 Python 异常（%s）：\n%s", kind.__name__, frames)
        self.status["last_python_exception"] = kind.__name__
        self.snapshot()
        if sys.stderr is not None:
            self.previous_hook(kind, value, tb)

    def close(self, exit_code, requested=False):
        if self.closed:
            return
        self.timer.stop()
        self.snapshot()
        self.status.update(clean_exit=exit_code == 0 and requested, exit_code=exit_code,
                           exit_requested=requested, stopped_utc=self._now())
        self._write()
        self.closed = True
        self.logger.info("进程结束；返回码 %s；主动退出 %s；运行 %s 秒",
                         exit_code, requested, self.status["elapsed_seconds"])
        if sys.excepthook == self.installed_hook:
            sys.excepthook = self.previous_hook
        if self.owns_faulthandler:
            faulthandler.disable()
        if self.native_file is not None:
            self.native_file.close()
