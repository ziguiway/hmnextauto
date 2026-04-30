# -*- coding: utf-8 -*-
"""
设备信息扩展测试
测试 battery_level, battery_status, screen_brightness, network_type, is_screen_on
"""

import pytest
from hmnextauto.hdc import HdcWrapper, list_devices


@pytest.fixture
def hdc():
    """获取 HdcWrapper 实例"""
    devices = list_devices()
    if not devices:
        pytest.skip("No device connected")
    hdc = HdcWrapper(devices[0])
    yield hdc


def test_battery_info(hdc):
    """测试电池信息获取"""
    info = hdc.battery_info()
    print(f"电池信息: {info}")

    # 验证必要字段存在
    assert "capacity" in info
    assert "chargingStatus" in info

    # 验证值范围
    assert 0 <= info["capacity"] <= 100
    assert info["chargingStatus"] in [1, 2, 3, 4]


def test_screen_brightness(hdc):
    """测试屏幕亮度获取"""
    brightness = hdc.screen_brightness()
    print(f"屏幕亮度: {brightness}")

    # 验证值范围 (1-255)
    assert isinstance(brightness, int)
    assert 0 <= brightness <= 255


def test_network_type(hdc):
    """测试网络类型获取"""
    network = hdc.network_type()
    print(f"网络类型: {network}")

    # 验证返回值
    assert network in ["WiFi", "MOBILE", "NO_NETWORK"]


def test_screen_state(hdc):
    """测试屏幕状态获取"""
    state = hdc.screen_state()
    print(f"屏幕状态: {state}")

    # 验证返回值
    assert state in ["AWAKE", "SLEEP", "INACTIVE", "DIM", None]


def test_battery_level_value(hdc):
    """测试电池电量值"""
    info = hdc.battery_info()
    level = info.get("capacity", 0)
    print(f"电池电量: {level}%")
    assert level >= 0


def test_battery_status_value(hdc):
    """测试电池状态值解析"""
    info = hdc.battery_info()
    status_code = info.get("chargingStatus", 1)

    status_map = {
        1: "DISCHARGING",
        2: "NOT_CHARGING",
        3: "CHARGING",
        4: "FULL"
    }
    status = status_map.get(status_code, "UNKNOWN")
    print(f"电池状态: {status} (code: {status_code})")
    assert status in ["DISCHARGING", "NOT_CHARGING", "CHARGING", "FULL", "UNKNOWN"]


if __name__ == "__main__":
    # 直接运行测试
    devices = list_devices()
    if not devices:
        print("No device connected")
        exit(1)

    hdc = HdcWrapper(devices[0])

    print("=" * 50)
    print("设备信息扩展测试")
    print("=" * 50)

    # 电池信息
    info = hdc.battery_info()
    print(f"\n[电池信息]")
    print(f"  电量: {info.get('capacity', 0)}%")
    status_map = {1: "放电中", 2: "未充电", 3: "充电中", 4: "满电"}
    print(f"  状态: {status_map.get(info.get('chargingStatus'), '未知')}")
    print(f"  温度: {info.get('temperature', 0)} (单位: 0.1°C)")
    print(f"  电压: {info.get('voltage', 0)} μV")

    # 屏幕亮度
    brightness = hdc.screen_brightness()
    print(f"\n[屏幕亮度]")
    print(f"  当前亮度: {brightness} (范围: 1-255)")

    # 网络类型
    network = hdc.network_type()
    print(f"\n[网络状态]")
    print(f"  网络类型: {network}")

    # 屏幕状态
    state = hdc.screen_state()
    print(f"\n[屏幕状态]")
    print(f"  当前状态: {state}")
    print(f"  屏幕亮起: {state == 'AWAKE'}")

    print("\n" + "=" * 50)
    print("测试完成!")
