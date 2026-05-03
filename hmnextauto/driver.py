# -*- coding: utf-8 -*-

import json
import uuid
import re
import tempfile
from typing import Type, Any, Tuple, Dict, Union, List, Optional
from functools import cached_property  # python3.8+

from . import logger
from .utils import delay, image_size
from ._client import HmClient
from ._uiobject import UiObject
from .hdc import list_devices
from .settings import Settings
from .exception import (
    AppNameAmbiguousError,
    AppNameNotFoundError,
    DeviceNotFoundError,
)
from .proto import HypiumResponse, KeyCode, Point, DisplayRotation, DeviceInfo, CommandResult


def _bundle_label_from_info(info: Optional[dict]) -> str:
    """
    Best-effort display / software name from `bm dump -n` JSON.
    Falls back to vendor, then ``bundleName``.
    """
    if not info:
        return ""

    def _dig(d: Any, *keys: str) -> Any:
        cur: Any = d
        for k in keys:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
        return cur

    for path in (("appInfo", "label"), ("summary", "label"), ("applicationInfo", "label")):
        v = _dig(info, *path)
        if isinstance(v, str) and v.strip() and not v.strip().startswith("$"):
            return v.strip()

    for k in ("label", "name"):
        v = info.get(k)
        if isinstance(v, str) and v.strip() and not v.strip().startswith("$"):
            return v.strip()

    app = info.get("applicationInfo")
    if isinstance(app, dict):
        for k in ("label", "name", "nameWithPrefix"):
            v = app.get(k)
            if isinstance(v, str) and v.strip() and not v.strip().startswith("$"):
                return v.strip()
        v = app.get("vendor")
        if isinstance(v, str) and v.strip():
            return v.strip()

    v = info.get("vendor")
    if isinstance(v, str) and v.strip():
        return v.strip()
    b = info.get("bundleName")
    if isinstance(b, str) and b.strip():
        return b.strip()
    return ""


class Driver:
    _instance: Dict[str, "Driver"] = {}

    def __new__(cls: Type["Driver"], serial: Optional[str] = None) -> "Driver":
        """
        Ensure that only one instance of Driver exists per serial.
        If serial is None, use the first serial from list_devices().
        """
        serial = cls._prepare_serial(serial)

        if serial not in cls._instance:
            instance = super().__new__(cls)
            cls._instance[serial] = instance
            # Temporarily store the serial in the instance for initialization
            instance._serial_for_init = serial
        return cls._instance[serial]

    def __init__(self, serial: Optional[str] = None):
        """
        Initialize the Driver instance. Only initialize if `_initialized` is not set.
        """
        if hasattr(self, "_initialized") and self._initialized:
            return

        # Use the serial prepared in `__new__`
        serial = getattr(self, "_serial_for_init", serial)
        if serial is None:
            raise ValueError("Serial number is required for initialization.")

        self.serial = serial
        self._client = HmClient(self.serial)
        self.hdc = self._client.hdc
        self._bundle_label_cache: Dict[str, str] = {}
        self._settings = Settings(self)
        self._init_hmclient()
        self._initialized = True  # Mark the instance as initialized
        del self._serial_for_init  # Clean up temporary attribute

    @classmethod
    def _prepare_serial(cls, serial: str = None) -> str:
        """
        Prepare the serial. Use the first available device if serial is None.
        """
        devices = list_devices()
        if not devices:
            raise DeviceNotFoundError("No devices found. Please connect a device.")

        if serial is None:
            logger.info(f"No serial provided, using the first device: {devices[0]}")
            return devices[0]
        if serial not in devices:
            raise DeviceNotFoundError(f"Device [{serial}] not found")
        return serial

    def __call__(self, **kwargs) -> UiObject:

        return UiObject(self._client, driver=self, **kwargs)

    @property
    def settings(self) -> Settings:
        """获取全局配置"""
        return self._settings

    def implicitly_wait(self, seconds: Optional[float] = None) -> float:
        """
        设置或获取元素等待超时时间。

        Args:
            seconds: 超时时间（秒），None 表示只获取当前值

        Returns:
            当前超时时间

        Example:
            d.implicitly_wait(10)  # 设置为 10 秒
            print(d.implicitly_wait())  # 获取当前值
        """
        if seconds is not None:
            self._settings["wait_timeout"] = seconds
        return self._settings["wait_timeout"]

    def _unregister_singleton_if_self(self) -> None:
        """
        Remove this instance from the per-serial singleton map only if the
        slot still references ``self``. Avoids clearing other devices' entries
        when one Driver is finalized (previously ``_instance.clear()``).
        """
        serial = getattr(self, "serial", None)
        if serial is None:
            return
        inst = Driver._instance.get(serial)
        if inst is self:
            Driver._instance.pop(serial, None)

    def __del__(self):
        self._unregister_singleton_if_self()
        if hasattr(self, "_client") and self._client:
            self._client.release()

    def close(self) -> None:
        """
        Close the Hypium connection and HDC port forward. Idempotent; call at
        the end of a script (e.g. in ``finally``) so cleanup runs before
        interpreter shutdown. :meth:`release` on the client still skips
        ``fport rm`` if :func:`sys.is_finalizing` is true.

        Also removes this ``serial`` from the singleton registry so a later
        ``Driver(serial)`` creates a new connection.
        """
        if hasattr(self, "_client") and self._client is not None:
            self._client.release()
        self._unregister_singleton_if_self()

    def _init_hmclient(self):
        self._client.start()

    def _invoke(self, api: str, args: List = []) -> HypiumResponse:
        return self._client.invoke(api, this="Driver#0", args=args)

    @delay
    def start_app(self, package_name: str, page_name: Optional[str] = None):
        """
        Start an application on the device.
        If the `package_name` is empty, it will retrieve main ability using `get_app_main_ability`.

        Args:
            package_name (str): The package name of the application.
            page_name (Optional[str]): Ability Name within the application to start.
        """
        if not page_name:
            page_name = self.get_app_main_ability(package_name).get('name', 'MainAbility')
        self.hdc.start_app(package_name, page_name)

    def force_start_app(self, package_name: str, page_name: Optional[str] = None):
        self.go_home()
        self.stop_app(package_name)
        self.start_app(package_name, page_name)

    def stop_app(self, package_name: str):
        self.hdc.stop_app(package_name)

    def clear_app(self, package_name: str):
        """
        Clear the application's cache and data.
        """
        self.hdc.shell(f"bm clean -n {package_name} -c")  # clear cache
        self.hdc.shell(f"bm clean -n {package_name} -d")  # clear data

    def install_app(self, apk_path: str):
        self.hdc.install(apk_path)

    def uninstall_app(self, package_name: str):
        self.hdc.uninstall(package_name)

    def list_apps(self, include_system_apps: bool = False) -> List:
        return self.hdc.list_apps(include_system_apps)

    def app_version(self, bundle_name) -> Dict:
        return self.hdc.app_version(bundle_name)

    def has_app(self, package_name: str) -> bool:
        return self.hdc.has_app(package_name)

    def current_app(self) -> Tuple[str, str]:
        """
        Get the current foreground application information.

        Returns:
            Tuple[str, str]: A tuple contain the package_name andpage_name of the foreground application.
                             If no foreground application is found, returns (None, None).
        """

        return self.hdc.current_app()

    def get_app_info(self, package_name: str) -> Dict:
        """
        Get detailed information about a specific application.

        Args:
            package_name (str): The package name of the application to retrieve information for.

        Returns:
            Dict: A dictionary containing the application information. If an error occurs during parsing,
                  an empty dictionary is returned.
        """
        app_info = {}
        data: CommandResult = self.hdc.shell(f"bm dump -n {package_name}")
        output = data.output
        try:
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            json_output = output[json_start:json_end]

            app_info = json.loads(json_output)
        except Exception as e:
            logger.error(f"An error occurred:{e}")
        return app_info

    def get_app_abilities(self, package_name: str) -> List[Dict]:
        """
        Get the abilities of an application.

        Args:
            package_name (str): The package name of the application.

        Returns:
            List[Dict]: A list of dictionaries containing the abilities of the application.
        """
        result = []
        app_info = self.get_app_info(package_name)
        hap_module_infos = app_info.get("hapModuleInfos")
        main_entry = app_info.get("mainEntry")
        for hap_module_info in hap_module_infos:
            # 尝试读取moduleInfo
            try:
                ability_infos = hap_module_info.get("abilityInfos")
                module_main = hap_module_info["mainAbility"]
            except Exception as e:
                logger.warning(f"Fail to parse moduleInfo item, {repr(e)}")
                continue
            # 尝试读取abilityInfo
            for ability_info in ability_infos:
                try:
                    is_launcher_ability = False
                    skills = ability_info['skills']
                    if len(skills) > 0 or "action.system.home" in skills[0]["actions"]:
                        is_launcher_ability = True
                    icon_ability_info = {
                        "name": ability_info["name"],
                        "moduleName": ability_info["moduleName"],
                        "moduleMainAbility": module_main,
                        "mainModule": main_entry,
                        "isLauncherAbility": is_launcher_ability
                    }
                    result.append(icon_ability_info)
                except Exception as e:
                    logger.warning(f"Fail to parse ability_info item, {repr(e)}")
                    continue
        logger.debug(f"all abilities: {result}")
        return result

    def get_app_main_ability(self, package_name: str) -> Dict:
        """
        Get the main ability of an application.

        Args:
            package_name (str): The package name of the application to retrieve information for.

        Returns:
            Dict: A dictionary containing the main ability of the application.

        """
        if not (abilities := self.get_app_abilities(package_name)):
            return {}
        for item in abilities:
            score = 0
            if (name := item["name"]) and name == item["moduleMainAbility"]:
                score += 1
            if (module_name := item["moduleName"]) and module_name == item["mainModule"]:
                score += 1
            item["score"] = score
        abilities.sort(key=lambda x: (not x["isLauncherAbility"], -x["score"]))
        logger.debug(f"main ability: {abilities[0]}")
        return abilities[0]

    def get_app_display_name(self, package_name: str) -> str:
        """
        Return the application's display / software name (from bundle metadata), if any.
        """
        if package_name in self._bundle_label_cache:
            return self._bundle_label_cache[package_name]
        label = _bundle_label_from_info(self.get_app_info(package_name))
        self._bundle_label_cache[package_name] = label
        return label

    @staticmethod
    def _display_name_matched(
        query: str, text: str, match: str, case_insensitive: bool
    ) -> bool:
        if not text:
            return False
        t, q = text, query
        if case_insensitive and match != "regex":
            t, q = t.casefold(), q.casefold()
        if match == "exact":
            return t == q
        if match == "contains":
            return q in t
        if match == "startswith":
            return t.startswith(q)
        if match == "endswith":
            return t.endswith(q)
        if match == "regex":
            flags = re.IGNORECASE if case_insensitive else 0
            return re.search(query, text, flags) is not None
        raise ValueError(
            f"match must be 'exact'|'contains'|'startswith'|'endswith'|'regex', got {match!r}"
        )

    def find_all_packages_by_display_name(
        self,
        name: str,
        *,
        include_system_apps: bool = False,
        match: str = "contains",
        case_insensitive: bool = True,
        include_bundle_name: bool = True,
    ) -> List[Tuple[str, str, str]]:
        """
        List ``(package_name, display_name, how)`` for installed apps whose display
        name (and optionally bundle id) matches ``name``.

        ``how`` is ``"label"`` or ``"bundle"`` for debugging.
        """
        out: List[Tuple[str, str, str]] = []
        for pkg in sorted(self.list_apps(include_system_apps)):
            display = self.get_app_display_name(pkg)
            if self._display_name_matched(name, display, match, case_insensitive):
                out.append((pkg, display, "label"))
                continue
            if include_bundle_name and self._display_name_matched(
                name, pkg, match, case_insensitive
            ):
                out.append((pkg, display or pkg, "bundle"))
        return out

    def find_package_by_display_name(
        self,
        name: str,
        *,
        include_system_apps: bool = False,
        match: str = "contains",
        case_insensitive: bool = True,
        include_bundle_name: bool = True,
        on_ambiguous: str = "error",
    ) -> str:
        """
        Resolve a single bundle name from an app display / software name.

        This may be slow: it iterates installed packages and may call
        ``bm dump -n`` for each. Results are cached per :class:`Driver` instance.
        """
        if on_ambiguous not in ("error", "first"):
            raise ValueError("on_ambiguous must be 'error' or 'first'")
        found = self.find_all_packages_by_display_name(
            name,
            include_system_apps=include_system_apps,
            match=match,
            case_insensitive=case_insensitive,
            include_bundle_name=include_bundle_name,
        )
        if not found:
            raise AppNameNotFoundError(f"No app matches name: {name!r}")
        if len(found) == 1:
            return found[0][0]
        if on_ambiguous == "first":
            return found[0][0]
        pretty = ", ".join(f"{p} ({d})" for p, d, _ in found)
        raise AppNameAmbiguousError(
            f"Multiple apps match {name!r}: {pretty}",
            matches=[(p, d) for p, d, _ in found],
        )

    def start_app_by_name(
        self,
        app_name: str,
        page_name: Optional[str] = None,
        *,
        include_system_apps: bool = False,
        match: str = "contains",
        case_insensitive: bool = True,
        include_bundle_name: bool = True,
        on_ambiguous: str = "error",
    ) -> str:
        """
        Start an app by its display / software name (as shown to users, or
        matching bundle id if ``include_bundle_name`` is true).

        Returns the resolved ``package_name``.
        """
        bundle = self.find_package_by_display_name(
            app_name,
            include_system_apps=include_system_apps,
            match=match,
            case_insensitive=case_insensitive,
            include_bundle_name=include_bundle_name,
            on_ambiguous=on_ambiguous,
        )
        self.start_app(bundle, page_name)
        return bundle

    def force_start_app_by_name(
        self,
        app_name: str,
        page_name: Optional[str] = None,
        *,
        include_system_apps: bool = False,
        match: str = "contains",
        case_insensitive: bool = True,
        include_bundle_name: bool = True,
        on_ambiguous: str = "error",
    ) -> str:
        """
        Like :meth:`force_start_app`, but resolve the target by display / software name.
        """
        bundle = self.find_package_by_display_name(
            app_name,
            include_system_apps=include_system_apps,
            match=match,
            case_insensitive=case_insensitive,
            include_bundle_name=include_bundle_name,
            on_ambiguous=on_ambiguous,
        )
        self.force_start_app(bundle, page_name)
        return bundle

    @cached_property
    def toast_watcher(self):

        obj = self

        class _Watcher:
            def start(self) -> bool:
                api = "Driver.uiEventObserverOnce"
                resp: HypiumResponse = obj._invoke(api, args=["toastShow"])
                return resp.result

            def get_toast(self, timeout: int = 3) -> str:
                api = "Driver.getRecentUiEvent"
                resp: HypiumResponse = obj._invoke(api, args=[timeout])
                if resp.result:
                    return resp.result.get("text")
                return None

        return _Watcher()

    @cached_property
    def watcher(self):
        """
        PC-side background rules (poll-based, thread-safe with :class:`HmClient`).

        Usage::

            d.watcher("ok").when(text="确定").click()
            d.watcher("skip").when_xpath('//Button[@text="跳过"]').click()
            d.watcher.start(interval=0.3)
            # main script …
            d.watcher.stop()
            d.watcher.remove("ok")
        """
        from ._watcher import WatcherManager
        return WatcherManager(self)

    @cached_property
    def performance_watcher(self):
        """
        Performance monitoring watcher for continuous metrics collection.

        Usage::

            # Simple usage
            pw = d.performance_watcher
            pw.start(output_file="perf.jsonl", interval=1.0)
            # ... test execution ...
            pw.stop()

            # With configuration
            pw.configure(
                metrics=["fps", "memory", "cpu"],
                package="com.example.app",
                output_file="perf.jsonl"
            ).start()
            # ... test execution ...
            pw.stop()

            # Context manager (recommended)
            with d.performance_watcher.start("perf.jsonl"):
                d(text="button").click()
                # ... auto stop and save
        """
        from ._performance_watcher import PerformanceWatcher
        return PerformanceWatcher(self)

    @cached_property
    def notification(self):
        """
        Notification panel operations.

        Usage::

            # Open/close notification panel
            d.notification.open()
            d.notification.close()

            # Click notification by text
            d.notification.click_notification(text="微信")

            # Open quick settings and click
            d.notification.click_quick_setting("WiFi")

            # Context manager
            with d.notification:
                d.notification.click_notification(index=0)
                # ... auto close
        """
        from ._notification import NotificationPanel
        return NotificationPanel(self)

    @delay
    def go_back(self):
        self.hdc.send_key(KeyCode.BACK)

    @delay
    def go_home(self):
        self.hdc.send_key(KeyCode.HOME)

    @delay
    def press_key(self, key_code: Union[KeyCode, int]):
        self.hdc.send_key(key_code)

    # -------------------------------------------------------------------------
    # Common key shortcuts (OpenHarmony :class:`~hmnextauto.proto.KeyCode` values
    # sent via HDC; arbitrary codes still use :meth:`press_key`.)
    # -------------------------------------------------------------------------

    def press_back(self) -> None:
        """Send BACK (same as :meth:`go_back`)."""
        self.go_back()

    def press_home(self) -> None:
        """Send HOME (same as :meth:`go_home`)."""
        self.go_home()

    @delay
    def press_power(self) -> None:
        self.hdc.send_key(KeyCode.POWER)

    @delay
    def press_menu(self) -> None:
        self.hdc.send_key(KeyCode.MENU)

    @delay
    def press_enter(self) -> None:
        self.hdc.send_key(KeyCode.ENTER)

    @delay
    def press_backspace(self) -> None:
        """退格 (``KeyCode.DEL``)。"""
        self.hdc.send_key(KeyCode.DEL)

    @delay
    def press_delete(self) -> None:
        """向前删除 (``KeyCode.FORWARD_DEL``)。"""
        self.hdc.send_key(KeyCode.FORWARD_DEL)

    @delay
    def volume_up(self) -> None:
        self.hdc.send_key(KeyCode.VOLUME_UP)

    @delay
    def volume_down(self) -> None:
        self.hdc.send_key(KeyCode.VOLUME_DOWN)

    @delay
    def volume_mute(self) -> None:
        self.hdc.send_key(KeyCode.VOLUME_MUTE)

    @delay
    def press_tab(self) -> None:
        self.hdc.send_key(KeyCode.TAB)

    @delay
    def press_space(self) -> None:
        self.hdc.send_key(KeyCode.SPACE)

    @delay
    def press_escape(self) -> None:
        self.hdc.send_key(KeyCode.ESCAPE)

    @delay
    def page_up(self) -> None:
        self.hdc.send_key(KeyCode.PAGE_UP)

    @delay
    def page_down(self) -> None:
        self.hdc.send_key(KeyCode.PAGE_DOWN)

    @delay
    def press_dpad_up(self) -> None:
        self.hdc.send_key(KeyCode.DPAD_UP)

    @delay
    def press_dpad_down(self) -> None:
        self.hdc.send_key(KeyCode.DPAD_DOWN)

    @delay
    def press_dpad_left(self) -> None:
        self.hdc.send_key(KeyCode.DPAD_LEFT)

    @delay
    def press_dpad_right(self) -> None:
        self.hdc.send_key(KeyCode.DPAD_RIGHT)

    @delay
    def press_dpad_center(self) -> None:
        self.hdc.send_key(KeyCode.DPAD_CENTER)

    @delay
    def press_multitask(self) -> None:
        """虚拟多任务 / 最近任务 (``VIRTUAL_MULTITASK``)。"""
        self.hdc.send_key(KeyCode.VIRTUAL_MULTITASK)

    @delay
    def press_search(self) -> None:
        self.hdc.send_key(KeyCode.FIND)

    @delay
    def press_brightness_up(self) -> None:
        self.hdc.send_key(KeyCode.BRIGHTNESS_UP)

    @delay
    def press_brightness_down(self) -> None:
        self.hdc.send_key(KeyCode.BRIGHTNESS_DOWN)

    def screen_on(self):
        self.hdc.wakeup()

    def screen_off(self):
        self.hdc.wakeup()
        self.press_key(KeyCode.POWER)

    @delay
    def unlock(self):
        self.screen_on()
        w, h = self.display_size
        self.swipe(0.5 * w, 0.8 * h, 0.5 * w, 0.2 * h, speed=6000)

    @cached_property
    def display_size(self) -> Tuple[int, int]:
        api = "Driver.getDisplaySize"
        resp: HypiumResponse = self._invoke(api)
        w, h = resp.result.get("x"), resp.result.get("y")
        return w, h

    @cached_property
    def display_rotation(self) -> DisplayRotation:
        api = "Driver.getDisplayRotation"
        value = self._invoke(api).result
        return DisplayRotation.from_value(value)

    def set_display_rotation(self, rotation: DisplayRotation):
        """
        Sets the display rotation to the specified orientation.

        Args:
            rotation (DisplayRotation): display rotation.
        """
        api = "Driver.setDisplayRotation"
        self._invoke(api, args=[rotation.value])

    @cached_property
    def device_info(self) -> DeviceInfo:
        """
        Get detailed information about the device.

        Returns:
            DeviceInfo: An object containing various properties of the device.
        """
        hdc = self.hdc
        return DeviceInfo(
            productName=hdc.product_name(),
            model=hdc.model(),
            sdkVersion=hdc.sdk_version(),
            sysVersion=hdc.sys_version(),
            cpuAbi=hdc.cpu_abi(),
            wlanIp=hdc.wlan_ip(),
            displaySize=self.display_size,
            displayRotation=self.display_rotation
        )

    @cached_property
    def battery_level(self) -> int:
        """
        Get the current battery level.

        Returns:
            int: Battery level (0-100)
        """
        return self.hdc.battery_info().get("capacity", 0)

    @cached_property
    def battery_status(self) -> str:
        """
        Get the current battery charging status.

        Returns:
            str: Charging status - "DISCHARGING", "NOT_CHARGING", "CHARGING", "FULL", or "UNKNOWN"
        """
        status_map = {
            1: "DISCHARGING",
            2: "NOT_CHARGING",
            3: "CHARGING",
            4: "FULL"
        }
        code = self.hdc.battery_info().get("chargingStatus", 1)
        return status_map.get(code, "UNKNOWN")

    @cached_property
    def screen_brightness(self) -> int:
        """
        Get the current screen brightness.

        Returns:
            int: Screen brightness value (1-255)
        """
        return self.hdc.screen_brightness()

    @cached_property
    def network_type(self) -> str:
        """
        Get the current network type.

        Returns:
            str: Network type - "WiFi", "MOBILE", or "NO_NETWORK"
        """
        return self.hdc.network_type()

    @cached_property
    def is_screen_on(self) -> bool:
        """
        Check if the screen is currently on.

        Returns:
            bool: True if screen is on (AWAKE), False otherwise
        """
        state = self.hdc.screen_state()
        return state == "AWAKE"

    # ============================================
    # Performance Monitoring Methods
    # ============================================

    def memory_info(self, package_name: Optional[str] = None) -> Dict:
        """
        Get memory information.

        Args:
            package_name: Package name to get memory for. If None, returns system-wide memory info.

        Returns:
            Dict: Memory information including total_pss, native_heap, ark_ts_heap, graph, etc.
        """
        return self.hdc.memory_info(package_name)

    def cpu_usage(self) -> Dict:
        """
        Get CPU usage information.

        Returns:
            Dict: CPU usage including total, user, kernel percentages and per-process usage.
        """
        return self.hdc.cpu_usage()

    def cpu_freq(self) -> List[Dict]:
        """
        Get CPU frequency information for each core.

        Returns:
            List[Dict]: List of CPU frequency info, each containing cpu, current, and max frequency.
        """
        return self.hdc.cpu_freq()

    @cached_property
    def refresh_rate(self) -> int:
        """
        Get the current screen refresh rate.

        Returns:
            int: Current refresh rate in Hz (e.g., 60, 90, 120).
        """
        return self.hdc.refresh_rate()

    def fps(self) -> float:
        """
        Get the current FPS (frames per second).

        Calculates FPS from recent frame timestamps.

        Returns:
            float: Current FPS value.
        """
        timestamps = self.hdc.fps_timestamps()
        if len(timestamps) < 2:
            return 0.0

        # Sort timestamps (they come in descending order)
        timestamps = sorted(timestamps)

        # Calculate time differences between consecutive frames
        diffs = []
        for i in range(1, len(timestamps)):
            diff = timestamps[i] - timestamps[i-1]
            if diff > 0:
                diffs.append(diff)

        if not diffs:
            return 0.0

        # Average time difference in nanoseconds
        avg_diff = sum(diffs) / len(diffs)

        # Convert to FPS (nanoseconds to seconds)
        fps_value = 1000000000 / avg_diff
        return round(fps_value, 2)

    def frame_hitchs(self) -> Dict:
        """
        Get frame hitch (jank) statistics.

        Returns:
            Dict: Hitch statistics with over_16ms, over_33ms, over_66ms counts.
        """
        return self.hdc.frame_hitchs()

    def app_start_time(self, package_name: str) -> Optional[int]:
        """
        Get the start timestamp of an application (system uptime when started).

        Note: This returns the system uptime timestamp when the app was started,
        not the actual startup duration. Use measure_cold_start() or measure_hot_start()
        to measure actual startup time.

        Args:
            package_name: The package name to look up.

        Returns:
            Optional[int]: Start timestamp in milliseconds (system uptime), or None if not found.
        """
        data: CommandResult = self.hdc.shell("aa dump -l")
        output = data.output

        # Find the mission block for the package
        mission_pattern = r'Mission ID #\d+.*?mission name #\[#' + re.escape(package_name) + r'.*?\]'
        mission_match = re.search(mission_pattern, output, re.DOTALL)

        if mission_match:
            mission_block = mission_match.group(0)
            # Parse: start time [137245554]
            time_match = re.search(r'start time \[(\d+)\]', mission_block)
            if time_match:
                return int(time_match.group(1))

        return None

    def measure_cold_start(self, package: str, ability: str = None, timeout: float = 10.0) -> Dict:
        """
        Measure cold start time for an application.

        This method measures the time for the `aa start` command to complete.
        Cold start is when the app process is not running and needs to be created.

        Note: Cold start takes longer because:
        - App process needs to be created
        - App resources need to be loaded from scratch

        Args:
            package: Package name.
            ability: Ability name (optional, will auto-detect if not provided).
            timeout: Maximum time to wait for app to start.

        Returns:
            Dict: {
                'success': bool,
                'duration_ms': int,  # Cold start time in milliseconds
                'package': str,
                'ability': str
            }
        """
        import time

        result = {
            'success': False,
            'duration_ms': 0,
            'package': package,
            'ability': ability or ''
        }

        # Get ability name BEFORE stopping app and timing (so parsing doesn't affect measurement)
        if not ability:
            ability_info = self.get_app_main_ability(package)
            ability = ability_info.get('name', 'MainAbility')
            result['ability'] = ability

        # Stop the app first (cold start)
        self.stop_app(package)
        time.sleep(0.5)

        # Measure start time - only the aa start command
        start_time = time.perf_counter()

        cmd_result = self.hdc.shell(f"aa start -a {ability} -b {package}")

        end_time = time.perf_counter()

        # Check if start was successful
        result['success'] = 'successfully' in cmd_result.output.lower()
        result['duration_ms'] = int((end_time - start_time) * 1000)

        return result

    def measure_hot_start(self, package: str, wait_time: float = 2.0, timeout: float = 5.0) -> Dict:
        """
        Measure hot start time for an application.

        This method measures the time for the `aa start` command to complete.
        Hot start is when the app is already running in background and just needs
        to be brought to foreground.

        Note: Hot start should be faster than cold start because:
        - App process is already running in background
        - No need to load app resources from scratch

        Args:
            package: Package name.
            wait_time: Time to wait in background before measuring.
            timeout: Maximum time to wait for app to come to foreground.

        Returns:
            Dict: {
                'success': bool,
                'duration_ms': int,  # Hot start time in milliseconds
                'package': str,
                'ability': str
            }
        """
        import time

        result = {
            'success': False,
            'duration_ms': 0,
            'package': package,
            'ability': ''
        }

        # Step 1: Ensure app is running and get its ability name
        # This is done BEFORE timing starts, so parsing time doesn't affect measurement
        current_pkg, _ = self.current_app()
        if current_pkg != package:
            # Start app first (this will also cache the ability)
            self.start_app(package)
            time.sleep(1)

        # Get ability name (already cached from previous start)
        ability_info = self.get_app_main_ability(package)
        ability = ability_info.get('name', 'MainAbility')
        result['ability'] = ability

        # Step 2: Go home to put app in background
        self.go_home()
        time.sleep(wait_time)

        # Step 3: Measure hot start time - only the aa start command
        start_time = time.perf_counter()

        cmd_result = self.hdc.shell(f"aa start -a {ability} -b {package}")

        end_time = time.perf_counter()

        # Check if start was successful
        result['success'] = 'successfully' in cmd_result.output.lower()
        result['duration_ms'] = int((end_time - start_time) * 1000)

        return result

    def process_info(self, package_name: str) -> Optional[Dict]:
        """
        Get process information for a package.

        Args:
            package_name: The package name to look up.

        Returns:
            Optional[Dict]: Process info including pid, memory, etc., or None if not found.
        """
        # Get memory info (which also finds PID)
        mem_info = self.hdc.memory_info(package_name)
        if not mem_info:
            return None

        # Get PID
        pid = self.hdc._get_pid(package_name)

        return {
            "pid": pid,
            "package_name": package_name,
            "total_pss": mem_info.get("total_pss", 0),
            "native_heap": mem_info.get("native_heap", 0),
            "ark_ts_heap": mem_info.get("ark_ts_heap", 0),
            "graph": mem_info.get("graph", 0)
        }

    @delay
    def open_url(self, url: str, system_browser: bool = True):
        if system_browser:
            # Use the system browser
            self.hdc.shell(f"aa start -A ohos.want.action.viewData -e entity.system.browsable -U {url}")
        else:
            # Default method
            self.hdc.shell(f"aa start -U {url}")

    def pull_file(self, rpath: str, lpath: str):
        """
        Pull a file from the device to the local machine.

        Args:
            rpath (str): The remote path of the file on the device.
            lpath (str): The local path where the file should be saved.
        """
        self.hdc.recv_file(rpath, lpath)

    def push_file(self, lpath: str, rpath: str):
        """
        Push a file from the local machine to the device.

        Args:
            lpath (str): The local path of the file.
            rpath (str): The remote path where the file should be saved on the device.
        """
        self.hdc.send_file(lpath, rpath)

    def screenshot(self, path: str, method: str = "snapshot_display") -> str:
        """
        Take a screenshot of the device display.

        Args:
            path (str): The local path to save the screenshot.
            method (str): The screenshot method to use. Options are:
                          - "snapshot_display" (default, recommended for better performance)
                          - "screenCap" (alternative method, higher quality but slower).

        Returns:
            str: The path where the screenshot is saved.
        """
        return self.hdc.screenshot(path, method=method)

    def _temp_screenshot(self, method: str = "snapshot_display") -> str:
        suffix = ".jpeg" if method == "snapshot_display" else ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            path = f.name
        return self.screenshot(path, method=method)

    @delay
    def click_from_screenshot(
        self,
        x: int,
        y: int,
        screenshot_path: str,
        assume_in_bounds: bool = True,
    ) -> Point:
        """
        Click using pixel coordinates from a screenshot image.
        
        Args:
            x: X coordinate in screenshot pixels
            y: Y coordinate in screenshot pixels
            screenshot_path: Path to screenshot image
            assume_in_bounds: Whether to clamp coordinates to image bounds
            
        Returns:
            Point: The actual coordinates clicked on the device
        """
        img_w, img_h = image_size(screenshot_path)
        if img_w <= 0 or img_h <= 0:
            raise ValueError(f"Invalid screenshot size: {img_w}x{img_h}")

        if assume_in_bounds:
            x = max(0, min(int(x), img_w - 1))
            y = max(0, min(int(y), img_h - 1))

        dev_w, dev_h = self.display_size
        if dev_w <= 0 or dev_h <= 0:
            raise RuntimeError("Cannot get device display size")

        # Check if screenshot size matches device resolution
        # If they match, use coordinates directly without scaling
        if abs(img_w - dev_w) <= 1 and abs(img_h - dev_h) <= 1:
            # Screenshot matches device resolution, use coordinates directly
            dx = max(0, min(int(x), dev_w - 1))
            dy = max(0, min(int(y), dev_h - 1))
            scale_x = scale_y = 1.0
        else:
            # Calculate scaling factors
            scale_x = dev_w / float(img_w)
            scale_y = dev_h / float(img_h)
            
            # Apply scaling
            dx = int(round(x * scale_x))
            dy = int(round(y * scale_y))
            
            # Clamp to device bounds
            dx = max(0, min(dx, dev_w - 1))
            dy = max(0, min(dy, dev_h - 1))

        logger.debug(
            f"click_from_screenshot: screenshot={img_w}x{img_h}, "
            f"device={dev_w}x{dev_h}, input=({x},{y}), output=({dx},{dy}), "
            f"scale=({scale_x:.2f}, {scale_y:.2f})"
        )

        self._invoke("Driver.click", args=[dx, dy])
        return Point(dx, dy)

    def click_image(
        self,
        template_path: str,
        threshold: float = 0.85,
        grayscale: bool = True,
        method: str = "snapshot_display",
        return_result: bool = False,
        draw_box: bool = True,
        multi_scale: bool = True,
        scale_range: Tuple[float, float] = (0.5, 2.0),
        scale_steps: int = 30,
    ) -> Union[bool, Tuple[bool, Optional["MatchResult"]]]:
        """
        Screenshot -> template match -> click (OpenCV).
        
        Args:
            template_path: Path to template image to find
            threshold: Matching threshold (0.0-1.0), default 0.85
            grayscale: Whether to use grayscale matching (faster)
            method: Screenshot method ("screenCap" or "snapshot_display")
            return_result: Whether to return the match result
            draw_box: Whether to draw a bounding box on the screenshot
            multi_scale: Enable multi-scale matching for resolution adaptation
            scale_range: (min_scale, max_scale) for multi-scale search
            scale_steps: Number of scale steps to search
            
        Returns:
            bool: True if found and clicked, False otherwise
            Or tuple (bool, MatchResult) if return_result=True
        """
        from ._vision import find_image, MatchResult, _require_cv2

        shot = self._temp_screenshot(method=method)
        try:
            r = find_image(
                shot,
                template_path,
                threshold=threshold,
                grayscale=grayscale,
                multi_scale=multi_scale,
                scale_range=scale_range,
                scale_steps=scale_steps,
            )
        except Exception as e:
            logger.error(f"Error finding image: {e}")
            return (False, None) if return_result else False
            
        if r is None:
            logger.debug(f"Image not found: {template_path}, threshold={threshold}")
            return (False, None) if return_result else False
            
        cx, cy = r.center
        logger.debug(
            f"Image found: {template_path}, score={r.score:.4f}, "
            f"position=({r.x},{r.y}), size=({r.w}x{r.h}), center=({cx},{cy})"
        )
        
        # Draw bounding box on screenshot
        if draw_box:
            try:
                cv2 = _require_cv2()
                # Read the screenshot
                img = cv2.imread(shot)
                if img is not None:
                    # Draw rectangle (green color, 2px thickness)
                    cv2.rectangle(img, (r.x, r.y), (r.x + r.w, r.y + r.h), (0, 255, 0), 2)
                    # Draw center dot (red)
                    cv2.circle(img, (cx, cy), 5, (0, 0, 255), -1)
                    # Draw score text
                    score_text = f"{r.score:.2f}"
                    cv2.putText(img, score_text, (r.x, r.y - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    # Save back to the same file
                    cv2.imwrite(shot, img)
                    logger.debug(f"Bounding box drawn on screenshot: {shot}")
            except Exception as e:
                logger.warning(f"Failed to draw bounding box: {e}")
        
        try:
            clicked_point = self.click_from_screenshot(cx, cy, shot)
            logger.debug(f"Clicked at: {clicked_point}")
        except Exception as e:
            logger.error(f"Error clicking image: {e}")
            return (False, r) if return_result else False
            
        return (True, r) if return_result else True

    def click_color(
        self,
        rgb: Tuple[int, int, int],
        tolerance: int = 10,
        region: Optional[Tuple[int, int, int, int]] = None,
        method: str = "snapshot_display",
        return_result: bool = False,
    ) -> Union[bool, Tuple[bool, Optional[Tuple[int, int]]]]:
        """
        Screenshot -> find a pixel by color -> click (OpenCV+NumPy).
        
        Args:
            rgb: Target color in RGB format (0-255, 0-255, 0-255)
            tolerance: Per-channel color tolerance (0-255), default 10
            region: Optional search region (x1, y1, x2, y2) in screenshot pixels
            method: Screenshot method ("screenCap" or "snapshot_display")
            return_result: Whether to return the found position
            
        Returns:
            bool: True if found and clicked, False otherwise
            Or tuple (bool, (x, y)) if return_result=True
        """
        from ._vision import find_color

        shot = self._temp_screenshot(method=method)
        try:
            pt = find_color(shot, rgb=rgb, tolerance=tolerance, region=region)
        except Exception as e:
            logger.error(f"Error finding color: {e}")
            return (False, None) if return_result else False
            
        if pt is None:
            logger.debug(f"Color not found: rgb={rgb}, tolerance={tolerance}, region={region}")
            return (False, None) if return_result else False
            
        logger.debug(f"Color found: rgb={rgb}, position=({pt[0]},{pt[1]})")
        
        try:
            clicked_point = self.click_from_screenshot(pt[0], pt[1], shot)
            logger.debug(f"Clicked at: {clicked_point}")
        except Exception as e:
            logger.error(f"Error clicking color: {e}")
            return (False, pt) if return_result else False
            
        return (True, pt) if return_result else True

    def shell(self, cmd) -> CommandResult:
        return self.hdc.shell(cmd)

    def _to_abs_pos(self, x: Union[int, float], y: Union[int, float]) -> Point:
        """
        Convert percentages to absolute screen coordinates.

        Args:
            x (Union[int, float]): X coordinate as a percentage or absolute value.
            y (Union[int, float]): Y coordinate as a percentage or absolute value.

        Returns:
            Point: A Point object with absolute screen coordinates.
        """
        assert x >= 0
        assert y >= 0

        w, h = self.display_size

        if x < 1:
            x = int(w * x)
        if y < 1:
            y = int(h * y)
        return Point(int(x), int(y))

    @delay
    def click(self, x: Union[int, float], y: Union[int, float]):

        # self.hdc.tap(point.x, point.y)
        point = self._to_abs_pos(x, y)
        api = "Driver.click"
        self._invoke(api, args=[point.x, point.y])

    @delay
    def double_click(self, x: Union[int, float], y: Union[int, float]):
        point = self._to_abs_pos(x, y)
        api = "Driver.doubleClick"
        self._invoke(api, args=[point.x, point.y])

    @delay
    def long_click(self, x: Union[int, float], y: Union[int, float]):
        point = self._to_abs_pos(x, y)
        api = "Driver.longClick"
        self._invoke(api, args=[point.x, point.y])

    @delay
    def swipe(self, x1, y1, x2, y2, speed=2000):
        """
        Perform a swipe action on the device screen.

        Args:
            x1 (float): The start X coordinate as a percentage or absolute value.
            y1 (float): The start Y coordinate as a percentage or absolute value.
            x2 (float): The end X coordinate as a percentage or absolute value.
            y2 (float): The end Y coordinate as a percentage or absolute value.
            speed (int, optional): The swipe speed in pixels per second. Default is 2000. Range: 200-40000,
            If not within the range, set to default value of 2000.
        """

        point1 = self._to_abs_pos(x1, y1)
        point2 = self._to_abs_pos(x2, y2)

        if speed < 200 or speed > 40000:
            logger.warning("`speed` is not in the range[200-40000], Set to default value of 2000.")
            speed = 2000

        api = "Driver.swipe"
        self._invoke(api, args=[point1.x, point1.y, point2.x, point2.y, speed])

    @cached_property
    def swipe_ext(self):
        """
        d.swipe_ext("up")
        d.swipe_ext("up", box=(0.2, 0.2, 0.8, 0.8))
        """
        from ._swipe import SwipeExt
        return SwipeExt(self)

    @delay
    def input_text(self, text: str):
        """
        Inputs text into the currently focused input field.

        Note: The input field must have focus before calling this method.

        Args:
            text (str): input value
        """
        return self._invoke("Driver.inputText", args=[{"x": 1, "y": 1}, text])

    def dump_hierarchy(self) -> Dict:
        """
        Dump the UI hierarchy of the device screen.

        Returns:
            Dict: The dumped UI hierarchy as a dictionary.
        """
        # return self._client.invoke_captures("captureLayout").result
        return self.hdc.dump_hierarchy()

    @cached_property
    def gesture(self):
        from ._gesture import _Gesture
        return _Gesture(self)

    @cached_property
    def screenrecord(self):
        from ._screenrecord import RecordClient
        return RecordClient(self.serial, self)

    def _invalidate_cache(self, attribute_name):
        """
        Invalidate the cached property.

        Args:
            attribute_name (str): The name of the attribute to invalidate.
        """
        if attribute_name in self.__dict__:
            del self.__dict__[attribute_name]

    @cached_property
    def xpath(self):
        """
        d.xpath("//*[@text='Hello']").click()
        d.xpath("//*[@text='Hello']").wait(timeout=15)
        d.xpath("//*[@text='Hello']").wait_gone(timeout=5)
        """
        from ._xpath import _XPath
        return _XPath(self)

