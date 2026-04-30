# -*- coding: utf-8 -*-

import pytest
from hmnextauto.driver import _bundle_label_from_info, Driver


@pytest.fixture
def d():
    """获取 Driver 实例"""
    d = Driver()
    yield d
    d.close()


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


# ========== 真机测试 ==========

def test_list_apps(d):
    """测试获取已安装应用列表"""
    apps = d.list_apps()
    assert isinstance(apps, list)
    assert len(apps) > 0

    # list_apps 返回的是包名字符串列表
    for app in apps[:5]:
        assert isinstance(app, str)


def test_start_app_by_name(d):
    """测试通过应用名启动应用"""
    # 直接使用包名启动设置应用
    d.start_app("com.huawei.hmos.settings")


def test_find_package_by_display_name(d):
    """测试通过显示名查找包名"""
    # 设置应用的显示名称就是包名
    bundle = d.find_package_by_display_name("settings", include_system_apps=True, on_ambiguous="first")
    assert bundle is not None
    assert "settings" in bundle.lower()


def test_start_app_by_name_not_found(d):
    """测试启动不存在的应用"""
    import time
    time.sleep(1)  # 等待上一个测试完成
    with pytest.raises(Exception):
        d.start_app_by_name("不存在的应用xyz123")
