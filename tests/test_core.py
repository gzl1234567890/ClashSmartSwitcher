import threading

import pytest

from smart_switcher.api import ApiError
from smart_switcher.config import Settings
from smart_switcher.core import Measurement, SwitchEngine, choose_target, group_members
from smart_switcher.regions import excluded_region
from smart_switcher.status import TrafficState
from tests.fakes import FakeClient


def engine(allowed=True):
    return SwitchEngine(lambda configs: TrafficState(allowed, False))


def run(client, subject=None, **changes):
    return (subject or engine()).run(client, Settings(group="组", minimum_switch_seconds=0, **changes), threading.Event(), True)


@pytest.mark.parametrize("delay", [80, 120])
def test_at_or_below_threshold_keeps(delay):
    client = FakeClient({"美国": delay, "德国": 50})
    assert not run(client).switched
    assert not client.writes


@pytest.mark.parametrize("delay", [121, 185])
def test_above_threshold_switches(delay):
    client = FakeClient({"美国": delay, "德国": 80})
    result = run(client)
    assert result.switched and result.current == "德国"
    assert client.writes == [("组", "德国")]


@pytest.mark.parametrize("name", ["香港", "HK01", "Hong Kong 01", "HongKong", "HKG-2", "🇭🇰 香港", "新加坡", "SG1", "Singapore", "SIN 2", "🇸🇬节点"])
def test_region_aliases(name):
    assert excluded_region(name, ["香港", "新加坡"])


@pytest.mark.parametrize("name", ["美国 ASGARD", "德国 HKEY", "日本 SINGER", "Washington", "英国 THK", "俄罗斯 MSGraph", "SGermany"])
def test_region_does_not_match_letters_inside_words(name):
    assert excluded_region(name, ["香港", "新加坡"]) is None


@pytest.mark.parametrize("name", ["香港 HK", "Singapore SG"])
def test_fastest_excluded_never_target(name):
    client = FakeClient({"美国": 185, name: 10, "德国": 80})
    assert run(client).current == "德国"


def test_current_excluded_under_threshold_still_kept():
    client = FakeClient({"香港 HK": 80, "德国": 60}, current="香港 HK")
    assert not run(client).switched


def test_all_failed_keeps_and_warns():
    client = FakeClient({"美国": None, "德国": None})
    result = run(client)
    assert "均不可用" in result.message and not client.writes


def test_current_failed_chooses_available():
    assert run(FakeClient({"美国": None, "德国": 80})).current == "德国"


def test_current_is_best_does_not_switch_to_self():
    client = FakeClient({"美国": 185, "德国": 190})
    assert "最低延迟" in run(client).message
    assert not client.writes


def test_high_latency_target_is_allowed_with_warning():
    result = run(FakeClient({"美国": 250, "德国": 180}))
    assert result.switched and "仍然较高" in result.message


def test_failed_write_never_reports_success_and_rereads():
    client = FakeClient(switch_error=True)
    result = run(client)
    assert not result.switched and result.current == "美国" and "请求失败" in result.message


def test_successful_request_without_actual_change_is_failure():
    result = run(FakeClient(apply_switch=False))
    assert not result.switched and "尚未确认" in result.message


def test_manual_change_during_round_is_respected():
    client = FakeClient(manual_after_read=True)
    result = run(client)
    assert not result.switched and result.current == "德国"
    assert not client.writes


def test_latest_current_is_read_each_round():
    client = FakeClient()
    subject = engine()
    assert run(client, subject).switched
    client.current = "美国"
    assert run(client, subject).switched


def test_only_direct_nodes_in_selected_group_are_tested():
    client = FakeClient()
    run(client)
    assert set(client.tests) == set(client.delays)
    assert "其他组节点" not in client.tests and "DIRECT" not in client.tests


def test_current_nested_group_prevents_automatic_switch():
    client = FakeClient(current="子组")
    result = run(client)
    assert not result.switched and "嵌套" in result.message


def test_no_traffic_rejects_before_tests():
    client = FakeClient()
    with pytest.raises(ApiError, match="系统代理"):
        run(client, engine(False))
    assert not client.tests and not client.writes


def test_cancelled_round_cannot_switch():
    cancel = threading.Event()
    cancel.set()
    client = FakeClient()
    result = engine().run(client, Settings(group="组"), cancel, True)
    assert not result.switched and not client.writes and not client.tests


def test_one_round_at_a_time():
    subject = engine()
    subject.round_lock.acquire()
    with pytest.raises(ApiError, match="上一轮"):
        run(FakeClient(), subject)
    subject.round_lock.release()


def test_minimum_switch_interval():
    subject = engine()
    client = FakeClient()
    settings = Settings(group="组", minimum_switch_seconds=60)
    assert subject.run(client, settings, threading.Event(), True).switched
    client.current = "美国"
    result = subject.run(client, settings, threading.Event(), True)
    assert not result.switched and "最小切换间隔" in result.message


def test_measure_only_cannot_switch():
    client = FakeClient()
    result = engine().run(client, Settings(group="组"), threading.Event(), False)
    assert not client.writes and not result.switched and "仅测速" in result.message


def test_non_selector_group_rejected():
    with pytest.raises(ApiError, match="Selector"):
        group_members("子组", FakeClient().proxies())
