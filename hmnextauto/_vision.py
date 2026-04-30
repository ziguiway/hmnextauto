# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class MatchResult:
    score: float
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> Tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2


def _require_cv2():
    try:
        import cv2  # type: ignore
        return cv2
    except Exception as e:
        raise RuntimeError(
            "OpenCV is required for vision features. "
            'Install with `pip install -U "hmnextauto[opencv-python]"` '
            "(opencv-python-headless)."
        ) from e


def find_image(
    screenshot_path: str,
    template_path: str,
    threshold: float = 0.85,
    grayscale: bool = True,
    multi_scale: bool = True,
    scale_range: Tuple[float, float] = (0.5, 2.0),
    scale_steps: int = 30,
) -> Optional[MatchResult]:
    """
    Find template in screenshot using multi-scale template matching.
    
    Args:
        screenshot_path: Path to screenshot image
        template_path: Path to template image
        threshold: Matching threshold (0.0-1.0)
        grayscale: Use grayscale matching
        multi_scale: Enable multi-scale matching
        scale_range: (min_scale, max_scale)
        scale_steps: Number of scale steps
        
    Returns:
        MatchResult if found, else None
    """
    cv2 = _require_cv2()
    import numpy as np  # type: ignore

    # Read images
    flag = cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR
    screenshot = cv2.imread(screenshot_path, flag)
    template = cv2.imread(template_path, flag)
    
    if screenshot is None:
        raise FileNotFoundError(f"Cannot read screenshot: {screenshot_path}")
    if template is None:
        raise FileNotFoundError(f"Cannot read template: {template_path}")

    h, w = template.shape[:2]
    best_match = None
    best_score = float(threshold)

    if multi_scale:
        # Multi-scale matching (user's verified logic)
        min_scale, max_scale = scale_range
        screenshot_h, screenshot_w = screenshot.shape[:2]
        
        for scale in np.linspace(min_scale, max_scale, scale_steps)[::-1]:
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # Skip if resized template exceeds screenshot bounds
            if new_w <= 0 or new_h <= 0 or new_w > screenshot_w or new_h > screenshot_h:
                continue
            
            # Resize template
            resized = cv2.resize(template, (new_w, new_h))
            
            # Template matching
            result = cv2.matchTemplate(screenshot, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            # Update best match
            if max_val >= best_score:
                best_score = float(max_val)
                best_match = MatchResult(
                    score=best_score,
                    x=int(max_loc[0]),
                    y=int(max_loc[1]),
                    w=new_w,
                    h=new_h
                )
    else:
        # Single-scale matching
        if w > screenshot.shape[1] or h > screenshot.shape[0]:
            return None
        
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        if float(max_val) >= float(threshold):
            best_match = MatchResult(
                score=float(max_val),
                x=int(max_loc[0]),
                y=int(max_loc[1]),
                w=int(w),
                h=int(h)
            )
    
    return best_match


def find_color(
    screenshot_path: str,
    rgb: Tuple[int, int, int],
    tolerance: int = 10,
    region: Optional[Tuple[int, int, int, int]] = None,
) -> Optional[Tuple[int, int]]:
    """
    Find the first pixel matching rgb within tolerance.
    """
    cv2 = _require_cv2()
    import numpy as np  # type: ignore

    img = cv2.imread(screenshot_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read screenshot: {screenshot_path}")

    bgr = np.array([rgb[2], rgb[1], rgb[0]], dtype=np.int16)
    tol = int(max(0, min(255, tolerance)))

    if region is not None:
        x1, y1, x2, y2 = region
        x1 = max(0, int(x1))
        y1 = max(0, int(y1))
        x2 = max(x1 + 1, int(x2))
        y2 = max(y1 + 1, int(y2))
        img2 = img[y1:y2, x1:x2]
        offset = (x1, y1)
    else:
        img2 = img
        offset = (0, 0)

    arr = img2.astype(np.int16)
    lo = bgr - tol
    hi = bgr + tol
    mask = (
        (arr[:, :, 0] >= lo[0])
        & (arr[:, :, 0] <= hi[0])
        & (arr[:, :, 1] >= lo[1])
        & (arr[:, :, 1] <= hi[1])
        & (arr[:, :, 2] >= lo[2])
        & (arr[:, :, 2] <= hi[2])
    )
    ys, xs = np.where(mask)
    if xs.size == 0:
        return None
    x = int(xs[0]) + offset[0]
    y = int(ys[0]) + offset[1]
    return x, y
