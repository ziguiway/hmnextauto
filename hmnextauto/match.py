# -*- coding: utf-8 -*-
"""
Match patterns for ``On.text`` / ``On.type`` / etc., aligned with
``@ohos.UiTest`` :js:class:`MatchPattern` (``On.text("x", MatchPattern.CONTAINS)`` in TS).

Int values follow common uitest wire format; if your device expects different numbers,
import :class:`MatchPattern` and adjust before calling, or set environment-specific patches.
"""
from enum import IntEnum
from typing import Dict, Optional, Tuple

__all__ = [
    "MatchPattern",
    "RESOLVED_SELECTOR_KEY",
    "is_selector_key",
    "FALLBACK_ON_ALTERNATE_NAME",
    "on_args",
]

# (base_on_name, pattern) -> alternate 1-argument method name (no "On." prefix)
# used when two-argument form is unsupported on a given device agent
FALLBACK_ON_ALTERNATE_NAME = {
    ("text", 1): "textContains",  # CONTAINS
    ("text", 4): "textMatches",  # REGEX
    ("type", 1): "typeContains",
    ("type", 4): "typeMatch",
    ("description", 1): "descriptionContains",
    ("description", 4): "descriptionMatch",
    ("id", 1): "idContains",
    ("id", 4): "idMatch",
    ("key", 1): "keyContains",
    ("key", 4): "keyMatch",
}


class MatchPattern(IntEnum):
    """Second argument to ``On.<attr>(value, pattern)`` when the native API uses two parameters."""

    EQUALS = 0
    CONTAINS = 1
    STARTS_WITH = 2
    ENDS_WITH = 3
    REGEX = 4
    # Some builds expose a fuzzy or glob mode; try last if using fallbacks
    FUZZY = 5


# user keyword -> (On-API attribute name, optional MatchPattern)
# bool attributes use (name, None) and pass a bool value
_RESOLVE: Dict[str, Tuple[str, Optional[MatchPattern]]] = {
    # text
    "text": ("text", None),
    "textContains": ("text", MatchPattern.CONTAINS),
    "textMatches": ("text", MatchPattern.REGEX),
    "textStartsWith": ("text", MatchPattern.STARTS_WITH),
    "textEndsWith": ("text", MatchPattern.ENDS_WITH),
    # description (content description / desc)
    "description": ("description", None),
    "descriptionContains": ("description", MatchPattern.CONTAINS),
    "descriptionMatches": ("description", MatchPattern.REGEX),
    "descriptionStartsWith": ("description", MatchPattern.STARTS_WITH),
    "descriptionEndsWith": ("description", MatchPattern.ENDS_WITH),
    # type / uiautomator2 "className"
    "type": ("type", None),
    "typeContains": ("type", MatchPattern.CONTAINS),
    "typeMatches": ("type", MatchPattern.REGEX),
    "className": ("type", None),
    "classNameContains": ("type", MatchPattern.CONTAINS),
    "classNameMatches": ("type", MatchPattern.REGEX),
    # id / key (resource id on OH)
    "id": ("id", None),
    "idContains": ("id", MatchPattern.CONTAINS),
    "idMatches": ("id", MatchPattern.REGEX),
    "key": ("key", None),
    "keyContains": ("key", MatchPattern.CONTAINS),
    "keyMatches": ("key", MatchPattern.REGEX),
    "resourceId": ("id", None),
    "resourceIdContains": ("id", MatchPattern.CONTAINS),
    "resourceIdMatches": ("id", MatchPattern.REGEX),
    # state flags
    "clickable": ("clickable", None),
    "longClickable": ("longClickable", None),
    "scrollable": ("scrollable", None),
    "enabled": ("enabled", None),
    "focused": ("focused", None),
    "selected": ("selected", None),
    "checked": ("checked", None),
    "checkable": ("checkable", None),
    "visible": ("visible", None),
    "password": ("password", None),
}

RESOLVED_SELECTOR_KEY = frozenset(_RESOLVE.keys())


def is_selector_key(name: str) -> bool:
    return name in _RESOLVE


def resolve_on_call(key: str) -> Tuple[str, Optional[MatchPattern]]:
    if key not in _RESOLVE:
        raise KeyError(key)
    return _RESOLVE[key]


def on_args(value, pattern: Optional[MatchPattern]) -> list:
    if pattern is None:
        return [value]
    return [value, int(pattern)]
