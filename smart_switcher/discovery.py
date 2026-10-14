from dataclasses import dataclass, field
import os
import re
from pathlib import Path

import yaml

from .config import validate_controller


@dataclass
class Endpoint:
    address: str
    secret: str = field(default="", repr=False)
    source: str = ""


def known_directories() -> list[Path]:
    roaming = Path(os.environ.get("APPDATA", str(Path.home())))
    return [roaming / name for name in (
        "io.github.clash-verge-rev.clash-verge-rev",
        "io.github.clash-verge-rev.clash-verge", "io.github.clash-verge.clash-verge",
    )]


def discover(directories=None, pipe_names=None) -> list[Endpoint]:
    found = []
    for directory in directories if directories is not None else known_directories():
        for filename in ("clash-verge.yaml", "config.yaml"):
            path = directory / filename
            try:
                if path.stat().st_size > 8 * 1024 * 1024:
                    continue
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue
            except (OSError, ValueError, yaml.YAMLError):
                continue
            for key in ("external-controller-pipe", "external-controller", "external-controller-tls"):
                address = data.get(key)
                if not isinstance(address, str) or not address:
                    continue
                if key != "external-controller-pipe":
                    address = ("https://" if key.endswith("tls") else "http://") + address
                try:
                    validate_controller(address)
                except ValueError:
                    continue
                if not any(x.address == address for x in found):
                    found.append(Endpoint(address, str(data.get("secret") or ""), filename))
    # Service mode may use another official Mihomo pipe for the same owner key.
    owner_keys = {match.group(1) for endpoint in found
                  if endpoint.address.startswith("\\\\.\\pipe\\")
                  and (match := re.search(r"-([0-9a-f]{64})$", endpoint.address))}
    if owner_keys and (os.name == "nt" or pipe_names is not None):
        try:
            names = pipe_names if pipe_names is not None else os.listdir("\\\\.\\pipe")
            for name in names:
                match = re.fullmatch(r"verge-mihomo-(?:production|development|sidecar-release|sidecar-dev)-([0-9a-f]{64})", name)
                if match and match.group(1) in owner_keys:
                    address = "\\\\.\\pipe\\" + name
                    found = [x for x in found if x.address != address]
                    found.insert(0, Endpoint(address, "", "当前用户的 Mihomo 活动管道"))
        except OSError:
            pass
    return found
