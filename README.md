# HMNextAuto 鸿蒙自动化框架

[![PyPI version](https://img.shields.io/pypi/v/hmnextauto.svg)](https://pypi.python.org/pypi/hmnextauto)
[![Python](https://img.shields.io/pypi/pyversions/hmnextauto.svg)](https://pypi.org/project/hmnextauto)
[![License](https://img.shields.io/github/license/ziguiway/HMNextAuto.svg)](https://github.com/ziguiway/HMNextAuto/blob/main/LICENSE)
[![Downloads](https://pepy.tech/badge/hmnextauto)](https://pepy.tech/project/hmnextauto)

> **持续维护的鸿蒙 NEXT 无侵入式 UI 自动化框架**，对齐 uiautomator2 API，零学习成本！

***

## 🌍 项目背景

随着华为鸿蒙 NEXT 系统的正式发布，纯血鸿蒙生态正在快速崛起。与传统 HarmonyOS 不同，HarmonyOS NEXT 不再兼容 Android 应用，这意味着基于 Android 的自动化测试框架（如 uiautomator2）将无法在新系统上运行。

在这样的背景下，原 [hmdriver2](https://github.com/codematrixer/hmdriver2) 项目应运而生，它是首款支持 HarmonyOS NEXT 的无侵入式 UI 自动化框架，为开发者提供了轻量高效的自动化测试能力。然而，由于原作者工作变动等原因，该项目已经两年没有更新维护。

为了让这款优秀的框架继续服务于广大鸿蒙开发者，我基于原 `hmdriver2` 的核心架构，完成了大量的 Bug 修复、功能增强和稳定性优化。**HMNextAuto** 由此诞生！

***

## 🌟 核心优势

| 特性          |       HMNextAuto       | Hypium (官方) | 原版 hmdriver2 |
| ----------- | :--------------------: | :---------: | :----------: |
| 无侵入式        |            ✅           |  ❌ 需安装测试框架  |       ✅      |
| 学习成本        |     🟢 零学习成本（对齐 u2）    |    🔴 较高    |  🟡 需熟悉 API  |
| 维护状态        |         ✅ 持续更新         |    ✅ 官方维护   |  ❌ 停止维护 2 年  |
| 视觉定位        |        ✅ 多尺度模板匹配       |      ❌      |       ❌      |
| 找色点击        |       ✅ RGB 容差匹配       |      ❌      |       ❌      |
| 后台 Watcher  |      ✅ 纯 Python 实现     |      ❌      |       ✅      |
| XPath 多元素操作 | ✅ count/all/first/last |      ❌      |       ❌      |
| 通知栏操作       |        ✅ 完整通知栏控制       |      ❌      |       ❌      |
| 性能监控        |        ✅ 后台性能采集        |      ❌      |       ❌      |
| 智能等待条件      |      ✅ wait\_until     |      ❌      |       ❌      |
| 依赖复杂度       |   🟢 仅 lxml + opencv   |     🔴 重    |     🟢 轻     |

***

## 📋 系统要求

| 项目     | 要求                                 |
| ------ | ---------------------------------- |
| Python | 3.8+                               |
| 操作系统   | Windows / macOS / Linux            |
| 设备     | HarmonyOS NEXT (API 12+)           |
| 工具     | HDC (HarmonyOS Command Line Tools) |

***

## 🚀 快速开始

### 1. 安装 HDC 工具

下载 [HarmonyOS Command Line Tools](https://developer.huawei.com/consumer/cn/download/) 并配置环境变量：

```bash
# macOS / Linux
export HM_SDK_HOME="/path/to/sdk"
export PATH=$PATH:$HM_SDK_HOME/openharmony/toolchains

# Windows (系统环境变量)
HM_SDK_HOME=C:\path\to\sdk
PATH=%PATH%;%HM_SDK_HOME%\openharmony\toolchains
```

### 2. 连接设备

开启 USB 调试，确认设备连接：

```bash
hdc list targets
# 输出设备序列号即连接成功
```

### 3. 安装 HMNextAuto

```bash
pip install -U hmnextauto
```

### 4. 验证安装

```python
from hmnextauto.driver import Driver

d = Driver()
print(d.device_info)
# 输出设备信息即配置成功
```

***

## ✨ 增强功能详解

> 以下功能均为 HMNextAuto 相比原版 hmdriver2 的**新增增强功能**

### 1. XPath 多元素操作 🆕

支持对匹配到的多个元素进行批量操作：

```python
# 获取匹配元素数量
count = d.xpath('//*[@clickable="true"]').count

# 获取所有匹配元素
elements = d.xpath('//*[@clickable="true"]').all()
for el in elements:
    print(el.bounds)
    el.click()

# 快速获取首/末元素
first = d.xpath('//*[@clickable="true"]').first()
last = d.xpath('//*[@clickable="true"]').last()
```

### 2. 通知栏操作 🆕

完整的下拉通知栏和快捷开关控制：

```python
# 打开通知栏（消息中心）
d.notification.open()

# 打开快捷设置面板
d.notification.open_quick_settings()

# 点击快捷开关
d.notification.click_quick_setting("wifi")        # WiFi
d.notification.click_quick_setting("bluetooth")   # 蓝牙
d.notification.click_quick_setting("airplane")    # 飞行模式
d.notification.click_quick_setting("flashlight")  # 手电筒

# 设置亮度 (0-255)
d.notification.set_brightness(128)

# 关闭通知栏
d.notification.close()
```

### 3. 性能监控 🆕

后台自动采集设备性能数据：

```python
from hmnextauto import PerformanceWatcher

# 创建性能监控器
perf = PerformanceWatcher(d)

# 开始后台监控（每隔 1 秒采集一次）
perf.start(interval=1.0)

# 执行测试操作...
d(text="按钮").click()

# 停止并获取报告
perf.stop()
report = perf.get_report()
print(f"平均 FPS: {report['fps']['avg']}")
print(f"平均内存: {report['memory']['avg']} MB")
print(f"CPU 使用率峰值: {report['cpu']['max']}%")
```

### 4. 智能等待条件 🆕

更丰富的控件等待条件：

```python
# 等待控件可点击
d(text="按钮").wait_clickable(timeout=10)

# 等待控件启用
d(text="输入框").wait_enabled(timeout=5)

# 自定义等待条件
d(text="列表").wait_until(lambda el: el.info["scrollable"], timeout=10)
```

### 5. 视觉定位能力

```python
# 图像匹配点击（支持多尺度）
ok = d.click_image("target.png", threshold=0.88)

# 找色点击（RGB 容差匹配）
d.click_color((255, 0, 0), tolerance=12)

# 限制区域找色
d.click_color((0, 160, 255), tolerance=10, region=(100, 400, 600, 1200))
```

### 6. 后台 Watcher 自动处理弹窗

```python
# 自动处理常见弹窗
d.watcher("ad").when_xpath('//*[@text="跳过"]').click()
d.watcher("ok").when(text="确定").click()
d.watcher.start(interval=0.3)

# 主流程执行
d.start_app("com.example.app")

d.watcher.stop()
```

### 7. 模糊匹配选择器

```python
# 子串匹配
d(textContains="登").click()

# 正则匹配
d(textMatches=r"^\d+条$").click()

# 资源 ID 模糊匹配
d(resourceIdContains="entry", type="Button").click()
```

***

## 🔄 从 uiautomator2 无缝迁移

如果你熟悉 Android 的 `uiautomator2`，**零学习成本**直接上手：

```python
# uiautomator2 写法
from uiautomator2 import Device
d = Device()
d(text="精选").click()
d.swipe(0.5, 0.8, 0.5, 0.2)

# HMNextAuto 写法（完全一致！）
from hmnextauto.driver import Driver
d = Driver()
d(text="精选").click()
d.swipe(0.5, 0.8, 0.5, 0.2)
```

***

## 📚 API 速查

> 💡 **详细 API 文档**: [docs/API.md](docs/API.md) - 完整的 API 文档，包含所有功能说明和示例代码

### App 管理

```python
d.install_app("demo.hap")              # 安装应用
d.uninstall_app("com.example.app")     # 卸载应用
d.start_app("com.example.app")         # 启动应用
d.stop_app("com.example.app")          # 停止应用
d.clear_app("com.example.app")         # 清除数据
d.start_app_by_name("微信")            # 用应用名启动
d.force_start_app("com.example.app")   # 强制启动（回桌面+停+启）
```

### 设备操作

```python
d.press_home()                         # Home 键
d.press_back()                         # 返回键
d.screen_on()                          # 亮屏
d.screen_off()                         # 息屏
d.unlock()                             # 解锁
d.open_url("https://baidu.com")        # 打开 URL
d.screenshot("screen.png")             # 截图
```

### 控件操作

```python
d(text="确定").click()                 # 点击
d(text="确定").click_if_exists()       # 存在才点击
d(text="输入框").input_text("hello")   # 输入文本
d(text="输入框").clear_text()          # 清除文本
d(type="Button").count                 # 控件数量
d(text="按钮").info                    # 控件信息
d(text="列表").scroll.to(text="目标")  # 滚动查找
```

### 手势操作

```python
d.click(0.5, 0.5)                      # 单击（支持百分比坐标）
d.double_click(0.5, 0.5)               # 双击
d.long_click(0.5, 0.5)                 # 长按
d.swipe(0.5, 0.8, 0.5, 0.4)            # 滑动
d.swipe_ext("up", scale=0.8)           # 方向滑动
d.gesture.start(100, 200).move(300, 400).action()  # 自定义手势
```

### 录屏

```python
# 推荐方式（自动清理资源）
with d.screenrecord.start("test.mp4"):
    d(text="按钮").click()
```

***

## 🔍 UI Inspector 工具

配合 **uiautodev** 可视化查看控件树：

```bash
pip install "uiautodev[harmony]"
uiauto.dev
# 打开浏览器访问 http://localhost:20242
```

功能特性：

- 实时查看控件树层级
- 自动生成 XPath
- 查看控件属性详情

项目地址：<https://github.com/codeskyblue/uiautodev>

***

## 🎯 应用场景

| 场景        | 说明        |
| --------- | --------- |
| App 自动化测试 | 功能测试、回归测试 |
| 性能测试      | 配合录屏分析    |
| 自动化运营     | 批量操作脚本    |
| UI 截图对比   | 视觉回归测试    |
| 兼容性测试     | 多设备并行     |

***

## ❓ 常见问题

### Q: 找不到设备？

确保已开启 USB 调试，运行 `hdc list targets` 确认连接。

### Q: pip 安装失败？

尝试使用镜像：

```bash
pip install -U hmnextauto -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: 图像匹配不准确？

调整 `threshold` 参数（默认 0.85），或使用更高分辨率的模板图片。

### Q: 如何连接远程设备？

```bash
export HDC_SERVER_HOST=192.168.1.100
export HDC_SERVER_PORT=8710
```

### Q: 控件找不到？

使用 UI Inspector 工具查看控件属性，确认选择器是否正确。

***

## 📅 更新日志

| 版本     | 日期         | 主要更新                               |
| ------ | ---------- | ---------------------------------- |
| v1.3.0 | 2026-04-30 | 🆕 新增通知栏操作、XPath 多元素操作、性能监控、智能等待条件 |
| v1.2.0 | 2026-04-29 | 升级 uitest\_agent v1.2.2，统一调用逻辑     |
| v1.1.0 | 2026-04-24 | 新增视觉定位功能（多尺度模板匹配、找色点击）             |
| v1.0.5 | 2026-04-23 | XPath wait/wait\_gone 方法           |
| v1.0.0 | 2026-04-20 | 首次发布，基于原 hmdriver2 重构              |

***

## 💡 未来规划

- [ ] 全场景弹窗处理
- [ ] 操作标记功能
- [ ] 云测平台集成
- [ ] 性能监控增强

***

## 🤝 参与贡献

欢迎提交 Issue 和 Pull Request！

- 🐛 [提交 Issue](https://github.com/ziguiway/HMNextAuto/issues)
- 📖 [贡献指南](CONTRIBUTING.md)

***

## 🙏 致谢

感谢原项目作者 [@codematrixer](https://github.com/codematrixer) 提供的优秀基础框架！

***

## 📄 License

[MIT License](LICENSE)

***

如果这个项目对你有帮助，请给一个 ⭐️ Star 支持一下！
