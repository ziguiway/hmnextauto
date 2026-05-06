# -*- coding: utf-8 -*-
"""
性能数据分析器：对采集的性能数据进行深度分析

功能：
- 统计分析（平均值、最大值、最小值、标准差、百分位）
- 异常检测（FPS 突降、内存泄漏、严重卡顿）
- 性能评分（S/A/B/C/D/F 等级）
- HTML 报告生成

示例::

    from hmnextauto._performance_analyzer import PerformanceAnalyzer

    # 从文件加载
    analyzer = PerformanceAnalyzer.from_file("perf.jsonl")

    # 获取统计
    stats = analyzer.stats()
    print(f"FPS 平均: {stats.fps.avg}")

    # 检测异常
    anomalies = analyzer.detect_anomalies()
    for a in anomalies:
        print(f"[{a.severity.value}] {a.message}")

    # 性能评分
    score = analyzer.score()
    print(f"性能等级: {score.grade}")

    # 生成报告
    analyzer.generate_report("report.html")
"""

from __future__ import annotations

import base64
import json
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AnomalyType(Enum):
    """异常类型"""
    FPS_DROP = "fps_drop"           # FPS 突降
    LOW_FPS = "low_fps"             # 持续低 FPS
    MEMORY_SPIKE = "memory_spike"   # 内存突增
    MEMORY_LEAK = "memory_leak"     # 内存泄漏
    HIGH_CPU = "high_cpu"           # CPU 占用过高
    JANK = "jank"                   # 严重卡顿
    HIGH_TEMPERATURE = "high_temperature"  # CPU 温度过高


class AnomalySeverity(Enum):
    """异常严重程度"""
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Anomaly:
    """异常记录"""
    type: AnomalyType
    severity: AnomalySeverity
    timestamp: str
    message: str
    value: float
    threshold: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
        }


@dataclass
class MetricStats:
    """单个指标的统计信息"""
    avg: float
    min: float
    max: float
    stdev: float
    median: float
    p95: float  # 95 百分位
    p99: float  # 99 百分位
    count: int  # 采样次数

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg": round(self.avg, 2),
            "min": round(self.min, 2),
            "max": round(self.max, 2),
            "stdev": round(self.stdev, 4) if self.stdev else 0,
            "median": round(self.median, 2),
            "p95": round(self.p95, 2),
            "p99": round(self.p99, 2),
            "count": self.count,
        }


@dataclass
class PerformanceStats:
    """性能统计摘要"""
    fps: Optional[MetricStats] = None
    cpu: Optional[MetricStats] = None
    memory: Optional[MetricStats] = None  # 单位: MB
    memory_peak_mb: float = 0.0
    memory_peak_timestamp: str = ""
    hitches_total: Dict[str, int] = field(default_factory=dict)
    thermal: Optional[MetricStats] = None  # CPU 温度统计（摄氏度）
    thermal_peak: float = 0.0  # 温度峰值
    thermal_peak_timestamp: str = ""
    memory_percent: Optional[MetricStats] = None  # 系统内存使用率统计
    duration_seconds: float = 0.0
    sample_count: int = 0
    start_time: str = ""
    end_time: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fps": self.fps.to_dict() if self.fps else None,
            "cpu": self.cpu.to_dict() if self.cpu else None,
            "memory": self.memory.to_dict() if self.memory else None,
            "memory_peak_mb": round(self.memory_peak_mb, 2),
            "memory_peak_timestamp": self.memory_peak_timestamp,
            "hitches_total": self.hitches_total,
            "thermal": self.thermal.to_dict() if self.thermal else None,
            "thermal_peak": round(self.thermal_peak, 1),
            "thermal_peak_timestamp": self.thermal_peak_timestamp,
            "memory_percent": self.memory_percent.to_dict() if self.memory_percent else None,
            "duration_seconds": round(self.duration_seconds, 2),
            "sample_count": self.sample_count,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass
class PerformanceScore:
    """性能评分"""
    fps: int          # 0-30 分
    fluency: int      # 0-30 分（基于卡顿）
    memory: int       # 0-20 分
    cpu: int          # 0-20 分
    total: int        # 0-100 分
    grade: str        # S/A/B/C/D/F
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fps": self.fps,
            "fluency": self.fluency,
            "memory": self.memory,
            "cpu": self.cpu,
            "total": self.total,
            "grade": self.grade,
            "summary": self.summary,
        }


def _calc_stats(values: List[float]) -> Optional[MetricStats]:
    """计算统计信息"""
    if not values:
        return None

    n = len(values)
    sorted_vals = sorted(values)

    # 百分位计算
    def percentile(data: List[float], p: float) -> float:
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (k - f) * (data[c] - data[f]) if c != f else data[f]

    return MetricStats(
        avg=statistics.mean(values),
        min=min(values),
        max=max(values),
        stdev=statistics.stdev(values) if n > 1 else 0,
        median=statistics.median(values),
        p95=percentile(sorted_vals, 95),
        p99=percentile(sorted_vals, 99),
        count=n,
    )


class PerformanceAnalyzer:
    """
    性能数据分析器

    对 PerformanceWatcher 采集的数据进行深度分析。
    """

    def __init__(self, records: List[Dict[str, Any]]) -> None:
        """
        初始化分析器

        Args:
            records: 从 JSONL 文件加载的记录列表
        """
        self._records = records
        self._stats: Optional[PerformanceStats] = None

    @classmethod
    def from_file(cls, path: str) -> "PerformanceAnalyzer":
        """
        从 JSONL 文件加载分析器

        Args:
            path: JSONL 文件路径

        Returns:
            PerformanceAnalyzer 实例

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误或无数据
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"性能数据文件不存在: {path}")

        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise ValueError(f"文件第 {line_num} 行 JSON 解析失败: {e}")

        if not records:
            raise ValueError(f"性能数据文件为空: {path}")

        return cls(records)

    @property
    def records(self) -> List[Dict[str, Any]]:
        """原始数据记录"""
        return self._records

    @property
    def count(self) -> int:
        """记录数量"""
        return len(self._records)

    def stats(self) -> PerformanceStats:
        """
        计算统计摘要

        Returns:
            PerformanceStats 统计结果
        """
        if self._stats is not None:
            return self._stats

        records = self._records

        # 提取各指标数据
        fps_values = [r["fps"] for r in records if r.get("fps") is not None]
        cpu_values = [r["cpu_percent"] for r in records if r.get("cpu_percent") is not None]
        mem_values = [r["memory_pss"] for r in records if r.get("memory_pss") is not None]

        # 时间范围
        timestamps = [r["timestamp"] for r in records if r.get("timestamp")]
        start_time = timestamps[0] if timestamps else ""
        end_time = timestamps[-1] if timestamps else ""

        # 计算持续时间
        duration_seconds = 0.0
        if len(timestamps) >= 2:
            try:
                t1 = datetime.fromisoformat(timestamps[0])
                t2 = datetime.fromisoformat(timestamps[-1])
                duration_seconds = (t2 - t1).total_seconds()
            except (ValueError, TypeError):
                pass

        # 内存峰值
        memory_peak_kb = max(mem_values) if mem_values else 0
        memory_peak_mb = memory_peak_kb / 1024
        memory_peak_timestamp = ""
        if mem_values:
            for r in records:
                if r.get("memory_pss") == memory_peak_kb:
                    memory_peak_timestamp = r.get("timestamp", "")
                    break

        # 内存统计（转换为 MB）
        mem_stats = None
        if mem_values:
            mem_mb_values = [v / 1024 for v in mem_values]
            mem_stats = _calc_stats(mem_mb_values)

        # 卡顿统计
        hitches_total = {
            "over_16ms": 0,
            "over_33ms": 0,
            "over_66ms": 0,
        }
        for r in records:
            hitches = r.get("hitches", {})
            if hitches:
                hitches_total["over_16ms"] += hitches.get("over_16ms", 0)
                hitches_total["over_33ms"] += hitches.get("over_33ms", 0)
                hitches_total["over_66ms"] += hitches.get("over_66ms", 0)

        # 温度统计（提取 soc_thermal）
        thermal_values = []
        for r in records:
            thermal = r.get("thermal", {})
            if thermal and "soc_thermal" in thermal:
                thermal_values.append(thermal["soc_thermal"])

        thermal_stats = _calc_stats(thermal_values) if thermal_values else None
        thermal_peak = max(thermal_values) if thermal_values else 0.0
        thermal_peak_timestamp = ""
        if thermal_values:
            for r in records:
                thermal = r.get("thermal", {})
                if thermal and thermal.get("soc_thermal") == thermal_peak:
                    thermal_peak_timestamp = r.get("timestamp", "")
                    break

        # 系统内存使用率统计
        mem_percent_values = [r["memory_percent"] for r in records if r.get("memory_percent") is not None]
        mem_percent_stats = _calc_stats(mem_percent_values) if mem_percent_values else None

        self._stats = PerformanceStats(
            fps=_calc_stats(fps_values),
            cpu=_calc_stats(cpu_values),
            memory=mem_stats,
            memory_peak_mb=memory_peak_mb,
            memory_peak_timestamp=memory_peak_timestamp,
            hitches_total=hitches_total,
            thermal=thermal_stats,
            thermal_peak=thermal_peak,
            thermal_peak_timestamp=thermal_peak_timestamp,
            memory_percent=mem_percent_stats,
            duration_seconds=duration_seconds,
            sample_count=len(records),
            start_time=start_time,
            end_time=end_time,
        )

        return self._stats

    def detect_anomalies(
        self,
        fps_drop_threshold: float = 0.5,
        fps_low_threshold: float = 30.0,
        memory_spike_threshold: float = 0.3,
        memory_leak_threshold: float = 0.1,
        cpu_high_threshold: float = 80.0,
        temp_warning_threshold: float = 45.0,
        temp_critical_threshold: float = 50.0,
    ) -> List[Anomaly]:
        """
        检测性能异常

        Args:
            fps_drop_threshold: FPS 下降比例阈值（默认 0.5，即下降 50%）
            fps_low_threshold: 低 FPS 阈值（默认 30）
            memory_spike_threshold: 内存突增比例阈值（默认 0.3，即增长 30%）
            memory_leak_threshold: 内存泄漏增长阈值（默认 0.1，即增长 10%）
            cpu_high_threshold: CPU 高占用阈值（默认 80%）
            temp_warning_threshold: 温度警告阈值（默认 45°C）
            temp_critical_threshold: 温度严重阈值（默认 50°C）

        Returns:
            异常列表
        """
        anomalies = []
        records = self._records

        if len(records) < 2:
            return anomalies

        # 1. FPS 突降检测
        fps_values = [(i, r.get("fps"), r.get("timestamp"))
                      for i, r in enumerate(records) if r.get("fps") is not None]

        for i in range(1, len(fps_values)):
            idx, fps_prev, ts_prev = fps_values[i-1]
            idx2, fps_curr, ts_curr = fps_values[i]

            if fps_prev > 0:
                drop_rate = (fps_prev - fps_curr) / fps_prev
                if drop_rate >= fps_drop_threshold and fps_curr < fps_low_threshold:
                    anomalies.append(Anomaly(
                        type=AnomalyType.FPS_DROP,
                        severity=AnomalySeverity.CRITICAL,
                        timestamp=ts_curr,
                        message=f"FPS 从 {fps_prev:.1f} 突降至 {fps_curr:.1f}（下降 {drop_rate*100:.0f}%）",
                        value=fps_curr,
                        threshold=fps_low_threshold,
                    ))

        # 2. 持续低 FPS 检测（连续 5 次低于阈值）
        low_fps_count = 0
        for idx, fps, ts in fps_values:
            if fps < fps_low_threshold:
                low_fps_count += 1
            else:
                low_fps_count = 0

            if low_fps_count >= 5:
                anomalies.append(Anomaly(
                    type=AnomalyType.LOW_FPS,
                    severity=AnomalySeverity.WARNING,
                    timestamp=ts,
                    message=f"FPS 持续低于 {fps_low_threshold}，当前 {fps:.1f}",
                    value=fps,
                    threshold=fps_low_threshold,
                ))
                low_fps_count = 0  # 避免重复报告

        # 3. 内存泄漏检测（趋势增长）
        mem_values = [r.get("memory_pss") for r in records if r.get("memory_pss") is not None]
        if len(mem_values) >= 10:
            n = len(mem_values)
            first_half = statistics.mean(mem_values[:n//2])
            second_half = statistics.mean(mem_values[n//2:])

            if first_half > 0:
                growth = (second_half - first_half) / first_half
                if growth >= memory_leak_threshold:
                    anomalies.append(Anomaly(
                        type=AnomalyType.MEMORY_LEAK,
                        severity=AnomalySeverity.WARNING,
                        timestamp=records[-1].get("timestamp", ""),
                        message=f"内存持续增长，增幅 {growth*100:.1f}%（{first_half/1024:.1f}MB → {second_half/1024:.1f}MB）",
                        value=second_half / 1024,
                        threshold=first_half / 1024 * (1 + memory_leak_threshold),
                    ))

        # 4. 内存突增检测
        for i in range(1, len(mem_values)):
            if mem_values[i-1] > 0:
                spike_rate = (mem_values[i] - mem_values[i-1]) / mem_values[i-1]
                if spike_rate >= memory_spike_threshold:
                    # 找到对应时间戳
                    mem_records = [(j, r) for j, r in enumerate(records) if r.get("memory_pss")]
                    if i < len(mem_records):
                        _, r = mem_records[i]
                        anomalies.append(Anomaly(
                            type=AnomalyType.MEMORY_SPIKE,
                            severity=AnomalySeverity.WARNING,
                            timestamp=r.get("timestamp", ""),
                            message=f"内存突增 {spike_rate*100:.0f}%（{mem_values[i-1]/1024:.1f}MB → {mem_values[i]/1024:.1f}MB）",
                            value=mem_values[i] / 1024,
                            threshold=mem_values[i-1] / 1024 * (1 + memory_spike_threshold),
                        ))

        # 5. CPU 高占用检测（持续超过阈值）
        cpu_values = [(r.get("cpu_percent"), r.get("timestamp"))
                      for r in records if r.get("cpu_percent") is not None]
        high_cpu_count = 0
        for cpu, ts in cpu_values:
            if cpu >= cpu_high_threshold:
                high_cpu_count += 1
            else:
                high_cpu_count = 0

            if high_cpu_count >= 5:
                anomalies.append(Anomaly(
                    type=AnomalyType.HIGH_CPU,
                    severity=AnomalySeverity.WARNING,
                    timestamp=ts,
                    message=f"CPU 持续高占用，当前 {cpu:.1f}%（阈值 {cpu_high_threshold}%）",
                    value=cpu,
                    threshold=cpu_high_threshold,
                ))
                high_cpu_count = 0

        # 6. 严重卡顿检测
        for r in records:
            hitches = r.get("hitches", {})
            if hitches:
                over_66 = hitches.get("over_66ms", 0)
                if over_66 > 0:
                    anomalies.append(Anomaly(
                        type=AnomalyType.JANK,
                        severity=AnomalySeverity.CRITICAL,
                        timestamp=r.get("timestamp", ""),
                        message=f"检测到严重卡顿: {over_66} 帧超过 66ms",
                        value=over_66,
                        threshold=0,
                    ))

        # 7. CPU 温度过高检测
        for r in records:
            thermal = r.get("thermal", {})
            if thermal:
                # 检查 soc_thermal 或 cpu 相关温度
                soc_temp = thermal.get("soc_thermal", 0)
                if soc_temp >= temp_critical_threshold:
                    anomalies.append(Anomaly(
                        type=AnomalyType.HIGH_TEMPERATURE,
                        severity=AnomalySeverity.CRITICAL,
                        timestamp=r.get("timestamp", ""),
                        message=f"CPU 温度过高: {soc_temp:.1f}°C（严重阈值 {temp_critical_threshold}°C）",
                        value=soc_temp,
                        threshold=temp_critical_threshold,
                    ))
                elif soc_temp >= temp_warning_threshold:
                    anomalies.append(Anomaly(
                        type=AnomalyType.HIGH_TEMPERATURE,
                        severity=AnomalySeverity.WARNING,
                        timestamp=r.get("timestamp", ""),
                        message=f"CPU 温度偏高: {soc_temp:.1f}°C（警告阈值 {temp_warning_threshold}°C）",
                        value=soc_temp,
                        threshold=temp_warning_threshold,
                    ))

        return anomalies

    def score(
        self,
        fps_target: float = 55.0,
        memory_limit_mb: float = 500.0,
        cpu_limit: float = 50.0,
    ) -> PerformanceScore:
        """
        计算性能评分

        评分规则:
        - FPS 评分 (30分): 目标 55+ FPS
        - 流畅度评分 (30分): 基于卡顿
        - 内存评分 (20分): 峰值内存限制
        - CPU 评分 (20分): 平均 CPU 限制

        Args:
            fps_target: FPS 目标值（默认 55）
            memory_limit_mb: 内存限制 MB（默认 500）
            cpu_limit: CPU 限制%（默认 50）

        Returns:
            PerformanceScore 评分结果
        """
        stats = self.stats()

        # FPS 评分 (30分)
        fps_score = 0
        if stats.fps:
            if stats.fps.avg >= fps_target:
                fps_score = 30
            elif stats.fps.avg >= 45:
                fps_score = 25
            elif stats.fps.avg >= 30:
                fps_score = 15
            elif stats.fps.avg >= 20:
                fps_score = 5

        # 流畅度评分 (30分): 基于卡顿
        total_hitches = (
            stats.hitches_total.get("over_16ms", 0) +
            stats.hitches_total.get("over_33ms", 0) * 2 +
            stats.hitches_total.get("over_66ms", 0) * 5
        )

        if total_hitches == 0:
            fluency_score = 30
        elif total_hitches < 10:
            fluency_score = 25
        elif total_hitches < 30:
            fluency_score = 20
        elif total_hitches < 100:
            fluency_score = 10
        else:
            fluency_score = 0

        # 内存评分 (20分)
        memory_score = 0
        if stats.memory_peak_mb <= memory_limit_mb:
            memory_score = 20
        elif stats.memory_peak_mb <= memory_limit_mb * 1.5:
            memory_score = 10
        elif stats.memory_peak_mb <= memory_limit_mb * 2:
            memory_score = 5

        # CPU 评分 (20分)
        cpu_score = 0
        if stats.cpu:
            if stats.cpu.avg <= cpu_limit * 0.5:  # 25%
                cpu_score = 20
            elif stats.cpu.avg <= cpu_limit:
                cpu_score = 15
            elif stats.cpu.avg <= cpu_limit * 1.5:  # 75%
                cpu_score = 8
            elif stats.cpu.avg <= cpu_limit * 2:  # 100%
                cpu_score = 3

        total = fps_score + fluency_score + memory_score + cpu_score

        # 等级
        if total >= 90:
            grade = "S"
        elif total >= 80:
            grade = "A"
        elif total >= 70:
            grade = "B"
        elif total >= 60:
            grade = "C"
        elif total >= 50:
            grade = "D"
        else:
            grade = "F"

        # 摘要
        fps_info = f"FPS {stats.fps.avg:.1f}" if stats.fps else "FPS N/A"
        mem_info = f"内存峰值 {stats.memory_peak_mb:.1f}MB"
        cpu_info = f"CPU {stats.cpu.avg:.1f}%" if stats.cpu else "CPU N/A"
        duration_info = f"时长 {stats.duration_seconds:.1f}s"

        summary = f"性能等级 {grade}（{total}分），{fps_info}，{mem_info}，{cpu_info}，{duration_info}"

        return PerformanceScore(
            fps=fps_score,
            fluency=fluency_score,
            memory=memory_score,
            cpu=cpu_score,
            total=total,
            grade=grade,
            summary=summary,
        )

    def generate_report(
        self,
        path: str,
        title: str = "性能分析报告",
        include_charts: bool = True,
    ) -> str:
        """
        生成 HTML 性能报告

        Args:
            path: 输出文件路径
            title: 报告标题
            include_charts: 是否包含图表（需要 matplotlib）

        Returns:
            生成的报告文件路径
        """
        stats = self.stats()
        score = self.score()
        anomalies = self.detect_anomalies()

        # 生成图表（如果支持）
        charts_base64 = {}
        if include_charts:
            try:
                charts_base64 = self._generate_charts_base64()
            except ImportError:
                pass  # matplotlib 未安装，跳过图表

        html = self._render_html(
            title=title,
            stats=stats,
            score=score,
            anomalies=anomalies,
            charts_base64=charts_base64,
        )

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

        return path

    def _generate_charts_base64(self) -> Dict[str, str]:
        """生成图表并返回 base64 编码"""
        import io

        import matplotlib
        matplotlib.use('Agg')  # 非交互式后端
        import matplotlib.pyplot as plt

        charts = {}
        records = self._records

        # 提取时间序列
        timestamps = []
        fps_values = []
        cpu_values = []
        mem_values = []
        thermal_values = []
        mem_percent_values = []

        for r in records:
            ts = r.get("timestamp", "")
            if ts:
                try:
                    timestamps.append(datetime.fromisoformat(ts))
                except (ValueError, TypeError):
                    timestamps.append(None)
            else:
                timestamps.append(None)

            fps_values.append(r.get("fps"))
            cpu_values.append(r.get("cpu_percent"))
            mem_values.append(r.get("memory_pss", 0) / 1024 if r.get("memory_pss") else None)

            # 温度数据
            thermal = r.get("thermal", {})
            thermal_values.append(thermal.get("soc_thermal") if thermal else None)

            # 内存使用率
            mem_percent_values.append(r.get("memory_percent"))

        # 过滤有效时间戳
        valid_indices = [i for i, t in enumerate(timestamps) if t is not None]
        if not valid_indices:
            return charts

        valid_times = [timestamps[i] for i in valid_indices]

        # FPS 趋势图
        valid_fps = [fps_values[i] for i in valid_indices if fps_values[i] is not None]
        if valid_fps:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(valid_times[:len(valid_fps)], valid_fps, 'b-', linewidth=1.5)
            ax.axhline(y=55, color='g', linestyle='--', label='Target (55 FPS)')
            ax.axhline(y=30, color='r', linestyle='--', label='Warning (30 FPS)')
            ax.set_xlabel('Time')
            ax.set_ylabel('FPS')
            ax.set_title('FPS Trend')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            charts['fps_trend'] = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)

        # 内存趋势图
        valid_mem = [mem_values[i] for i in valid_indices if mem_values[i] is not None]
        if valid_mem:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(valid_times[:len(valid_mem)], valid_mem, 'r-', linewidth=1.5)
            ax.set_xlabel('Time')
            ax.set_ylabel('Memory (MB)')
            ax.set_title('Memory Trend')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            charts['memory_trend'] = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)

        # CPU 趋势图
        valid_cpu = [cpu_values[i] for i in valid_indices if cpu_values[i] is not None]
        if valid_cpu:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(valid_times[:len(valid_cpu)], valid_cpu, 'orange', linewidth=1.5)
            ax.axhline(y=50, color='r', linestyle='--', label='Warning (50%)')
            ax.set_xlabel('Time')
            ax.set_ylabel('CPU (%)')
            ax.set_title('CPU Usage Trend')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            charts['cpu_trend'] = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)

        # CPU 温度趋势图
        valid_thermal = [thermal_values[i] for i in valid_indices if thermal_values[i] is not None]
        if valid_thermal:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(valid_times[:len(valid_thermal)], valid_thermal, 'red', linewidth=1.5)
            ax.axhline(y=45, color='orange', linestyle='--', label='Warning (45C)')
            ax.axhline(y=50, color='red', linestyle='--', label='Critical (50C)')
            ax.set_xlabel('Time')
            ax.set_ylabel('Temperature (C)')
            ax.set_title('CPU Temperature Trend')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            charts['thermal_trend'] = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)

        # 内存使用率趋势图
        valid_mem_percent = [mem_percent_values[i] for i in valid_indices if mem_percent_values[i] is not None]
        if valid_mem_percent:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(valid_times[:len(valid_mem_percent)], valid_mem_percent, 'purple', linewidth=1.5)
            ax.axhline(y=80, color='orange', linestyle='--', label='Warning (80%)')
            ax.axhline(y=90, color='red', linestyle='--', label='Critical (90%)')
            ax.set_xlabel('Time')
            ax.set_ylabel('Memory Usage (%)')
            ax.set_title('System Memory Usage Trend')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            charts['memory_percent_trend'] = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)

        return charts

    def _render_html(
        self,
        title: str,
        stats: PerformanceStats,
        score: PerformanceScore,
        anomalies: List[Anomaly],
        charts_base64: Dict[str, str],
    ) -> str:
        """渲染 HTML 报告"""

        # 异常列表 HTML
        anomalies_html = ""
        if anomalies:
            for a in anomalies:
                severity_class = "anomaly-critical" if a.severity == AnomalySeverity.CRITICAL else "anomaly-warning"
                anomalies_html += f"""
                <div class="anomaly-item {severity_class}">
                    <span class="anomaly-type">{a.type.value}</span>
                    <span class="anomaly-time">{a.timestamp}</span>
                    <span class="anomaly-message">{a.message}</span>
                </div>
                """
        else:
            anomalies_html = '<div class="no-anomalies">✓ 未检测到性能异常</div>'

        # 图表 HTML
        charts_html = ""
        if 'fps_trend' in charts_base64:
            charts_html += f'<div class="chart"><h3>FPS 趋势</h3><img src="data:image/png;base64,{charts_base64["fps_trend"]}" alt="FPS Trend"></div>'
        if 'memory_trend' in charts_base64:
            charts_html += f'<div class="chart"><h3>内存趋势</h3><img src="data:image/png;base64,{charts_base64["memory_trend"]}" alt="Memory Trend"></div>'
        if 'cpu_trend' in charts_base64:
            charts_html += f'<div class="chart"><h3>CPU 趋势</h3><img src="data:image/png;base64,{charts_base64["cpu_trend"]}" alt="CPU Trend"></div>'
        if 'thermal_trend' in charts_base64:
            charts_html += f'<div class="chart"><h3>CPU 温度趋势</h3><img src="data:image/png;base64,{charts_base64["thermal_trend"]}" alt="Temperature Trend"></div>'
        if 'memory_percent_trend' in charts_base64:
            charts_html += f'<div class="chart"><h3>内存使用率趋势</h3><img src="data:image/png;base64,{charts_base64["memory_percent_trend"]}" alt="Memory Percent Trend"></div>'

        # 统计表格
        fps_row = ""
        if stats.fps:
            fps_row = f"""
            <tr>
                <td>FPS</td>
                <td>{stats.fps.avg:.1f}</td>
                <td>{stats.fps.min:.1f}</td>
                <td>{stats.fps.max:.1f}</td>
                <td>{stats.fps.p95:.1f}</td>
                <td>{stats.fps.p99:.1f}</td>
            </tr>
            """

        cpu_row = ""
        if stats.cpu:
            cpu_row = f"""
            <tr>
                <td>CPU (%)</td>
                <td>{stats.cpu.avg:.1f}</td>
                <td>{stats.cpu.min:.1f}</td>
                <td>{stats.cpu.max:.1f}</td>
                <td>{stats.cpu.p95:.1f}</td>
                <td>{stats.cpu.p99:.1f}</td>
            </tr>
            """

        mem_row = ""
        if stats.memory:
            mem_row = f"""
            <tr>
                <td>内存 (MB)</td>
                <td>{stats.memory.avg:.1f}</td>
                <td>{stats.memory.min:.1f}</td>
                <td>{stats.memory.max:.1f}</td>
                <td>{stats.memory.p95:.1f}</td>
                <td>{stats.memory.p99:.1f}</td>
            </tr>
            """

        thermal_row = ""
        if stats.thermal:
            thermal_row = f"""
            <tr>
                <td>CPU 温度 (C)</td>
                <td>{stats.thermal.avg:.1f}</td>
                <td>{stats.thermal.min:.1f}</td>
                <td>{stats.thermal.max:.1f}</td>
                <td>{stats.thermal.p95:.1f}</td>
                <td>{stats.thermal.p99:.1f}</td>
            </tr>
            """

        mem_percent_row = ""
        if stats.memory_percent:
            mem_percent_row = f"""
            <tr>
                <td>内存使用率 (%)</td>
                <td>{stats.memory_percent.avg:.1f}</td>
                <td>{stats.memory_percent.min:.1f}</td>
                <td>{stats.memory_percent.max:.1f}</td>
                <td>{stats.memory_percent.p95:.1f}</td>
                <td>{stats.memory_percent.p99:.1f}</td>
            </tr>
            """

        # 温度颜色（用于概况卡片）
        temp_color = "#ef4444" if stats.thermal_peak >= 50 else "#f59e0b" if stats.thermal_peak >= 45 else "#333"
        mem_percent_peak_display = f"{stats.memory_percent.max:.1f}%" if stats.memory_percent else "N/A"

        # 评分颜色
        grade_colors = {
            "S": "#22c55e",
            "A": "#84cc16",
            "B": "#eab308",
            "C": "#f97316",
            "D": "#ef4444",
            "F": "#dc2626",
        }
        grade_color = grade_colors.get(score.grade, "#6b7280")

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; padding: 20px; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        header p {{ opacity: 0.9; }}

        .score-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 20px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .grade {{ font-size: 72px; font-weight: bold; color: {grade_color}; }}
        .total {{ font-size: 36px; color: #666; }}
        .score-breakdown {{ display: flex; justify-content: center; gap: 30px; margin-top: 20px; flex-wrap: wrap; }}
        .score-item {{ text-align: center; }}
        .score-item .label {{ font-size: 14px; color: #888; }}
        .score-item .value {{ font-size: 24px; font-weight: bold; color: #333; }}

        section {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        section h2 {{ font-size: 20px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #eee; }}

        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f9f9f9; font-weight: 600; }}
        tr:hover {{ background: #f5f5f5; }}

        .anomaly-item {{ padding: 12px; margin-bottom: 10px; border-radius: 8px; border-left: 4px solid; }}
        .anomaly-critical {{ background: #fef2f2; border-color: #ef4444; }}
        .anomaly-warning {{ background: #fffbeb; border-color: #f59e0b; }}
        .anomaly-type {{ font-weight: bold; margin-right: 10px; }}
        .anomaly-time {{ font-size: 12px; color: #888; margin-right: 10px; }}
        .no-anomalies {{ padding: 20px; text-align: center; color: #22c55e; font-size: 18px; }}

        .charts {{ display: flex; flex-direction: column; gap: 20px; }}
        .chart {{ text-align: center; }}
        .chart img {{ max-width: 100%; border-radius: 8px; }}

        .summary-info {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .info-item {{ background: #f9f9f9; padding: 15px; border-radius: 8px; }}
        .info-item .label {{ font-size: 12px; color: #888; margin-bottom: 5px; }}
        .info-item .value {{ font-size: 18px; font-weight: bold; }}

        footer {{ text-align: center; padding: 20px; color: #888; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{title}</h1>
            <p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </header>

        <div class="score-card">
            <div class="grade">{score.grade}</div>
            <div class="total">{score.total} / 100</div>
            <p style="margin-top: 10px; color: #666;">{score.summary}</p>
            <div class="score-breakdown">
                <div class="score-item">
                    <div class="label">FPS</div>
                    <div class="value">{score.fps}/30</div>
                </div>
                <div class="score-item">
                    <div class="label">流畅度</div>
                    <div class="value">{score.fluency}/30</div>
                </div>
                <div class="score-item">
                    <div class="label">内存</div>
                    <div class="value">{score.memory}/20</div>
                </div>
                <div class="score-item">
                    <div class="label">CPU</div>
                    <div class="value">{score.cpu}/20</div>
                </div>
            </div>
        </div>

        <section>
            <h2>测试概况</h2>
            <div class="summary-info">
                <div class="info-item">
                    <div class="label">监控时长</div>
                    <div class="value">{stats.duration_seconds:.1f}s</div>
                </div>
                <div class="info-item">
                    <div class="label">采样次数</div>
                    <div class="value">{stats.sample_count}</div>
                </div>
                <div class="info-item">
                    <div class="label">内存峰值</div>
                    <div class="value">{stats.memory_peak_mb:.1f} MB</div>
                </div>
                <div class="info-item">
                    <div class="label">卡顿次数</div>
                    <div class="value">{stats.hitches_total.get('over_66ms', 0)}</div>
                </div>
                <div class="info-item">
                    <div class="label">CPU 温度峰值</div>
                    <div class="value" style="color: {temp_color}">{stats.thermal_peak:.1f} C</div>
                </div>
                <div class="info-item">
                    <div class="label">内存使用率峰值</div>
                    <div class="value">{mem_percent_peak_display}</div>
                </div>
            </div>
        </section>

        <section>
            <h2>统计摘要</h2>
            <table>
                <thead>
                    <tr>
                        <th>指标</th>
                        <th>平均值</th>
                        <th>最小值</th>
                        <th>最大值</th>
                        <th>P95</th>
                        <th>P99</th>
                    </tr>
                </thead>
                <tbody>
                    {fps_row}
                    {cpu_row}
                    {mem_row}
                    {thermal_row}
                    {mem_percent_row}
                </tbody>
            </table>
        </section>

        <section>
            <h2>异常检测</h2>
            {anomalies_html}
        </section>

        {f'<section><h2>趋势图表</h2><div class="charts">{charts_html}</div></section>' if charts_html else ''}

        <footer>
            Generated by HMNextAuto PerformanceAnalyzer
        </footer>
    </div>
</body>
</html>
"""
        return html
