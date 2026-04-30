# -*- coding: utf-8 -*-
"""
通知栏操作模块
支持打开/关闭通知栏、操作通知消息、快捷设置面板等
"""

import time
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from . import logger

if TYPE_CHECKING:
    from .driver import Driver


class NotificationPanel:
    """
    通知栏操作类

    提供通知栏的打开、关闭、通知消息操作、快捷设置等功能。
    """

    def __init__(self, driver: "Driver") -> None:
        self._d = driver
        self._is_open = False

    def open(self, wait_time: float = 0.5) -> bool:
        """
        打开通知栏（从顶部下滑）

        Args:
            wait_time: 打开后等待时间（秒）

        Returns:
            True 如果成功打开
        """
        if self._is_open:
            logger.debug("通知栏已经打开")
            return True

        w, h = self._d.display_size

        # 从屏幕左侧中间向下滑动（左侧是消息通知）
        self._d.swipe(w // 4, 10, w // 4, h // 2, speed=8000)

        time.sleep(wait_time)
        self._is_open = True
        logger.info("通知栏已打开")
        return True

    def close(self, wait_time: float = 0.3) -> bool:
        """
        关闭通知栏（向上滑动或按返回键）

        Args:
            wait_time: 关闭后等待时间（秒）

        Returns:
            True 如果成功关闭
        """
        if not self._is_open:
            logger.debug("通知栏已经关闭")
            return True

        # 方式1: 向上滑动关闭
        w, h = self._d.display_size
        self._d.swipe(w // 2, h // 2, w // 2, 10, speed=8000)

        time.sleep(wait_time)
        self._is_open = False
        logger.info("通知栏已关闭")
        return True

    def toggle(self) -> bool:
        """
        切换通知栏状态

        Returns:
            切换后的状态（True=打开，False=关闭）
        """
        if self._is_open:
            self.close()
            return False
        else:
            self.open()
            return True

    def open_quick_settings(self, wait_time: float = 0.5) -> bool:
        """
        打开快捷设置面板（从屏幕右侧顶部下滑）

        Args:
            wait_time: 打开后等待时间（秒）

        Returns:
            True 如果成功打开
        """
        w, h = self._d.display_size

        # 从屏幕右侧顶部向下滑动（右侧是快捷设置开关）
        self._d.swipe(w * 3 // 4, 10, w * 3 // 4, h // 2, speed=8000)

        time.sleep(wait_time)
        self._is_open = True
        logger.info("快捷设置面板已打开")
        return True

    def get_notifications(self) -> List[Dict[str, Any]]:
        """
        获取通知栏中的通知列表

        Returns:
            通知列表，每个通知包含 text、description 等信息
        """
        # 确保通知栏打开
        if not self._is_open:
            self.open()

        notifications = []

        # 查找通知项（鸿蒙系统中通知通常在 List 或 ListItem 中）
        # 尝试多种方式查找通知
        try:
            # 方式1: 查找包含通知内容的 ListItem
            items = self._d(type="ListItem")
            count = items.count

            for i in range(min(count, 10)):  # 最多获取10条
                try:
                    item = self._d(type="ListItem", index=i)
                    info = item.info
                    notification = {
                        "index": i,
                        "text": info.text if hasattr(info, 'text') else "",
                        "type": info.type if hasattr(info, 'type') else "",
                        "clickable": info.isClickable if hasattr(info, 'isClickable') else False,
                    }
                    notifications.append(notification)
                except Exception as e:
                    logger.debug(f"获取通知 {i} 失败: {e}")
                    continue

        except Exception as e:
            logger.warning(f"获取通知列表失败: {e}")

        logger.info(f"获取到 {len(notifications)} 条通知")
        return notifications

    def click_notification(self, index: int = 0, text: Optional[str] = None) -> bool:
        """
        点击通知

        Args:
            index: 通知索引（从0开始）
            text: 通知文本内容（如果指定，则查找包含该文本的通知）

        Returns:
            True 如果成功点击
        """
        # 确保通知栏打开
        if not self._is_open:
            self.open()

        try:
            if text:
                # 查找包含指定文本的通知
                if self._d(textContains=text).exists():
                    self._d(textContains=text).click()
                    logger.info(f"点击包含 '{text}' 的通知")
                    self._is_open = False  # 点击通知后通知栏会关闭
                    return True
                else:
                    logger.warning(f"未找到包含 '{text}' 的通知")
                    return False
            else:
                # 点击指定索引的通知
                item = self._d(type="ListItem", index=index)
                if item.exists():
                    item.click()
                    logger.info(f"点击第 {index} 条通知")
                    self._is_open = False
                    return True
                else:
                    logger.warning(f"未找到第 {index} 条通知")
                    return False
        except Exception as e:
            logger.error(f"点击通知失败: {e}")
            return False

    def clear_all_notifications(self) -> bool:
        """
        清除所有通知

        Returns:
            True 如果成功清除
        """
        # 确保通知栏打开
        if not self._is_open:
            self.open()

        try:
            # 查找"清除"或"删除"按钮
            clear_selectors = [
                {"text": "清除"},
                {"text": "删除"},
                {"text": "清空"},
                {"textContains": "清除"},
                {"idContains": "clear"},
                {"idContains": "delete"},
            ]

            for selector in clear_selectors:
                try:
                    if self._d(**selector).exists():
                        self._d(**selector).click()
                        logger.info("清除所有通知")
                        return True
                except Exception:
                    continue

            logger.warning("未找到清除通知按钮")
            return False

        except Exception as e:
            logger.error(f"清除通知失败: {e}")
            return False

    def click_quick_setting(self, name: str) -> bool:
        """
        点击快捷设置项

        Args:
            name: 设置项名称，如 "wifi"、"蓝牙"、"飞行模式"、"静音" 等

        Returns:
            True 如果成功点击
        """
        # 打开快捷设置面板
        self.open_quick_settings()

        try:
            # 映射常见名称到精确的 id
            name_to_id = {
                "wifi": ["transition_togglewifi_ui_extension"],
                "wlan": ["transition_togglewifi_ui_extension"],
                "蓝牙": ["transition_togglebluetooth_ui_extension"],
                "bluetooth": ["transition_togglebluetooth_ui_extension"],
                "飞行模式": ["transition_toggleairplane_ui_extension"],
                "飞行": ["transition_toggleairplane_ui_extension"],
                "静音": ["transition_togglemute_ui_extension"],
                "手电筒": ["transition_toggleflashlight_ui_extension"],
                "定位": ["transition_togglegps_ui_extension"],
                "数据": ["transition_togglemobile_ui_extension"],
            }

            name_lower = name.lower()
            ids = name_to_id.get(name_lower, [])

            # 尝试通过精确 id 查找
            for id_val in ids:
                if self._d(id=id_val).exists():
                    self._d(id=id_val).click()
                    logger.info(f"点击快捷设置: {name} (id: {id_val})")
                    return True

            # 尝试通过 id 包含查找
            if self._d(idContains=name_lower).exists():
                self._d(idContains=name_lower).click()
                logger.info(f"点击快捷设置: {name} (id contains: {name_lower})")
                return True

            # 尝试通过 text 查找
            if self._d(textContains=name).exists():
                self._d(textContains=name).click()
                logger.info(f"点击快捷设置: {name}")
                return True

            logger.warning(f"未找到快捷设置: {name}")
            return False
        except Exception as e:
            logger.error(f"点击快捷设置失败: {e}")
            return False

    def set_brightness(self, level: int) -> bool:
        """
        设置屏幕亮度（通过快捷设置面板）

        Args:
            level: 亮度级别 (0-100)

        Returns:
            True 如果成功设置
        """
        if not 0 <= level <= 100:
            logger.warning(f"亮度级别 {level} 超出范围 (0-100)")
            return False

        # 打开快捷设置面板
        self.open_quick_settings()

        try:
            # 查找亮度滑块
            # 鸿蒙系统中亮度滑块通常是 Slider 类型
            slider = self._d(type="Slider")
            if not slider.exists():
                # 尝试其他方式查找
                slider = self._d(typeContains="Slider")

            if slider.exists():
                # 计算滑动位置
                w, h = self._d.display_size
                info = slider.info
                bounds = info.bounds

                # 计算目标位置
                total_width = bounds.right - bounds.left
                target_x = bounds.left + int(total_width * level / 100)

                # 滑动到目标位置
                self._d.swipe(bounds.left + 10, bounds.top, target_x, bounds.top, speed=3000)
                logger.info(f"设置亮度为 {level}%")
                return True
            else:
                logger.warning("未找到亮度滑块")
                return False

        except Exception as e:
            logger.error(f"设置亮度失败: {e}")
            return False

    def __enter__(self) -> "NotificationPanel":
        self.open()
        return self

    def __exit__(self, *args) -> None:
        self.close()