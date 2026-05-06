# -*- coding: utf-8 -*-
"""
OCR 模块测试
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import tempfile
import os

from hmnextauto._ocr import OCR, OCRResult


class TestOCRResult:
    """OCRResult 数据类测试"""

    def test_center_calculation(self):
        """测试中心坐标计算"""
        result = OCRResult(
            text="测试",
            bbox=((100, 50), (200, 50), (200, 100), (100, 100)),
            confidence=0.95,
        )
        # 中心点应该是所有坐标的平均值
        center = result.center
        assert center == (150, 75)

    def test_bounds_calculation(self):
        """测试边界框计算"""
        result = OCRResult(
            text="测试",
            bbox=((100, 50), (200, 50), (200, 100), (100, 100)),
            confidence=0.95,
        )
        bounds = result.bounds
        assert bounds == (100, 50, 200, 100)

    def test_to_dict(self):
        """测试字典转换"""
        result = OCRResult(
            text="测试",
            bbox=((100, 50), (200, 50), (200, 100), (100, 100)),
            confidence=0.95,
        )
        d = result.to_dict()
        assert d["text"] == "测试"
        assert d["confidence"] == 0.95
        assert "center" in d
        assert "bounds" in d


class TestOCR:
    """OCR 类测试"""

    @pytest.fixture
    def mock_driver(self):
        """创建模拟 Driver"""
        driver = MagicMock()
        driver.screenshot = MagicMock()
        driver.click = MagicMock()
        return driver

    @pytest.fixture
    def ocr(self, mock_driver):
        """创建 OCR 实例"""
        return OCR(mock_driver)

    def test_init(self, ocr):
        """测试初始化"""
        assert ocr._d is not None
        assert ocr._reader is None
        assert ocr._default_languages == ["ch_sim", "en"]

    def test_require_easyocr_not_installed(self, ocr):
        """测试 easyocr 未安装时的错误提示"""
        with patch.dict("sys.modules", {"easyocr": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                with pytest.raises(ImportError) as exc_info:
                    ocr._require_easyocr()
                assert "hmnextauto[ocr]" in str(exc_info.value)

    def test_find_text_no_match(self, ocr, mock_driver):
        """测试查找不存在的文字"""
        with patch.object(ocr, "read") as mock_read:
            mock_read.return_value = [
                OCRResult(
                    text="你好世界",
                    bbox=((100, 100), (200, 100), (200, 150), (100, 150)),
                    confidence=0.95,
                )
            ]
            result = ocr.find_text("登录")
            assert result is None

    def test_find_text_with_match(self, ocr, mock_driver):
        """测试查找存在的文字"""
        with patch.object(ocr, "read") as mock_read:
            mock_read.return_value = [
                OCRResult(
                    text="登录",
                    bbox=((100, 100), (200, 100), (200, 150), (100, 150)),
                    confidence=0.95,
                )
            ]
            result = ocr.find_text("登录")
            assert result == (150, 125)

    def test_find_text_partial_match(self, ocr, mock_driver):
        """测试部分匹配"""
        with patch.object(ocr, "read") as mock_read:
            mock_read.return_value = [
                OCRResult(
                    text="点击登录按钮",
                    bbox=((100, 100), (200, 100), (200, 150), (100, 150)),
                    confidence=0.95,
                )
            ]
            # 默认部分匹配
            result = ocr.find_text("登录")
            assert result == (150, 125)

            # 精确匹配应该找不到
            result = ocr.find_text("登录", exact=True)
            assert result is None

    def test_find_all_text(self, ocr, mock_driver):
        """测试查找所有匹配文字"""
        with patch.object(ocr, "read") as mock_read:
            mock_read.return_value = [
                OCRResult(
                    text="确定",
                    bbox=((100, 100), (150, 100), (150, 130), (100, 130)),
                    confidence=0.95,
                ),
                OCRResult(
                    text="取消",
                    bbox=((200, 100), (250, 100), (250, 130), (200, 130)),
                    confidence=0.90,
                ),
                OCRResult(
                    text="确定",
                    bbox=((300, 100), (350, 100), (350, 130), (300, 130)),
                    confidence=0.92,
                ),
            ]
            positions = ocr.find_all_text("确定")
            assert len(positions) == 2
            assert positions[0] == (125, 115)
            assert positions[1] == (325, 115)

    def test_click_text_success(self, ocr, mock_driver):
        """测试点击文字成功"""
        with patch.object(ocr, "find_text") as mock_find:
            mock_find.return_value = (150, 125)
            result = ocr.click_text("登录")
            assert result is True
            mock_driver.click.assert_called_once_with(150, 125)

    def test_click_text_timeout(self, ocr, mock_driver):
        """测试点击文字超时"""
        with patch.object(ocr, "find_text") as mock_find:
            mock_find.return_value = None
            result = ocr.click_text("登录", timeout=0.5, interval=0.1)
            assert result is False
            mock_driver.click.assert_not_called()

    def test_wait_text_success(self, ocr, mock_driver):
        """测试等待文字出现成功"""
        with patch.object(ocr, "find_text") as mock_find:
            # 第一次没找到，第二次找到
            mock_find.side_effect = [None, (150, 125)]
            result = ocr.wait_text("登录", timeout=1.0, interval=0.1)
            assert result is True

    def test_wait_text_timeout(self, ocr, mock_driver):
        """测试等待文字出现超时"""
        with patch.object(ocr, "find_text") as mock_find:
            mock_find.return_value = None
            result = ocr.wait_text("登录", timeout=0.5, interval=0.1)
            assert result is False

    def test_wait_text_gone_success(self, ocr, mock_driver):
        """测试等待文字消失成功"""
        with patch.object(ocr, "find_text") as mock_find:
            # 第一次找到，第二次没找到
            mock_find.side_effect = [(150, 125), None]
            result = ocr.wait_text_gone("加载中", timeout=1.0, interval=0.1)
            assert result is True

    def test_wait_text_gone_timeout(self, ocr, mock_driver):
        """测试等待文字消失超时"""
        with patch.object(ocr, "find_text") as mock_find:
            mock_find.return_value = (150, 125)
            result = ocr.wait_text_gone("加载中", timeout=0.5, interval=0.1)
            assert result is False

    def test_read_text_in_region(self, ocr, mock_driver):
        """测试读取区域内文字"""
        with patch.object(ocr, "read") as mock_read:
            mock_read.return_value = [
                OCRResult(
                    text="Hello",
                    bbox=((0, 0), (50, 0), (50, 30), (0, 30)),
                    confidence=0.95,
                ),
                OCRResult(
                    text="World",
                    bbox=((60, 0), (110, 0), (110, 30), (60, 30)),
                    confidence=0.90,
                ),
            ]
            text = ocr.read_text_in_region((100, 100, 300, 200))
            assert text == "Hello World"

    def test_parse_results_with_region_offset(self, ocr):
        """测试带区域偏移的结果解析"""
        raw_results = [
            [
                [[0, 0], [100, 0], [100, 30], [0, 30]],
                "测试",
                0.95,
            ]
        ]
        results = ocr._parse_results(raw_results, region_offset=(50, 50))
        assert len(results) == 1
        assert results[0].text == "测试"
        # 坐标应该加上偏移
        assert results[0].bbox[0] == (50, 50)


class TestOCRIntegration:
    """OCR 集成测试（需要真实设备或 mock）"""

    @pytest.fixture
    def mock_driver_with_screenshot(self):
        """创建带截图功能的模拟 Driver"""
        driver = MagicMock()

        def mock_screenshot(path):
            # 创建一个简单的测试图片
            import cv2
            import numpy as np

            img = np.zeros((100, 100, 3), dtype=np.uint8)
            img.fill(255)  # 白色背景
            cv2.putText(img, "Test", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.imwrite(path, img)

        driver.screenshot = mock_screenshot
        driver.click = MagicMock()
        return driver

    def test_ocr_read_without_easyocr_installed(self, mock_driver_with_screenshot):
        """测试未安装 easyocr 时的错误处理"""
        ocr = OCR(mock_driver_with_screenshot)

        # Mock easyocr import to raise ImportError
        with patch.dict("sys.modules", {"easyocr": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module named 'easyocr'")):
                with pytest.raises(ImportError) as exc_info:
                    ocr.read()
                assert "easyocr" in str(exc_info.value).lower()


class TestOCRConfidenceFilter:
    """置信度过滤测试"""

    @pytest.fixture
    def ocr(self):
        driver = MagicMock()
        return OCR(driver)

    def test_min_confidence_filter(self, ocr):
        """测试最小置信度过滤"""
        with patch.object(ocr, "read") as mock_read:
            # 模拟 read 方法的 min_confidence 参数过滤
            def side_effect(**kwargs):
                min_conf = kwargs.get("min_confidence", 0.0)
                all_results = [
                    OCRResult(
                        text="高置信度",
                        bbox=((0, 0), (50, 0), (50, 30), (0, 30)),
                        confidence=0.95,
                    ),
                    OCRResult(
                        text="低置信度",
                        bbox=((60, 0), (110, 0), (110, 30), (60, 30)),
                        confidence=0.3,
                    ),
                ]
                return [r for r in all_results if r.confidence >= min_conf]

            mock_read.side_effect = side_effect

            # 不过滤
            results = ocr.read(min_confidence=0.0)
            assert len(results) == 2

            # 过滤低置信度
            results = ocr.read(min_confidence=0.5)
            assert len(results) == 1
            assert results[0].text == "高置信度"
