# -*- coding: utf-8 -*-
"""
PerformanceWatcher 测试
测试后台持续性能监控功能
"""

import json
import os
import time

import pytest

from hmnextauto.driver import Driver


@pytest.fixture
def d():
    """获取 Driver 实例"""
    d = Driver()
    yield d
    d.close()


def test_performance_watcher_basic(d, tmp_path):
    """测试基础性能监控"""
    output_file = str(tmp_path / "perf.jsonl")

    pw = d.performance_watcher
    pw.start(output_file=output_file, interval=0.5)

    # 运行 3 秒
    time.sleep(3)

    pw.stop()

    # 验证文件存在
    assert os.path.exists(output_file)

    # 验证数据行数
    with open(output_file, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    print(f"\n=== 采集数据行数: {len(lines)} ===")
    assert len(lines) >= 3  # 至少 3 条记录

    # 验证数据格式
    for line in lines[:2]:
        data = json.loads(line)
        print(f"数据: {data}")
        assert "timestamp" in data
        assert "fps" in data
        assert "cpu_percent" in data
        assert "cpu_freqs" in data
        assert "memory_pss" in data
        assert "hitches" in data


def test_performance_watcher_configure(d, tmp_path):
    """测试配置监控参数"""
    output_file = str(tmp_path / "perf_custom.jsonl")

    pw = d.performance_watcher
    pw.configure(
        metrics=["fps", "cpu"],
        output_file=output_file,
        interval=0.5
    ).start()

    time.sleep(2)

    pw.stop()

    # 验证只采集了指定指标
    with open(output_file, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    assert len(lines) >= 2

    data = json.loads(lines[0])
    print(f"\n=== 配置后数据: {data}")
    assert "fps" in data
    assert "cpu_percent" in data
    # memory 不在 metrics 中，可能不存在或为 None
    assert data.get("memory_pss") is None


def test_performance_watcher_context_manager(d, tmp_path):
    """测试上下文管理器"""
    output_file = str(tmp_path / "perf_context.jsonl")

    with d.performance_watcher.start(output_file, interval=0.5):
        time.sleep(2)

    # 验证自动停止
    assert not d.performance_watcher.running

    # 验证文件存在
    assert os.path.exists(output_file)

    with open(output_file, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    print(f"\n=== 上下文管理器采集行数: {len(lines)} ===")
    assert len(lines) >= 2


def test_performance_watcher_summary(d, tmp_path):
    """测试统计摘要"""
    output_file = str(tmp_path / "perf_summary.jsonl")

    pw = d.performance_watcher
    pw.start(output_file=output_file, interval=0.3)

    time.sleep(2)

    pw.stop()

    # 获取摘要
    summary = pw.get_summary()

    print(f"\n=== 统计摘要 ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    assert summary is not None
    assert "count" in summary
    assert summary["count"] >= 3
    assert "metrics" in summary

    # 验证 FPS 统计
    if "fps" in summary["metrics"]:
        fps_stats = summary["metrics"]["fps"]
        assert "avg" in fps_stats
        assert "min" in fps_stats
        assert "max" in fps_stats
        print(f"FPS: avg={fps_stats['avg']}, min={fps_stats['min']}, max={fps_stats['max']}")


def test_performance_watcher_with_package(d, tmp_path):
    """测试指定应用包名的内存监控"""
    output_file = str(tmp_path / "perf_package.jsonl")

    pw = d.performance_watcher
    pw.configure(
        metrics=["memory"],
        package="com.huawei.hmos.camera",
        output_file=output_file,
        interval=0.5
    ).start()

    time.sleep(2)

    pw.stop()

    # 验证内存数据
    with open(output_file, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    assert len(lines) >= 2

    data = json.loads(lines[0])
    print(f"\n=== 指定包名内存数据: {data}")

    # 相机应用应该有内存数据
    if data.get("memory_pss"):
        assert data["memory_pss"] > 0


if __name__ == "__main__":
    # 直接运行测试
    import tempfile

    d = Driver()
    tmp_path = tempfile.mkdtemp()

    print("=" * 60)
    print("PerformanceWatcher 测试")
    print("=" * 60)

    print("\n1. 基础性能监控测试")
    test_performance_watcher_basic(d, type("obj", (object,), {"path": tmp_path})())

    print("\n2. 配置监控参数测试")
    test_performance_watcher_configure(d, type("obj", (object,), {"path": tmp_path})())

    print("\n3. 统计摘要测试")
    test_performance_watcher_summary(d, type("obj", (object,), {"path": tmp_path})())

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

    d.close()
