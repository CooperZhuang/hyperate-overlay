#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hyperate 三值置顶悬浮窗（当前 / 最高 / 最低心率）
完美适配你的页面结构，直接用 id 抓取
Python 3.14 + uv + requests

重构版本 - 模块化设计
"""

from config import ConfigWatcher, load_config
from ui import HeartRateUI
from websocket_client import WebSocketClient


class HyperateTripleOverlay:
    def __init__(self):
        # 加载配置
        self.config = load_config()

        # 初始化 UI
        self.ui = HeartRateUI(self.config)

        # 初始化配置监视器
        self.config_watcher = ConfigWatcher()

        # 初始化 WebSocket 客户端
        self.ws_client = WebSocketClient(self.config, self.ui.update_heart_rate)

        # 启动 WebSocket 连接
        self.ws_client.start()

        # 启动环境变量监视线程
        self.start_env_watch_thread()

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

        # 运行 UI
        self.ui.run()


if __name__ == "__main__":
    app = HyperateTripleOverlay()
    app.run()
