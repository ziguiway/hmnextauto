# -*- coding: utf-8 -*-

import time
from typing import List, Optional, Union

from . import logger
from .utils import delay
from ._client import HmClient
from .exception import ElementNotFoundError, InvokeHypiumError
from .match import (
    MatchPattern,
    is_selector_key,
    on_args,
    resolve_on_call,
    FALLBACK_ON_ALTERNATE_NAME,
)
from .proto import ComponentData, ByData, HypiumResponse, Point, Bounds, ElementInfo


class UiObject:
    # exists(retries, wait_time) fallbacks; see method docstring
    DEFAULT_TIMEOUT = 2
    # uiautomator2: wait / wait_gone default, seconds
    DEFAULT_WAIT_TIMEOUT = 20.0
    _WAIT_POLL_INTERVAL = 0.1

    def __init__(self, client: HmClient, **kwargs) -> None:
        self._client = client
        self._raw_kwargs = kwargs

        self._index = kwargs.pop("index", 0)
        self._isBefore = kwargs.pop("isBefore", False)
        self._isAfter = kwargs.pop("isAfter", False)

        self._kwargs = kwargs
        self.__verify()

        self._component: Union[ComponentData, None] = None  # cache

    def __str__(self) -> str:
        return f"UiObject [{self._raw_kwargs}"

    def __verify(self):
        for k, v in self._kwargs.items():
            if not is_selector_key(k):
                raise ReferenceError(
                    f"{k} is not a supported selector. "
                    f"See hmnextauto.match.RESOLVED_SELECTOR_KEY for uiautomator2-style textContains, textMatches, …"
                )
        if "id" in self._kwargs and "resourceId" in self._kwargs:
            raise ReferenceError("use only one of `id` and `resourceId`")
        if "type" in self._kwargs and "className" in self._kwargs:
            raise ReferenceError("use only one of `type` and `className`")

    def _invoke_on(self, on_name: str, value, pattern: Optional[MatchPattern], this: str = "On#seed") -> str:
        last_err: Optional[Exception] = None
        arg_lists: List[list] = [on_args(value, pattern)]
        if pattern is not None:
            arg_lists.append([value, str(pattern.name)])
            arg_lists.append([value, pattern.name.lower()])
        for args in arg_lists:
            try:
                resp: HypiumResponse = self._client.invoke(
                    f"On.{on_name}", this=this, args=args
                )
                return resp.result
            except InvokeHypiumError as e:
                last_err = e
                logger.debug("On.%s%r: %s", on_name, args, e)
        if pattern is not None:
            alt = FALLBACK_ON_ALTERNATE_NAME.get((on_name, int(pattern)))
            if alt:
                try:
                    r = self._client.invoke(
                        f"On.{alt}", this=this, args=[value]
                    )
                    return r.result
                except InvokeHypiumError as e:
                    last_err = e
                    logger.debug("On.%s([%r]): %s", alt, value, e)
        if last_err:
            raise last_err
        raise RuntimeError(f"On.{on_name} failed")

    @property
    def count(self) -> int:
        eleements = self.__find_components()
        return len(eleements) if eleements else 0

    def __len__(self):
        return self.count

    def exists(self, retries: int = 2, wait_time=1) -> bool:
        obj = self.find_component(retries, wait_time)
        return True if obj else False

    def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Block until a component matching this selector (and :attr:`index`) is found, or the timeout elapses.

        Semantics are similar to uiautomator2's ``UiObject.wait()`` (timeout in **seconds**, returns ``bool``).

        Args:
            timeout: Maximum time to wait in seconds. Defaults to :data:`DEFAULT_WAIT_TIMEOUT`.

        Returns:
            True if a matching component appeared in time, False otherwise.
        """
        if timeout is None:
            timeout = self.DEFAULT_WAIT_TIMEOUT
        deadline = time.time() + max(0.0, timeout)
        while True:
            components = self.__find_components()
            if components and self._index < len(components):
                self.__set_component(components[self._index])
                return True
            if time.time() >= deadline:
                return False
            time.sleep(self._WAIT_POLL_INTERVAL)

    def wait_gone(self, timeout: Optional[float] = None) -> bool:
        """
        Block until this selector no longer matches (at least ``index + 1`` results), or the timeout elapses.

        Similar to uiautomator2's ``UiObject.wait_gone()``. If the target is already absent, returns True
        immediately.

        Args:
            timeout: Maximum time to wait in seconds. Defaults to :data:`DEFAULT_WAIT_TIMEOUT`.

        Returns:
            True if the element became absent (or was never present) before timeout, False if it is still
            there when the wait ends.
        """
        if timeout is None:
            timeout = self.DEFAULT_WAIT_TIMEOUT
        deadline = time.time() + max(0.0, timeout)
        while True:
            if not self.exists(retries=1, wait_time=0):
                return True
            if time.time() >= deadline:
                return False
            time.sleep(self._WAIT_POLL_INTERVAL)

    def wait_enabled(self, timeout: Optional[float] = None) -> bool:
        """
        等待元素变为可用状态（enabled=True）。

        Args:
            timeout: 最大等待时间（秒），默认 20.0

        Returns:
            True 如果元素在超时前变为可用，False 否则
        """
        if timeout is None:
            timeout = self.DEFAULT_WAIT_TIMEOUT
        deadline = time.time() + max(0.0, timeout)
        while True:
            components = self.__find_components()
            if components and self._index < len(components):
                self.__set_component(components[self._index])
                if self.isEnabled:
                    return True
            if time.time() >= deadline:
                return False
            time.sleep(self._WAIT_POLL_INTERVAL)

    def wait_disabled(self, timeout: Optional[float] = None) -> bool:
        """
        等待元素变为禁用状态（enabled=False）。

        Args:
            timeout: 最大等待时间（秒），默认 20.0

        Returns:
            True 如果元素在超时前变为禁用，False 否则
        """
        if timeout is None:
            timeout = self.DEFAULT_WAIT_TIMEOUT
        deadline = time.time() + max(0.0, timeout)
        while True:
            components = self.__find_components()
            if components and self._index < len(components):
                self.__set_component(components[self._index])
                if not self.isEnabled:
                    return True
            if time.time() >= deadline:
                return False
            time.sleep(self._WAIT_POLL_INTERVAL)

    def wait_clickable(self, timeout: Optional[float] = None) -> bool:
        """
        等待元素变为可点击状态（clickable=True）。

        Args:
            timeout: 最大等待时间（秒），默认 20.0

        Returns:
            True 如果元素在超时前变为可点击，False 否则
        """
        if timeout is None:
            timeout = self.DEFAULT_WAIT_TIMEOUT
        deadline = time.time() + max(0.0, timeout)
        while True:
            components = self.__find_components()
            if components and self._index < len(components):
                self.__set_component(components[self._index])
                if self.isClickable:
                    return True
            if time.time() >= deadline:
                return False
            time.sleep(self._WAIT_POLL_INTERVAL)

    def wait_until(
        self,
        condition: callable,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        等待自定义条件满足。

        Args:
            condition: 条件函数，接收 ElementInfo 对象，返回 bool
            timeout: 最大等待时间（秒），默认 20.0

        Returns:
            True 如果条件在超时前满足，False 否则

        Example:
            # 等待文本变为 "完成"
            d(id="status").wait_until(lambda e: e.text == "完成")

            # 等待元素被选中
            d(id="checkbox").wait_until(lambda e: e.isChecked)
        """
        if timeout is None:
            timeout = self.DEFAULT_WAIT_TIMEOUT
        deadline = time.time() + max(0.0, timeout)
        while True:
            components = self.__find_components()
            if components and self._index < len(components):
                self.__set_component(components[self._index])
                try:
                    if condition(self.info):
                        return True
                except Exception as e:
                    logger.debug(f"Condition check failed: {e}")
            if time.time() >= deadline:
                return False
            time.sleep(self._WAIT_POLL_INTERVAL)

    def wait_until_not(
        self,
        condition: callable,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        等待自定义条件不再满足。

        Args:
            condition: 条件函数，接收 ElementInfo 对象，返回 bool
            timeout: 最大等待时间（秒），默认 20.0

        Returns:
            True 如果条件在超时前不再满足，False 否则
        """
        if timeout is None:
            timeout = self.DEFAULT_WAIT_TIMEOUT
        deadline = time.time() + max(0.0, timeout)
        while True:
            components = self.__find_components()
            if components and self._index < len(components):
                self.__set_component(components[self._index])
                try:
                    if not condition(self.info):
                        return True
                except Exception as e:
                    logger.debug(f"Condition check failed: {e}")
                    return True  # 元素不存在或出错时，条件不满足
            else:
                # 元素不存在
                return True
            if time.time() >= deadline:
                return False
            time.sleep(self._WAIT_POLL_INTERVAL)

    def __set_component(self, component: ComponentData):
        self._component = component

    def find_component(self, retries: int = 1, wait_time=1) -> ComponentData:
        for attempt in range(retries):
            components = self.__find_components()
            if components and self._index < len(components):
                self.__set_component(components[self._index])
                return self._component

            if attempt < retries:
                time.sleep(wait_time)
                logger.info(f"Retry found element {self}")

        return None

    # useless
    def __find_component(self) -> Union[ComponentData, None]:
        by: ByData = self.__get_by()
        resp: HypiumResponse = self._client.invoke("Driver.findComponent", args=[by.value])
        if not resp.result:
            return None
        return ComponentData(resp.result)

    def __find_components(self) -> Union[List[ComponentData], None]:
        by: ByData = self.__get_by()
        resp: HypiumResponse = self._client.invoke("Driver.findComponents", args=[by.value])
        if not resp.result:
            return None
        components: List[ComponentData] = []
        for item in resp.result:
            components.append(ComponentData(item))

        return components

    def _by_data(self) -> ByData:
        """Build the Hypium ``On``/``By`` handle for this selector (for e.g. :attr:`scroll`)."""
        return self.__get_by()

    def __get_by(self) -> ByData:
        this = "On#seed"
        for k, v in self._kwargs.items():
            on_name, pat = resolve_on_call(k)
            this = self._invoke_on(on_name, v, pat, this)

        if self._isBefore:
            resp: HypiumResponse = self._client.invoke(
                "On.isBefore", this="On#seed", args=[this]
            )
            this = resp.result

        if self._isAfter:
            resp: HypiumResponse = self._client.invoke(
                "On.isAfter", this="On#seed", args=[this]
            )
            this = resp.result

        return ByData(this)

    def __operate(self, api, args=[], retries: int = 2):
        if not self._component:
            if not self.find_component(retries):
                raise ElementNotFoundError(f"Element({self}) not found after {retries} retries")

        resp: HypiumResponse = self._client.invoke(api, this=self._component.value, args=args)
        return resp.result

    @property
    def scroll(self):
        """uiautomator2-style list scroller: ``.vert`` / ``.horiz`` / ``.to`` / ``.toBeginning`` / ``.toEnd``."""
        from ._scrollable import UiScroll
        return UiScroll(self)

    @property
    def id(self) -> str:
        return self.__operate("Component.getId")

    @property
    def key(self) -> str:
        return self.__operate("Component.getId")

    @property
    def type(self) -> str:
        return self.__operate("Component.getType")

    @property
    def text(self) -> str:
        return self.__operate("Component.getText")

    @property
    def description(self) -> str:
        return self.__operate("Component.getDescription")

    @property
    def isSelected(self) -> bool:
        return self.__operate("Component.isSelected")

    @property
    def isChecked(self) -> bool:
        return self.__operate("Component.isChecked")

    @property
    def isEnabled(self) -> bool:
        return self.__operate("Component.isEnabled")

    @property
    def isFocused(self) -> bool:
        return self.__operate("Component.isFocused")

    @property
    def isCheckable(self) -> bool:
        return self.__operate("Component.isCheckable")

    @property
    def isClickable(self) -> bool:
        return self.__operate("Component.isClickable")

    @property
    def isLongClickable(self) -> bool:
        return self.__operate("Component.isLongClickable")

    @property
    def isScrollable(self) -> bool:
        return self.__operate("Component.isScrollable")

    @property
    def bounds(self) -> Bounds:
        _raw = self.__operate("Component.getBounds")
        _raw = {k: v for k, v in _raw.items() if k in {"bottom", "left", "right", "top"}}
        return Bounds(**_raw)

    @property
    def boundsCenter(self) -> Point:
        _raw = self.__operate("Component.getBoundsCenter")
        _raw = {k: v for k, v in _raw.items() if k in {"x", "y"}}
        return Point(**_raw)

    @property
    def info(self) -> ElementInfo:
        return ElementInfo(
            id=self.id,
            key=self.key,
            type=self.type,
            text=self.text,
            description=self.description,
            isSelected=self.isSelected,
            isChecked=self.isChecked,
            isEnabled=self.isEnabled,
            isFocused=self.isFocused,
            isCheckable=self.isCheckable,
            isClickable=self.isClickable,
            isLongClickable=self.isLongClickable,
            isScrollable=self.isScrollable,
            bounds=self.bounds,
            boundsCenter=self.boundsCenter)

    @delay
    def click(self):
        return self.__operate("Component.click")

    @delay
    def click_if_exists(self):
        try:
            return self.__operate("Component.click")
        except ElementNotFoundError:
            pass

    @delay
    def double_click(self):
        return self.__operate("Component.doubleClick")

    @delay
    def long_click(self):
        return self.__operate("Component.longClick")

    @delay
    def drag_to(self, component: ComponentData):
        return self.__operate("Component.dragTo", [component.value])

    @delay
    def input_text(self, text: str):
        return self.__operate("Component.inputText", [text])

    @delay
    def clear_text(self):
        return self.__operate("Component.clearText")

    @delay
    def pinch_in(self, scale: float = 0.5):
        return self.__operate("Component.pinchIn", [scale])

    @delay
    def pinch_out(self, scale: float = 2):
        return self.__operate("Component.pinchOut", [scale])
