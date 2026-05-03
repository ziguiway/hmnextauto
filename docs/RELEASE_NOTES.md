# HMNextAuto：鸿蒙 NEXT 自动化框架新篇章

## 🌍 项目背景

随着华为鸿蒙 NEXT 系统的正式发布，纯血鸿蒙生态正在快速崛起。与传统 HarmonyOS 不同，HarmonyOS NEXT 不再兼容 Android 应用，这意味着基于 Android 的自动化测试框架（如 uiautomator2）将无法在新系统上运行。

在这样的背景下，原 `hmdriver2` 项目应运而生，它是首款支持 HarmonyOS NEXT 的无侵入式 UI 自动化框架，为开发者提供了轻量高效的自动化测试能力。然而，由于原作者工作变动等原因，该项目已经两年没有更新维护。

作为一名深耕移动端自动化测试领域的开发者，我深知自动化框架对测试效率的重要性。为了让这款优秀的框架继续服务于广大鸿蒙开发者，我决定接手项目进行持续维护和开发。

经过数月的努力，基于原 `hmdriver2` 的核心架构，我完成了大量的 Bug 修复、功能增强和稳定性优化。今天，我非常高兴地宣布：**HMNextAuto** 正式发布！

---

## 🎉 项目发布

**项目地址**: https://github.com/ziguiway/HMNextAuto

**PyPI**: `pip install -U hmnextauto`

---

## ✨ 核心亮点

### 1. 无缝迁移：从 uiautomator2 到鸿蒙 NEXT

如果你熟悉 Android 的 `uiautomator2`，那么使用 HMNextAuto 将**零学习成本**！

**相同的 API 设计，无缝切换体验：**

```python
# uiautomator2 写法
from uiautomator2 import Device
d = Device()
d(text="精选").click()
d.swipe(0.5, 0.8, 0.5, 0.2)

# HMNextAuto 写法（完全一致）
from hmnextauto.driver import Driver
d = Driver()
d(text="精选").click()
d.swipe(0.5, 0.8, 0.5, 0.2)
```

无需重新学习，直接将 Android 自动化脚本迁移到鸿蒙 NEXT！

---

### 2. 视觉定位能力大幅增强

新增**多尺度图像匹配**和**颜色点击**功能：

```python
# 图像匹配点击
ok = d.click_image("target.png", threshold=0.88)

# 在截图上绘制匹配结果边框（调试神器）
result = d.find_image("target.png")
d.draw_bounds(result)

# 找色点击（RGB 容差）
d.click_color((255, 0, 0), tolerance=12)

# 支持应用显示名启动
d.start_app_by_name("快手")
```

---

### 3. 稳定性与兼容性全面提升

| 修复内容 | 说明 |
|---------|------|
| **Windows 平台兼容** | 修复 `grep` 命令缺失、路径引用等问题 |
| **控件操作稳定性** | 修复 `getBounds` 崩溃、坐标类型错误等问题 |
| **图像验证增强** | 安全处理 numpy 数组，支持设备旋转场景 |
| **应用信息获取** | 改进 `current_app` 方法，获取更可靠 |

---

### 4. XPath 定位增强

```python
# 等待控件出现（最多等待10秒）
d.xpath('//Text[@text="精选"]').wait(timeout=10).click()

# 等待控件消失
d.xpath('//ProgressBar').wait_gone(timeout=5)
```

---

### 5. 后台 Watcher 自动处理弹窗

```python
# 自动处理常见弹窗
d.watcher("ad").when_xpath('//*[@text="跳过"]').click()
d.watcher("ok").when(text="确定").click()
d.watcher.start(interval=0.3)

# 主流程执行
d.start_app("com.example.app")
# ...

d.watcher.stop()
```

---

### 6. 依赖优化

- **升级 uitest_agent** 至 v1.2.2，性能更稳定
- **opencv-python** 移入主依赖，安装更简单

---

## 🚀 快速上手

### 环境配置

1. **安装 HDC 工具**
   - 下载 [HarmonyOS Command Line Tools](https://developer.huawei.com/consumer/cn/download/)
   - 配置环境变量：
   ```bash
   export HM_SDK_HOME="/path/to/sdk"
   export PATH=$PATH:$HM_SDK_HOME/openharmony/toolchains
   ```

2. **安装 HMNextAuto**
   ```bash
   pip install -U hmnextauto
   ```

3. **连接设备**
   - 开启 USB 调试
   - 执行 `hdc list targets` 确认设备连接

### 基础使用

```python
from hmnextauto.driver import Driver

# 初始化驱动
d = Driver()

# 获取设备信息
print(d.device_info)

# 启动应用
d.start_app("com.kuaishou.hmapp")

# 控件操作
d(text="精选").click()
d(textContains="同意").click_if_exists()

# 滑动操作
d.swipe(0.5, 0.8, 0.5, 0.4)
d.swipe_ext("up", scale=0.8)

# XPath 操作
d.xpath('//Text[@text="精选"]').click()

# 视觉定位
d.click_image("btn_ok.png")

# 屏幕截图
d.screenshot("screen.png")

# 录屏（需要 opencv-python）
with d.screenrecord.start("test.mp4"):
    d(text="按钮").click()
```

---

## 🔍 UI Inspector 工具

配合 **uiautodev** 工具可以可视化查看控件树：

```bash
# 安装 uiautodev
pip install "uiautodev[harmony]"

# 启动服务
uiauto.dev

# 打开浏览器访问 http://localhost:20242
```

**功能特性：**
- 实时查看控件树层级
- 自动生成 XPath
- 查看控件属性详情

项目地址：https://github.com/codeskyblue/uiautodev

---

## 📚 API 示例速查

### App 管理
```python
d.install_app("demo.hap")          # 安装应用
d.uninstall_app("com.example.app") # 卸载应用
d.stop_app("com.example.app")      # 停止应用
d.clear_app("com.example.app")     # 清除数据
info = d.get_app_info("com.example.app")  # 获取应用详情
```

### 设备操作
```python
d.press_home()    # Home键
d.press_back()    # 返回键
d.screen_on()     # 亮屏
d.screen_off()    # 息屏
d.unlock()        # 解锁
d.open_url("https://baidu.com")  # 打开URL
```

### 控件操作
```python
d(text="确定").click()              # 点击
d(text="输入框").input_text("hello") # 输入文本
d(text="输入框").clear_text()        # 清除文本
d(type="Button").count             # 获取控件数量
info = d(text="按钮").info          # 获取控件信息
d(text="列表").scroll.to(text="目标") # 滚动查找
```

### 手势操作
```python
d.click(0.5, 0.5)           # 单击
d.double_click(0.5, 0.5)    # 双击
d.long_click(0.5, 0.5)      # 长按
d.gesture.start(100, 200).move(300, 400).action()  # 自定义手势
```

---

## 🔧 设计理念

- **无侵入式**：无需安装 testRunner APP
- **易上手**：对齐 uiautomator2 API 设计
- **轻量高效**：几乎零依赖，操作响应快
- **持续演进**：积极维护，快速响应反馈

---

## 📅 更新记录

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| v1.4.0 | 2026-05-03 | 新增全局隐式等待 `implicitly_wait`，Settings 配置管理 |
| v1.3.0 | 2026-04-30 | 新增通知栏操作、XPath 多元素操作、性能监控、智能等待条件 |
| v1.2.0 | 2026-04-29 | 升级 uitest_agent v1.2.2，统一调用逻辑 |
| v1.1.0 | 2026-04-24 | 新增视觉定位功能 |
| v1.0.5 | 2026-04-23 | XPath wait/wait_gone 方法 |

---

## 💡 未来规划

- [ ] 全场景弹窗处理
- [ ] 操作标记功能
- [ ] 云测平台集成

---

## 🙏 致谢

感谢原项目作者 @codematrixer 提供的优秀基础框架！

欢迎提 PR 和 issue，你的支持是我持续迭代的动力！⭐️

*发布日期：2026年4月29日*
*作者：ziguiway*