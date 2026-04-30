# -*- coding: utf-8 -*-
"""
通知栏操作测试
测试: 打开/关闭通知栏、通知消息操作、快捷设置面板
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


def test_notification_open_close(d):
    """测试打开和关闭通知栏"""
    # 先回到桌面
    d.go_home()
    time.sleep(0.5)

    # 打开通知栏
    print("\n=== 打开通知栏 ===")
    result = d.notification.open()
    print(f"打开结果: {result}")
    assert result is True
    time.sleep(1)

    # 关闭通知栏
    print("\n=== 关闭通知栏 ===")
    result = d.notification.close()
    print(f"关闭结果: {result}")
    assert result is True
    time.sleep(0.5)


def test_notification_toggle(d):
    """测试切换通知栏状态"""
    d.go_home()
    time.sleep(0.5)

    # 切换打开
    print("\n=== 切换通知栏（打开）===")
    state = d.notification.toggle()
    print(f"切换后状态: {state}")
    assert state is True
    time.sleep(1)

    # 切换关闭
    print("\n=== 切换通知栏（关闭）===")
    state = d.notification.toggle()
    print(f"切换后状态: {state}")
    assert state is False


def test_notification_context_manager(d):
    """测试上下文管理器"""
    d.go_home()
    time.sleep(0.5)

    print("\n=== 使用上下文管理器 ===")
    with d.notification:
        print("通知栏已打开")
        time.sleep(1)
        # 获取通知列表
        notifications = d.notification.get_notifications()
        print(f"通知数量: {len(notifications)}")

    print("通知栏已自动关闭")


def test_get_notifications(d):
    """测试获取通知列表"""
    d.go_home()
    time.sleep(0.5)

    print("\n=== 获取通知列表 ===")
    notifications = d.notification.get_notifications()
    print(f"通知数量: {len(notifications)}")

    for i, notif in enumerate(notifications[:5]):
        print(f"  通知 {i}: text={notif.get('text')}, type={notif.get('type')}")


def test_open_quick_settings(d):
    """测试打开快捷设置面板"""
    d.go_home()
    time.sleep(0.5)

    print("\n=== 打开快捷设置面板 ===")
    result = d.notification.open_quick_settings()
    print(f"打开结果: {result}")
    assert result is True
    time.sleep(1)

    # 关闭
    d.notification.close()


def test_click_quick_setting(d):
    """测试点击快捷设置"""
    d.go_home()
    time.sleep(0.5)

    print("\n=== 点击快捷设置 ===")
    # 尝试点击 WiFi 开关
    result = d.notification.click_quick_setting("WiFi")
    print(f"点击 WiFi 结果: {result}")
    time.sleep(0.5)

    # 关闭通知栏
    d.notification.close()


def test_set_brightness(d):
    """测试设置亮度"""
    d.go_home()
    time.sleep(0.5)

    print("\n=== 设置亮度 ===")
    result = d.notification.set_brightness(50)
    print(f"设置亮度 50% 结果: {result}")

    # 关闭通知栏
    d.notification.close()


def test_click_notification_by_index(d):
    """测试按索引点击通知"""
    d.go_home()
    time.sleep(0.5)

    print("\n=== 按索引点击通知 ===")
    # 先获取通知列表
    notifications = d.notification.get_notifications()

    if len(notifications) > 0:
        print(f"有 {len(notifications)} 条通知，点击第一条")
        result = d.notification.click_notification(index=0)
        print(f"点击结果: {result}")
        time.sleep(1)
    else:
        print("没有通知，跳过测试")


if __name__ == "__main__":
    # 直接运行测试
    d = Driver()

    print("=" * 60)
    print("通知栏操作测试")
    print("=" * 60)

    print("\n1. 打开/关闭通知栏测试")
    test_notification_open_close(d)

    print("\n2. 切换通知栏测试")
    test_notification_toggle(d)

    print("\n3. 上下文管理器测试")
    test_notification_context_manager(d)

    print("\n4. 获取通知列表测试")
    test_get_notifications(d)

    print("\n5. 打开快捷设置面板测试")
    test_open_quick_settings(d)

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

    d.close()
