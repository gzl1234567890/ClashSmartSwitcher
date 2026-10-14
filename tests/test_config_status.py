import json
import logging
import os

import pytest

from smart_switcher.config import ConfigStore, Settings, validate_controller
from smart_switcher.discovery import discover
from smart_switcher.logging_service import RedactingFilter
from smart_switcher.status import detect_traffic, system_proxy_status


def test_missing_config_created_and_roundtrip(tmp_path):
    store = ConfigStore(tmp_path)
    settings = store.load()
    assert settings.threshold_ms == 120 and settings.interval_seconds == 60
    settings.group = "中文组"
    store.save(settings)
    assert store.load().group == "中文组"


@pytest.mark.parametrize("contents", ["not json", "[]", '{"timeout_ms":999999}', '{"auto_enabled":"yes"}'])
def test_corrupt_config_is_backed_up(tmp_path, contents):
    (tmp_path / "settings.json").write_text(contents, encoding="utf-8")
    store = ConfigStore(tmp_path)
    assert store.load().threshold_ms == 120
    assert store.warning and list(tmp_path.glob("settings.corrupt-*.json"))


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI")
def test_secret_is_protected_and_not_plaintext(tmp_path):
    store = ConfigStore(tmp_path)
    settings = Settings(secret="mock-local-test-secret")
    store.save(settings)
    assert settings.secret not in store.path.read_text(encoding="utf-8")
    assert store.load().secret == settings.secret


def test_secret_session_only(tmp_path):
    store = ConfigStore(tmp_path)
    store.save(Settings(secret="mock-local-test-secret", save_secret=False))
    assert store.load().secret == ""


@pytest.mark.parametrize("address", ["http://192.168.1.1:9090", "http://example.com", "http://127.0.0.1@example.com", "http://127.0.0.1:9090/proxies", "ftp://localhost:9090", "http://localhost:99999"])
def test_remote_and_invalid_controller_rejected(address):
    with pytest.raises(ValueError):
        validate_controller(address)


def test_discovery_bounded_and_does_not_modify_files(tmp_path):
    text = 'external-controller: 127.0.0.1:9990\nsecret: "mock"\n'
    path = tmp_path / "config.yaml"
    path.write_text(text)
    endpoints = discover([tmp_path])
    assert len(endpoints) == 1 and endpoints[0].address == "http://127.0.0.1:9990"
    assert path.read_text() == text


def test_discovery_ignores_remote_endpoint(tmp_path):
    (tmp_path / "config.yaml").write_text("external-controller: 0.0.0.0:9090\n")
    assert discover([tmp_path]) == []


def test_discovery_matches_only_same_owner_official_pipes(tmp_path):
    owner = "a" * 64
    other = "b" * 64
    (tmp_path / "config.yaml").write_text('external-controller-pipe: "\\\\\\\\.\\\\pipe\\\\verge-mihomo-sidecar-release-' + owner + '"\n')
    endpoints = discover([tmp_path], ["verge-mihomo-production-" + owner,
                                     "verge-mihomo-production-" + other, "clash-verge-service"])
    assert endpoints[0].address.endswith("production-" + owner)
    assert all(other not in x.address for x in endpoints)


def test_proxy_disabled_and_tun_disabled():
    state = detect_traffic({"tun": {"enable": False}}, lambda: (0, "", ""), {})
    assert not state.allowed and state.system_proxy is False and state.tun is False


def test_proxy_must_match_mihomo_port():
    cfg = {"mixed-port": 7897}
    assert system_proxy_status(cfg, lambda: (1, "http=127.0.0.1:7897;https=127.0.0.1:7897", ""))[0] is True
    assert system_proxy_status(cfg, lambda: (1, "127.0.0.1:8888", ""))[0] is None


def test_pac_is_unknown_not_fake_enabled():
    assert system_proxy_status({}, lambda: (0, "", "http://localhost/pac"))[0] is None


def test_live_tun_needs_active_adapter():
    cfg = {"tun": {"enable": True, "device": "Meta"}}
    assert detect_traffic(cfg, lambda: (0, "", ""), {"Meta": True}).allowed
    assert not detect_traffic(cfg, lambda: (0, "", ""), {"Meta": False}).allowed
    assert not detect_traffic(cfg, lambda: (0, "", ""), {"Ethernet": True}).allowed


def test_routing_mode_does_not_enable_gate():
    state = detect_traffic({"mode": "global", "tun": {"enable": False}}, lambda: (0, "", ""), {})
    assert not state.allowed


def test_redactor_removes_secret():
    redactor = RedactingFilter()
    redactor.secrets.add("mock-test-secret")
    record = logging.LogRecord("test", logging.INFO, "", 0, "key mock-test-secret Authorization Bearer another-test", (), None)
    redactor.filter(record)
    assert "mock-test-secret" not in record.getMessage() and "another-test" not in record.getMessage()
