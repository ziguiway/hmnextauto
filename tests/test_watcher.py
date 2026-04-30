# -*- coding: utf-8 -*-
import time
from unittest.mock import MagicMock

import pytest

from hmnextauto._watcher import WatcherManager


@pytest.fixture
def manager():
    d = MagicMock()
    m = WatcherManager(d)
    return m, d


def test_watcher_when_click_registers(manager):
    w, d = manager
    w("ok").when(text="确定").click()
    assert w.rule_names == ["ok"]
    assert len(w) == 1
    w.remove("ok")
    assert w.rule_names == []


def test_watcher_replace_same_name(manager):
    w, _ = manager
    w("a").when(text="1").click()
    w("a").when(text="2").click()
    assert len(w) == 1
    assert w.rule_names == ["a"]


def test_watcher_when_xpath(manager):
    w, _ = manager
    w("x").when_xpath('//Button').press_back()
    assert w.rule_names == ["x"]
    assert len(w) == 1


def test_watcher_when_empty_raises(manager):
    w, _ = manager
    with pytest.raises(ValueError, match="at least one"):
        w("a").when()
    with pytest.raises(ValueError, match="call when"):
        w("a").click()


def test_watcher_start_stop_thread(manager):
    w, d = manager
    d.__call__ = MagicMock(return_value=MagicMock(exists=MagicMock(return_value=False)))
    w("a").when(text="x").click()
    w.start(interval=0.05)
    assert w.running
    time.sleep(0.15)
    w.stop()
    time.sleep(0.05)
    assert not w.running
