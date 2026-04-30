# -*- coding: utf-8 -*-
"""
等待条件增强测试
测试: wait_enabled, wait_clickable, wait_until, wait_until_not
"""

import pytest
import time
from hmnextauto.driver import Driver


@pytest.fixture
def d():
    """获取 Driver 实例"""
    d = Driver()
    yield d
    d.close()


def test_wait_enabled_basic(d):
    """测试等待元素可用"""
    # 先回到桌面
    d.go_home()
    time.sleep(0.5)

    # 打开设置应用
    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    # 设置应用中查找可点击元素，应该是可用的
    result = d(clickable=True).wait_enabled(timeout=5)
    print(f"\n=== wait_enabled 结果: {result}")
    assert result is True


def test_wait_clickable_basic(d):
    """测试等待元素可点击"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    # 设置应用中查找可点击元素，应该是可点击的
    result = d(clickable=True).wait_clickable(timeout=5)
    print(f"\n=== wait_clickable 结果: {result}")
    assert result is True


def test_wait_until_text(d):
    """测试自定义条件等待 - 等待文本"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    # 等待出现可点击元素
    result = d(clickable=True).wait_until(lambda e: e.isClickable, timeout=5)
    print(f"\n=== wait_until(clickable) 结果: {result}")
    assert result is True


def test_wait_until_enabled(d):
    """测试自定义条件等待 - 等待可用状态"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    # 等待元素可用
    result = d(enabled=True).wait_until(lambda e: e.isEnabled, timeout=5)
    print(f"\n=== wait_until(enabled) 结果: {result}")
    assert result is True


def test_wait_until_not_checked(d):
    """测试自定义条件等待 - 等待条件不满足"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    # 等待可点击元素未被选中
    result = d(clickable=True).wait_until_not(lambda e: e.isChecked, timeout=5)
    print(f"\n=== wait_until_not(checked) 结果: {result}")
    assert result is True


def test_xpath_wait_enabled(d):
    """测试 XPath 等待可用"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    # 使用 XPath 查找可点击元素
    result = d.xpath('//*[@clickable="true"]').wait_enabled(timeout=5)
    print(f"\n=== xpath wait_enabled 结果: {result}")
    assert result is True


def test_xpath_wait_clickable(d):
    """测试 XPath 等待可点击"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    result = d.xpath('//*[@clickable="true"]').wait_clickable(timeout=5)
    print(f"\n=== xpath wait_clickable 结果: {result}")
    assert result is True


def test_xpath_wait_until(d):
    """测试 XPath 自定义条件等待"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    # 等待出现可点击元素
    result = d.xpath('//*[@clickable="true"]').wait_until(lambda e: e.get("clickable") == "true", timeout=5)
    print(f"\n=== xpath wait_until 结果: {result}")
    assert result is True


def test_wait_timeout(d):
    """测试等待超时"""
    d.go_home()
    time.sleep(0.5)

    # 等待一个不存在的元素，应该超时返回 False
    result = d(id="nonexistent_element_xyz").wait_enabled(timeout=2)
    print(f"\n=== wait_enabled 超时结果: {result}")
    assert result is False

    result = d(id="nonexistent_element_xyz").wait_clickable(timeout=2)
    print(f"\n=== wait_clickable 超时结果: {result}")
    assert result is False


def test_wait_disabled(d):
    """测试等待禁用状态"""
    d.go_home()
    time.sleep(0.5)

    # 等待一个不存在的元素变为禁用，应该立即返回 True（元素不存在视为禁用）
    result = d(id="nonexistent_element_xyz").wait_disabled(timeout=2)
    print(f"\n=== wait_disabled 结果: {result}")
    # 不存在的元素应该返回 True（因为无法确定状态，视为条件满足）
    assert result is True


if __name__ == "__main__":
    # 直接运行测试
    d = Driver()

    print("=" * 60)
    print("等待条件增强测试")
    print("=" * 60)

    print("\n1. wait_enabled 测试")
    test_wait_enabled_basic(d)

    print("\n2. wait_clickable 测试")
    test_wait_clickable_basic(d)

    print("\n3. wait_until(text) 测试")
    test_wait_until_text(d)

    print("\n4. xpath wait_enabled 测试")
    test_xpath_wait_enabled(d)

    print("\n5. xpath wait_clickable 测试")
    test_xpath_wait_clickable(d)

    print("\n6. wait 超时测试")
    test_wait_timeout(d)

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

    d.close()