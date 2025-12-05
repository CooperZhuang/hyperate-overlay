#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hyperate 三值置顶悬浮窗（当前 / 最高 / 最低心率）
Python 3.14 + uv + requests
"""

from config import ConfigWatcher, load_config
from rtss_integration import RTSSIntegration
from ui import HeartRateUI
from websocket_client import WebSocketClient


class HyperateTripleOverlay:
    def __init__(self):
        # 加载配置
        self.config = load_config()

        # 初始化 UI
        self.ui = HeartRateUI(self.config)

        # 初始化RTSS集成
        self.rtss = RTSSIntegration(self.config)

        # 初始化配置监视器
        self.config_watcher = ConfigWatcher()

        # 初始化 WebSocket 客户端
        self.ws_client = WebSocketClient(self.config, self.update_heart_rate_callback)

        # 启动 WebSocket 连接
        self.ws_client.start()

        # 启动环境变量监视线程
        self.start_env_watch_thread()

    def update_heart_rate_callback(self, heart_rate):
        """
        心率数据更新回调函数
        根据显示模式更新UI和/或RTSS显示
        """
        # 获取显示模式
        display_mode = self.config.get("DISPLAY_MODE", "both")

        # 更新UI显示（如果显示模式不是仅RTSS）
        if display_mode in ["both", "default"]:
            self.ui.update_heart_rate(heart_rate)
        else:
            # 仅RTSS模式，仍然需要更新UI内部状态但不显示
            self.ui.update_heart_rate(heart_rate, update_display=False)

        # 更新RTSS显示（如果显示模式不是仅默认UI）
        if display_mode in ["both", "rtss"] and self.rtss.is_enabled():
            self.rtss.update_heart_rate(self.ui.current, self.ui.max_hr, self.ui.min_hr)

    def start_env_watch_thread(self):
        """启动环境变量监视线程"""
        import threading

        def env_watch_loop():
            while True:
                try:
                    if self.config_watcher.check_and_reload_env():
                        print("环境变量已重新加载")
                        # 重新加载配置
                        from config import load_config

                        new_config = load_config()
                        self.config = new_config
                        # 更新 UI 配置
                        self.ui.update_config(new_config)
                        # 更新RTSS配置
                        self.rtss.config = new_config
                except Exception as e:
                    print(f"环境变量监视线程出错: {e}")
                import time

                time.sleep(2)  # 每2秒检查一次

        threading.Thread(target=env_watch_loop, daemon=True).start()

    def run(self):
        """运行应用程序"""
        if "你的会话ID" in self.config["HYPERATE_URL"]:
            print("请先修改 HYPERATE_URL 为你的真实链接！")
            import sys

            sys.exit(1)

        # 显示启动信息
        print("=" * 50)
        print("Hyperate Triple Overlay 启动")
        display_mode = self.config.get("DISPLAY_MODE", "both")
        print(f"显示模式: {display_mode}")
        print(f"RTSS集成: {'已启用' if self.rtss.is_enabled() else '已禁用'}")
        print("=" * 50)

        # 根据显示模式决定是否运行UI
        if display_mode in ["both", "default"]:
            # 运行 UI
            self.ui.run()
        else:
            # rtss模式：不显示UI窗口，但保持应用运行
            print("RTSS模式：UI窗口已隐藏，仅RTSS OSD显示")
            print("按Ctrl+C退出应用")

            # 保持应用运行以处理心率数据
            try:
                import time

                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("接收到退出信号")

        # 应用退出时清理RTSS显示
        if self.rtss.is_enabled():
            self.rtss.clear_display()


if __name__ == "__main__":
    app = HyperateTripleOverlay()
    app.run()
