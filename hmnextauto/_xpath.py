# -*- coding: utf-8 -*-

import re
import time
from typing import Dict, Optional

from lxml import etree
from functools import cached_property

from . import logger
from .proto import Bounds
from .driver import Driver
from .utils import delay, parse_bounds
from .exception import XmlElementNotFoundError

# Same defaults as UiObject.wait / wait_gone
_DEFAULT_XPATH_WAIT_TIMEOUT = 20.0
_WAIT_POLL_INTERVAL = 0.1


class _XPath:
    def __init__(self, d: Driver):
        self._d = d

    def __call__(self, xpath: str) -> "_XMLElement":
        return _XPath._resolve(self._d, xpath)

    @staticmethod
    def _resolve(d: Driver, xpath: str) -> "_XMLElement":
        """Evaluate *xpath* against the current view hierarchy; returns a bound _XMLElement."""
        hierarchy: Dict = d.dump_hierarchy()
        if not hierarchy:
            raise RuntimeError("hierarchy is empty")

        xml = _XPath._json2xml(hierarchy)
        result = xml.xpath(xpath)

        if len(result) > 0:
            node = result[0]
            raw_bounds: str = node.attrib.get("bounds")  # [832,1282][1125,1412]
            bounds: Bounds = parse_bounds(raw_bounds)
            logger.debug(f"{xpath} Bounds: {bounds}")
            _xe = _XMLElement(bounds, d, xpath)
            setattr(_xe, "attrib_info", node.attrib)
            return _xe

        return _XMLElement(None, d, xpath)

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Remove XML-incompatible control characters."""
        return re.sub(r'[\x00-\x1F\x7F]', '', text)

    @staticmethod
    def _json2xml(hierarchy: Dict) -> etree.Element:
        """Convert JSON-like hierarchy to XML."""
        attributes = hierarchy.get("attributes", {})

        # 过滤所有属性的值，确保无非法字符
        cleaned_attributes = {k: _XPath._sanitize_text(str(v)) for k, v in attributes.items()}

        tag = cleaned_attributes.get("type", "orgRoot") or "orgRoot"
        xml = etree.Element(tag, attrib=cleaned_attributes)

        children = hierarchy.get("children", [])
        for item in children:
            xml.append(_XPath._json2xml(item))

        return xml


class _XMLElement:
    def __init__(self, bounds: Optional[Bounds], d: Driver, xpath: str) -> None:
        self.bounds = bounds
        self._d = d
        self._xpath = xpath

    def _invalidate_center_cache(self) -> None:
        self.__dict__.pop("center", None)

    def _merge_state_from(self, el: "_XMLElement") -> None:
        self.bounds = el.bounds
        if hasattr(el, "attrib_info"):
            self.attrib_info = el.attrib_info
        else:
            self.__dict__.pop("attrib_info", None)
        self._invalidate_center_cache()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Re-query the hierarchy until this xpath matches an element, or the timeout elapses.
        If found, this object's bounds (and :attr:`attrib_info` if present) are updated so
        a subsequent :meth:`click` reuses the resolved node.

        Same timeout semantics as :meth:`hmnextauto._uiobject.UiObject.wait` (seconds, default 20).
        """
        if timeout is None:
            timeout = _DEFAULT_XPATH_WAIT_TIMEOUT
        deadline = time.time() + max(0.0, float(timeout))
        while True:
            el = _XPath._resolve(self._d, self._xpath)
            if el.exists():
                self._merge_state_from(el)
                return True
            if time.time() >= deadline:
                return False
            time.sleep(_WAIT_POLL_INTERVAL)

    def wait_gone(self, timeout: Optional[float] = None) -> bool:
        """
        Re-query until the xpath no longer matches, or the timeout elapses.
        If the node is already absent, returns True immediately.
        """
        if timeout is None:
            timeout = _DEFAULT_XPATH_WAIT_TIMEOUT
        deadline = time.time() + max(0.0, float(timeout))
        while True:
            el = _XPath._resolve(self._d, self._xpath)
            if not el.exists():
                return True
            if time.time() >= deadline:
                return False
            time.sleep(_WAIT_POLL_INTERVAL)

    def _verify(self):
        if not self.bounds:
            raise XmlElementNotFoundError("xpath not found")

    @cached_property
    def center(self):
        self._verify()
        return self.bounds.get_center()

    def exists(self) -> bool:
        return self.bounds is not None

    @delay
    def click(self):
        x, y = self.center.x, self.center.y
        self._d.click(x, y)

    @delay
    def click_if_exists(self):

        if not self.exists():
            logger.debug("click_exist: xpath not found")
            return

        x, y = self.center.x, self.center.y
        self._d.click(x, y)

    @delay
    def double_click(self):
        x, y = self.center.x, self.center.y
        self._d.double_click(x, y)

    @delay
    def long_click(self):
        x, y = self.center.x, self.center.y
        self._d.long_click(x, y)

    @delay
    def input_text(self, text):
        self.click()
        self._d.input_text(text)

    @property
    @delay
    def info(self) -> dict:
        if hasattr(self, 'attrib_info'):
            return getattr(self, 'attrib_info')
        else:
            logger.warning("the attribute <attrib_info> does not exists！")
            return {}

    @property
    @delay
    def text(self) -> str:
        return self.info.get("text")
