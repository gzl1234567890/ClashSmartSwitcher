from copy import deepcopy
import time

from smart_switcher.api import ApiError


class FakeClient:
    def __init__(self, delays=None, current="美国", switch_error=False, apply_switch=True, manual_after_read=False, latency=0):
        self.delays = delays or {"美国": 185, "德国": 80, "香港 HK": 10, "Singapore SG": 12}
        self.current = current
        self.switch_error = switch_error
        self.apply_switch = apply_switch
        self.manual_after_read = manual_after_read
        self.latency = latency
        self.reads = 0
        self.writes = []
        self.tests = []
        self.connected = True

    def configs(self):
        if not self.connected:
            raise ApiError("接口已断开")
        return {"mixed-port": 7897, "tun": {"enable": True, "device": "Meta"}}

    def version(self):
        if not self.connected:
            raise ApiError("接口已断开")
        return "mock-test"

    def proxies(self):
        self.reads += 1
        if self.manual_after_read and self.reads > 1:
            self.current = "德国"
        data = {name: {"type": "Shadowsocks"} for name in self.delays}
        data.update({"组": {"type": "Selector", "all": list(self.delays) + ["DIRECT", "子组"], "now": self.current},
                     "DIRECT": {"type": "Direct"}, "子组": {"type": "URLTest", "all": ["其他组节点"], "now": "其他组节点"},
                     "其他组节点": {"type": "Shadowsocks"}})
        return deepcopy(data)

    def proxy(self, group):
        return {"now": self.current}

    def delay(self, name, url, timeout_ms):
        time.sleep(self.latency)
        self.tests.append(name)
        value = self.delays[name]
        if value is None:
            raise ApiError("测速失败：节点或测速地址不可达")
        return value

    def switch(self, group, node):
        self.writes.append((group, node))
        if self.switch_error:
            raise ApiError("模拟切换拒绝")
        if self.apply_switch:
            self.current = node
