from dataclasses import dataclass
import os
import re


@dataclass
class TrafficState:
    system_proxy: bool | None
    tun: bool | None
    detail: str = ""

    @property
    def allowed(self):
        return self.system_proxy is True or self.tun is True

    @staticmethod
    def label(value):
        return {True: "已启用", False: "未启用", None: "状态无法确认"}[value]


def system_proxy_status(configs, registry_reader=None):
    if os.name != "nt" and registry_reader is None:
        return None, "仅支持检测 Windows 系统代理"
    try:
        if registry_reader:
            enabled, server, pac = registry_reader()
        else:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
                def read(name, default):
                    try:
                        return winreg.QueryValueEx(key, name)[0]
                    except FileNotFoundError:
                        return default
                enabled, server, pac = read("ProxyEnable", 0), read("ProxyServer", ""), read("AutoConfigURL", "")
        if not enabled:
            return (None, "检测到 PAC，无法确认它是否实际使用当前 Mihomo") if pac else (False, "Windows 手动系统代理未启用")
        ports = {configs.get(key) for key in ("mixed-port", "port") if configs.get(key)}
        targets = re.findall(r"(?:^|[;=\s])(?:127\.0\.0\.1|localhost|\[::1\]):(\d+)(?=$|[;\s])", str(server), re.I)
        if any(int(port) in ports for port in targets):
            return True, "Windows 系统代理指向当前内核的本机 HTTP/混合端口"
        return None, "Windows 代理已启用，但未确认它属于当前 Mihomo"
    except (OSError, ValueError):
        return None, "无法读取 Windows 系统代理状态"


def detect_traffic(configs, registry_reader=None, adapters=None):
    proxy, proxy_detail = system_proxy_status(configs, registry_reader)
    tun_config = configs.get("tun", {})
    if not isinstance(tun_config, dict) or type(tun_config.get("enable")) is not bool:
        tun, tun_detail = None, "内核未提供实时 TUN 状态"
    elif not tun_config["enable"]:
        tun, tun_detail = False, "内核实时 TUN 未启用"
    else:
        try:
            if adapters is None:
                import psutil
                adapters = {name: stat.isup for name, stat in psutil.net_if_stats().items()}
            device = tun_config.get("device")
            if isinstance(device, str) and device:
                matched = [name for name in adapters if name.casefold() == device.casefold()]
            else:
                matched = [name for name in adapters if name.casefold() in ("mihomo", "meta", "clash")]
            tun = True if any(adapters[name] for name in matched) else None
            tun_detail = "实时 TUN 已启用且对应网卡处于活动状态" if tun else "实时配置启用了 TUN，但无法确认对应活动网卡"
        except (OSError, ImportError):
            tun, tun_detail = None, "无法读取 TUN 网卡运行状态"
    return TrafficState(proxy, tun, proxy_detail + "；" + tun_detail)
