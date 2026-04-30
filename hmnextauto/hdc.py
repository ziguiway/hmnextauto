# -*- coding: utf-8 -*-
import tempfile
import json
import uuid
import shlex
import re
import os
import subprocess
from typing import Union, List, Dict, Tuple, Optional

from . import logger
from .utils import FreePort
from .proto import CommandResult, KeyCode
from .exception import HdcError, DeviceNotFoundError


def _execute_command(cmdargs: Union[str, List[str]]) -> CommandResult:
    if isinstance(cmdargs, (list, tuple)):
        cmdline: str = ' '.join(list(map(shlex.quote, cmdargs)))
    elif isinstance(cmdargs, str):
        cmdline = cmdargs

    logger.debug(cmdline)
    try:
        process = subprocess.Popen(cmdline, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True)
        output, error = process.communicate()
        output = output.decode('utf-8')
        error = error.decode('utf-8')
        exit_code = process.returncode

        if 'error:' in output.lower() or '[fail]' in output.lower():
            return CommandResult("", output, -1)

        return CommandResult(output, error, exit_code)
    except Exception as e:
        return CommandResult("", str(e), -1)


def _build_hdc_prefix() -> str:
    """
    Construct the hdc command prefix based on environment variables.
    """
    host = os.getenv("HDC_SERVER_HOST")
    port = os.getenv("HDC_SERVER_PORT")
    if host and port:
        logger.debug(f"HDC_SERVER_HOST: {host}, HDC_SERVER_PORT: {port}")
        return f"hdc -s {host}:{port}"
    return "hdc"


def list_devices() -> List[str]:
    devices = []
    hdc_prefix = _build_hdc_prefix()
    result = _execute_command(f"{hdc_prefix} list targets")
    if result.exit_code == 0 and result.output:
        lines = result.output.strip().split('\n')
        for line in lines:
            if line.__contains__('Empty'):
                continue
            devices.append(line.strip())

    if result.exit_code != 0:
        raise HdcError("HDC error", result.error)

    return devices


class HdcWrapper:
    def __init__(self, serial: str) -> None:
        self.serial = serial
        self.hdc_prefix = _build_hdc_prefix()

        if not self.is_online():
            raise DeviceNotFoundError(f"Device [{self.serial}] not found")

    def is_online(self):
        _serials = list_devices()
        return True if self.serial in _serials else False

    def forward_port(self, rport: int) -> int:
        lport: int = FreePort().get()
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} fport tcp:{lport} tcp:{rport}")
        if result.exit_code != 0:
            raise HdcError("HDC forward port error", result.error)
        return lport

    def rm_forward(self, lport: int, rport: int) -> int:
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} fport rm tcp:{lport} tcp:{rport}")
        if result.exit_code != 0:
            raise HdcError("HDC rm forward error", result.error)
        return lport

    def list_fport(self) -> List:
        """
        eg.['tcp:10001 tcp:8012', 'tcp:10255 tcp:8012']
        """
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} fport ls")
        if result.exit_code != 0:
            raise HdcError("HDC forward list error", result.error)
        pattern = re.compile(r"tcp:\d+ tcp:\d+")
        return pattern.findall(result.output)

    def send_file(self, lpath: str, rpath: str):
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} file send {lpath} {rpath}")
        if result.exit_code != 0:
            raise HdcError("HDC send file error", result.error)
        return result

    def recv_file(self, rpath: str, lpath: str):
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} file recv {rpath} {lpath}")
        if result.exit_code != 0:
            raise HdcError("HDC receive file error", result.error)
        return result

    def shell(self, cmd: str, error_raise=True) -> CommandResult:
        # ensure the command is wrapped in double quotes
        if cmd[0] != '\"':
            cmd = "\"" + cmd
        if cmd[-1] != '\"':
            cmd += '\"'
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} shell {cmd}")
        if result.exit_code != 0 and error_raise:
            raise HdcError("HDC shell error", f"{cmd}\n{result.output}\n{result.error}")
        return result

    def uninstall(self, bundlename: str):
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} uninstall {bundlename}")
        if result.exit_code != 0:
            raise HdcError("HDC uninstall error", result.output)
        return result

    def install(self, apkpath: str):
        # Ensure the path is properly quoted for Windows
        quoted_path = f'"{apkpath}"'

        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} install {quoted_path}")
        if result.exit_code != 0:
            raise HdcError("HDC install error", result.error)
        return result

    def list_apps(self, include_system_apps: bool = False) -> List[str]:
        """
        List installed applications on the device. (Lazy loading, default: third-party apps)

        Args:
            include_system_apps (bool): If True, include system apps in the list.
                                        If False, only list third-party apps.

        Returns:
            List[str]: A list of application package names.

        Note:
        - When include_system_apps is False, the list typically contains around 50 third-party apps.
        - When include_system_apps is True, the list typically contains around 200 apps in total.
        """
        # Construct the shell command based on the include_system_apps flag
        if include_system_apps:
            command = "bm dump -a"
        else:
            command = "bm dump -a | grep -v 'com.huawei'"

        # Execute the shell command
        result = self.shell(command)
        raw = result.output.split('\n')

        # Filter out strings starting with 'ID:' and empty strings
        return [item.strip() for item in raw if item.strip() and not re.match(r'^ID:', item.strip())]

    def app_version(self, bundlename: str) -> Dict[str, Optional[str]]:
        """
        Get the version information of an app installed on the device.

        Args:
            bundlename (str): The bundle name of the app.

        Returns:
            dict: A dictionary containing the version information:
                  - "versionName": The version name of the app.
                  - "versionCode": The version code of the app.
        """
        result = _execute_command(f"{self.hdc_prefix} -t {self.serial} shell bm dump -n {bundlename} | grep '\"versionCode\":\\|versionName\"'")

        matches = re.findall(r'"versionCode":\s*(\d+),\s*"versionName":\s*"([^"]*)"', result.output)
        if not matches:
            return dict(
                version_name='',
                version_code=''
            )

        # Select the last match
        version_code, version_name = matches[-1]
        version_code = int(version_code) if version_code.isdigit() else None
        version_name = version_name if version_name != "" else None

        return dict(
            version_name=version_name,
            version_code=version_code
        )

    def has_app(self, package_name: str) -> bool:
        data = self.shell("bm dump -a").output
        return True if package_name in data else False

    def start_app(self, package_name: str, ability_name: str):
        return self.shell(f"aa start -a {ability_name} -b {package_name}")

    def stop_app(self, package_name: str):
        return self.shell(f"aa force-stop {package_name}")

    def current_app(self) -> Tuple[Optional[str], Optional[str]]:
            """
            Get the current foreground application information.
            
            Returns:
                Tuple[Optional[str], Optional[str]]: (package_name, page_name) or (None, None)
                
            Examples:
                >>> current_app()
                ('cn.rayneo.mercury', 'cn.rayneo.mercury.SplashActivity')
            """
            data: CommandResult = self.shell("aa dump -l")
            if not data or not data.output:
                return (None, None)
            
            output = data.output
            
            # 找到所有 Mission 块，定位 FOREGROUND 状态的任务
            # 使用正则匹配 Mission 块
            mission_pattern = r'Mission ID #\d+(.*?)(?=Mission ID #\d+|$)'
            missions = re.findall(mission_pattern, output, re.DOTALL)
            
            for mission in missions:
                if 'state #FOREGROUND' in mission:
                    # 方法1：从 mission name 中提取真实应用信息（最准确）
                    mission_name_match = re.search(r'mission name #\[#([^\]]+)\]', mission)
                    if mission_name_match:
                        mission_name = mission_name_match.group(1)
                        parts = mission_name.split(':')
                        
                        if len(parts) >= 3:
                            # 格式: package:type:ability
                            package_name = parts[0]      # cn.rayneo.mercury
                            page_name = parts[2]         # cn.rayneo.mercury.SplashActivity
                            return (package_name, page_name)
                        elif len(parts) >= 1:
                            return (parts[0], None)
                    
                    # 方法2：如果 mission name 解析失败，使用 bundle name 作为备选
                    bundle_match = re.search(r'bundle name \[([^\]]+)\]', mission)
                    main_match = re.search(r'main name \[([^\]]+)\]', mission)
                    if bundle_match:
                        return (bundle_match.group(1), main_match.group(1) if main_match else None)
                    
                    break
            
            return (None, None)

    def wakeup(self):
        self.shell("power-shell wakeup")

    def screen_state(self) -> str:
        """
        ["INACTIVE", "SLEEP, AWAKE"]
        """
        data = self.shell("hidumper -s PowerManagerService -a -s").output
        pattern = r"Current State:\s*(\w+)"
        match = re.search(pattern, data)

        return match.group(1) if match else None

    def wlan_ip(self) -> Union[str, None]:
        data = self.shell("ifconfig").output
        matches = re.findall(r'inet addr:(?!127)(\d+\.\d+\.\d+\.\d+)', data)
        return matches[0] if matches else None

    def __split_text(self, text: str) -> str:
        return text.split("\n")[0].strip() if text else None

    def sdk_version(self) -> str:
        data = self.shell("param get const.ohos.apiversion").output
        return self.__split_text(data)

    def sys_version(self) -> str:
        data = self.shell("param get const.product.software.version").output
        return self.__split_text(data)

    def model(self) -> str:
        data = self.shell("param get const.product.model").output
        return self.__split_text(data)

    def brand(self) -> str:
        data = self.shell("param get const.product.brand").output
        return self.__split_text(data)

    def product_name(self) -> str:
        data = self.shell("param get const.product.name").output
        return self.__split_text(data)

    def cpu_abi(self) -> str:
        data = self.shell("param get const.product.cpu.abilist").output
        return self.__split_text(data)

    def display_size(self) -> Tuple[int, int]:
        data = self.shell("hidumper -s RenderService -a screen").output
        match = re.search(r'activeMode:\s*(\d+)x(\d+),\s*refreshrate=\d+', data)

        if match:
            w = int(match.group(1))
            h = int(match.group(2))
            return (w, h)
        return (0, 0)

    def send_key(self, key_code: Union[KeyCode, int]) -> None:
        if isinstance(key_code, KeyCode):
            key_code = key_code.value

        MAX = 3200
        if key_code > MAX:
            raise HdcError("Invalid HDC keycode")

        self.shell(f"uitest uiInput keyEvent {key_code}")

    def tap(self, x: int, y: int) -> None:
        self.shell(f"uitest uiInput click {x} {y}")

    def swipe(self, x1, y1, x2, y2, speed=1000):
        self.shell(f"uitest uiInput swipe {x1} {y1} {x2} {y2} {speed}")

    def input_text(self, x: int, y: int, text: str):
        self.shell(f"uitest uiInput inputText {x} {y} {text}")

    def screenshot(self, path: str, method: str = "snapshot_display") -> str:
        """
        Take a screenshot using one of the two available methods.

        Args:
            path (str): The local path where the screenshot will be saved.
            method (str): The screenshot method to use. Options are:
                          - "snapshot_display" (default, recommended for better performance)
                            This method is faster and more efficient, but the image quality is lower.
                          - "screenCap" (alternative method)
                            This method produces higher-quality images (5~20 times clearer), but it is slower.

        Returns:
            str: The local path where the screenshot is saved.
        """
        if method == "snapshot_display":
            # Use the recommended method (snapshot_display)
            _uuid = uuid.uuid4().hex
            _tmp_path = f"/data/local/tmp/_tmp_{_uuid}.jpeg"
            self.shell(f"snapshot_display -f {_tmp_path}")
            self.recv_file(_tmp_path, path)
            self.shell(f"rm -rf {_tmp_path}")
        elif method == "screenCap":
            # Use the alternative method (screenCap)
            _uuid = uuid.uuid4().hex
            _tmp_path = f"/data/local/tmp/{_uuid}.png"
            self.shell(f"uitest screenCap -p {_tmp_path}")
            self.recv_file(_tmp_path, path)
            self.shell(f"rm -rf {_tmp_path}")
        else:
            raise ValueError(f"Invalid screenshot method: {method}. Use 'snapshot_display' or 'screenCap'.")

        return path

    def dump_hierarchy(self) -> Dict:
        _tmp_path = f"/data/local/tmp/{self.serial}_tmp.json"
        self.shell(f"uitest dumpLayout -p {_tmp_path}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            path = f.name
            self.recv_file(_tmp_path, path)

            try:
                with open(path, 'r', encoding='utf8') as file:
                    data = json.load(file)
            except Exception as e:
                logger.error(f"Error loading JSON file: {e}")
                data = {}

            return data

    def battery_info(self) -> Dict:
        """
        Get battery information from the device.

        Returns:
            Dict: Battery information including:
                - capacity: Battery level (0-100)
                - chargingStatus: Charging status (1=DISCHARGING, 2=NOT_CHARGING, 3=CHARGING, 4=FULL)
                - healthState: Battery health state
                - pluggedType: Plugged type
                - voltage: Battery voltage
                - temperature: Battery temperature
        """
        data: CommandResult = self.shell("hidumper -s BatteryService -a '-i'")
        output = data.output

        result = {}
        # Parse key-value pairs like "capacity: 100"
        for line in output.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                # Try to convert to int
                try:
                    result[key] = int(value)
                except ValueError:
                    result[key] = value

        return result

    def screen_brightness(self) -> int:
        """
        Get the current screen brightness.

        Returns:
            int: Screen brightness value (1-255)
        """
        data: CommandResult = self.shell("hidumper -s DisplayPowerManagerService")
        output = data.output

        # Parse: Brightness=38
        match = re.search(r'Brightness=(\d+)', output)
        if match:
            return int(match.group(1))
        return 0

    def network_type(self) -> str:
        """
        Get the current network type.

        Returns:
            str: Network type - "WiFi", "MOBILE", or "NO_NETWORK"
        """
        data: CommandResult = self.shell("ifconfig")
        output = data.output

        # Check if wlan0 has an IP address (WiFi connected)
        if 'wlan0' in output:
            wlan_section = output.split('wlan0')[1].split('\n\n')[0] if '\n\n' in output.split('wlan0')[1] else output.split('wlan0')[1]
            if re.search(r'inet addr:(\d+\.\d+\.\d+\.\d+)', wlan_section):
                return "WiFi"

        # Check for mobile data (rmnet0, ccmni0, etc.)
        if re.search(r'rmnet\d|ccmni\d', output):
            return "MOBILE"

        return "NO_NETWORK"

    # ============================================
    # Performance Monitoring Methods
    # ============================================

    def _get_pid(self, package_name: str) -> Optional[int]:
        """
        Get the PID of a package by its name.

        Args:
            package_name: The package name to look up.

        Returns:
            Optional[int]: The PID if found, None otherwise.
        """
        data: CommandResult = self.shell(f"ps -ef | grep {package_name}")
        output = data.output

        for line in output.strip().split('\n'):
            if package_name in line and 'grep' not in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        return int(parts[1])
                    except ValueError:
                        continue
        return None

    def memory_info(self, package_name: Optional[str] = None) -> Dict:
        """
        Get memory information.

        Args:
            package_name: Package name to get memory for. If None, returns system-wide memory info.

        Returns:
            Dict: Memory information including total_pss, native_heap, ark_ts_heap, graph, etc.
        """
        if package_name:
            pid = self._get_pid(package_name)
            if not pid:
                return {}
            data: CommandResult = self.shell(f"hidumper --mem {pid}")
        else:
            data: CommandResult = self.shell("hidumper --mem")

        output = data.output
        result = {}

        if package_name:
            # Parse per-PID memory format (detailed categories)
            # Format: Category    Pss Total  Shared Clean  ...
            # Example: GL           2698              0              0              0           2698
            for line in output.split('\n'):
                line = line.strip()

                # Parse summary line like "Total         238067         174544          ..."
                if line.startswith('Total') and 'kB' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            result['total_pss'] = int(parts[1])
                            result['total'] = int(parts[1])
                        except ValueError:
                            pass

                # Parse individual categories like "GL           2698" or "ark ts heap          48776"
                # Match lines that start with a category name followed by numbers
                match = re.match(r'^([A-Za-z][\w\s]*?)\s+(\d+)\s+', line)
                if match:
                    category = match.group(1).strip().lower().replace(' ', '_')
                    try:
                        result[category] = int(match.group(2))
                    except ValueError:
                        pass
        else:
            # Parse system-wide memory format (process list)
            # Format: PID    Total Pss(xxx in SwapPss) kB    Total Vss kB    ...    Name
            # Calculate totals across all processes
            total_pss = 0
            total_vss = 0
            total_rss = 0
            total_uss = 0
            process_count = 0

            for line in output.split('\n'):
                line = line.strip()

                # Skip header lines
                if not line or line.startswith('-') or line.startswith('PID') or '[memory]' in line:
                    continue

                # Parse process line: PID    Total Pss(...) kB    Total Vss kB    Total Rss kB    Total Uss kB    ...
                # Example: 1            4196(284 in SwapPss) kB   2162036 kB      7316 kB      3604 kB
                match = re.match(r'^(\d+)\s+(\d+)\(', line)
                if match:
                    try:
                        total_pss += int(match.group(2))
                        process_count += 1
                    except ValueError:
                        continue

                    # Try to get more fields
                    parts = line.split()
                    # Find kB positions and extract values
                    try:
                        # Format: PID Pss kB Vss kB Rss kB Uss kB ...
                        # Find indices of 'kB' tokens
                        kb_indices = [i for i, p in enumerate(parts) if p == 'kB']
                        if len(kb_indices) >= 4:
                            # Pss is already captured
                            # Vss is before second kB
                            vss_idx = kb_indices[1] - 1
                            rss_idx = kb_indices[2] - 1
                            uss_idx = kb_indices[3] - 1
                            if vss_idx > 0:
                                total_vss += int(parts[vss_idx])
                            if rss_idx > 0:
                                total_rss += int(parts[rss_idx])
                            if uss_idx > 0:
                                total_uss += int(parts[uss_idx])
                    except (ValueError, IndexError):
                        pass

            result = {
                'total_pss': total_pss,
                'total_vss': total_vss,
                'total_rss': total_rss,
                'total_uss': total_uss,
                'process_count': process_count
            }

        return result

    def cpu_usage(self) -> Dict:
        """
        Get CPU usage information.

        Returns:
            Dict: CPU usage including total, user, kernel percentages and per-process usage.
        """
        data: CommandResult = self.shell("hidumper --cpuusage")
        output = data.output

        result = {
            "total": 0.0,
            "user": 0.0,
            "kernel": 0.0,
            "iowait": 0.0,
            "irq": 0.0,
            "idle": 0.0,
            "processes": []
        }

        for line in output.split('\n'):
            line = line.strip()

            # Parse: Total: 3.01%; User Space: 1.53%; Kernel Space: 1.48%; iowait: 0.00%; irq: 0.05%; idle: 96.94%
            if 'Total:' in line:
                match = re.search(r'Total:\s*([\d.]+)%', line)
                if match:
                    result['total'] = float(match.group(1))

                match = re.search(r'User Space:\s*([\d.]+)%', line)
                if match:
                    result['user'] = float(match.group(1))

                match = re.search(r'Kernel Space:\s*([\d.]+)%', line)
                if match:
                    result['kernel'] = float(match.group(1))

                match = re.search(r'iowait:\s*([\d.]+)%', line)
                if match:
                    result['iowait'] = float(match.group(1))

                match = re.search(r'irq:\s*([\d.]+)%', line)
                if match:
                    result['irq'] = float(match.group(1))

                match = re.search(r'idle:\s*([\d.]+)%', line)
                if match:
                    result['idle'] = float(match.group(1))

            # Parse process lines like: "    1512       0.57%           0.57%          0.00%           40937                3466            sensor_host    "
            parts = line.split()
            if len(parts) >= 7:
                try:
                    pid = int(parts[0])
                    total_usage = float(parts[1].rstrip('%'))
                    user_usage = float(parts[2].rstrip('%'))
                    kernel_usage = float(parts[3].rstrip('%'))
                    name = parts[-1]

                    result['processes'].append({
                        "pid": pid,
                        "total": total_usage,
                        "user": user_usage,
                        "kernel": kernel_usage,
                        "name": name
                    })
                except (ValueError, IndexError):
                    continue

        return result

    def cpu_freq(self) -> List[Dict]:
        """
        Get CPU frequency information for each core.

        Returns:
            List[Dict]: List of CPU frequency info, each containing cpu, current, and max frequency.
        """
        data: CommandResult = self.shell("hidumper --cpufreq")
        output = data.output

        result = []
        lines = output.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Parse: cmd is: cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_cur_freq
            cur_match = re.search(r'cpu(\d+)/cpufreq/cpuinfo_cur_freq', line)
            if cur_match:
                cpu_num = int(cur_match.group(1))
                current_freq = None
                max_freq = None

                # Next non-empty line is current frequency
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if i < len(lines):
                    try:
                        current_freq = int(lines[i].strip())
                    except ValueError:
                        pass

                # Skip to find max_freq line
                i += 1
                while i < len(lines) and 'cpuinfo_max_freq' not in lines[i]:
                    i += 1

                if i < len(lines):
                    # Next non-empty line is max frequency
                    i += 1
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    if i < len(lines):
                        try:
                            max_freq = int(lines[i].strip())
                        except ValueError:
                            pass

                if current_freq is not None:
                    result.append({
                        "cpu": cpu_num,
                        "current": current_freq,
                        "max": max_freq if max_freq else current_freq
                    })

            i += 1

        return result

    def refresh_rate(self) -> int:
        """
        Get the current screen refresh rate.

        Returns:
            int: Current refresh rate in Hz (e.g., 60, 90, 120).
        """
        data: CommandResult = self.shell("hidumper -s RenderService -a 'allInfo'")
        output = data.output

        # Parse: activeMode: 1320x2848, refreshRate=60
        match = re.search(r'activeMode:.*refreshRate=(\d+)', output)
        if match:
            return int(match.group(1))
        return 60  # Default to 60Hz

    def fps_timestamps(self) -> List[int]:
        """
        Get frame timestamps for FPS calculation.

        Returns:
            List[int]: List of frame timestamps in nanoseconds.
        """
        data: CommandResult = self.shell("hidumper -s RenderService -a 'fps ScreenNode'")
        output = data.output

        timestamps = []
        for line in output.strip().split('\n'):
            line = line.strip()
            # Timestamps are large integers (nanoseconds)
            if line.isdigit():
                timestamps.append(int(line))

        return timestamps

    def frame_hitchs(self) -> Dict:
        """
        Get frame hitch (jank) statistics.

        Returns:
            Dict: Hitch statistics with over_16ms, over_33ms, over_66ms counts.
        """
        data: CommandResult = self.shell("hidumper -s RenderService -a 'hitchs ScreenNode'")
        output = data.output

        result = {
            "over_16ms": 0,
            "over_33ms": 0,
            "over_66ms": 0
        }

        # Parse: more than 66 ms       0
        #        more than 33 ms       0
        #        more than 16.67 ms    0
        for line in output.split('\n'):
            line = line.strip()

            if 'more than 66 ms' in line or 'more than 66.67 ms' in line:
                match = re.search(r'(\d+)\s*$', line)
                if match:
                    result['over_66ms'] = int(match.group(1))

            if 'more than 33 ms' in line or 'more than 33.33 ms' in line:
                match = re.search(r'(\d+)\s*$', line)
                if match:
                    result['over_33ms'] = int(match.group(1))

            if 'more than 16.67 ms' in line or 'more than 16 ms' in line:
                match = re.search(r'(\d+)\s*$', line)
                if match:
                    result['over_16ms'] = int(match.group(1))

        return result
