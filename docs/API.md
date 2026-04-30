# HMNextAuto API 完整文档

本文档提供 HMNextAuto 所有 API 的详细说明和示例代码。

---

## 目录

- [初始化](#初始化)
- [App 管理](#app-管理)
- [设备信息](#设备信息)
- [设备操作](#设备操作)
- [按键操作](#按键操作)
- [触摸手势](#触摸手势)
- [控件操作](#控件操作)
- [XPath 定位](#xpath-定位)
- [视觉定位](#视觉定位)
- [后台 Watcher](#后台-watcher)
- [Toast 监控](#toast-监控)
- [屏幕录制](#屏幕录制)
- [文件操作](#文件操作)
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

# 关闭连接
d.close()
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
| `.click()` | 点击 | - |
| `.click_if_exists()` | 存在才点击 | - |
| `.double_click()` | 双击 | - |
| `.long_click()` | 长按 | - |
| `.input_text(text)` | 输入文本 | - |
| `.info` | 控件属性 | `dict` |
| `.text` | 文本内容 | `str` |

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

# 存在才点击
d.xpath('//*[@text="跳过"]').click_if_exists()

# 输入文本
d.xpath('//TextField').input_text("hello")

# 获取控件信息
info = d.xpath('//*[@text="确定"]').info
text = d.xpath('//*[@text="确定"]').text
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
