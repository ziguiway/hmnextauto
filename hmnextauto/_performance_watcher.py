# -*- coding: utf-8 -*-
"""
性能监控 Watcher：后台持续收集性能指标并导出到文件

示例::

    # 基础用法 - 监控所有指标
    pw = d.performance_watcher
    pw.start(output_file="perf.jsonl", interval=1.0)
    # ... 测试执行 ...
    pw.stop()

    # 高级用法 - 选择性监控（推荐，更快）
    pw.configure(
        metrics=["fps", "memory"],  # 只采集需要的指标
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

注意:
    性能采集依赖 hidumper 命令，每个命令执行需要 1-5 秒。
    建议使用 configure() 选择性采集指标，减少采集时间。
    可用指标: fps, cpu, cpu_freq, memory, hitches
"""

from __future__ import annotations

import json
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from . import logger

if TYPE_CHECKING:
    from .driver import Driver


# 每个指标的超时时间（秒）
# 注意:
# - memory 指定 PID 时约 1-2 秒，不指定 PID 时需要 40+ 秒
# - 建议在 configure() 时设置 package 参数以获得快速采集
# - thermal 约 0.5 秒，memory_percent 约 0.2 秒
METRIC_TIMEOUTS = {
    "fps": 3.0,
    "cpu": 5.0,
    "cpu_freq": 5.0,
    "memory": 5.0,  # 指定 PID 时约 1-2 秒
    "hitches": 3.0,
    "thermal": 2.0,
    "memory_percent": 1.0,
}


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
    thermal: Optional[Dict[str, float]] = None  # 温度信息（摄氏度）
    memory_percent: Optional[float] = None  # 系统内存使用率（0-100）

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
    METRICS_THERMAL = "thermal"
    METRICS_MEMORY_PERCENT = "memory_percent"

    ALL_METRICS = [
        METRICS_FPS,
        METRICS_CPU,
        METRICS_CPU_FREQ,
        METRICS_MEMORY,
        METRICS_HITCHES,
        METRICS_THERMAL,
        METRICS_MEMORY_PERCENT,
    ]

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
        """收集一次性能数据（并行采集，带超时）"""
        now = datetime.now().isoformat()
        data = PerformanceData(timestamp=now)

        # 使用线程池并行采集
        with ThreadPoolExecutor(max_workers=len(self._metrics)) as executor:
            futures = {}

            # FPS
            if self.METRICS_FPS in self._metrics:
                futures["fps"] = executor.submit(self._collect_fps)

            # CPU 使用率
            if self.METRICS_CPU in self._metrics:
                futures["cpu"] = executor.submit(self._collect_cpu)

            # CPU 频率
            if self.METRICS_CPU_FREQ in self._metrics:
                futures["cpu_freq"] = executor.submit(self._collect_cpu_freq)

            # 内存
            if self.METRICS_MEMORY in self._metrics:
                futures["memory"] = executor.submit(self._collect_memory)

            # 帧卡顿
            if self.METRICS_HITCHES in self._metrics:
                futures["hitches"] = executor.submit(self._collect_hitches)

            # CPU 温度
            if self.METRICS_THERMAL in self._metrics:
                futures["thermal"] = executor.submit(self._collect_thermal)

            # 系统内存使用率
            if self.METRICS_MEMORY_PERCENT in self._metrics:
                futures["memory_percent"] = executor.submit(self._collect_memory_percent)

            # 获取结果（带超时）
            for metric, future in futures.items():
                timeout = METRIC_TIMEOUTS.get(metric, 5.0)
                try:
                    result = future.result(timeout=timeout)
                    if metric == "fps":
                        data.fps = result
                    elif metric == "cpu":
                        data.cpu_percent = result
                    elif metric == "cpu_freq":
                        data.cpu_freqs = result
                    elif metric == "memory":
                        if result:
                            data.memory_pss = result.get("total_pss")
                            data.memory_native = result.get("native_heap")
                            data.memory_ark = result.get("ark_ts_heap")
                    elif metric == "hitches":
                        data.hitches = result
                    elif metric == "thermal":
                        data.thermal = result
                    elif metric == "memory_percent":
                        data.memory_percent = result
                except FuturesTimeoutError:
                    logger.debug(f"采集 {metric} 超时 ({timeout}s)")
                except Exception as e:
                    logger.debug(f"采集 {metric} 失败: {e}")

        return data

    def _collect_fps(self) -> Optional[float]:
        """采集 FPS"""
        try:
            return self._d.fps()
        except Exception as e:
            logger.debug(f"采集 FPS 失败: {e}")
            return None

    def _collect_cpu(self) -> Optional[float]:
        """采集 CPU 使用率"""
        try:
            cpu_info = self._d.cpu_usage()
            return cpu_info.get("total")
        except Exception as e:
            logger.debug(f"采集 CPU 失败: {e}")
            return None

    def _collect_cpu_freq(self) -> Optional[List[Dict[str, int]]]:
        """采集 CPU 频率"""
        try:
            return self._d.cpu_freq()
        except Exception as e:
            logger.debug(f"采集 CPU 频率失败: {e}")
            return None

    def _collect_memory(self) -> Optional[Dict]:
        """采集内存"""
        try:
            return self._d.memory_info(self._package)
        except Exception as e:
            logger.debug(f"采集内存失败: {e}")
            return None

    def _collect_hitches(self) -> Optional[Dict]:
        """采集帧卡顿"""
        try:
            return self._d.frame_hitchs()
        except Exception as e:
            logger.debug(f"采集 Hitch 失败: {e}")
            return None

    def _collect_thermal(self) -> Optional[Dict[str, float]]:
        """采集 CPU 温度"""
        try:
            return self._d.thermal_info()
        except Exception as e:
            logger.debug(f"采集温度失败: {e}")
            return None

    def _collect_memory_percent(self) -> Optional[float]:
        """采集系统内存使用率"""
        try:
            return self._d.memory_percent()
        except Exception as e:
            logger.debug(f"采集内存使用率失败: {e}")
            return None

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
        numeric_fields = [
            "fps",
            "cpu_percent",
            "memory_pss",
            "memory_native",
            "memory_ark",
            "memory_percent",
        ]

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

    def analyze(self) -> "PerformanceAnalyzer":
        """
        返回性能分析器实例，用于深度分析。

        Returns:
            PerformanceAnalyzer 实例

        Raises:
            ValueError: 未设置输出文件或文件不存在

        Example:
            >>> with d.performance_watcher.start("perf.jsonl") as pw:
            ...     # 执行测试
            ...     d(text="按钮").click()
            >>> analyzer = pw.analyze()
            >>> print(analyzer.score().grade)
            'A'
            >>> analyzer.generate_report("report.html")
        """
        if self.running:
            logger.warning("建议先调用 stop() 再分析")

        if not self._output_file:
            raise ValueError("未设置输出文件")

        from ._performance_analyzer import PerformanceAnalyzer
        return PerformanceAnalyzer.from_file(self._output_file)

    def __enter__(self) -> "PerformanceWatcher":
        return self

    def __exit__(self, *args) -> None:
        self.stop()
