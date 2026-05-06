# -*- coding: utf-8 -*-
"""
性能分析器测试
"""

import json
import os
import tempfile
from datetime import datetime

import pytest

from hmnextauto._performance_analyzer import (
    Anomaly,
    AnomalySeverity,
    AnomalyType,
    MetricStats,
    PerformanceAnalyzer,
    PerformanceScore,
    PerformanceStats,
    _calc_stats,
)


class TestMetricStats:
    """MetricStats 测试"""

    def test_to_dict(self):
        """测试字典转换"""
        stats = MetricStats(
            avg=55.5,
            min=30.0,
            max=60.0,
            stdev=5.5,
            median=56.0,
            p95=59.0,
            p99=60.0,
            count=100,
        )
        d = stats.to_dict()
        assert d["avg"] == 55.5
        assert d["min"] == 30.0
        assert d["max"] == 60.0
        assert d["count"] == 100


class TestCalcStats:
    """_calc_stats 测试"""

    def test_empty_values(self):
        """测试空值"""
        result = _calc_stats([])
        assert result is None

    def test_single_value(self):
        """测试单个值"""
        result = _calc_stats([50.0])
        assert result is not None
        assert result.avg == 50.0
        assert result.min == 50.0
        assert result.max == 50.0
        assert result.stdev == 0
        assert result.count == 1

    def test_multiple_values(self):
        """测试多个值"""
        values = [10, 20, 30, 40, 50]
        result = _calc_stats(values)
        assert result is not None
        assert result.avg == 30.0
        assert result.min == 10.0
        assert result.max == 50.0
        assert result.median == 30.0
        assert result.count == 5
        assert result.stdev > 0


class TestPerformanceAnalyzer:
    """PerformanceAnalyzer 测试"""

    @pytest.fixture
    def sample_records(self):
        """生成示例数据"""
        records = []
        base_time = datetime(2026, 5, 6, 10, 0, 0)

        for i in range(20):
            ts = base_time.replace(second=i)
            records.append({
                "timestamp": ts.isoformat(),
                "fps": 55 + (i % 5),
                "cpu_percent": 20 + (i % 10),
                "memory_pss": 100000 + i * 1000,
                "hitches": {
                    "over_16ms": i % 3,
                    "over_33ms": i % 5,
                    "over_66ms": 0,
                },
            })
        return records

    @pytest.fixture
    def temp_jsonl(self, sample_records):
        """创建临时 JSONL 文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for r in sample_records:
                f.write(json.dumps(r) + "\n")
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_from_file(self, temp_jsonl):
        """测试从文件加载"""
        analyzer = PerformanceAnalyzer.from_file(temp_jsonl)
        assert analyzer.count == 20

    def test_from_file_not_found(self):
        """测试文件不存在"""
        with pytest.raises(FileNotFoundError):
            PerformanceAnalyzer.from_file("nonexistent.jsonl")

    def test_stats(self, temp_jsonl):
        """测试统计计算"""
        analyzer = PerformanceAnalyzer.from_file(temp_jsonl)
        stats = analyzer.stats()

        assert stats.fps is not None
        assert stats.cpu is not None
        assert stats.memory is not None
        assert stats.sample_count == 20
        assert stats.duration_seconds > 0
        assert stats.memory_peak_mb > 0

    def test_stats_cached(self, temp_jsonl):
        """测试统计缓存"""
        analyzer = PerformanceAnalyzer.from_file(temp_jsonl)
        stats1 = analyzer.stats()
        stats2 = analyzer.stats()
        assert stats1 is stats2  # 同一对象

    def test_detect_anomalies_no_anomalies(self, temp_jsonl):
        """测试无异常情况"""
        analyzer = PerformanceAnalyzer.from_file(temp_jsonl)
        anomalies = analyzer.detect_anomalies()
        # 正常数据不应有严重异常
        critical = [a for a in anomalies if a.severity == AnomalySeverity.CRITICAL]
        assert len(critical) == 0

    def test_detect_anomalies_fps_drop(self):
        """测试 FPS 突降检测"""
        records = []
        base_time = datetime(2026, 5, 6, 10, 0, 0)

        for i in range(10):
            ts = base_time.replace(second=i)
            fps = 60 if i < 5 else 20  # 第 5 帧开始突降
            records.append({
                "timestamp": ts.isoformat(),
                "fps": fps,
                "cpu_percent": 30,
                "memory_pss": 100000,
                "hitches": {"over_16ms": 0, "over_33ms": 0, "over_66ms": 0},
            })

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            path = f.name

        try:
            analyzer = PerformanceAnalyzer.from_file(path)
            anomalies = analyzer.detect_anomalies()

            fps_drops = [a for a in anomalies if a.type == AnomalyType.FPS_DROP]
            assert len(fps_drops) > 0
        finally:
            os.unlink(path)

    def test_detect_anomalies_memory_leak(self):
        """测试内存泄漏检测"""
        records = []
        base_time = datetime(2026, 5, 6, 10, 0, 0)

        for i in range(20):
            ts = base_time.replace(second=i)
            records.append({
                "timestamp": ts.isoformat(),
                "fps": 55,
                "cpu_percent": 30,
                "memory_pss": 100000 + i * 10000,  # 持续增长
                "hitches": {"over_16ms": 0, "over_33ms": 0, "over_66ms": 0},
            })

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            path = f.name

        try:
            analyzer = PerformanceAnalyzer.from_file(path)
            anomalies = analyzer.detect_anomalies()

            leaks = [a for a in anomalies if a.type == AnomalyType.MEMORY_LEAK]
            assert len(leaks) > 0
        finally:
            os.unlink(path)

    def test_detect_anomalies_jank(self):
        """测试严重卡顿检测"""
        records = []
        base_time = datetime(2026, 5, 6, 10, 0, 0)

        for i in range(10):
            ts = base_time.replace(second=i)
            records.append({
                "timestamp": ts.isoformat(),
                "fps": 55,
                "cpu_percent": 30,
                "memory_pss": 100000,
                "hitches": {"over_16ms": 1, "over_33ms": 1, "over_66ms": 1},  # 严重卡顿
            })

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            path = f.name

        try:
            analyzer = PerformanceAnalyzer.from_file(path)
            anomalies = analyzer.detect_anomalies()

            janks = [a for a in anomalies if a.type == AnomalyType.JANK]
            assert len(janks) == 10  # 每帧都有卡顿
        finally:
            os.unlink(path)

    def test_score(self, temp_jsonl):
        """测试性能评分"""
        analyzer = PerformanceAnalyzer.from_file(temp_jsonl)
        score = analyzer.score()

        assert 0 <= score.fps <= 30
        assert 0 <= score.fluency <= 30
        assert 0 <= score.memory <= 20
        assert 0 <= score.cpu <= 20
        assert 0 <= score.total <= 100
        assert score.grade in ["S", "A", "B", "C", "D", "F"]
        assert score.summary != ""

    def test_score_grade_s(self):
        """测试 S 级评分"""
        records = []
        base_time = datetime(2026, 5, 6, 10, 0, 0)

        for i in range(20):
            ts = base_time.replace(second=i)
            records.append({
                "timestamp": ts.isoformat(),
                "fps": 60,  # 高 FPS
                "cpu_percent": 15,  # 低 CPU
                "memory_pss": 100000,  # 低内存
                "hitches": {"over_16ms": 0, "over_33ms": 0, "over_66ms": 0},  # 无卡顿
            })

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            path = f.name

        try:
            analyzer = PerformanceAnalyzer.from_file(path)
            score = analyzer.score()
            assert score.grade == "S"
            assert score.total >= 90
        finally:
            os.unlink(path)

    def test_score_grade_f(self):
        """测试 F 级评分"""
        records = []
        base_time = datetime(2026, 5, 6, 10, 0, 0)

        for i in range(20):
            ts = base_time.replace(second=i)
            records.append({
                "timestamp": ts.isoformat(),
                "fps": 15,  # 低 FPS
                "cpu_percent": 90,  # 高 CPU
                "memory_pss": 1500000,  # 高内存
                "hitches": {"over_16ms": 10, "over_33ms": 5, "over_66ms": 2},  # 严重卡顿
            })

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            path = f.name

        try:
            analyzer = PerformanceAnalyzer.from_file(path)
            score = analyzer.score()
            assert score.grade == "F"
            assert score.total < 50
        finally:
            os.unlink(path)

    def test_generate_report(self, temp_jsonl):
        """测试生成 HTML 报告"""
        analyzer = PerformanceAnalyzer.from_file(temp_jsonl)

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            report_path = f.name

        try:
            result = analyzer.generate_report(report_path, include_charts=False)
            assert os.path.exists(report_path)

            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "性能分析报告" in content
                assert "<!DOCTYPE html>" in content
        finally:
            if os.path.exists(report_path):
                os.unlink(report_path)

    def test_generate_report_with_charts(self, temp_jsonl):
        """测试生成带图表的报告"""
        pytest.importorskip("matplotlib")

        analyzer = PerformanceAnalyzer.from_file(temp_jsonl)

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            report_path = f.name

        try:
            result = analyzer.generate_report(report_path, include_charts=True)
            assert os.path.exists(report_path)

            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "data:image/png;base64" in content
        finally:
            if os.path.exists(report_path):
                os.unlink(report_path)

    def test_anomaly_to_dict(self):
        """测试异常转字典"""
        anomaly = Anomaly(
            type=AnomalyType.FPS_DROP,
            severity=AnomalySeverity.CRITICAL,
            timestamp="2026-05-06T10:00:00",
            message="FPS 突降",
            value=20.0,
            threshold=30.0,
        )
        d = anomaly.to_dict()
        assert d["type"] == "fps_drop"
        assert d["severity"] == "critical"
        assert d["message"] == "FPS 突降"

    def test_performance_stats_to_dict(self, temp_jsonl):
        """测试统计转字典"""
        analyzer = PerformanceAnalyzer.from_file(temp_jsonl)
        stats = analyzer.stats()
        d = stats.to_dict()

        assert "fps" in d
        assert "cpu" in d
        assert "memory" in d
        assert "sample_count" in d
        assert "duration_seconds" in d

    def test_performance_score_to_dict(self, temp_jsonl):
        """测试评分转字典"""
        analyzer = PerformanceAnalyzer.from_file(temp_jsonl)
        score = analyzer.score()
        d = score.to_dict()

        assert d["fps"] == score.fps
        assert d["total"] == score.total
        assert d["grade"] == score.grade


class TestPerformanceAnalyzerEdgeCases:
    """边界情况测试"""

    def test_minimal_records(self):
        """测试最少记录"""
        records = [{
            "timestamp": datetime(2026, 5, 6, 10, 0, 0).isoformat(),
            "fps": 55,
        }]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            f.write(json.dumps(records[0]) + "\n")
            path = f.name

        try:
            analyzer = PerformanceAnalyzer.from_file(path)
            stats = analyzer.stats()
            assert stats.sample_count == 1

            anomalies = analyzer.detect_anomalies()
            assert len(anomalies) == 0  # 单条记录无法检测异常
        finally:
            os.unlink(path)

    def test_missing_fields(self):
        """测试缺失字段"""
        records = []
        base_time = datetime(2026, 5, 6, 10, 0, 0)

        for i in range(5):
            ts = base_time.replace(second=i)
            records.append({
                "timestamp": ts.isoformat(),
                # 只有 fps，没有其他字段
                "fps": 55,
            })

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            path = f.name

        try:
            analyzer = PerformanceAnalyzer.from_file(path)
            stats = analyzer.stats()

            assert stats.fps is not None
            assert stats.cpu is None
            assert stats.memory is None
        finally:
            os.unlink(path)

    def test_empty_jsonl(self):
        """测试空文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            path = f.name

        try:
            with pytest.raises(ValueError, match="为空"):
                PerformanceAnalyzer.from_file(path)
        finally:
            os.unlink(path)

    def test_invalid_json(self):
        """测试无效 JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            f.write("not valid json\n")
            path = f.name

        try:
            with pytest.raises(ValueError, match="JSON 解析失败"):
                PerformanceAnalyzer.from_file(path)
        finally:
            os.unlink(path)
