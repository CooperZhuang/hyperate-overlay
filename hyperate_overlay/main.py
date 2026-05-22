#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Hyperate 三值置顶悬浮窗（当前 / 最高 / 最低心率）"""

import logging
import sys
import threading
import time

from .config import ConfigWatcher, HeartRateConfig
from .rtss_integration import RTSSIntegration
from .stats_analyzer import HeartRateStats
from .ui import HeartRateUI
from .websocket_client import WebSocketClient

logger = logging.getLogger(__name__)


class HyperateTripleOverlay:
    """心率悬浮窗应用主控制器"""

    def __init__(self) -> None:
        self.config = HeartRateConfig.from_env()
        self.stats_analyzer = HeartRateStats()
        self.ui = HeartRateUI(self.config)
        self.rtss = RTSSIntegration(self.config)
        self.config_watcher = ConfigWatcher()
        self.ws_client = WebSocketClient(self.config, self._on_heart_rate)

        self.ws_client.start()
        self._start_env_watcher()

    def _on_heart_rate(self, heart_rate: str) -> None:
        """心率数据回调"""
        try:
            hr_int = int(heart_rate)
            self.stats_analyzer.add_heart_rate(hr_int)
        except ValueError:
            return

        display_mode = self.config.display_mode

        if display_mode in ("both", "default"):
            self.ui.update_heart_rate(heart_rate)
        else:
            self.ui.update_heart_rate(heart_rate, update_display=False)

        if display_mode in ("both", "rtss") and self.rtss.is_enabled():
            current, max_hr, min_hr = self.ui.get_display_values()
            self.rtss.update_heart_rate(current, max_hr, min_hr)

    def _start_env_watcher(self) -> None:
        """启动环境变量监视线程"""

        def _watch():
            while True:
                try:
                    if self.config_watcher.check_and_reload_env():
                        logger.info("环境变量已重新加载")
                        new_config = HeartRateConfig.from_env()
                        old_mode = self.config.display_mode
                        self.config = new_config
                        new_mode = new_config.display_mode

                        if old_mode != new_mode:
                            logger.info(
                                "显示模式已从 %s 更改为 %s", old_mode, new_mode
                            )
                            if new_mode in ("both", "default"):
                                self.ui.show_window()
                            elif new_mode == "rtss":
                                self.ui.hide_window()

                        self.ui.update_config(new_config)
                        self.rtss.config = new_config
                except Exception:
                    logger.exception("环境变量监视线程出错")
                time.sleep(2)

        threading.Thread(target=_watch, daemon=True).start()

    def run(self) -> None:
        """运行应用程序"""
        url = self.config.hyperate_url
        if "YOUR_ID_HERE" in url or "你的会话ID" in url:
            logger.error("请先修改 HYPERATE_URL 为你的真实链接！")
            sys.exit(1)

        logger.info("=" * 50)
        logger.info("Hyperate Triple Overlay 启动")
        logger.info("显示模式: %s", self.config.display_mode)
        logger.info(
            "RTSS集成: %s",
            "已启用" if self.rtss.is_enabled() else "已禁用",
        )
        logger.info("=" * 50)

        if self.config.display_mode in ("both", "default"):
            self.ui.run()
        else:
            logger.info("RTSS模式：UI窗口已隐藏，仅RTSS OSD显示")
            logger.info("按Ctrl+C退出应用")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("接收到退出信号")

        if self.rtss.is_enabled():
            self.rtss.clear_display()


def main() -> None:
    """应用入口点"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    app = HyperateTripleOverlay()
    app.run()


if __name__ == "__main__":
    main()
