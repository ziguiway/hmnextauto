# -*- coding: utf-8 -*-

from hmnextauto.driver import _bundle_label_from_info, Driver


def test_bundle_label_from_info_kuaishou_shape():
    info = {
        "applicationInfo": {
            "bundleName": "com.kuaishou.hmapp",
            "vendor": "快手",
        },
        "vendor": "快手",
    }
    assert _bundle_label_from_info(info) == "快手"


def test_display_name_matched():
    assert Driver._display_name_matched("快", "快手", "contains", True) is True
    assert Driver._display_name_matched("ab", "AbX", "contains", True) is True
    assert Driver._display_name_matched("ab", "Xab", "startswith", True) is False
    assert Driver._display_name_matched("^a", "ab", "regex", False) is True
