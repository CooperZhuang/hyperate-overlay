#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""配置模块 - 处理环境变量加载和配置管理"""

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_FILE = SCRIPT_DIR / ".env"


@dataclass
class HeartRateConfig:
    """心率监控应用配置"""

    hyperate_url: str = ""
    current_size: int = 96
    unit_size: int = 67
    current_font_size: int = 134
    current_color: str = "#FF2D00"
    max_color: str = "#FF6B6B"
    min_color: str = "#4ECDC4"
    bpm_color: str = "#FFFFFF"
    bg_transparent: bool = True
    opacity: float = 0.85
    pos_x: int = 50
    pos_y: int = 30
    blink_enable: bool = True
    blink_threshold: int = 160
    row_spacing: int = 0
    rtss_display_format: str = "BPM {current} ({max}/{min})"
    rtss_update_interval: int = 1
    display_mode: str = "both"

    @classmethod
    def from_env(cls) -> "HeartRateConfig":
        """从环境变量加载配置"""
        load_dotenv(ENV_FILE)

        hyperate_url = os.getenv("HYPERATE_URL", "")
        if not hyperate_url:
            logger.error("未设置 HYPERATE_URL 环境变量")
            logger.error("请复制 .env.example 为 .env 并填写你的配置")
            sys.exit(1)

        current_size = int(os.getenv("CURRENT_SIZE", "96"))
        unit_size = int(current_size * 0.70)

        return cls(
            hyperate_url=hyperate_url,
            current_size=current_size,
            unit_size=unit_size,
            current_font_size=unit_size * 2,
            current_color=os.getenv("CURRENT_COLOR", "#FF2D00"),
            max_color=os.getenv("MAX_COLOR", "#FF6B6B"),
            min_color=os.getenv("MIN_COLOR", "#4ECDC4"),
            bpm_color=os.getenv("BPM_COLOR", "#FFFFFF"),
            bg_transparent=os.getenv("BG_TRANSPARENT", "true").lower() == "true",
            opacity=float(os.getenv("OPACITY", "0.85")),
            pos_x=int(os.getenv("POS_X", "50")),
            pos_y=int(os.getenv("POS_Y", "30")),
            blink_enable=os.getenv("BLINK_ENABLE", "true").lower() == "true",
            blink_threshold=int(os.getenv("BLINK_THRESHOLD", "160")),
            row_spacing=int(os.getenv("ROW_SPACING", "0")),
            rtss_display_format=os.getenv(
                "RTSS_DISPLAY_FORMAT", "BPM {current} ({max}/{min})"
            ),
            rtss_update_interval=int(os.getenv("RTSS_UPDATE_INTERVAL", "1")),
            display_mode=os.getenv("DISPLAY_MODE", "both"),
        )


def extract_channel_id(hyperate_url: str) -> str:
    """从URL中提取channelId"""
    try:
        if "id=" in hyperate_url:
            channel_id = hyperate_url.split("id=")[1]
            if "&" in channel_id:
                channel_id = channel_id.split("&")[0]
            if "#" in channel_id:
                channel_id = channel_id.split("#")[0]
            return channel_id
    except Exception:
        logger.exception("提取channelId失败")
    return "internal-testing"


class ConfigWatcher:
    """配置监视线程类，检测 .env 文件变化"""

    def __init__(self) -> None:
        self._env_file_mtime: float = 0
        self._update_mtime()

    def _update_mtime(self) -> None:
        try:
            if ENV_FILE.exists():
                self._env_file_mtime = ENV_FILE.stat().st_mtime
        except Exception:
            pass

    def check_and_reload_env(self) -> bool:
        """检查 .env 是否被修改，如果是则重新加载并返回 True"""
        try:
            if ENV_FILE.exists():
                current_mtime = ENV_FILE.stat().st_mtime
                if current_mtime > self._env_file_mtime:
                    logger.info("检测到.env文件已修改，重新加载环境变量...")
                    load_dotenv(ENV_FILE, override=True)
                    self._env_file_mtime = current_mtime
                    return True
        except Exception:
            logger.exception("检查.env文件时出错")
        return False
