# -*- coding: utf-8 -*-
"""
性能监控测试
测试: 内存、CPU、FPS、应用启动时间等
"""

import pytest
from hmnextauto.hdc import HdcWrapper, list_devices
from hmnextauto.driver import Driver


@pytest.fixture
def hdc():
    """获取 HdcWrapper 实例"""
    devices = list_devices()
    if not devices:
        pytest.skip("No device connected")
    hdc = HdcWrapper(devices[0])
    yield hdc


@pytest.fixture
def d():
    """获取 Driver 实例"""
    d = Driver()
    yield d
    del d


# ============================================
# 内存测试
# ============================================

def test_memory_info_system(hdc):
    """测试系统内存信息"""
    info = hdc.memory_info()
    print(f"\n=== 系统内存信息 ===")
    print(info)

    # 验证有返回数据
    assert isinstance(info, dict)


def test_memory_info_by_package(hdc):
    """测试按包名获取内存"""
    info = hdc.memory_info("com.huawei.hmos.camera")
    print(f"\n=== 相机应用内存信息 ===")
    print(info)

    # 验证有返回数据
    assert isinstance(info, dict)


# ============================================
# CPU 测试
# ============================================

def test_cpu_usage(hdc):
    """测试 CPU 使用率"""
    info = hdc.cpu_usage()
    print(f"\n=== CPU 使用率 ===")
    print(f"Total: {info.get('total')}%")
    print(f"User: {info.get('user')}%")
    print(f"Kernel: {info.get('kernel')}%")
    print(f"进程数: {len(info.get('processes', []))}")

    # 验证关键字段
    assert "total" in info
    assert "user" in info
    assert "kernel" in info


def test_cpu_freq(hdc):
    """测试 CPU 频率"""
    freqs = hdc.cpu_freq()
    print(f"\n=== CPU 频率 ===")
    for f in freqs[:4]:  # 只打印前4个核心
        print(f"CPU {f.get('cpu')}: {f.get('current')} / {f.get('max')} kHz")

    # 验证有返回数据
    assert isinstance(freqs, list)


# ============================================
# FPS 测试
# ============================================

def test_refresh_rate(hdc):
    """测试屏幕刷新率"""
    rate = hdc.refresh_rate()
    print(f"\n=== 屏幕刷新率 ===")
    print(f"当前刷新率: {rate}Hz")

    # 验证值合理
    assert rate in [30, 45, 60, 72, 90, 120]


def test_fps_timestamps(hdc):
    """测试帧时间戳获取"""
    timestamps = hdc.fps_timestamps()
    print(f"\n=== 帧时间戳 ===")
    print(f"时间戳数量: {len(timestamps)}")
    if timestamps:
        print(f"前5个: {timestamps[:5]}")

    # 验证有返回数据
    assert isinstance(timestamps, list)


def test_frame_hitchs(hdc):
    """测试帧卡顿统计"""
    hitchs = hdc.frame_hitchs()
    print(f"\n=== 帧卡顿统计 ===")
    print(f"超过16ms: {hitchs.get('over_16ms')}")
    print(f"超过33ms: {hitchs.get('over_33ms')}")
    print(f"超过66ms: {hitchs.get('over_66ms')}")

    # 验证有返回数据
    assert isinstance(hitchs, dict)


# ============================================
# Driver 层测试
# ============================================

def test_driver_memory_info(d):
    """测试 Driver 内存信息"""
    # 系统内存
    sys_mem = d.memory_info()
    print(f"\n=== Driver 系统内存 ===")
    print(sys_mem)

    # 应用内存
    app_mem = d.memory_info("com.huawei.hmos.camera")
    print(f"\n=== Driver 应用内存 ===")
    print(app_mem)


def test_driver_cpu_usage(d):
    """测试 Driver CPU 使用率"""
    info = d.cpu_usage()
    print(f"\n=== Driver CPU 使用率 ===")
    print(f"Total: {info.get('total')}%")


def test_driver_cpu_freq(d):
    """测试 Driver CPU 频率"""
    freqs = d.cpu_freq()
    print(f"\n=== Driver CPU 频率 ===")
    print(f"核心数: {len(freqs)}")


def test_driver_refresh_rate(d):
    """测试 Driver 屏幕刷新率"""
    rate = d.refresh_rate
    print(f"\n=== Driver 屏幕刷新率 ===")
    print(f"刷新率: {rate}Hz")


def test_driver_fps(d):
    """测试 Driver 实时 FPS"""
    fps = d.fps()
    print(f"\n=== Driver 实时 FPS ===")
    print(f"FPS: {fps}")

    # FPS 应该在合理范围内
    assert 0 <= fps <= 120


def test_driver_frame_hitchs(d):
    """测试 Driver 帧卡顿"""
    hitchs = d.frame_hitchs()
    print(f"\n=== Driver 帧卡顿 ===")
    print(hitchs)


def test_driver_app_start_time(d):
    """测试 Driver 应用启动时间"""
    # 测试设置应用的冷启动时间
    result = d.measure_cold_start("com.huawei.hmos.settings")
    print(f"\n=== 设置应用冷启动时间 ===")
    print(f"成功: {result['success']}")
    print(f"启动时间: {result['duration_ms']} ms")
    print(f"包名: {result['package']}")

    # 验证启动成功
    assert result['success'] is True
    assert result['duration_ms'] > 0


def test_driver_hot_start(d):
    """测试 Driver 热启动时间"""
    # 先确保设置应用在前台
    d.start_app("com.huawei.hmos.settings")

    # 测试热启动时间
    result = d.measure_hot_start("com.huawei.hmos.settings")
    print(f"\n=== 设置应用热启动时间 ===")
    print(f"成功: {result['success']}")
    print(f"启动时间: {result['duration_ms']} ms")
    print(f"包名: {result['package']}")

    # 验证启动成功
    assert result['success'] is True
    assert result['duration_ms'] > 0


def test_driver_process_info(d):
    """测试 Driver 进程信息"""
    info = d.process_info("com.huawei.hmos.camera")
    print(f"\n=== 进程信息 ===")
    print(info)


if __name__ == "__main__":
    # 直接运行测试
    devices = list_devices()
    if not devices:
        print("No device connected")
        exit(1)

    d = Driver()

    print("=" * 60)
    print("性能监控测试")
    print("=" * 60)

    # 测试所有功能
    print("\n" + "=" * 60)
    print("1. 内存测试")
    print("=" * 60)
    test_driver_memory_info(d)

    print("\n" + "=" * 60)
    print("2. CPU 测试")
    print("=" * 60)
    test_driver_cpu_usage(d)
    test_driver_cpu_freq(d)

    print("\n" + "=" * 60)
    print("3. FPS 测试")
    print("=" * 60)
    test_driver_refresh_rate(d)
    test_driver_fps(d)
    test_driver_frame_hitchs(d)

    print("\n" + "=" * 60)
    print("4. 应用启动时间测试")
    print("=" * 60)
    test_driver_app_start_time(d)
    test_driver_process_info(d)

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
