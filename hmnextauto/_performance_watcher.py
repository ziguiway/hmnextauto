# -*- coding: utf-8 -*-
"""
性能监控 Watcher：后台持续收集性能指标并导出到文件

示例::

    # 基础用法 - 监控所有指标
    pw = d.performance_watcher
    pw.start(output_file="perf.jsonl", interval=1.0)
    # ... 测试执行 ...
    pw.stop()

    # 高级用法 - 选择性监控
    pw.configure(
        metrics=["fps", "memory", "cpu"],
        package="com.example.app",
        output_file="perf.jsonl",
        interval=0.5
    ).start()
    # ... 测试执行 ...
    pw.stop()

    # 上下文管理器（推荐）
    with d.performance_watcher.start("perf.jsonl"):
        d(text="按钮").click()
        # ... 自动停止并保存
"""

from __future__ import annotations

import json
import statistics
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from . import logger

if TYPE_CHECKING:
    from .driver import Driver


@dataclass
class PerformanceData:
    """性能数据记录"""

    timestamp: str
    fps: Optional[float] = None
    cpu_percent: Optional[float] = None
    cpu_freqs: Optional[List[Dict[str, int]]] = None
    memory_pss: Optional[int] = None
    memory_native: Optional[int] = None
    memory_ark: Optional[int] = None
    hitches: Optional[Dict[str, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，过滤 None 值"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class PerformanceWatcher:
    """
    后台性能监控器，持续收集 FPS、CPU、内存、帧卡顿等指标。

    Features:
        - 后台线程持续采集
        - 可配置监控哪些指标
        - JSON Lines 格式导出
        - 支持上下文管理器
        - 统计摘要生成
    """

    # 支持的指标类型
    METRICS_FPS = "fps"
    METRICS_CPU = "cpu"
    METRICS_CPU_FREQ = "cpu_freq"
    METRICS_MEMORY = "memory"
    METRICS_HITCHES = "hitches"

    ALL_METRICS = [METRICS_FPS, METRICS_CPU, METRICS_CPU_FREQ, METRICS_MEMORY, METRICS_HITCHES]

    def __init__(self, driver: "Driver") -> None:
        self._d = driver
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._interval = 1.0
        self._output_file: Optional[str] = None
        self._metrics: List[str] = self.ALL_METRICS.copy()
        self._package: Optional[str] = None
        self._lock = threading.Lock()

    def configure(
        self,
        metrics: Optional[List[str]] = None,
        package: Optional[str] = None,
        output_file: Optional[str] = None,
        interval: Optional[float] = None,
    ) -> "PerformanceWatcher":
        """
        配置监控参数。

        Args:
            metrics: 要监控的指标列表，可选值: fps, cpu, cpu_freq, memory, hitches
            package: 要监控内存的特定应用包名
            output_file: 输出文件路径（JSON Lines 格式）
            interval: 采样间隔（秒），默认 1.0

        Returns:
            self，支持链式调用
        """
        if metrics is not None:
            invalid = set(metrics) - set(self.ALL_METRICS)
            if invalid:
                raise ValueError(f"无效指标: {invalid}，可用: {self.ALL_METRICS}")
            self._metrics = metrics.copy()

        if package is not None:
            self._package = package

        if output_file is not None:
            self._output_file = output_file

        if interval is not None:
            self._interval = max(0.1, float(interval))  # 最小 100ms

        return self

    @property
    def running(self) -> bool:
        """是否正在运行"""
        t = self._thread
        return bool(t and t.is_alive())

    @property
    def output_file(self) -> Optional[str]:
        """当前输出文件路径"""
        return self._output_file

    def start(
        self,
        output_file: Optional[str] = None,
        interval: Optional[float] = None,
    ) -> "PerformanceWatcher":
        """
        启动性能监控（后台线程）。

        Args:
            output_file: 可选，覆盖配置中的输出文件
            interval: 可选，覆盖配置中的采样间隔

        Returns:
            self，支持链式调用
        """
        if output_file:
            self._output_file = output_file
        if interval:
            self._interval = max(0.1, float(interval))

        if not self._output_file:
            raise ValueError("必须指定 output_file")

        with self._lock:
            if self._thread and self._thread.is_alive():
                logger.warning("PerformanceWatcher 已在运行")
                return self

        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="hmnextauto-perf-watcher",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"PerformanceWatcher 启动，间隔 {self._interval}s，输出 {self._output_file}")
        return self

    def stop(self, join_timeout: float = 2.0) -> None:
        """
        停止监控。

        Args:
            join_timeout: 等待线程结束的超时时间（秒）
        """
        self._stop.set()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=join_timeout)
        self._thread = None
        logger.info("PerformanceWatcher 已停止")

    def _collect(self) -> PerformanceData:
        """收集一次性能数据"""
        now = datetime.now().isoformat()
        data = PerformanceData(timestamp=now)

        # FPS
        if self.METRICS_FPS in self._metrics:
            try:
                data.fps = self._d.fps()
            except Exception as e:
                logger.debug(f"采集 FPS 失败: {e}")

        # CPU 使用率
        if self.METRICS_CPU in self._metrics:
            try:
                cpu_info = self._d.cpu_usage()
                data.cpu_percent = cpu_info.get("total")
            except Exception as e:
                logger.debug(f"采集 CPU 失败: {e}")

        # CPU 频率
        if self.METRICS_CPU_FREQ in self._metrics:
            try:
                data.cpu_freqs = self._d.cpu_freq()
            except Exception as e:
                logger.debug(f"采集 CPU 频率失败: {e}")

        # 内存
        if self.METRICS_MEMORY in self._metrics:
            try:
                mem_info = self._d.memory_info(self._package)
                if mem_info:
                    data.memory_pss = mem_info.get("total_pss")
                    data.memory_native = mem_info.get("native_heap")
                    data.memory_ark = mem_info.get("ark_ts_heap")
            except Exception as e:
                logger.debug(f"采集内存失败: {e}")

        # 帧卡顿
        if self.METRICS_HITCHES in self._metrics:
            try:
                data.hitches = self._d.frame_hitchs()
            except Exception as e:
                logger.debug(f"采集 Hitch 失败: {e}")

        return data

    def _loop(self) -> None:
        """后台线程主循环"""
        with open(self._output_file, "w", encoding="utf-8") as f:
            while not self._stop.is_set():
                start_time = time.perf_counter()

                # 收集数据
                data = self._collect()

                # 写入 JSON Lines
                line = json.dumps(data.to_dict(), ensure_ascii=False)
                f.write(line + "\n")
                f.flush()

                # 计算实际耗时，调整等待时间
                elapsed = time.perf_counter() - start_time
                sleep_time = max(0, self._interval - elapsed)

                # 使用 Event.wait 以便可以被 stop 中断
                if self._stop.wait(sleep_time):
                    break

    def get_summary(self) -> Optional[Dict[str, Any]]:
        """
        读取输出文件并生成统计摘要。

        Returns:
            包含平均值、最大/最小值等的统计信息，或 None 如果文件不存在
        """
        if self.running:
            logger.warning("建议先调用 stop() 再获取摘要")

        if not self._output_file:
            return None

        records = []
        try:
            with open(self._output_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return None

        if not records:
            return None

        summary: Dict[str, Any] = {"count": len(records), "metrics": {}}

        # 数值型字段统计
        numeric_fields = ["fps", "cpu_percent", "memory_pss", "memory_native", "memory_ark"]

        for field_name in numeric_fields:
            values = [r[field_name] for r in records if field_name in r and r[field_name] is not None]
            if values:
                field_summary: Dict[str, float] = {
                    "avg": round(statistics.mean(values), 2),
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                }
                if len(values) > 1:
                    field_summary["stdev"] = round(statistics.stdev(values), 2)
                summary["metrics"][field_name] = field_summary

        # hitches 统计（累计值）
        hitches_records = [r["hitches"] for r in records if "hitches" in r and r["hitches"]]
        if hitches_records:
            total_16 = sum(h.get("over_16ms", 0) for h in hitches_records)
            total_33 = sum(h.get("over_33ms", 0) for h in hitches_records)
            total_66 = sum(h.get("over_66ms", 0) for h in hitches_records)
            summary["metrics"]["hitches_total"] = {
                "over_16ms": total_16,
                "over_33ms": total_33,
                "over_66ms": total_66,
            }

        return summary

    def __enter__(self) -> "PerformanceWatcher":
        return self

    def __exit__(self, *args) -> None:
        self.stop()
