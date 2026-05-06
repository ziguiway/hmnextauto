# HMNextAuto API 完整文档

本文档提供 HMNextAuto 所有 API 的详细说明和示例代码。

---

## 目录

- [初始化](#初始化)
- [全局配置](#全局配置)
- [App 管理](#app-管理)
- [设备信息](#设备信息)
- [设备操作](#设备操作)
- [按键操作](#按键操作)
- [触摸手势](#触摸手势)
- [控件操作](#控件操作)
- [XPath 定位](#xpath-定位)
- [视觉定位](#视觉定位)
- [OCR 文字识别](#ocr-文字识别)
- [后台 Watcher](#后台-watcher)
- [Toast 监控](#toast-监控)
- [屏幕录制](#屏幕录制)
- [文件操作](#文件操作)
- [性能监控](#性能监控)
- [后台性能监控](#后台性能监控)
- [性能数据分析](#性能数据分析)
- [通知栏操作](#通知栏操作)
- [HDC 命令](#hdc-命令)

---

## 初始化

### Driver 初始化

```python
from hmnextauto.driver import Driver

# 自动选择第一个连接的设备
d = Driver()

# 指定设备序列号
d = Driver("FMR0223C13000649")

# 关闭连接（推荐在脚本末尾 finally 中调用）
d.close()
```

**单例与 `close()`：** 每个设备序列号（serial）最多对应一个 `Driver` 实例。调用 `close()` 会释放 Hypium/HDC 转发，并从内部注册表移除该 serial；之后再次执行 `Driver(serial)` 会建立**新的**连接与实例。多设备脚本下，关闭一台设备不会影响其它 serial 的已缓存实例。`__del__` 仅作兜底释放连接；请勿依赖析构顺序，务必优先使用 `close()`。

---

## 全局配置

### Settings

通过 `d.settings` 访问全局配置，或使用 `d.implicitly_wait()` 快捷方法。

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `wait_timeout` | 元素等待超时（秒） | `20.0` |
| `poll_interval` | 轮询间隔（秒） | `0.1` |
| `operation_delay` | 操作前后延迟 `(before, after)` | `(0, 0)` |

### implicitly_wait

```python
# 设置全局隐式等待为 10 秒
d.implicitly_wait(10)

# 获取当前超时值
print(d.implicitly_wait())  # 10.0

# 所有 wait 方法自动使用全局超时
d(text="确定").wait()                        # 使用 10 秒
d.xpath('//Button').wait()                    # 使用 10 秒

# 显式 timeout 仍然可以覆盖全局设置
d(text="确定").wait(timeout=3)               # 使用 3 秒
```

### Settings 字典访问

```python
# 查看所有配置
print(d.settings)

# 读取配置
print(d.settings["wait_timeout"])       # 20.0
print(d.settings.get("wait_timeout"))   # 20.0

# 修改配置
d.settings["wait_timeout"] = 15.0
```

---

## App 管理

| API | 说明 | 示例 |
|-----|------|------|
| `install_app(path)` | 安装应用 | `d.install_app("demo.hap")` |
| `uninstall_app(package)` | 卸载应用 | `d.uninstall_app("com.example.app")` |
| `start_app(package, ability)` | 启动应用 | `d.start_app("com.example.app", "EntryAbility")` |
| `stop_app(package)` | 停止应用 | `d.stop_app("com.example.app")` |
| `clear_app(package)` | 清除应用数据 | `d.clear_app("com.example.app")` |
| `force_start_app(package, ability)` | 强制启动（回桌面+停+启） | `d.force_start_app("com.example.app")` |
| `start_app_by_name(name)` | 用应用名启动 | `d.start_app_by_name("微信")` |
| `list_apps(include_system)` | 获取应用列表 | `d.list_apps()` |
| `has_app(package)` | 检查应用是否安装 | `d.has_app("com.example.app")` |
| `get_app_info(package)` | 获取应用详情 | `d.get_app_info("com.example.app")` |
| `current_app()` | 获取当前前台应用 | `d.current_app()` |
| `app_version(package)` | 获取应用版本 | `d.app_version("com.example.app")` |

### 示例代码

```python
# 安装应用
d.install_app("/path/to/app.hap")

# 启动应用（自动获取 main ability）
d.start_app("com.example.app")

# 启动应用（指定 ability）
d.start_app("com.example.app", "EntryAbility")

# 强制启动（先回桌面、停止应用、再启动）
d.force_start_app("com.example.app")

# 用应用名启动（支持模糊匹配）
d.start_app_by_name("微信")
d.start_app_by_name("设置", match="contains", include_system_apps=True)

# 获取应用列表
apps = d.list_apps()                    # 第三方应用
all_apps = d.list_apps(include_system_apps=True)  # 包含系统应用

# 获取当前前台应用
package, ability = d.current_app()
print(f"当前应用: {package}, Ability: {ability}")

# 获取应用信息
info = d.get_app_info("com.example.app")
print(info["versionName"])

# 清除应用数据
d.clear_app("com.example.app")

# 卸载应用
d.uninstall_app("com.example.app")
```

---

## 设备信息

| API | 说明 | 返回类型 |
|-----|------|----------|
| `device_info` | 设备完整信息 | `DeviceInfo` |
| `display_size` | 屏幕分辨率 | `Tuple[int, int]` |
| `display_rotation` | 屏幕旋转状态 | `DisplayRotation` |
| `set_display_rotation(rotation)` | 设置屏幕旋转 | `None` |
| `battery_level` | 电池电量 | `int` |
| `battery_status` | 电池充电状态 | `str` |
| `screen_brightness` | 屏幕亮度 | `int` |
| `network_type` | 网络类型 | `str` |
| `is_screen_on` | 屏幕是否亮起 | `bool` |

### 示例代码

```python
from hmnextauto.proto import DeviceInfo, DisplayRotation

# 获取设备信息
info: DeviceInfo = d.device_info
print(info.productName)    # 产品名称: HUAWEI Mate 60 Pro
print(info.model)          # 型号: ALN-AL00
print(info.sdkVersion)     # SDK 版本: 12
print(info.sysVersion)     # 系统版本
print(info.cpuAbi)         # CPU 架构: arm64-v8a
print(info.wlanIp)         # WLAN IP
print(info.displaySize)    # 分辨率: (1260, 2720)
print(info.displayRotation)# 旋转状态: DisplayRotation.ROTATION_0

# 获取屏幕分辨率
width, height = d.display_size
print(f"分辨率: {width}x{height}")

# 获取/设置屏幕旋转
rotation = d.display_rotation
d.set_display_rotation(DisplayRotation.ROTATION_180)

# 获取电池信息
print(f"电池电量: {d.battery_level}")      # 0-100
print(f"电池状态: {d.battery_status}")    # DISCHARGING/CHARGING/FULL/NOT_CHARGING

# 获取屏幕亮度
print(f"屏幕亮度: {d.screen_brightness}")  # 1-255

# 获取网络类型
print(f"网络类型: {d.network_type}")      # WiFi/MOBILE/NO_NETWORK

# 检查屏幕状态
print(f"屏幕亮起: {d.is_screen_on}")      # True/False
```

---

## 设备操作

| API | 说明 |
|-----|------|
| `screen_on()` | 亮屏 |
| `screen_off()` | 息屏 |
| `unlock()` | 解锁屏幕 |
| `go_home()` | 回到桌面 |
| `go_back()` | 返回 |
| `open_url(url)` | 打开 URL/Schema |
| `screenshot(path)` | 截图 |

### 示例代码

```python
# 亮屏/息屏
d.screen_on()
d.screen_off()

# 解锁屏幕（会自动亮屏并上滑）
d.unlock()

# 回到桌面
d.go_home()
d.press_home()  # 别名

# 返回
d.go_back()
d.press_back()  # 别名

# 打开 URL
d.open_url("https://www.baidu.com")
d.open_url("kwai://myprofile")  # Schema

# 截图
d.screenshot("./screenshot.png")

# 截图（高质量模式）
d.screenshot("./screenshot.png", method="screenCap")
```

---

## 按键操作

| API | 说明 | KeyCode |
|-----|------|---------|
| `press_key(key)` | 发送任意按键 | - |
| `press_power()` | 电源键 | `POWER` |
| `press_menu()` | 菜单键 | `MENU` |
| `press_enter()` | 回车键 | `ENTER` |
| `press_backspace()` | 退格键 | `DEL` |
| `press_delete()` | 删除键 | `FORWARD_DEL` |
| `press_tab()` | Tab 键 | `TAB` |
| `press_space()` | 空格键 | `SPACE` |
| `press_escape()` | ESC 键 | `ESCAPE` |
| `volume_up()` | 音量+ | `VOLUME_UP` |
| `volume_down()` | 音量- | `VOLUME_DOWN` |
| `volume_mute()` | 静音 | `VOLUME_MUTE` |
| `page_up()` | 上翻页 | `PAGE_UP` |
| `page_down()` | 下翻页 | `PAGE_DOWN` |
| `press_dpad_up()` | 方向键上 | `DPAD_UP` |
| `press_dpad_down()` | 方向键下 | `DPAD_DOWN` |
| `press_dpad_left()` | 方向键左 | `DPAD_LEFT` |
| `press_dpad_right()` | 方向键右 | `DPAD_RIGHT` |
| `press_dpad_center()` | 方向键确认 | `DPAD_CENTER` |
| `press_multitask()` | 多任务键 | `VIRTUAL_MULTITASK` |
| `press_search()` | 搜索键 | `FIND` |
| `press_brightness_up()` | 亮度+ | `BRIGHTNESS_UP` |
| `press_brightness_down()` | 亮度- | `BRIGHTNESS_DOWN` |

### 示例代码

```python
from hmnextauto.proto import KeyCode

# 使用封装方法
d.press_power()
d.press_back()
d.volume_up()

# 发送任意按键
d.press_key(KeyCode.POWER)
d.press_key(2017)  # 直接使用数字码
```

---

## 触摸手势

### 基础手势

| API | 说明 |
|-----|------|
| `click(x, y)` | 单击 |
| `double_click(x, y)` | 双击 |
| `long_click(x, y)` | 长按 |
| `swipe(x1, y1, x2, y2, speed)` | 滑动 |
| `swipe_ext(direction, scale, box)` | 方向滑动 |
| `input_text(text)` | 输入文本 |

### 示例代码

```python
# 单击（支持绝对坐标和百分比）
d.click(500, 1000)      # 绝对坐标
d.click(0.5, 0.4)       # 百分比坐标

# 双击
d.double_click(500, 1000)
d.double_click(0.5, 0.4)

# 长按
d.long_click(500, 1000)

# 滑动
d.swipe(500, 1000, 500, 500, speed=2000)  # 绝对坐标
d.swipe(0.5, 0.8, 0.5, 0.4, speed=2000)   # 百分比坐标

# 方向滑动
from hmnextauto.proto import SwipeDirection

d.swipe_ext("up")                              # 向上滑动
d.swipe_ext("down")                            # 向下滑动
d.swipe_ext("left")                            # 向左滑动
d.swipe_ext("right")                           # 向右滑动
d.swipe_ext(SwipeDirection.UP)                 # 使用枚举
d.swipe_ext("up", scale=0.8)                   # 滑动距离为屏幕高度的 80%
d.swipe_ext("up", box=(0.2, 0.2, 0.8, 0.8))   # 在指定区域内滑动

# 输入文本（需要先点击输入框获取焦点）
d.click(500, 1000)
d.input_text("hello world")
```

### 复杂手势

```python
# 链式调用复杂手势
d.gesture.start(630, 984, interval=0.5) \
    .move(200, 400, interval=0.5) \
    .pause(interval=1) \
    .move(500, 600, interval=0.5) \
    .action()

# 简单点击（只有 start）
d.gesture.start(0.5, 0.5).action()  # 等价于 d.click(0.5, 0.5)
```

---

## 控件操作

### 选择器

| 选择器 | 说明 |
|--------|------|
| `id` / `resourceId` | 资源 ID |
| `key` | 控件 key |
| `text` | 文本内容 |
| `type` / `className` | 控件类型 |
| `description` | 描述 |
| `clickable` | 是否可点击 |
| `longClickable` | 是否可长按 |
| `scrollable` | 是否可滚动 |
| `enabled` | 是否启用 |
| `focused` | 是否获焦 |
| `selected` | 是否选中 |
| `checked` | 是否勾选 |
| `checkable` | 是否可勾选 |
| `index` | 索引（多个匹配时选择第几个） |
| `isBefore` | 定位前面的元素 |
| `isAfter` | 定位后面的元素 |

### 模糊匹配选择器

| 选择器 | 说明 |
|--------|------|
| `textContains` | 文本包含 |
| `textStartsWith` | 文本开头 |
| `textEndsWith` | 文本结尾 |
| `textMatches` | 文本正则匹配 |
| `descriptionContains` | 描述包含 |
| `descriptionMatches` | 描述正则匹配 |
| `typeContains` | 类型包含 |
| `typeMatches` | 类型正则匹配 |
| `idContains` | ID 包含 |
| `idMatches` | ID 正则匹配 |
| `resourceIdContains` | 资源 ID 包含 |
| `resourceIdMatches` | 资源 ID 正则匹配 |

### 控件方法

| API | 说明 | 返回类型 |
|-----|------|----------|
| `exists()` | 是否存在 | `bool` |
| `wait(timeout)` | 等待出现 | `bool` |
| `wait_gone(timeout)` | 等待消失 | `bool` |
| `wait_enabled(timeout)` | 等待可用 | `bool` |
| `wait_disabled(timeout)` | 等待禁用 | `bool` |
| `wait_clickable(timeout)` | 等待可点击 | `bool` |
| `wait_until(condition, timeout)` | 等待自定义条件 | `bool` |
| `wait_until_not(condition, timeout)` | 等待条件不满足 | `bool` |
| `find_component()` | 查找控件 | `ComponentData` |
| `count` | 控件数量 | `int` |
| `info` | 控件信息 | `ElementInfo` |
| `click()` | 点击 | - |
| `click_if_exists()` | 存在才点击 | - |
| `double_click()` | 双击 | - |
| `long_click()` | 长按 | - |
| `input_text(text)` | 输入文本 | - |
| `clear_text()` | 清除文本 | - |
| `drag_to(component)` | 拖拽到目标 | - |
| `pinch_in(scale)` | 捏合缩小 | - |
| `pinch_out(scale)` | 捏合放大 | - |

### 示例代码

```python
# 基础定位
d(text="确定").click()
d(id="btn_submit").click()
d(type="Button", text="登录").click()

# 索引定位（多个匹配时选择第几个）
d(type="Button", index=0).click()

# 组合定位
d(type="Button", text="确定", enabled=True).click()

# 相对定位
d(text="密码", isAfter=True).input_text("123456")  # 定位"密码"后面的元素
d(text="用户名", isBefore=True).input_text("admin")  # 定位"用户名"前面的元素

# 模糊匹配
d(textContains="确").click()                    # 文本包含"确"
d(textMatches=r"^\d+条$").click()              # 正则匹配
d(resourceIdContains="entry").click()          # ID 包含"entry"
d(typeMatches="Text|Button").click()           # 类型正则匹配

# 检查存在
if d(text="确定").exists():
    d(text="确定").click()

# 等待出现/消失
if d(text="加载完成").wait(timeout=10):
    print("加载完成")

if d(type="Dialog").wait_gone(timeout=5):
    print("弹窗已消失")

# 等待可用/禁用
if d(id="submit_btn").wait_enabled(timeout=5):
    print("按钮已可用")

if d(id="submit_btn").wait_disabled(timeout=5):
    print("按钮已禁用")

# 等待可点击
if d(text="确定").wait_clickable(timeout=5):
    d(text="确定").click()

# 自定义条件等待
# 等待文本变为指定内容
d(id="status").wait_until(lambda e: e.text == "完成", timeout=10)

# 等待元素被选中
d(id="checkbox").wait_until(lambda e: e.isChecked, timeout=5)

# 等待条件不再满足
d(id="loading").wait_until_not(lambda e: e.isEnabled, timeout=10)

# 存在才点击（不存在不报错）
d(text="跳过").click_if_exists()

# 获取控件数量
count = d(type="Button").count
print(f"页面有 {count} 个按钮")

# 获取控件信息
info = d(text="确定").info
print(info.text)
print(info.bounds)
print(info.boundsCenter)

# 输入文本
d(text="用户名").input_text("admin")
d(text="密码").input_text("123456")

# 清除文本
d(text="用户名").clear_text()

# 拖拽
from hmnextauto.proto import ComponentData
target: ComponentData = d(type="ListItem", index=5).find_component()
d(type="ListItem", index=0).drag_to(target)

# 缩放
d(text="图片").pinch_in(scale=0.5)   # 缩小
d(text="图片").pinch_out(scale=2)    # 放大
```

### 滚动操作

```python
# 获取可滚动容器
lst = d(type="List", scrollable=True)

# 滚动查找
if lst.scroll.to(text="目标文案", max_swipes=20):
    d(text="目标文案").click()

# 纵向滚动
lst.scroll.vert.forward()    # 向下滚动
lst.scroll.vert.backward()   # 向上滚动
lst.scroll.vert.fling()      # 快速下滑

# 横向滚动
lst.scroll.horiz.forward()   # 向右滚动
lst.scroll.horiz.backward()  # 向左滚动

# 滚动到顶部/底部
lst.scroll.toBeginning()
lst.scroll.toEnd()
```

---

## XPath 定位

| API | 说明 | 返回类型 |
|-----|------|----------|
| `xpath(path)` | XPath 选择器 | `_XMLElement` |
| `.exists()` | 是否存在 | `bool` |
| `.wait(timeout)` | 等待出现 | `bool` |
| `.wait_gone(timeout)` | 等待消失 | `bool` |
| `.wait_enabled(timeout)` | 等待可用 | `bool` |
| `.wait_clickable(timeout)` | 等待可点击 | `bool` |
| `.wait_until(condition)` | 等待条件满足 | `bool` |
| `.wait_until_not(condition)` | 等待条件不满足 | `bool` |
| `.click()` | 点击 | - |
| `.click_if_exists()` | 存在才点击 | - |
| `.double_click()` | 双击 | - |
| `.long_click()` | 长按 | - |
| `.input_text(text)` | 输入文本 | - |
| `.info` | 控件属性 | `dict` |
| `.text` | 文本内容 | `str` |
| `.count` | 匹配数量 | `int` |
| `.all()` | 所有匹配元素 | `List[_XMLElement]` |
| `.first()` | 第一个匹配 | `_XMLElement` |
| `.last()` | 最后一个匹配 | `_XMLElement` |

### 示例代码

```python
# XPath 定位
d.xpath('//*[@text="确定"]').click()
d.xpath('//root[1]/Row[1]/Column[1]/Button[3]').click()

# 等待出现/消失
if d.xpath('//Text[@text="加载完成"]').wait(timeout=10):
    print("加载完成")

if d.xpath('//ProgressBar').wait_gone(timeout=5):
    print("加载完成")

# 等待可用/可点击
d.xpath('//Button').wait_enabled(timeout=5)
d.xpath('//Button').wait_clickable(timeout=5)

# 自定义条件等待
d.xpath('//Text[@id="status"]').wait_until(lambda e: e.get("text") == "完成")

# 存在才点击
d.xpath('//*[@text="跳过"]').click_if_exists()

# 输入文本
d.xpath('//TextField').input_text("hello")

# 获取控件信息
info = d.xpath('//*[@text="确定"]').info
text = d.xpath('//*[@text="确定"]').text

# 获取匹配数量
count = d.xpath('//*[@clickable="true"]').count
print(f"找到 {count} 个可点击元素")

# 获取所有匹配元素
elements = d.xpath('//*[@clickable="true"]').all()
for el in elements:
    print(f"元素位置: {el.bounds}")
    el.click_if_exists()

# 获取第一个/最后一个匹配
first_el = d.xpath('//*[@clickable="true"]').first()
last_el = d.xpath('//*[@clickable="true"]').last()
```

---

## 视觉定位

### 图像匹配

```python
# 图像匹配点击
ok = d.click_image("target.png", threshold=0.88)
if not ok:
    print("未找到目标图片")

# 完整参数
ok = d.click_image(
    template_path="target.png",  # 模板图片路径
    threshold=0.85,              # 匹配阈值 (0.0-1.0)
    grayscale=True,              # 灰度匹配（更快）
    multi_scale=True,            # 多尺度匹配
    scale_range=(0.5, 2.0),      # 缩放范围
    scale_steps=30,              # 缩放步数
    return_result=True,          # 返回匹配结果
    draw_box=True                # 在截图上绘制匹配框
)
```

### 找色点击

```python
# 找色点击
ok = d.click_color((255, 0, 0), tolerance=12)  # RGB 颜色，容差 12

# 限制区域找色
ok = d.click_color(
    rgb=(0, 160, 255),           # RGB 颜色
    tolerance=10,                # 容差
    region=(100, 400, 600, 1200) # 搜索区域 (x1, y1, x2, y2)
)
```

---

## OCR 文字识别

OCR 功能用于识别屏幕上的文字，支持全屏识别、区域识别、查找文字位置等。

> **安装依赖**: OCR 功能需要额外安装 easyocr：
> ```bash
> pip install hmnextauto[ocr]
> # 或
> pip install easyocr
> ```

| API | 说明 | 返回类型 |
|-----|------|----------|
| `ocr.read()` | 识别屏幕所有文字 | `List[OCRResult]` |
| `ocr.read(region)` | 识别指定区域文字 | `List[OCRResult]` |
| `ocr.read(detail=False)` | 只返回文字列表 | `List[str]` |
| `ocr.find_text(text)` | 查找文字位置 | `Tuple[int, int]` 或 `None` |
| `ocr.find_all_text(text)` | 查找所有匹配位置 | `List[Tuple[int, int]]` |
| `ocr.click_text(text)` | 查找并点击文字 | `bool` |
| `ocr.wait_text(text, timeout)` | 等待文字出现 | `bool` |
| `ocr.wait_text_gone(text, timeout)` | 等待文字消失 | `bool` |
| `ocr.read_text_in_region(region)` | 读取区域内文字拼接 | `str` |

### OCRResult 数据结构

```python
@dataclass
class OCRResult:
    text: str                    # 识别的文字
    bbox: Tuple[Tuple[int, int], ...]  # 四个角坐标
    confidence: float            # 置信度 (0.0-1.0)
    
    @property
    def center(self) -> Tuple[int, int]:  # 中心坐标
        ...
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:  # (x1, y1, x2, y2)
        ...
```

### 示例代码

```python
# 识别屏幕所有文字
results = d.ocr.read()
for r in results:
    print(f"文字: {r.text}, 置信度: {r.confidence:.2f}, 位置: {r.center}")

# 只获取文字列表（不返回坐标等信息）
texts = d.ocr.read(detail=False)
print(texts)  # ['文字1', '文字2', ...]

# 识别指定区域
results = d.ocr.read(region=(100, 100, 500, 300))

# 查找文字位置
pos = d.ocr.find_text("登录")
if pos:
    print(f"找到文字，位置: {pos}")
    d.click(pos[0], pos[1])

# 查找所有匹配位置
positions = d.ocr.find_all_text("确定")
for pos in positions:
    print(f"位置: {pos}")

# 查找并点击文字（自动等待）
if d.ocr.click_text("确定", timeout=10):
    print("点击成功")
else:
    print("未找到文字")

# 等待文字出现
if d.ocr.wait_text("加载完成", timeout=30):
    print("文字已出现")

# 等待文字消失
if d.ocr.wait_text_gone("加载中...", timeout=30):
    print("加载完成")

# 读取区域内所有文字（拼接成字符串）
text = d.ocr.read_text_in_region((100, 100, 500, 300))
print(f"区域内文字: {text}")

# 精确匹配（默认部分匹配）
pos = d.ocr.find_text("登录", exact=True)  # 必须完全匹配

# 设置置信度阈值
results = d.ocr.read(min_confidence=0.8)  # 只返回置信度 >= 0.8 的结果

# 指定语言
results = d.ocr.read(languages=["ch_sim", "en"])  # 简体中文 + 英文（默认）
results = d.ocr.read(languages=["en"])  # 仅英文
```

### 完整 OCR 示例

```python
from hmnextauto.driver import Driver

d = Driver()

# 启动应用
d.start_app("com.example.app")

# 等待并点击登录按钮
if d.ocr.click_text("登录", timeout=10):
    print("点击登录成功")

# 识别验证码区域
captcha_text = d.ocr.read_text_in_region((100, 500, 400, 600))
print(f"验证码: {captcha_text}")

# 输入验证码
d(text="验证码输入框").input_text(captcha_text)

# 等待登录成功
if d.ocr.wait_text("欢迎", timeout=10):
    print("登录成功")
```

---

## 后台 Watcher

用于自动处理弹窗、广告等。

| API | 说明 |
|-----|------|
| `watcher(name)` | 创建/获取 watcher |
| `.when(**kwargs)` | 设置选择器条件 |
| `.when_xpath(path)` | 设置 XPath 条件 |
| `.click()` | 匹配时点击 |
| `.press_back()` | 匹配时返回 |
| `.do(fn)` | 匹配时执行自定义函数 |
| `watcher.start(interval)` | 启动监控 |
| `watcher.stop()` | 停止监控 |
| `watcher.remove(name)` | 移除规则 |
| `watcher.clear()` | 清空所有规则 |
| `watcher.running` | 是否运行中 |
| `watcher.rule_names` | 规则名称列表 |

### 示例代码

```python
# 注册规则
d.watcher("ad").when_xpath('//*[@text="跳过"]').click()
d.watcher("ok").when(text="确定").click()
d.watcher("back").when(text="暂无").press_back()

# 自定义回调
def my_handler(driver):
    driver.go_back()
    print("处理完成")

d.watcher("custom").when(type="Dialog").do(my_handler)

# 启动监控
d.watcher.start(interval=0.3)  # 每 0.3 秒检查一次

# 主流程
d.start_app("com.example.app")
d(text="按钮").click()

# 停止监控
d.watcher.stop()

# 移除规则
d.watcher.remove("ad")

# 清空所有规则
d.watcher.clear()

# 查看状态
print(d.watcher.running)       # 是否运行中
print(d.watcher.rule_names)    # 规则名称列表
```

---

## Toast 监控

| API | 说明 |
|-----|------|
| `toast_watcher.start()` | 启动 Toast 监控 |
| `toast_watcher.get_toast(timeout)` | 获取 Toast 内容 |

### 示例代码

```python
# 启动监控
d.toast_watcher.start()

# 触发 Toast 的操作
d(text="显示 Toast").click()

# 获取 Toast
toast = d.toast_watcher.get_toast(timeout=3)
print(f"Toast: {toast}")
```

---

## 屏幕录制

| API | 说明 |
|-----|------|
| `screenrecord.start(path)` | 开始录屏 |
| `screenrecord.stop()` | 停止录屏 |

### 示例代码

```python
# 方式一：手动控制
d.screenrecord.start("test.mp4")
# 执行操作
time.sleep(5)
d.screenrecord.stop()

# 方式二：上下文管理器（推荐）
with d.screenrecord.start("test.mp4"):
    d(text="按钮").click()
    time.sleep(5)
# 自动停止录屏
```

---

## 性能数据分析

PerformanceAnalyzer 用于对采集的性能数据进行深度分析。

| API | 说明 | 返回类型 |
|-----|------|----------|
| `PerformanceAnalyzer.from_file(path)` | 从 JSONL 文件加载 | `PerformanceAnalyzer` |
| `.stats()` | 获取统计摘要 | `PerformanceStats` |
| `.detect_anomalies()` | 检测性能异常 | `List[Anomaly]` |
| `.score()` | 计算性能评分 | `PerformanceScore` |
| `.generate_report(path)` | 生成 HTML 报告 | `str` |

### 示例代码

```python
from hmnextauto._performance_analyzer import PerformanceAnalyzer

# 方式1: 从文件加载
analyzer = PerformanceAnalyzer.from_file("perf.jsonl")

# 方式2: 从 PerformanceWatcher 获取
with d.performance_watcher.start("perf.jsonl") as pw:
    # 执行测试
    d(text="按钮").click()
analyzer = pw.analyze()

# 获取统计摘要
stats = analyzer.stats()
print(f"FPS 平均: {stats.fps.avg:.1f}")
print(f"FPS P95: {stats.fps.p95:.1f}")
print(f"内存峰值: {stats.memory_peak_mb:.1f} MB")
print(f"监控时长: {stats.duration_seconds:.1f}s")

# 检测异常
anomalies = analyzer.detect_anomalies()
for a in anomalies:
    print(f"[{a.severity.value}] {a.type.value}: {a.message}")

# 性能评分
score = analyzer.score()
print(f"性能等级: {score.grade} ({score.total}/100)")
print(f"FPS: {score.fps}/30, 流畅度: {score.fluency}/30")
print(f"内存: {score.memory}/20, CPU: {score.cpu}/20")

# 生成 HTML 报告
analyzer.generate_report("perf_report.html", include_charts=True)
```

### 性能评分规则

| 维度 | 分值 | 评分标准 |
|------|------|----------|
| FPS | 30分 | ≥55 FPS 得满分，45-55 得 25 分，30-45 得 15 分 |
| 流畅度 | 30分 | 无卡顿得满分，卡顿越少分数越高 |
| 内存 | 20分 | 峰值内存 ≤500MB 得满分 |
| CPU | 20分 | 平均 CPU ≤25% 得满分 |

| 等级 | 分数范围 |
|------|----------|
| S | ≥90 |
| A | ≥80 |
| B | ≥70 |
| C | ≥60 |
| D | ≥50 |
| F | <50 |

### 异常检测类型

| 类型 | 说明 | 严重程度 |
|------|------|----------|
| `fps_drop` | FPS 突降（下降 50%+） | CRITICAL |
| `low_fps` | 持续低 FPS（连续 5 次低于 30） | WARNING |
| `memory_spike` | 内存突增（增长 30%+） | WARNING |
| `memory_leak` | 内存泄漏（持续增长 10%+） | WARNING |
| `high_cpu` | CPU 持续高占用（连续 5 次高于 80%） | WARNING |
| `jank` | 严重卡顿（帧超过 66ms） | CRITICAL |

---

## 文件操作

| API | 说明 |
|-----|------|
| `pull_file(rpath, lpath)` | 从设备拉取文件 |
| `push_file(lpath, rpath)` | 推送文件到设备 |

### 示例代码

```python
# 从设备拉取文件
d.pull_file("/data/local/tmp/test.png", "./test.png")

# 推送文件到设备
d.push_file("./local.txt", "/data/local/tmp/remote.txt")
```

---

## 性能监控

| API | 说明 | 返回类型 |
|-----|------|----------|
| `memory_info()` | 获取系统内存信息 | `Dict` |
| `memory_info(package)` | 获取指定应用内存信息 | `Dict` |
| `memory_percent()` | 获取系统内存使用率 | `float` |
| `cpu_usage()` | 获取 CPU 使用率 | `Dict` |
| `cpu_freq()` | 获取 CPU 频率 | `List[Dict]` |
| `thermal_info()` | 获取设备温度信息 | `Dict[str, float]` |
| `refresh_rate` | 获取屏幕刷新率 | `int` |
| `fps()` | 获取实时 FPS | `float` |
| `frame_hitchs()` | 获取帧卡顿统计 | `Dict` |
| `app_start_time(package)` | 获取应用启动时间戳 | `int` |
| `measure_cold_start(package)` | 测量冷启动时间 | `Dict` |
| `measure_hot_start(package)` | 测量热启动时间 | `Dict` |
| `process_info(package)` | 获取进程信息 | `Dict` |
| `performance_watcher` | 后台持续性能监控 | `PerformanceWatcher` |

### 示例代码

```python
# 获取系统内存信息（来自 /proc/meminfo，快速 ~0.2s）
sys_mem = d.memory_info()
print(f"总内存: {sys_mem['memtotal'] / 1024:.1f} MB")
print(f"可用内存: {sys_mem['memfree'] / 1024:.1f} MB")
print(f"已用内存: {sys_mem['total_pss'] / 1024:.1f} MB")

# 获取指定应用内存信息（来自 hidumper --mem <PID>，~1.5s）
app_mem = d.memory_info("com.huawei.hmos.camera")
print(f"总 PSS: {app_mem['total_pss'] / 1024:.1f} MB")
print(f"Native Heap: {app_mem['native_heap'] / 1024:.1f} MB")
print(f"Ark TS Heap: {app_mem['ark_ts_heap'] / 1024:.1f} MB")
print(f"Graph: {app_mem.get('graph', 0) / 1024:.1f} MB")

# 获取 CPU 使用率
cpu = d.cpu_usage()
print(f"总使用率: {cpu['total']}%")
print(f"用户态: {cpu['user']}%")
print(f"内核态: {cpu['kernel']}%")
print(f"进程数: {len(cpu['processes'])}")

# 获取 CPU 频率
freqs = d.cpu_freq()
for f in freqs:
    print(f"CPU {f['cpu']}: {f['current'] / 1000} MHz / {f['max'] / 1000} MHz")

# 获取屏幕刷新率
print(f"刷新率: {d.refresh_rate} Hz")

# 获取实时 FPS
fps = d.fps()
print(f"当前 FPS: {fps}")

# 获取帧卡顿统计
hitchs = d.frame_hitchs()
print(f"超过 16ms: {hitchs['over_16ms']}")
print(f"超过 33ms: {hitchs['over_33ms']}")
print(f"超过 66ms: {hitchs['over_66ms']}")

# 获取设备温度信息（摄氏度）
thermal = d.thermal_info()
print(f"CPU 温度: {thermal.get('soc_thermal', 0):.1f} C")
print(f"电池温度: {thermal.get('battery', 0):.1f} C")

# 获取系统内存使用率
mem_percent = d.memory_percent()
print(f"内存使用率: {mem_percent:.1f}%")

# 获取应用启动时间戳（系统启动后的时间）
start_time = d.app_start_time("com.huawei.hmos.camera")
print(f"启动时间戳: {start_time} ms")

# 测量冷启动时间（先停止应用再启动）
cold_result = d.measure_cold_start("com.huawei.hmos.settings")
print(f"冷启动成功: {cold_result['success']}")
print(f"冷启动时间: {cold_result['duration_ms']} ms")

# 测量热启动时间（应用在后台，切回前台）
hot_result = d.measure_hot_start("com.huawei.hmos.settings")
print(f"热启动成功: {hot_result['success']}")
print(f"热启动时间: {hot_result['duration_ms']} ms")

# 获取进程信息
info = d.process_info("com.huawei.hmos.camera")
print(f"PID: {info['pid']}")
print(f"包名: {info['package_name']}")
print(f"总 PSS: {info['total_pss'] / 1024:.1f} MB")
```

### 性能监控完整示例

```python
import time
from hmnextauto.driver import Driver

d = Driver()

# 启动应用并监控性能
d.force_start_app("com.example.app")

# 等待应用启动
time.sleep(2)

# 性能快照
print("=== 性能快照 ===")
print(f"FPS: {d.fps():.1f}")
print(f"CPU: {d.cpu_usage()['total']:.1f}%")

app_mem = d.memory_info("com.example.app")
print(f"内存: {app_mem['total_pss'] / 1024:.1f} MB")

hitchs = d.frame_hitchs()
print(f"卡顿帧: {hitchs['over_16ms']}")

# 持续监控
for i in range(10):
    time.sleep(1)
    print(f"[{i+1}] FPS: {d.fps():.1f}, CPU: {d.cpu_usage()['total']:.1f}%")
```

---

## 后台性能监控

PerformanceWatcher 用于在测试过程中持续监控性能指标，后台线程采集数据并导出到文件。

| API | 说明 |
|-----|------|
| `performance_watcher` | 获取 PerformanceWatcher 实例 |
| `.configure(metrics, package, output_file, interval)` | 配置监控参数 |
| `.start(output_file, interval)` | 启动监控 |
| `.stop()` | 停止监控 |
| `.running` | 是否运行中 |
| `.get_summary()` | 获取统计摘要 |
| `.analyze()` | 返回性能分析器实例 |

### 支持的指标

| 指标 | 说明 | 采集速度 |
|------|------|----------|
| `fps` | 实时帧率 | ~0.3s |
| `cpu` | CPU 使用率 | ~0.3s |
| `cpu_freq` | 各核心 CPU 频率 | ~1.8s |
| `memory` | 内存 PSS | ~1.5s (指定 PID) / ~40s (全系统) |
| `hitches` | 帧卡顿统计 | ~0.2s |
| `thermal` | CPU 温度（摄氏度） | ~0.5s |
| `memory_percent` | 系统内存使用率 | ~0.2s |

> ⚠️ **性能提示**: 内存采集时，指定 `package` 参数可将采集时间从 40 秒降至 1-2 秒！

### 示例代码

```python
# 方式1: 简单用法 - 监控所有指标
pw = d.performance_watcher
pw.start(output_file="perf.jsonl", interval=1.0)
# ... 执行业务测试 ...
pw.stop()

# 方式2: 指定应用和指标（推荐，更快）
pw.configure(
    metrics=["fps", "cpu", "memory", "hitches"],
    package="com.example.app",  # 指定包名加速内存采集
    output_file="app_perf.jsonl",
    interval=0.5
).start()
# ... 测试 ...
pw.stop()

# 方式3: 上下文管理器（推荐）
with d.performance_watcher.start("perf.jsonl", interval=0.5):
    d(text="按钮").click()
    # ... 自动停止并保存

# 获取统计摘要
summary = pw.get_summary()
print(f"采样次数: {summary['count']}")
print(f"FPS 平均: {summary['metrics']['fps']['avg']}")
print(f"CPU 平均: {summary['metrics']['cpu_percent']['avg']}%")
print(f"内存平均: {summary['metrics']['memory_pss']['avg']} KB")

# 深度分析（异常检测、评分、报告）
analyzer = pw.analyze()
print(f"性能等级: {analyzer.score().grade}")
analyzer.generate_report("report.html", include_charts=True)
```

### 数据文件格式

输出文件采用 JSON Lines 格式 (`.jsonl`)，每行一个 JSON 对象：

```json
{"timestamp": "2026-04-30T12:00:00.123456", "fps": 59.5, "cpu_percent": 15.2, "cpu_freqs": [{"cpu": 0, "current": 650000, "max": 1720000}, {"cpu": 1, "current": 650000, "max": 1720000}], "memory_pss": 250000, "memory_native": 40000, "memory_ark": 50000, "hitches": {"over_16ms": 0, "over_33ms": 0, "over_66ms": 0}}
```

字段说明：
- `timestamp`: ISO 8601 格式时间戳
- `fps`: 帧率 (float)
- `cpu_percent`: CPU 使用率百分比 (float)
- `cpu_freqs`: 各核心频率列表 `[{"cpu": 0, "current": kHz, "max": kHz}, ...]`
- `memory_pss`: 总 PSS 内存 KB (int)
- `memory_native`: Native heap KB (int)
- `memory_ark`: Ark TS heap KB (int)
- `hitches`: 帧卡顿统计 `{"over_16ms": n, "over_33ms": n, "over_66ms": n}`
- `thermal`: 温度信息 `{"soc_thermal": 45.0, "battery": 32.0, ...}` (摄氏度)
- `memory_percent`: 系统内存使用率百分比 (float, 0-100)

---

## 通知栏操作

| API | 说明 |
|-----|------|
| `notification.open()` | 打开通知栏 |
| `notification.close()` | 关闭通知栏 |
| `notification.toggle()` | 切换通知栏状态 |
| `notification.open_quick_settings()` | 打开快捷设置面板 |
| `notification.get_notifications()` | 获取通知列表 |
| `notification.click_notification(index/text)` | 点击通知 |
| `notification.clear_all_notifications()` | 清除所有通知 |
| `notification.click_quick_setting(name)` | 点击快捷设置项 |
| `notification.set_brightness(level)` | 设置屏幕亮度 |

### 示例代码

```python
# 打开/关闭通知栏
d.notification.open()
d.notification.close()

# 切换通知栏状态
d.notification.toggle()

# 使用上下文管理器（自动关闭）
with d.notification:
    # 获取通知列表
    notifications = d.notification.get_notifications()
    print(f"通知数量: {len(notifications)}")
    
    # 点击通知（按索引）
    d.notification.click_notification(index=0)
    
    # 点击通知（按文本）
    d.notification.click_notification(text="微信")

# 打开快捷设置面板
d.notification.open_quick_settings()

# 点击快捷设置项
d.notification.click_quick_setting("WiFi")
d.notification.click_quick_setting("蓝牙")
d.notification.click_quick_setting("飞行模式")

# 设置屏幕亮度 (0-100)
d.notification.set_brightness(50)

# 清除所有通知
d.notification.clear_all_notifications()
```

---

## HDC 命令

| API | 说明 |
|-----|------|
| `shell(cmd)` | 执行 HDC shell 命令 |

### 示例代码

```python
# 执行 shell 命令
result = d.shell("bm dump -a")
print(result.output)

# 获取命令结果
result = d.shell("ls -l /data/local/tmp")
print(result.output)    # 标准输出
print(result.error)     # 错误输出
print(result.exit_code) # 退出码
```

---

## 获取控件树

```python
# 获取控件树
hierarchy = d.dump_hierarchy()
print(hierarchy)
```

---

## 远程设备连接

```bash
# 设置环境变量连接远程 HDC Server
export HDC_SERVER_HOST=192.168.1.100
export HDC_SERVER_PORT=8710
```

```python
# 或在代码中设置
import os
os.environ["HDC_SERVER_HOST"] = "192.168.1.100"
os.environ["HDC_SERVER_PORT"] = "8710"

from hmnextauto.driver import Driver
d = Driver()
```

---

## 完整示例

```python
# -*- coding: utf-8 -*-
import time
from hmnextauto.driver import Driver
from hmnextauto.proto import KeyCode, DisplayRotation

# 初始化
d = Driver()

# 设备信息
print(d.device_info)

# 解锁屏幕
d.unlock()

# 启动应用
d.force_start_app("com.example.app")

# 等待控件出现
if d(text="首页").wait(timeout=10):
    print("应用启动成功")

# 点击操作
d(text="按钮").click()
d.click(0.5, 0.5)

# 输入文本
d(text="输入框").input_text("hello")

# 滑动操作
d.swipe_ext("up")

# XPath 定位
d.xpath('//*[@text="确定"]').click()

# 图像匹配
d.click_image("target.png")

# 后台 Watcher
d.watcher("ad").when_xpath('//*[@text="跳过"]').click()
d.watcher.start(interval=0.3)

# 录屏
with d.screenrecord.start("test.mp4"):
    d(text="按钮").click()
    time.sleep(3)

# 停止 Watcher
d.watcher.stop()

# 返回桌面
d.go_home()

# 关闭连接
d.close()
```
