# -*- coding: utf-8 -*-
"""
OCR 文字识别模块
基于 EasyOCR 实现，支持全屏/区域识别、文字查找、点击等操作

使用方式:
    # 基础用法
    text = d.ocr.read()  # 全屏识别
    text = d.ocr.read(region=(100, 100, 500, 200))  # 区域识别

    # 查找文字
    pos = d.ocr.find_text("登录")  # 返回 (x, y) 或 None

    # 识别并点击
    d.ocr.click_text("确定")  # 找到文字并点击
"""

from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from . import logger

if TYPE_CHECKING:
    from .driver import Driver


@dataclass
class OCRResult:
    """OCR 识别结果"""

    text: str
    bbox: Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int], Tuple[int, int]]
    confidence: float

    @property
    def center(self) -> Tuple[int, int]:
        """获取文字中心坐标"""
        x_coords = [p[0] for p in self.bbox]
        y_coords = [p[1] for p in self.bbox]
        return (sum(x_coords) // 4, sum(y_coords) // 4)

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """获取边界框 (left, top, right, bottom)"""
        x_coords = [p[0] for p in self.bbox]
        y_coords = [p[1] for p in self.bbox]
        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "center": self.center,
            "bounds": self.bounds,
        }


class OCR:
    """
    OCR 文字识别类

    支持功能:
    - 全屏/区域文字识别
    - 查找指定文字位置
    - 识别并点击文字
    - 多语言支持
    """

    def __init__(self, driver: "Driver") -> None:
        self._d = driver
        self._reader: Any = None
        self._default_languages = ["ch_sim", "en"]

    def _require_easyocr(self):
        """检查并导入 easyocr"""
        try:
            import easyocr

            return easyocr
        except ImportError:
            raise ImportError(
                "OCR 功能需要安装 easyocr。\n"
                "请运行: pip install hmnextauto[ocr]\n"
                "或直接运行: pip install easyocr"
            ) from None

    def _get_reader(
        self,
        languages: Optional[List[str]] = None,
        gpu: bool = False,
        download_enabled: bool = True,
    ) -> Any:
        """
        获取或创建 EasyOCR Reader (懒加载)

        Args:
            languages: 语言列表，默认 ["ch_sim", "en"]
            gpu: 是否使用 GPU 加速
            download_enabled: 是否允许下载模型

        Returns:
            EasyOCR Reader 实例
        """
        if languages is None:
            languages = self._default_languages

        # 如果已有 reader 且语言相同，直接返回
        if self._reader is not None:
            return self._reader

        easyocr = self._require_easyocr()

        # 设置模型存储路径
        model_storage_directory = os.path.join(
            os.path.expanduser("~"), ".hmnextauto", "ocr_models"
        )
        os.makedirs(model_storage_directory, exist_ok=True)

        logger.info(f"初始化 OCR Reader，语言: {languages}, GPU: {gpu}")
        self._reader = easyocr.Reader(
            languages,
            gpu=gpu,
            download_enabled=download_enabled,
            model_storage_directory=model_storage_directory,
        )
        return self._reader

    def _crop_image(
        self, image_path: str, region: Tuple[int, int, int, int]
    ) -> str:
        """
        裁剪图片

        Args:
            image_path: 原图路径
            region: 裁剪区域 (x1, y1, x2, y2)

        Returns:
            裁剪后的图片路径
        """
        try:
            import cv2
        except ImportError:
            raise ImportError(
                "OCR 功能需要安装 opencv-python。\n"
                "请运行: pip install hmnextauto[opencv-python]"
            ) from None

        x1, y1, x2, y2 = region
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")

        # 确保坐标在图片范围内
        h, w = img.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        cropped = img[y1:y2, x1:x2]

        # 保存裁剪后的图片
        cropped_path = image_path + ".cropped.png"
        cv2.imwrite(cropped_path, cropped)

        return cropped_path

    def _parse_results(
        self,
        raw_results: List,
        region_offset: Optional[Tuple[int, int]] = None,
    ) -> List[OCRResult]:
        """
        解析 EasyOCR 返回结果

        Args:
            raw_results: EasyOCR 原始结果
            region_offset: 区域偏移量 (x_offset, y_offset)

        Returns:
            OCRResult 列表
        """
        results = []
        for item in raw_results:
            if len(item) >= 3:
                bbox, text, confidence = item[0], item[1], item[2]
            else:
                continue

            # 转换 bbox 格式
            bbox_points = []
            for point in bbox:
                x, y = int(point[0]), int(point[1])
                if region_offset:
                    x += region_offset[0]
                    y += region_offset[1]
                bbox_points.append((x, y))

            results.append(
                OCRResult(
                    text=text,
                    bbox=tuple(bbox_points),  # type: ignore
                    confidence=float(confidence),
                )
            )

        return results

    def read(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        languages: Optional[List[str]] = None,
        gpu: bool = False,
        detail: bool = True,
        paragraph: bool = False,
        min_confidence: float = 0.0,
    ) -> Union[List[OCRResult], List[str]]:
        """
        识别屏幕文字

        Args:
            region: 识别区域 (x1, y1, x2, y2)，None 表示全屏
            languages: 语言列表，默认 ["ch_sim", "en"]
            gpu: 是否使用 GPU 加速
            detail: True 返回详细结果，False 只返回文字列表
            paragraph: 是否合并为段落
            min_confidence: 最小置信度阈值

        Returns:
            detail=True: List[OCRResult]
            detail=False: List[str] 文字列表

        Example:
            # 全屏识别
            results = d.ocr.read()

            # 区域识别
            results = d.ocr.read(region=(100, 100, 500, 200))

            # 只获取文字
            texts = d.ocr.read(detail=False)
        """
        # 截图
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot_path = f.name

        self._d.screenshot(screenshot_path)
        logger.debug(f"截图保存至: {screenshot_path}")

        # 获取 reader
        reader = self._get_reader(languages, gpu)

        # 处理区域识别
        region_offset = None
        image_path = screenshot_path

        if region:
            x1, y1, x2, y2 = region
            image_path = self._crop_image(screenshot_path, region)
            region_offset = (x1, y1)
            logger.debug(f"裁剪区域: {region}, 偏移: {region_offset}")

        # 执行 OCR
        logger.info(f"开始 OCR 识别...")
        start_time = time.time()

        raw_results = reader.readtext(
            image_path,
            detail=1,
            paragraph=paragraph,
        )

        elapsed = time.time() - start_time
        logger.info(f"OCR 识别完成，耗时: {elapsed:.2f}s，识别到 {len(raw_results)} 个文本块")

        # 解析结果
        results = self._parse_results(raw_results, region_offset)

        # 过滤置信度
        if min_confidence > 0:
            results = [r for r in results if r.confidence >= min_confidence]
            logger.debug(f"置信度过滤后剩余 {len(results)} 个结果")

        # 清理临时文件
        try:
            os.unlink(screenshot_path)
            if region and image_path != screenshot_path:
                os.unlink(image_path)
        except Exception:
            pass

        if detail:
            return results
        else:
            return [r.text for r in results]

    def find_text(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        languages: Optional[List[str]] = None,
        gpu: bool = False,
        exact: bool = False,
        min_confidence: float = 0.5,
    ) -> Optional[Tuple[int, int]]:
        """
        查找文字位置

        Args:
            text: 要查找的文字
            region: 搜索区域，None 表示全屏
            languages: 语言列表
            gpu: 是否使用 GPU
            exact: 是否精确匹配
            min_confidence: 最小置信度

        Returns:
            文字中心坐标 (x, y)，未找到返回 None

        Example:
            pos = d.ocr.find_text("登录")
            if pos:
                print(f"找到文字，位置: {pos}")
        """
        results = self.read(
            region=region,
            languages=languages,
            gpu=gpu,
            detail=True,
            min_confidence=min_confidence,
        )

        for result in results:
            if exact:
                if result.text == text:
                    logger.info(f"找到文字 '{text}'，位置: {result.center}")
                    return result.center
            else:
                if text in result.text:
                    logger.info(f"找到文字 '{text}' (匹配: '{result.text}')，位置: {result.center}")
                    return result.center

        logger.debug(f"未找到文字: {text}")
        return None

    def find_all_text(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        languages: Optional[List[str]] = None,
        gpu: bool = False,
        exact: bool = False,
        min_confidence: float = 0.5,
    ) -> List[Tuple[int, int]]:
        """
        查找所有匹配文字的位置

        Args:
            text: 要查找的文字
            region: 搜索区域
            languages: 语言列表
            gpu: 是否使用 GPU
            exact: 是否精确匹配
            min_confidence: 最小置信度

        Returns:
            所有匹配文字的中心坐标列表

        Example:
            positions = d.ocr.find_all_text("确定")
            for pos in positions:
                print(f"位置: {pos}")
        """
        results = self.read(
            region=region,
            languages=languages,
            gpu=gpu,
            detail=True,
            min_confidence=min_confidence,
        )

        positions = []
        for result in results:
            if exact:
                if result.text == text:
                    positions.append(result.center)
            else:
                if text in result.text:
                    positions.append(result.center)

        logger.info(f"找到 {len(positions)} 个 '{text}' 文字")
        return positions

    def click_text(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        languages: Optional[List[str]] = None,
        gpu: bool = False,
        exact: bool = False,
        min_confidence: float = 0.5,
        timeout: float = 10.0,
        interval: float = 0.5,
    ) -> bool:
        """
        查找并点击文字

        Args:
            text: 要点击的文字
            region: 搜索区域
            languages: 语言列表
            gpu: 是否使用 GPU
            exact: 是否精确匹配
            min_confidence: 最小置信度
            timeout: 超时时间（秒）
            interval: 重试间隔（秒）

        Returns:
            True 表示点击成功，False 表示未找到

        Example:
            if d.ocr.click_text("登录", timeout=10):
                print("点击成功")
        """
        deadline = time.time() + timeout

        while True:
            pos = self.find_text(
                text=text,
                region=region,
                languages=languages,
                gpu=gpu,
                exact=exact,
                min_confidence=min_confidence,
            )

            if pos:
                self._d.click(pos[0], pos[1])
                logger.info(f"点击文字 '{text}' 成功，位置: {pos}")
                return True

            if time.time() >= deadline:
                logger.warning(f"点击文字 '{text}' 超时")
                return False

            time.sleep(interval)

    def wait_text(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        languages: Optional[List[str]] = None,
        gpu: bool = False,
        exact: bool = False,
        min_confidence: float = 0.5,
        timeout: float = 20.0,
        interval: float = 0.5,
    ) -> bool:
        """
        等待文字出现

        Args:
            text: 要等待的文字
            region: 搜索区域
            languages: 语言列表
            gpu: 是否使用 GPU
            exact: 是否精确匹配
            min_confidence: 最小置信度
            timeout: 超时时间（秒）
            interval: 轮询间隔（秒）

        Returns:
            True 表示文字出现，False 表示超时

        Example:
            if d.ocr.wait_text("加载完成", timeout=30):
                print("加载完成")
        """
        deadline = time.time() + timeout

        while True:
            pos = self.find_text(
                text=text,
                region=region,
                languages=languages,
                gpu=gpu,
                exact=exact,
                min_confidence=min_confidence,
            )

            if pos:
                logger.info(f"文字 '{text}' 已出现")
                return True

            if time.time() >= deadline:
                logger.warning(f"等待文字 '{text}' 超时")
                return False

            time.sleep(interval)

    def wait_text_gone(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        languages: Optional[List[str]] = None,
        gpu: bool = False,
        exact: bool = False,
        min_confidence: float = 0.5,
        timeout: float = 20.0,
        interval: float = 0.5,
    ) -> bool:
        """
        等待文字消失

        Args:
            text: 要等待消失的文字
            region: 搜索区域
            languages: 语言列表
            gpu: 是否使用 GPU
            exact: 是否精确匹配
            min_confidence: 最小置信度
            timeout: 超时时间（秒）
            interval: 轮询间隔（秒）

        Returns:
            True 表示文字消失，False 表示超时

        Example:
            if d.ocr.wait_text_gone("加载中"):
                print("加载完成")
        """
        deadline = time.time() + timeout

        while True:
            pos = self.find_text(
                text=text,
                region=region,
                languages=languages,
                gpu=gpu,
                exact=exact,
                min_confidence=min_confidence,
            )

            if pos is None:
                logger.info(f"文字 '{text}' 已消失")
                return True

            if time.time() >= deadline:
                logger.warning(f"等待文字 '{text}' 消失超时")
                return False

            time.sleep(interval)

    def read_text_in_region(
        self,
        region: Tuple[int, int, int, int],
        languages: Optional[List[str]] = None,
        gpu: bool = False,
    ) -> str:
        """
        读取指定区域内的所有文字（合并为单个字符串）

        Args:
            region: 识别区域 (x1, y1, x2, y2)
            languages: 语言列表
            gpu: 是否使用 GPU

        Returns:
            合并后的文字字符串

        Example:
            text = d.ocr.read_text_in_region((100, 100, 500, 200))
            print(f"区域文字: {text}")
        """
        results = self.read(
            region=region,
            languages=languages,
            gpu=gpu,
            detail=True,
        )

        texts = [r.text for r in results]
        return " ".join(texts)