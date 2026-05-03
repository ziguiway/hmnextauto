# -*- coding: utf-8 -*-
"""
全局隐式等待测试
测试: Settings, implicitly_wait, 全局超时在 UiObject 和 XPath 中的生效
"""

import time
import pytest
from hmnextauto.driver import Driver


@pytest.fixture
def d():
    """获取 Driver 实例"""
    d = Driver()
    yield d
    d.close()
    Driver._instance.clear()


def test_settings_defaults(d):
    """测试默认设置值"""
    assert d.settings["wait_timeout"] == 20.0
    assert d.settings["poll_interval"] == 0.1
    assert d.settings["operation_delay"] == (0, 0)


def test_settings_getitem(d):
    """测试 Settings 字典式访问"""
    assert d.settings["wait_timeout"] == 20.0
    d.settings["wait_timeout"] = 10.0
    assert d.settings["wait_timeout"] == 10.0


def test_settings_get(d):
    """测试 Settings.get 方法"""
    assert d.settings.get("wait_timeout") == 20.0
    assert d.settings.get("nonexistent", 42) == 42


def test_settings_invalid_key(d):
    """测试设置不存在的 key 抛出异常"""
    with pytest.raises(KeyError):
        d.settings["invalid_key"] = 1


def test_implicitly_wait_get(d):
    """测试获取隐式等待值"""
    value = d.implicitly_wait()
    assert value == 20.0


def test_implicitly_wait_set(d):
    """测试设置隐式等待值"""
    d.implicitly_wait(5.0)
    assert d.implicitly_wait() == 5.0

    d.implicitly_wait(10)
    assert d.implicitly_wait() == 10


def test_uiobject_wait_uses_global_timeout(d):
    """测试 UiObject.wait() 使用全局超时"""
    d.implicitly_wait(3.0)

    start = time.time()
    result = d(text="NonExistentElement12345").wait()
    elapsed = time.time() - start

    assert result is False
    assert 2.0 <= elapsed <= 5.0, f"elapsed={elapsed:.1f}s, expected ~3s"


def test_uiobject_wait_explicit_overrides_global(d):
    """测试显式 timeout 覆盖全局设置"""
    d.implicitly_wait(10.0)

    start = time.time()
    result = d(text="NonExistentElement12345").wait(timeout=1.0)
    elapsed = time.time() - start

    assert result is False
    assert elapsed <= 3.0, f"elapsed={elapsed:.1f}s, expected ~1s"


def test_uiobject_wait_gone_uses_global_timeout(d):
    """测试 UiObject.wait_gone() 使用全局超时"""
    d.implicitly_wait(1.0)

    # 不存在的元素，wait_gone 应立即返回 True
    start = time.time()
    result = d(text="NonExistentElement12345").wait_gone()
    elapsed = time.time() - start

    assert result is True
    assert elapsed <= 3.0


def test_xpath_wait_uses_global_timeout(d):
    """测试 XPath.wait() 使用全局超时"""
    d.implicitly_wait(3.0)

    start = time.time()
    result = d.xpath('//Text[@text="NonExistent12345"]').wait()
    elapsed = time.time() - start

    assert result is False
    # XPath 轮询开销较大（dumpLayout + 文件传输），放宽范围
    assert 2.0 <= elapsed <= 8.0, f"elapsed={elapsed:.1f}s, expected ~3s"


def test_xpath_wait_explicit_overrides_global(d):
    """测试 XPath 显式 timeout 覆盖全局"""
    d.implicitly_wait(10.0)

    start = time.time()
    result = d.xpath('//Text[@text="NonExistent12345"]').wait(timeout=1.0)
    elapsed = time.time() - start

    assert result is False
    assert elapsed <= 5.0, f"elapsed={elapsed:.1f}s, expected ~1s"


def test_implicitly_wait_multiple_changes(d):
    """测试多次修改隐式等待值"""
    d.implicitly_wait(5.0)
    assert d.implicitly_wait() == 5.0

    d.implicitly_wait(3.0)
    assert d.implicitly_wait() == 3.0

    d.implicitly_wait(1.0)
    assert d.implicitly_wait() == 1.0


if __name__ == "__main__":
    d = Driver()

    print("=" * 60)
    print("全局隐式等待测试")
    print("=" * 60)

    try:
        print("\n1. 默认设置值")
        test_settings_defaults(d)
        print("   PASS")

        print("\n2. Settings 字典式访问")
        test_settings_getitem(d)
        print("   PASS")

        print("\n3. Settings.get 方法")
        test_settings_get(d)
        print("   PASS")

        print("\n4. implicitly_wait 获取")
        test_implicitly_wait_get(d)
        print("   PASS")

        print("\n5. implicitly_wait 设置")
        test_implicitly_wait_set(d)
        print("   PASS")

        print("\n6. UiObject.wait() 使用全局超时")
        test_uiobject_wait_uses_global_timeout(d)
        print("   PASS")

        print("\n7. 显式 timeout 覆盖全局设置")
        test_uiobject_wait_explicit_overrides_global(d)
        print("   PASS")

        print("\n8. UiObject.wait_gone() 使用全局超时")
        test_uiobject_wait_gone_uses_global_timeout(d)
        print("   PASS")

        print("\n9. XPath.wait() 使用全局超时")
        test_xpath_wait_uses_global_timeout(d)
        print("   PASS")

        print("\n10. XPath 显式 timeout 覆盖全局")
        test_xpath_wait_explicit_overrides_global(d)
        print("   PASS")

        print("\n11. 多次修改隐式等待值")
        test_implicitly_wait_multiple_changes(d)
        print("   PASS")

    finally:
        d.close()
        Driver._instance.clear()

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)
