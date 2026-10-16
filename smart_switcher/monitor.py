from copy import deepcopy
import threading
import time

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot

from .api import ApiError, MihomoClient
from .core import SwitchEngine, controllable_groups, group_members
from .discovery import Endpoint, discover
from .status import detect_traffic


class TaskThread(QThread):
    completed = Signal(object)
    failed = Signal(str)
    message = Signal(str)

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task

    def run(self):
        try:
            self.completed.emit(self.task(self.message.emit))
        except (ApiError, ValueError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"后台任务未完成（{type(exc).__name__}），请重新检测连接或查看帮助")


class MonitorController(QObject):
    connection = Signal(object)
    result = Signal(object)
    error = Signal(str)
    message = Signal(str)
    status = Signal(str)
    busy_changed = Signal(bool)
    idle = Signal()

    def __init__(self, settings, client_factory=MihomoClient, engine=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.client_factory = client_factory
        self.engine = engine or SwitchEngine()
        self.client = None
        self.worker = None
        self.cancel = threading.Event()
        self.active = False
        self.failures = 0
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._timed_round)
        self.started_at = 0

    @property
    def busy(self):
        return self.worker is not None

    def _launch(self, operation, kind, start_after=False):
        if self.busy:
            return False
        self.cancel = threading.Event()
        self.started_at = time.monotonic()
        self._outcome = None
        self._failure = ""
        thread = TaskThread(operation, self)
        thread.kind, thread.start_after = kind, start_after
        thread.completed.connect(self._received, Qt.QueuedConnection)
        thread.failed.connect(self._failed, Qt.QueuedConnection)
        thread.message.connect(self.message)
        thread.finished.connect(self._task_finished, Qt.QueuedConnection)
        self.worker = thread
        self.busy_changed.emit(True)
        thread.start()
        return True

    @Slot(object)
    def _received(self, value):
        self._outcome = value

    @Slot(str)
    def _failed(self, message):
        self._failure = message

    @Slot()
    def _task_finished(self):
        worker = self.worker
        if worker is not None:
            self._finished(worker.kind, worker.start_after)

    def _finished(self, kind, start_after):
        worker, self.worker = self.worker, None
        worker.task = None
        worker.deleteLater()
        cancelled = self.cancel.is_set()
        self.busy_changed.emit(False)
        if self._failure and not cancelled:
            self.failures += 1
            self.error.emit(self._failure)
            self.message.emit(self._failure)
            if kind == "connect" or "系统代理" in self._failure or "TUN" in self._failure:
                self.pause()
            elif self.active:
                self.status.emit("接口异常，等待重试")
        elif not cancelled and self._outcome is not None:
            self.failures = 0
            if kind == "connect":
                data = self._outcome
                self.client = data["client"]
                self.settings.controller = data["endpoint"].address
                self.settings.secret = data["endpoint"].secret
                if self.settings.group not in data["groups"]:
                    self.settings.group = data["groups"][0] if len(data["groups"]) == 1 else ""
                self.connection.emit(data)
                self.status.emit("已连接，自动切换已关闭")
                if start_after:
                    if not data["traffic"].allowed:
                        self.error.emit("未检测到正在启用的系统代理或 TUN 模式。请先打开 Clash Verge，启用其中一种模式后再重新检测。\n" + data["traffic"].detail)
                    elif not self.settings.group:
                        self.error.emit("无法可靠判断正在使用的代理组，请先选择需要管理的代理组")
                    else:
                        try:
                            members = group_members(self.settings.group, data["proxies"])
                            if not members:
                                raise ApiError("该代理组没有直接服务器节点，请更换代理组")
                            self.active = True
                            self.status.emit("自动切换运行中")
                            self.timer.start(0)
                        except ApiError as exc:
                            self.error.emit(str(exc))
            else:
                self.result.emit(self._outcome)
                self.message.emit(self._outcome.message)
                self.status.emit("自动切换运行中" if self.active else "自动切换已关闭")
        if self.active and kind == "round":
            interval = min(self.settings.interval_seconds * (2 ** min(self.failures, 4)), 600) if self.failures else self.settings.interval_seconds
            elapsed = time.monotonic() - self.started_at
            self.timer.start(max(1000, int((interval - elapsed) * 1000)))
        self.idle.emit()

    def connect_api(self, start_after=False, force_discovery=False):
        if self.busy:
            return False
        self.pause()
        self.client = None
        settings = deepcopy(self.settings)
        # Event is replaced by _launch before the closure runs.
        def operation(log):
            endpoints = []
            if settings.controller and not force_discovery:
                endpoints.append(Endpoint(settings.controller, settings.secret, "用户设置"))
            for item in discover():
                if not any(x.address == item.address for x in endpoints):
                    endpoints.append(item)
            if not endpoints:
                raise ApiError("未找到本机控制接口。请在连接设置中填写 HTTP 控制地址与密钥，或查看帮助启用本机外部控制器。")
            last_error = ""
            for endpoint in endpoints[:6]:
                if self.cancel.is_set():
                    return None
                try:
                    client = self.client_factory(endpoint.address, endpoint.secret)
                    version = client.version()
                    proxies = client.proxies()
                    configs = client.configs()
                    traffic = detect_traffic(configs)
                    log(f"控制接口已连接；Mihomo {version}；可控代理组 {len(controllable_groups(proxies))} 个")
                    return {"client": client, "endpoint": endpoint, "version": version,
                            "proxies": proxies, "groups": controllable_groups(proxies), "traffic": traffic}
                except (ApiError, ValueError) as exc:
                    last_error = str(exc)
                    log(f"本机接口检测未成功：{last_error}")
            raise ApiError(last_error + "。可点击“自动发现”重试，或查看帮助配置本机 HTTP 控制器。")
        self.status.emit("正在检测连接")
        return self._launch(operation, "connect", start_after)

    def run_round(self, automatic=None):
        if self.busy:
            return False
        auto = self.active if automatic is None else automatic
        if self.client is None:
            self.error.emit("请先重新检测连接")
            return False
        settings = deepcopy(self.settings)
        if not settings.group:
            self.error.emit("请先选择代理组")
            return False
        client = self.client
        self.status.emit("正在刷新节点延迟")
        return self._launch(lambda log: self.engine.run(client, settings, self.cancel, auto, log), "round")

    def _timed_round(self):
        if self.active:
            self.run_round()

    def pause(self):
        self.active = False
        self.timer.stop()
        self.cancel.set()
        self.status.emit("自动切换已暂停" if self.busy else "自动切换已关闭")

    def shutdown(self):
        self.pause()
        return not self.busy
