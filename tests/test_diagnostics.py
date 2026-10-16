import json
import logging
import sys
from types import SimpleNamespace

from smart_switcher.diagnostics import RuntimeDiagnostics


def test_runtime_status_has_no_config_and_marks_normal_exit(qapp, tmp_path):
    subject = RuntimeDiagnostics(tmp_path, logging.getLogger("diagnostics-test"))
    try:
        subject.controller = SimpleNamespace(active=True, busy=False, failures=2,
                                             settings=SimpleNamespace(secret="must-not-be-recorded"))
        subject.snapshot()
        data = json.loads(subject.path.read_text(encoding="utf-8"))
        assert data["automation_active"] and not data["worker_busy"]
        assert data["retry_failures"] == 2 and not data["clean_exit"]
        assert "must-not-be-recorded" not in subject.path.read_text(encoding="utf-8")
        assert data["rss_mb"] > 0 and data["threads"] > 0
    finally:
        subject.close(0, requested=True)
    assert json.loads(subject.path.read_text())["clean_exit"]
    assert not subject.timer.isActive()


def test_unexpected_event_loop_exit_is_not_marked_clean(qapp, tmp_path):
    subject = RuntimeDiagnostics(tmp_path, logging.getLogger("diagnostics-test"))
    subject.close(0, requested=False)
    assert not json.loads(subject.path.read_text())["clean_exit"]


def test_previous_unclean_run_is_logged_and_crash_stack_preserved(qapp, tmp_path, caplog, monkeypatch):
    from smart_switcher import diagnostics
    monkeypatch.setattr(diagnostics.faulthandler, "is_enabled", lambda: False)
    monkeypatch.setattr(diagnostics.faulthandler, "enable", lambda *args, **kwargs: None)
    monkeypatch.setattr(diagnostics.faulthandler, "disable", lambda: None)
    (tmp_path / "runtime-status.json").write_text('{"clean_exit": false}', encoding="utf-8")
    (tmp_path / "native-crash.log").write_text("native call stack", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        subject = RuntimeDiagnostics(tmp_path, logging.getLogger("diagnostics-test"))
    subject.close(0, requested=True)
    assert "上次运行没有正常退出标记" in caplog.text
    assert (tmp_path / "native-crash.previous.log").read_text() == "native call stack"


def test_python_exception_records_type_and_frames_without_value(qapp, tmp_path, caplog, monkeypatch):
    monkeypatch.setattr(sys, "excepthook", lambda *args: None)
    previous = sys.excepthook
    subject = RuntimeDiagnostics(tmp_path, logging.getLogger("diagnostics-test"))
    try:
        try:
            raise ValueError("sensitive-runtime-value")
        except ValueError:
            with caplog.at_level(logging.ERROR):
                sys.excepthook(*sys.exc_info())
        assert "ValueError" in caplog.text and "test_diagnostics.py" in caplog.text
        assert "sensitive-runtime-value" not in caplog.text
        assert json.loads(subject.path.read_text())["last_python_exception"] == "ValueError"
    finally:
        subject.close(0, requested=True)
    assert sys.excepthook == previous
