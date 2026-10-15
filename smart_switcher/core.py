from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass, field
import threading
import time

from .api import ApiError
from .config import Settings
from .regions import excluded_region
from .status import detect_traffic


SPECIAL_TYPES = {"direct", "reject", "rejectdrop", "pass", "compatible", "dns"}
SPECIAL_NAMES = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE", "GLOBAL"}


def is_node(name, proxies):
    item = proxies.get(name)
    return (isinstance(item, dict) and isinstance(item.get("type"), str)
            and "all" not in item and name.upper() not in SPECIAL_NAMES
            and item["type"].casefold() not in SPECIAL_TYPES
            and item["type"].casefold() not in {"selector", "urltest", "fallback", "loadbalance", "relay"})


def group_members(group, proxies):
    item = proxies.get(group)
    if not item or item.get("type") != "Selector" or not isinstance(item.get("all"), list):
        raise ApiError("请选择可手动控制的 Selector 代理组；自动测速组由内核自身管理")
    return list(dict.fromkeys(name for name in item["all"] if isinstance(name, str) and is_node(name, proxies)))


def controllable_groups(proxies):
    return [name for name, item in proxies.items()
            if item.get("type") == "Selector" and isinstance(item.get("all"), list)]


@dataclass
class Measurement:
    name: str
    delay: int | None = None
    error: str = ""
    excluded: str | None = None


@dataclass
class RoundResult:
    group: str
    current: str
    measurements: list[Measurement] = field(default_factory=list)
    message: str = ""
    switched: bool = False
    previous: str = ""
    target: str = ""
    traffic: object = None


def choose_target(current, results, threshold):
    active = next((x for x in results if x.name == current), None)
    if active and active.delay is not None and active.delay <= threshold:
        return None, f"当前节点延迟 {active.delay} ms，未超过阈值 {threshold} ms，保持当前节点"
    usable = [x for x in results if x.delay is not None and x.excluded is None]
    if not usable:
        return None, "所有合格候选节点均不可用，保持当前状态；请检查测速地址和网络"
    best = min(usable, key=lambda x: x.delay)
    if best.name == current:
        return None, "当前节点已是候选节点中的最低延迟"
    reason = f"当前节点延迟 {active.delay} ms，超过阈值 {threshold} ms" if active and active.delay else "当前节点测速失败"
    return best.name, f"{reason}，选择 {best.name}（{best.delay} ms）"


class SwitchEngine:
    def __init__(self, traffic_detector=detect_traffic):
        self.round_lock = threading.Lock()
        self.control_lock = threading.Lock()
        self.last_switch = None
        self.traffic_detector = traffic_detector

    def run(self, client, settings: Settings, cancel: threading.Event, automatic=False, log=lambda text: None):
        if not self.round_lock.acquire(blocking=False):
            raise ApiError("上一轮检测仍在进行")
        try:
            return self._run(client, settings, cancel, automatic, log)
        finally:
            self.round_lock.release()

    def _run(self, client, settings, cancel, automatic, log):
        settings.validate()
        traffic = self.traffic_detector(client.configs())
        if automatic and not traffic.allowed:
            raise ApiError("未检测到正在启用的系统代理或 TUN 模式。请先在 Clash Verge 中启用其中一种模式后重新检测。" + traffic.detail)
        proxies = client.proxies()
        members = group_members(settings.group, proxies)
        if not members:
            raise ApiError("该代理组没有直接服务器节点，请选择包含实际服务器的可控代理组")
        current = proxies[settings.group].get("now", "")
        if not isinstance(current, str):
            raise ApiError("当前节点状态的数据格式不兼容")
        result = RoundResult(settings.group, current, traffic=traffic)
        log(f"本轮测速开始：代理组 {settings.group}，当前节点 {current}，{len(members)} 个服务器节点")

        def measure(name):
            item = Measurement(name, excluded=excluded_region(name, settings.excluded_regions))
            if cancel.is_set():
                item.error = "已取消"
                return item
            try:
                item.delay = client.delay(name, settings.test_url, settings.timeout_ms)
            except ApiError as exc:
                item.error = str(exc)
            return item

        # Only keep at most concurrency pending requests; cancellation stops new submissions.
        with ThreadPoolExecutor(max_workers=min(settings.concurrency, len(members)),
                                thread_name_prefix="node-delay") as pool:
            pending = {}
            names = iter(members)
            for _ in range(min(settings.concurrency, len(members))):
                name = next(names)
                pending[pool.submit(measure, name)] = name
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    pending.pop(future)
                    item = future.result()
                    result.measurements.append(item)
                    log(f"{item.name}：{str(item.delay) + ' ms' if item.delay is not None else item.error}" +
                        (f"；已排除地区 {item.excluded}" if item.excluded else ""))
                    if not cancel.is_set():
                        name = next(names, None)
                        if name is not None:
                            pending[pool.submit(measure, name)] = name
        result.measurements.sort(key=lambda x: members.index(x.name))
        log("本轮测速完成")
        if cancel.is_set():
            result.message = "本轮已取消，未继续自动切换"
            return result
        if current not in members:
            result.message = "当前选择是策略或嵌套代理组，无法以服务器延迟判定；请在 Clash Verge 选择实际服务器或更换管理组"
            return result
        target, message = choose_target(current, result.measurements, settings.threshold_ms)
        result.message, result.target = message, target or ""
        if not automatic or target is None:
            if target and not automatic:
                result.message += "；仅测速，未执行切换"
            return result
        if self.last_switch is not None and time.monotonic() - self.last_switch < settings.minimum_switch_seconds:
            result.message += "；最小切换间隔尚未到达，保持当前节点"
            return result
        with self.control_lock:
            if cancel.is_set():
                result.message = "自动切换已暂停"
                return result
            fresh = client.proxies()
            fresh_members = group_members(settings.group, fresh)
            latest = fresh[settings.group].get("now", "")
            if latest != current:
                result.current = latest
                result.message = "检测到用户手动切换了节点，本轮保持新的选择，下轮重新测速"
                return result
            if target not in fresh_members or excluded_region(target, settings.excluded_regions):
                result.message = "候选节点或代理组已变化，本轮取消切换"
                return result
            if not self.traffic_detector(client.configs()).allowed:
                raise ApiError("系统代理或 TUN 已关闭或状态无法确认，已停止自动切换")
            if cancel.is_set():
                result.message = "自动切换已暂停"
                return result
            error = None
            try:
                client.switch(settings.group, target)
            except ApiError as exc:
                error = str(exc)
            try:
                actual = client.proxy(settings.group).get("now", "")
            except ApiError:
                actual = ""
            result.previous = current
            result.current = actual
            if error:
                result.message = f"切换请求失败：{error}；实际节点：{actual or '状态无法确认'}"
            elif actual != target:
                result.message = f"节点切换请求已执行，但尚未确认切换生效；实际节点：{actual or '状态无法确认'}"
            else:
                result.switched = True
                self.last_switch = time.monotonic()
                result.message += f"；已验证切换成功：{current} → {target}"
                chosen = next(x for x in result.measurements if x.name == target)
                if chosen.delay > settings.threshold_ms:
                    result.message += "；当前网络延迟仍然较高"
        return result
