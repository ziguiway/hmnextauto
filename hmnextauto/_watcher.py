# -*- coding: utf-8 -*-
"""
PC-side background watcher: poll UI and run rules (uiautomator2-style usage, without new device protocol).

Example::

    d.watcher("ok").when(text="确定").click()
    d.watcher("x").when_xpath('//Button[@text="跳过"]').click()
    d.watcher.start(interval=0.3)
    # ... main flow ...
    d.watcher.stop()
    d.watcher.remove("ok")
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from . import logger

if TYPE_CHECKING:
    from .driver import Driver


@dataclass
class _Rule:
    name: str
    mode: str  # "selector" | "xpath"
    when_kwargs: Dict
    xpath: Optional[str]
    action: str  # "click" | "press_back" | "do"
    do_fn: Optional[Callable[[Any], None]] = None


class WatcherBuilder:
    def __init__(self, name: str, parent: "WatcherManager") -> None:
        self._name = name
        self._parent = parent
        self._mode: Optional[str] = None
        self._kwargs: Dict = {}
        self._xpath: Optional[str] = None

    def when(self, **kwargs) -> "WatcherBuilder":
        if not kwargs:
            raise ValueError("when() requires at least one selector keyword (same as d(...))")
        self._mode = "selector"
        self._kwargs = dict(kwargs)
        self._xpath = None
        return self

    def when_xpath(self, path: str) -> "WatcherBuilder":
        p = (path or "").strip()
        if not p:
            raise ValueError("when_xpath() requires a non-empty xpath string")
        self._mode = "xpath"
        self._xpath = p
        self._kwargs = {}
        return self

    def _require_match(self) -> None:
        if self._mode == "selector" and not self._kwargs:
            raise ValueError("call when() with at least one argument first")
        if self._mode == "xpath" and not self._xpath:
            raise ValueError("call when_xpath() first")
        if self._mode is None:
            raise ValueError("call when() or when_xpath() first")

    def click(self) -> "WatcherManager":
        self._require_match()
        self._parent._add_rule(
            _Rule(
                name=self._name,
                mode=self._mode,
                when_kwargs=self._kwargs,
                xpath=self._xpath,
                action="click",
            )
        )
        return self._parent

    def press_back(self) -> "WatcherManager":
        self._require_match()
        self._parent._add_rule(
            _Rule(
                name=self._name,
                mode=self._mode,
                when_kwargs=self._kwargs,
                xpath=self._xpath,
                action="press_back",
            )
        )
        return self._parent

    def do(self, fn: Callable[[Any], None]) -> "WatcherManager":
        self._require_match()
        if not callable(fn):
            raise TypeError("do() requires a callable")
        self._parent._add_rule(
            _Rule(
                name=self._name,
                mode=self._mode,
                when_kwargs=self._kwargs,
                xpath=self._xpath,
                action="do",
                do_fn=fn,
            )
        )
        return self._parent


class WatcherManager:
    """
    Register named rules via ``d.watcher(name)``, then :meth:`start` a daemon thread
    that polls the device and runs the first matching rule each cycle.
    """

    def __init__(self, driver: "Driver") -> None:
        self._d = driver
        self._rules: Dict[str, _Rule] = {}
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._interval = 0.3

    def __call__(self, name: str) -> WatcherBuilder:
        if not name or not str(name).strip():
            raise ValueError("watcher name must be non-empty")
        return WatcherBuilder(str(name), self)

    def _add_rule(self, rule: _Rule) -> None:
        with self._lock:
            self._rules[rule.name] = rule
        logger.debug("watcher register %r: %s", rule.name, rule)

    @property
    def rule_names(self) -> List[str]:
        with self._lock:
            return list(self._rules.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._rules)

    @property
    def running(self) -> bool:
        t = self._thread
        return bool(t and t.is_alive())

    def remove(self, name: str) -> bool:
        with self._lock:
            if name in self._rules:
                del self._rules[name]
                return True
        return False

    def clear(self) -> None:
        with self._lock:
            self._rules.clear()

    def start(self, interval: float = 0.3) -> "WatcherManager":
        self._interval = max(0.05, float(interval))
        with self._lock:
            if self._thread and self._thread.is_alive():
                logger.warning("Watcher is already started (interval unchanged if you need a new value, stop() first)")
                return self
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="hmnextauto-watcher", daemon=True
        )
        self._thread.start()
        return self

    def stop(self, join_timeout: float = 2.0) -> None:
        self._stop.set()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=join_timeout)
        self._thread = None

    def _apply_rule(self, rule: _Rule) -> bool:
        d: Any = self._d
        if rule.mode == "selector":
            obj = d(**rule.when_kwargs)
            if not obj.exists(retries=1, wait_time=0):
                return False
        elif rule.mode == "xpath":
            el = d.xpath(rule.xpath)
            if not el.exists():
                return False
        else:
            return False

        if rule.action == "click":
            if rule.mode == "selector":
                d(**rule.when_kwargs).click()
            else:
                d.xpath(rule.xpath).click()
        elif rule.action == "press_back":
            d.go_back()
        elif rule.action == "do" and rule.do_fn is not None:
            rule.do_fn(d)
        return True

    def _loop(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                items: List[_Rule] = list(self._rules.values())
            for rule in items:
                if self._stop.is_set():
                    break
                try:
                    if self._apply_rule(rule):
                        logger.info("watcher matched rule %r", rule.name)
                        break
                except Exception as e:
                    logger.exception("watcher rule %r error: %s", rule.name, e)
            if self._stop.wait(self._interval):
                break
