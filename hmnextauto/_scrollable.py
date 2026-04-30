# -*- coding: utf-8 -*-
"""
uiautomator2-style :attr:`UiObject.scroll` (``vert`` / ``horiz`` / ``to`` / ``fling``) using Hypium
``Component.*`` when the device build supports them, with in-``bounds`` :meth:`Driver.swipe` as fallback.
"""
from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING, Any, Tuple

from . import logger
from .exception import InvokeHypiumError
from .utils import delay
from .proto import ByData

if TYPE_CHECKING:
    from ._uiobject import UiObject

_VERT_FORWARD: Tuple[str, ...] = (
    "Component.scrollForward",
    "Component.scrollNext",
    "Component.scrollDown",
)
_VERT_BACKWARD: Tuple[str, ...] = (
    "Component.scrollBackward",
    "Component.scrollPrevious",
    "Component.scrollUp",
)
_HORIZ_FORWARD: Tuple[str, ...] = (
    "Component.horizScrollForward",
    "Component.scrollHorizForward",
    "Component.horizForward",
    "Component.scrollLeft",
)
_HORIZ_BACKWARD: Tuple[str, ...] = (
    "Component.horizScrollBackward",
    "Component.scrollHorizBackward",
    "Component.horizBackward",
    "Component.scrollRight",
)
_TO_START: Tuple[str, ...] = (
    "Component.scrollToTop",
    "Component.scrollToBeginning",
)
_TO_END: Tuple[str, ...] = (
    "Component.scrollToBottom",
    "Component.scrollToEnd",
)
_SCROLL_SEARCH: Tuple[str, ...] = (
    "Component.scrollSearch",
    "Component.findAndScroll",
    "Component.scrollTo",
)
_VERT_FLING: Tuple[str, ...] = (
    "Component.fling",
    "Component.flingVertically",
    "Component.flingUp",
)
_HORIZ_FLING: Tuple[str, ...] = (
    "Component.flingHorizontally",
    "Component.horizFling",
    "Component.flingLeft",
)


def _swipe_in_bounds(
    uio: "UiObject",
    direction: str,
    speed: int = 2000,
    extent: float = 0.72,
) -> None:
    b = uio.bounds
    w = b.right - b.left
    h = b.bottom - b.top
    if w < 2 or h < 2:
        return
    cx = (b.left + b.right) // 2
    cy = (b.top + b.bottom) // 2
    marginx = max(2, int(w * (1 - extent) / 2))
    marginy = max(2, int(h * (1 - extent) / 2))
    if direction == "up":  # finger from bottom to top: show lower content
        x1, y1 = cx, b.bottom - marginy
        x2, y2 = cx, b.top + marginy
    elif direction == "down":
        x1, y1 = cx, b.top + marginy
        x2, y2 = cx, b.bottom - marginy
    elif direction == "left":
        x1, y1 = b.right - marginx, cy
        x2, y2 = b.left + marginx, cy
    elif direction == "right":
        x1, y1 = b.left + marginx, cy
        x2, y2 = b.right - marginx, cy
    else:
        raise ValueError("direction must be up/down/left/right")
    uio._client.invoke(  # noqa: SLF001
        "Driver.swipe", this="Driver#0", args=[x1, y1, x2, y2, speed]
    )


def _try_component_apis(
    uio: "UiObject", apis: Tuple[str, ...], arg_variants: List[list]
) -> bool:
    uio.find_component()
    for api in apis:
        for args in arg_variants:
            try:
                uio._client.invoke(  # noqa: SLF001
                    api, this=uio._component.value, args=args
                )
                return True
            except InvokeHypiumError as e:
                logger.debug("%s%r: %s", api, args, e)
    return False


def _search_native(uio: "UiObject", by: ByData) -> bool:
    for api in _SCROLL_SEARCH:
        if _try_component_apis(uio, (api,), [[by.value]]):
            return True
    return False


class _Axis:
    def __init__(self, uio: "UiObject", name: str) -> None:
        self._o = uio
        self._name = name  # "vert" | "horiz"

    @delay
    def forward(
        self, steps: int = 1, speed: int = 2000, extent: float = 0.72
    ) -> bool:
        n = max(1, int(steps))
        sp = int(max(200, min(40000, speed)))
        for _ in range(n):
            u = self._o
            if not u.find_component():
                return False
            if self._name == "vert":
                if not _try_component_apis(
                    u, _VERT_FORWARD, [[], [sp], [sp, 0]]
                ):
                    _swipe_in_bounds(u, "up", speed=sp, extent=extent)
            else:
                if not _try_component_apis(u, _HORIZ_FORWARD, [[], [sp]]):
                    _swipe_in_bounds(u, "left", speed=sp, extent=extent)
        return True

    @delay
    def backward(
        self, steps: int = 1, speed: int = 2000, extent: float = 0.72
    ) -> bool:
        n = max(1, int(steps))
        sp = int(max(200, min(40000, speed)))
        for _ in range(n):
            u = self._o
            if not u.find_component():
                return False
            if self._name == "vert":
                if not _try_component_apis(u, _VERT_BACKWARD, [[], [sp]]):
                    _swipe_in_bounds(u, "down", speed=sp, extent=extent)
            else:
                if not _try_component_apis(u, _HORIZ_BACKWARD, [[], [sp]]):
                    _swipe_in_bounds(u, "right", speed=sp, extent=extent)
        return True

    @delay
    def fling(
        self, speed: int = 5000, extent: float = 0.9
    ) -> bool:
        u = self._o
        if not u.find_component():
            return False
        sp = int(max(200, min(40000, speed)))
        apis = _VERT_FLING if self._name == "vert" else _HORIZ_FLING
        if not _try_component_apis(u, apis, [[sp], [sp, 0], []]):
            if self._name == "vert":
                _swipe_in_bounds(u, "up", speed=sp, extent=extent)
            else:
                _swipe_in_bounds(u, "left", speed=sp, extent=extent)
        return True


class UiScroll:
    """
    Similar to uiautomator2's scroll helper: use ``.vert`` / ``.horiz`` for axis,
    or ``.to`` / ``.toBeginning`` / ``.toEnd`` for list navigation.
    """

    def __init__(self, uio: "UiObject") -> None:
        self._o = uio
        self.vert: _Axis = _Axis(uio, "vert")
        self.horiz: _Axis = _Axis(uio, "horiz")

    @delay
    def toBeginning(  # noqa: N802
        self, speed: int = 2000, max_strokes: int = 8
    ) -> bool:
        u = self._o
        if not u.find_component():
            return False
        if _try_component_apis(
            u, _TO_START, [[], [speed], [speed, 0]]
        ):
            return True
        m = max(1, int(max_strokes))
        for _ in range(m):
            _swipe_in_bounds(u, "down", speed=speed, extent=0.85)
        return True

    @delay
    def toEnd(self, speed: int = 2000, max_strokes: int = 8) -> bool:  # noqa: N802
        u = self._o
        if not u.find_component():
            return False
        if _try_component_apis(
            u, _TO_END, [[], [speed], [speed, 0]]
        ):
            return True
        m = max(1, int(max_strokes))
        for _ in range(m):
            _swipe_in_bounds(u, "up", speed=speed, extent=0.85)
        return True

    @delay
    def to(  # pylint: disable=invalid-name
        self, max_swipes: int = 20, **kwargs: Any
    ) -> bool:
        u = self._o
        if not u.find_component():
            return False
        from ._uiobject import UiObject  # import here to break circular import

        target = UiObject(u._client, **kwargs)  # noqa: SLF001
        if target.exists(retries=1, wait_time=0):
            return True
        by: ByData = target._by_data()  # noqa: SLF001
        if _search_native(u, by) and target.exists(1, 0):
            return True
        m = max(1, int(max_swipes))
        for _ in range(m):
            if target.exists(retries=1, wait_time=0):
                return True
            _swipe_in_bounds(u, "up", speed=2200, extent=0.78)
        return bool(target.exists(1, 0))

    @delay
    def fling(
        self, direction: str = "vert", speed: int = 5000, extent: float = 0.9
    ) -> bool:
        ax = _Axis(
            self._o, "vert" if str(direction) != "horiz" else "horiz"
        )
        return ax.fling(speed=speed, extent=extent)
