"""Read-only integration probe. Never sends PUT or alters any selected node."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from smart_switcher.api import ApiError, MihomoClient
from smart_switcher.config import Settings
from smart_switcher.core import controllable_groups, group_members
from smart_switcher.discovery import discover
from smart_switcher.status import detect_traffic


parser = argparse.ArgumentParser()
parser.add_argument("--measure-current", action="store_true", help="对一个直接节点执行真实测速；仍不切换")
parser.add_argument("--output", type=Path, default=Path("verification/live-probe.json"))
args = parser.parse_args()
report = {"timestamp": datetime.now().isoformat(timespec="seconds"), "writes_sent": 0}
for endpoint in discover():
    try:
        client = MihomoClient(endpoint.address, endpoint.secret)
        report["core_version"] = client.version()
        proxies = client.proxies()
        cfg = client.configs()
        groups = controllable_groups(proxies)
        report["transport"] = "named-pipe-http" if endpoint.address.startswith("\\\\.\\pipe\\") else "http"
        report["selector_count"] = len(groups)
        state = detect_traffic(cfg)
        report["system_proxy"] = state.system_proxy
        report["tun"] = state.tun
        report["group_members_and_current_readable"] = True
        if args.measure_current:
            name = next((proxies[g].get("now") for g in groups if proxies[g].get("now") in group_members(g, proxies)), None)
            if name:
                settings = Settings()
                try:
                    report["current_node_delay_ms"] = client.delay(name, settings.test_url, settings.timeout_ms)
                    report["delay_api_verified"] = True
                except ApiError as exc:
                    report["delay_api_verified"] = False
                    report["delay_error"] = str(exc)
        break
    except ApiError as exc:
        report["last_connection_error"] = str(exc)
else:
    report["connected"] = False
report["connected"] = "core_version" in report
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
