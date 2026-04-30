# -*- coding: utf-8 -*-


import time
import socket
import re
import struct
from functools import wraps
from typing import Union, Tuple

from .proto import Bounds


def delay(func):
    """
    After each UI operation, it is necessary to wait for a while to ensure the stability of the UI,
    so as not to affect the next UI operation.
    """
    DELAY_TIME = 0.6

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        time.sleep(DELAY_TIME)
        return result
    return wrapper


class FreePort:
    def __init__(self):
        self._start = 10000
        self._end = 20000
        self._now = self._start - 1

    def get(self) -> int:
        while True:
            self._now += 1
            if self._now > self._end:
                self._now = self._start
            if not self.is_port_in_use(self._now):
                return self._now

    @staticmethod
    def is_port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0


def parse_bounds(bounds: str) -> Union[Bounds, None]:
    """
    Parse bounds string to Bounds.
    bounds is str, like: "[832,1282][1125,1412]"
    """
    result = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
    if result:
        g = result.groups()
        return Bounds(int(g[0]),
                      int(g[1]),
                      int(g[2]),
                      int(g[3]))
    return None


def _png_size(path: str) -> Tuple[int, int]:
    with open(path, "rb") as f:
        sig = f.read(8)
        if sig != b"\x89PNG\r\n\x1a\n":
            raise ValueError("not png")
        f.read(4)  # length
        ctype = f.read(4)
        if ctype != b"IHDR":
            raise ValueError("png missing IHDR")
        w, h = struct.unpack(">II", f.read(8))
        return int(w), int(h)


def _jpeg_size(path: str) -> Tuple[int, int]:
    with open(path, "rb") as f:
        if f.read(2) != b"\xff\xd8":
            raise ValueError("not jpeg")
        while True:
            b = f.read(1)
            if not b:
                break
            if b != b"\xff":
                continue
            # skip fill bytes
            while True:
                m = f.read(1)
                if not m:
                    break
                if m != b"\xff":
                    break
            if not m:
                break
            marker = m[0]
            if marker in (0xD8, 0xD9):
                continue
            ln = f.read(2)
            if len(ln) != 2:
                break
            seg_len = struct.unpack(">H", ln)[0]
            if seg_len < 2:
                break
            if marker in (0xC0, 0xC2):  # SOF0 / SOF2
                f.read(1)  # precision
                h, w = struct.unpack(">HH", f.read(4))
                return int(w), int(h)
            f.seek(seg_len - 2, 1)
    raise ValueError("jpeg size not found")


def image_size(path: str) -> Tuple[int, int]:
    """
    Return (width, height) for PNG/JPEG without third-party dependencies.
    """
    p = str(path).lower()
    if p.endswith(".png"):
        return _png_size(path)
    if p.endswith(".jpg") or p.endswith(".jpeg"):
        return _jpeg_size(path)
    try:
        return _png_size(path)
    except Exception:
        return _jpeg_size(path)