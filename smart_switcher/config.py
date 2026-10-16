from __future__ import annotations

import base64
from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
from urllib.parse import urlsplit


MAX_CONCURRENCY = 256
# Mihomo can handle more requests, but probing a whole subscription at once
# makes slow nodes compete for connections and causes avoidable 504 results.
AUTO_CONCURRENCY_CAP = 8
RETRY_TIMEOUT_MS = 5000


def data_directory() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ClashSmartSwitcher"


@dataclass
class Settings:
    controller: str = ""
    secret: str = field(default="", repr=False)
    auto_enabled: bool = False
    group: str = ""
    threshold_ms: int = 120
    interval_seconds: int = 60
    timeout_ms: int = 5000
    test_url: str = "https://www.gstatic.com/generate_204"
    excluded_regions: list[str] = field(default_factory=lambda: ["香港", "新加坡"])
    concurrency: int = 4
    concurrency_auto: bool = True
    minimum_switch_seconds: int = 60
    close_to_tray: bool = True
    save_secret: bool = True

    def validate(self) -> None:
        for name, lower, upper in [
            ("threshold_ms", 1, 60000), ("interval_seconds", 5, 86400),
            ("timeout_ms", 500, 30000), ("concurrency", 1, MAX_CONCURRENCY),
            ("minimum_switch_seconds", 0, 86400),
        ]:
            value = getattr(self, name)
            if type(value) is not int or not lower <= value <= upper:
                raise ValueError(f"{name} 必须在 {lower} 至 {upper} 之间")
        if not isinstance(self.excluded_regions, list) or any(
            not isinstance(x, str) or not x.strip() for x in self.excluded_regions
        ):
            raise ValueError("排除地区必须是非空名称列表")
        for name in ("controller", "secret", "group", "test_url"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} 格式错误")
        for name in ("auto_enabled", "close_to_tray", "save_secret", "concurrency_auto"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} 格式错误")
        if any(c in self.secret for c in "\r\n"):
            raise ValueError("密钥不能包含换行符")
        if self.controller:
            validate_controller(self.controller)
        target = urlsplit(self.test_url)
        if target.scheme not in ("http", "https") or not target.hostname or target.username:
            raise ValueError("测速地址必须是有效的 HTTP 或 HTTPS 地址")


def validate_controller(address: str) -> None:
    if address.startswith("\\\\.\\pipe\\"):
        if len(address) <= 9 or any(c in address[9:] for c in "\\/\r\n"):
            raise ValueError("本机命名管道地址无效")
        return
    parsed = urlsplit(address)
    if (parsed.scheme not in ("http", "https") or parsed.hostname not in
            ("127.0.0.1", "localhost", "::1") or parsed.username or parsed.password
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ValueError("控制接口仅支持本机 HTTP/HTTPS 地址或本机命名管道；请勿填写代理流量端口")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("控制端口无效") from exc


class ConfigStore:
    def __init__(self, directory: Path | None = None):
        self.directory = directory or data_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "settings.json"
        self.warning = ""

    def load(self) -> Settings:
        if not self.path.exists():
            settings = Settings()
            self.save(settings)
            return settings
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("配置不是对象")
            cipher = raw.pop("secret_dpapi", "")
            raw.pop("schema_version", None)
            raw.pop("secret", None)
            settings = Settings(**{k: v for k, v in raw.items() if k in Settings.__dataclass_fields__})
            settings.validate()
        except (OSError, ValueError, TypeError):
            backup = self.path.with_name(f"settings.corrupt-{datetime.now():%Y%m%d-%H%M%S-%f}.json")
            self.path.replace(backup)
            self.warning = "配置已损坏，原文件已备份；已恢复默认设置，请重新连接。"
            settings = Settings()
            self.save(settings)
            return settings
        if cipher:
            try:
                import win32crypt
                settings.secret = win32crypt.CryptUnprotectData(base64.b64decode(cipher), None, None, None, 0)[1].decode("utf-8")
            except Exception:
                self.warning = "无法解密保存的密钥，请重新填写；其他设置已保留。"
        return settings

    def save(self, settings: Settings) -> None:
        settings.validate()
        raw = asdict(settings)
        secret = raw.pop("secret")
        raw["schema_version"] = 1
        if secret and settings.save_secret:
            try:
                import win32crypt
                cipher = win32crypt.CryptProtectData(secret.encode("utf-8"), "ClashSmartSwitcher", None, None, None, 0)
                raw["secret_dpapi"] = base64.b64encode(cipher).decode("ascii")
            except Exception as exc:
                raise ValueError("无法使用 Windows 账户加密密钥，请关闭“加密保存密钥”后重试") from exc
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)
