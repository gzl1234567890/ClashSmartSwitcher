"""Fetch the small, pinned Lucide subset used by the native UI (build-time only)."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT / "resources" / "icons" / "lucide"
VERSION = "0.468.0"
ICONS = (
    "activity", "play", "pause", "square", "refresh-cw", "search", "folder-open",
    "trash-2", "chevron-down", "chevron-up", "circle-alert",
    "circle-check", "plug", "radar", "gauge", "settings-2",
    "circle-help", "power", "save", "arrow-up-right", "network",
)


def download(name):
    relative = "LICENSE" if name == "LICENSE" else f"icons/{name}.svg"
    url = f"https://raw.githubusercontent.com/lucide-icons/lucide/{VERSION}/{relative}"
    destination = DESTINATION / ("LICENSE" if name == "LICENSE" else f"{name}.svg")
    if destination.exists() and destination.stat().st_size > 30:
        return name
    request = urllib.request.Request(url, headers={"User-Agent": "ClashSmartSwitcher icon fetcher"})
    error = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                content = response.read()
            destination.write_bytes(content)
            return name
        except Exception as exc:
            error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"unable to download {name}: {error}")


if __name__ == "__main__":
    DESTINATION.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        print("Downloaded: " + ", ".join(pool.map(download, (*ICONS, "LICENSE"))))
