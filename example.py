# -*- coding: utf-8 -*-
"""
HMNextAuto 完整示例代码
展示所有主要功能的使用方法
"""

import time
from hmnextauto.driver import Driver
from hmnextauto.proto import DeviceInfo, KeyCode, ComponentData, DisplayRotation, SwipeDirection


def main():
    # ============================================
    # 初始化
    # ============================================
    # 自动选择第一个连接的设备
    d = Driver()

    # 或指定设备序列号
    # d = Driver("FMR0223C13000649")

    print("=== 设备信息 ===")

    # ============================================
    # 设备信息
    # ============================================
    info: DeviceInfo = d.device_info
    print(f"产品名称: {info.productName}")    # HUAWEI Mate 60 Pro
    print(f"型号: {info.model}")              # ALN-AL00
    print(f"SDK 版本: {info.sdkVersion}")     # 12
    print(f"系统版本: {info.sysVersion}")
    print(f"CPU 架构: {info.cpuAbi}")         # arm64-v8a
    print(f"WLAN IP: {info.wlanIp}")
    print(f"分辨率: {info.displaySize}")      # (1260, 2720)

    # 获取屏幕分辨率
    width, height = d.display_size
    print(f"屏幕分辨率: {width}x{height}")

    # 获取/设置屏幕旋转
    rotation = d.display_rotation
    print(f"屏幕旋转状态: {rotation}")

    # ============================================
    # 设备基础操作
    # ============================================
    print("\n=== 设备操作 ===")

    # 亮屏/息屏
    d.screen_on()
    # d.screen_off()

    # 解锁屏幕（会自动亮屏并上滑）
    d.unlock()

    # 回到桌面
    d.go_home()
    d.press_home()  # 别名

    # 返回
    # d.go_back()
    # d.press_back()  # 别名

    # ============================================
    # 按键操作
    # ============================================
    print("\n=== 按键操作 ===")

    # 电源键
    # d.press_power()

    # 音量控制
    # d.volume_up()
    # d.volume_down()
    # d.volume_mute()

    # 方向键
    # d.press_dpad_up()
    # d.press_dpad_down()
    # d.press_dpad_left()
    # d.press_dpad_right()
    # d.press_dpad_center()

    # 其他按键
    # d.press_enter()
    # d.press_backspace()
    # d.press_tab()
    # d.press_space()
    # d.press_escape()
    # d.press_menu()
    # d.press_multitask()

    # 发送任意按键
    # d.press_key(KeyCode.POWER)
    # d.press_key(2017)  # 直接使用数字码

    # ============================================
    # App 管理
    # ============================================
    print("\n=== App 管理 ===")

    # 安装应用
    # d.install_app("/path/to/app.hap")

    # 卸载应用
    # d.uninstall_app("com.example.app")

    # 启动应用（自动获取 main ability）
    # d.start_app("com.example.app")

    # 启动应用（指定 ability）
    # d.start_app("com.example.app", "EntryAbility")

    # 强制启动（先回桌面、停止应用、再启动）
    # d.force_start_app("com.example.app")

    # 用应用名启动（支持模糊匹配）
    # d.start_app_by_name("微信")
    # d.start_app_by_name("设置", match="contains", include_system_apps=True)

    # 停止应用
    # d.stop_app("com.example.app")

    # 清除应用数据
    # d.clear_app("com.example.app")

    # 检查应用是否安装
    # if d.has_app("com.example.app"):
    #     print("应用已安装")

    # 获取应用列表
    apps = d.list_apps()  # 第三方应用
    print(f"已安装第三方应用数量: {len(apps)}")

    # all_apps = d.list_apps(include_system_apps=True)  # 包含系统应用

    # 获取当前前台应用
    package, ability = d.current_app()
    print(f"当前应用: {package}, Ability: {ability}")

    # 获取应用信息
    # info = d.get_app_info("com.example.app")
    # print(f"应用版本: {info['versionName']}")

    # 获取应用版本
    # version = d.app_version("com.example.app")

    # ============================================
    # 触摸手势
    # ============================================
    print("\n=== 触摸手势 ===")

    # 单击（支持绝对坐标和百分比）
    # d.click(500, 1000)      # 绝对坐标
    # d.click(0.5, 0.4)       # 百分比坐标

    # 双击
    # d.double_click(500, 1000)
    # d.double_click(0.5, 0.4)

    # 长按
    # d.long_click(500, 1000)

    # 滑动
    # d.swipe(500, 1000, 500, 500, speed=2000)  # 绝对坐标
    # d.swipe(0.5, 0.8, 0.5, 0.4, speed=2000)   # 百分比坐标

    # 方向滑动
    # d.swipe_ext("up")                              # 向上滑动
    # d.swipe_ext("down")                            # 向下滑动
    # d.swipe_ext("left")                            # 向左滑动
    # d.swipe_ext("right")                           # 向右滑动
    # d.swipe_ext(SwipeDirection.UP)                 # 使用枚举
    # d.swipe_ext("up", scale=0.8)                   # 滑动距离为屏幕高度的 80%
    # d.swipe_ext("up", box=(0.2, 0.2, 0.8, 0.8))   # 在指定区域内滑动

    # 输入文本（需要先点击输入框获取焦点）
    # d.click(500, 1000)
    # d.input_text("hello world")

    # 复杂手势
    # d.gesture.start(630, 984, interval=0.5) \
    #     .move(200, 400, interval=0.5) \
    #     .pause(interval=1) \
    #     .move(500, 600, interval=0.5) \
    #     .action()

    # ============================================
    # 控件操作
    # ============================================
    print("\n=== 控件操作 ===")

    # 基础定位
    # d(text="确定").click()
    # d(id="btn_submit").click()
    # d(type="Button", text="登录").click()

    # 索引定位（多个匹配时选择第几个）
    # d(type="Button", index=0).click()

    # 组合定位
    # d(type="Button", text="确定", enabled=True).click()

    # 相对定位
    # d(text="密码", isAfter=True).input_text("123456")  # 定位"密码"后面的元素
    # d(text="用户名", isBefore=True).input_text("admin")  # 定位"用户名"前面的元素

    # 模糊匹配
    # d(textContains="确").click()                    # 文本包含"确"
    # d(textMatches=r"^\d+条$").click()              # 正则匹配
    # d(resourceIdContains="entry").click()          # ID 包含"entry"
    # d(typeMatches="Text|Button").click()           # 类型正则匹配

    # 检查存在
    # if d(text="确定").exists():
    #     d(text="确定").click()

    # 等待出现/消失
    # if d(text="加载完成").wait(timeout=10):
    #     print("加载完成")

    # if d(type="Dialog").wait_gone(timeout=5):
    #     print("弹窗已消失")

    # 存在才点击（不存在不报错）
    # d(text="跳过").click_if_exists()

    # 获取控件数量
    # count = d(type="Button").count
    # print(f"页面有 {count} 个按钮")

    # 获取控件信息
    # info = d(text="确定").info
    # print(info.text)
    # print(info.bounds)
    # print(info.boundsCenter)

    # 输入文本
    # d(text="用户名").input_text("admin")
    # d(text="密码").input_text("123456")

    # 清除文本
    # d(text="用户名").clear_text()

    # 拖拽
    # target: ComponentData = d(type="ListItem", index=5).find_component()
    # d(type="ListItem", index=0).drag_to(target)

    # 缩放
    # d(text="图片").pinch_in(scale=0.5)   # 缩小
    # d(text="图片").pinch_out(scale=2)    # 放大

    # ============================================
    # 滚动操作
    # ============================================
    print("\n=== 滚动操作 ===")

    # 获取可滚动容器
    # lst = d(type="List", scrollable=True)

    # 滚动查找
    # if lst.scroll.to(text="目标文案", max_swipes=20):
    #     d(text="目标文案").click()

    # 纵向滚动
    # lst.scroll.vert.forward()    # 向下滚动
    # lst.scroll.vert.backward()   # 向上滚动
    # lst.scroll.vert.fling()      # 快速下滑

    # 横向滚动
    # lst.scroll.horiz.forward()   # 向右滚动
    # lst.scroll.horiz.backward()  # 向左滚动

    # 滚动到顶部/底部
    # lst.scroll.toBeginning()
    # lst.scroll.toEnd()

    # ============================================
    # XPath 定位
    # ============================================
    print("\n=== XPath 定位 ===")

    # XPath 定位
    # d.xpath('//*[@text="确定"]').click()
    # d.xpath('//root[1]/Row[1]/Column[1]/Button[3]').click()

    # 等待出现/消失
    # if d.xpath('//Text[@text="加载完成"]').wait(timeout=10):
    #     print("加载完成")

    # if d.xpath('//ProgressBar').wait_gone(timeout=5):
    #     print("加载完成")

    # 存在才点击
    # d.xpath('//*[@text="跳过"]').click_if_exists()

    # 输入文本
    # d.xpath('//TextField').input_text("hello")

    # 获取控件信息
    # info = d.xpath('//*[@text="确定"]').info
    # text = d.xpath('//*[@text="确定"]').text

    # ============================================
    # 视觉定位
    # ============================================
    print("\n=== 视觉定位 ===")

    # 图像匹配点击
    # ok = d.click_image("target.png", threshold=0.88)
    # if not ok:
    #     print("未找到目标图片")

    # 完整参数
    # ok = d.click_image(
    #     template_path="target.png",  # 模板图片路径
    #     threshold=0.85,              # 匹配阈值 (0.0-1.0)
    #     grayscale=True,              # 灰度匹配（更快）
    #     multi_scale=True,            # 多尺度匹配
    #     scale_range=(0.5, 2.0),      # 缩放范围
    #     scale_steps=30,              # 缩放步数
    #     return_result=True,          # 返回匹配结果
    #     draw_box=True                # 在截图上绘制匹配框
    # )

    # 找色点击
    # ok = d.click_color((255, 0, 0), tolerance=12)  # RGB 颜色，容差 12

    # 限制区域找色
    # ok = d.click_color(
    #     rgb=(0, 160, 255),           # RGB 颜色
    #     tolerance=10,                # 容差
    #     region=(100, 400, 600, 1200) # 搜索区域 (x1, y1, x2, y2)
    # )

    # ============================================
    # 后台 Watcher
    # ============================================
    print("\n=== 后台 Watcher ===")

    # 注册规则
    # d.watcher("ad").when_xpath('//*[@text="跳过"]').click()
    # d.watcher("ok").when(text="确定").click()
    # d.watcher("back").when(text="暂无").press_back()

    # 自定义回调
    # def my_handler(driver):
    #     driver.go_back()
    #     print("处理完成")

    # d.watcher("custom").when(type="Dialog").do(my_handler)

    # 启动监控
    # d.watcher.start(interval=0.3)  # 每 0.3 秒检查一次

    # 主流程
    # d.start_app("com.example.app")
    # d(text="按钮").click()

    # 停止监控
    # d.watcher.stop()

    # 移除规则
    # d.watcher.remove("ad")

    # 清空所有规则
    # d.watcher.clear()

    # 查看状态
    # print(d.watcher.running)       # 是否运行中
    # print(d.watcher.rule_names)    # 规则名称列表

    # ============================================
    # Toast 监控
    # ============================================
    print("\n=== Toast 监控 ===")

    # 启动监控
    # d.toast_watcher.start()

    # 触发 Toast 的操作
    # d(text="显示 Toast").click()

    # 获取 Toast
    # toast = d.toast_watcher.get_toast(timeout=3)
    # print(f"Toast: {toast}")

    # ============================================
    # 屏幕录制
    # ============================================
    print("\n=== 屏幕录制 ===")

    # 方式一：手动控制
    # d.screenrecord.start("test.mp4")
    # # 执行操作
    # time.sleep(5)
    # d.screenrecord.stop()

    # 方式二：上下文管理器（推荐）
    # with d.screenrecord.start("test.mp4"):
    #     d(text="按钮").click()
    #     time.sleep(5)
    # # 自动停止录屏

    # ============================================
    # 文件操作
    # ============================================
    print("\n=== 文件操作 ===")

    # 从设备拉取文件
    # d.pull_file("/data/local/tmp/test.png", "./test.png")

    # 推送文件到设备
    # d.push_file("./local.txt", "/data/local/tmp/remote.txt")

    # ============================================
    # 截图
    # ============================================
    print("\n=== 截图 ===")

    # 截图
    # d.screenshot("./screenshot.png")

    # 截图（高质量模式）
    # d.screenshot("./screenshot.png", method="screenCap")

    # ============================================
    # HDC 命令
    # ============================================
    print("\n=== HDC 命令 ===")

    # 执行 shell 命令
    result = d.shell("bm dump -a")
    print(f"命令输出: {result.output[:200]}...")

    # 获取命令结果
    # result = d.shell("ls -l /data/local/tmp")
    # print(result.output)    # 标准输出
    # print(result.error)     # 错误输出
    # print(result.exit_code) # 退出码

    # ============================================
    # 获取控件树
    # ============================================
    print("\n=== 获取控件树 ===")

    # hierarchy = d.dump_hierarchy()
    # print(hierarchy)

    # ============================================
    # 打开 URL
    # ============================================
    print("\n=== 打开 URL ===")

    # 打开 URL
    # d.open_url("https://www.baidu.com")
    # d.open_url("kwai://myprofile")  # Schema

    # ============================================
    # 清理
    # ============================================
    print("\n=== 完成 ===")

    # 关闭连接
    d.close()
    print("Done!")


if __name__ == "__main__":
    main()
