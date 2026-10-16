import json
from pathlib import Path
import subprocess
import sys


def test_real_worker_and_ui_lifecycles_in_separate_process(tmp_path):
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run([sys.executable, str(root / "scripts/soak_ui.py"),
                             "--rounds", "150", "--vary-members", "--output-dir", str(tmp_path)],
                            cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    report = json.loads((tmp_path / "result.json").read_text())
    assert report["completed"] == 150 and report["normal_exit"]
    assert not report["python_exceptions"] and not report["controller_errors"]
    assert report["real_network_requests"] == 0
    assert all(sample["qt_workers"] == 0 for sample in report["samples"])
