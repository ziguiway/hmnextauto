# -*- coding: utf-8 -*-

class Settings:
    """全局配置管理（客户端维护）"""

    def __init__(self, driver):
        self._driver = driver
        self._defaults = {
            "wait_timeout": 20.0,           # 元素等待超时（秒）
            "operation_delay": (0, 0),      # 操作前后延迟 (before, after)
            "poll_interval": 0.1,           # 轮询间隔（秒）
        }

    def __getitem__(self, key):
        return self._defaults.get(key)

    def __setitem__(self, key, value):
        if key not in self._defaults:
            raise KeyError(f"Unknown setting: {key}")
        self._defaults[key] = value

    def get(self, key, default=None):
        return self._defaults.get(key, default)

    def __repr__(self):
        import pprint
        return pprint.pformat(self._defaults)
