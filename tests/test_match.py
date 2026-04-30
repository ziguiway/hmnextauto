# -*- coding: utf-8 -*-
import pytest

from hmnextauto.match import (
    MatchPattern,
    is_selector_key,
    on_args,
    resolve_on_call,
)


def test_is_selector_key():
    assert is_selector_key("textContains")
    assert is_selector_key("classNameMatches")
    assert is_selector_key("resourceId")
    assert not is_selector_key("nope")


def test_resolve_fuzzy():
    n, p = resolve_on_call("textContains")
    assert n == "text" and p == MatchPattern.CONTAINS
    n, p = resolve_on_call("textMatches")
    assert p == MatchPattern.REGEX
    n, p = resolve_on_call("className")
    assert n == "type" and p is None
    n, p = resolve_on_call("resourceIdMatches")
    assert n == "id" and p == MatchPattern.REGEX


def test_on_args():
    assert on_args("a", None) == ["a"]
    assert on_args("a", MatchPattern.CONTAINS) == ["a", int(MatchPattern.CONTAINS)]


def test_uiobject_rejects_conflicting_id_keys():
    from unittest.mock import MagicMock
    from hmnextauto._uiobject import UiObject

    with pytest.raises(ReferenceError, match="id.*resourceId"):
        UiObject(MagicMock(), id="a", resourceId="b")
