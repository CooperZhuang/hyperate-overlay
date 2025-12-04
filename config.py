#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置模块
处理环境变量加载和配置管理
"""

import os
import sys

from dotenv import load_dotenv


def load_config():
    """加载环境变量配置"""
    load_dotenv()

    # 从环境变量读取配置，提供默认值
    HYPERATE_URL = os.getenv("HYPERATE_URL", "")
    if not HYPERATE_URL:
        print("错误: 未设置 HYPERATE_URL 环境变量")
        print("请复制 .env.example 为 .env 并填写你的配置")
        sys.exit(1)

    # 显示设置（从环境变量读取，提供默认值）
    current_size = int(os.getenv("CURRENT_SIZE", "96"))
    unit_size = int(current_size * 0.70)  # Max/Min字体大小缩小到70%
    current_font_size = unit_size * 2  # 当前心率字体大小是Max/Min的两倍

    config = {
        "HYPERATE_URL": HYPERATE_URL,
        "CURRENT_SIZE": current_size,  # 保留原始配置，但实际使用current_font_size
        "UNIT_SIZE": unit_size,  # Max/Min字体大小
        "CURRENT_FONT_SIZE": current_font_size,  # 当前心率字体大小（UNIT_SIZE的两倍）
        "CURRENT_COLOR": os.getenv("CURRENT_COLOR", "#FF2D00"),
        "MAX_COLOR": os.getenv("MAX_COLOR", "#FF6B6B"),
        "MIN_COLOR": os.getenv("MIN_COLOR", "#4ECDC4"),
        "BPM_COLOR": os.getenv("BPM_COLOR", "#FFFFFF"),
        "BG_TRANSPARENT": os.getenv("BG_TRANSPARENT", "true").lower() == "true",
        "OPACITY": float(os.getenv("OPACITY", "0.85")),
        "UPDATE_INTERVAL": int(os.getenv("UPDATE_INTERVAL", "3")),
        "POS_X": int(os.getenv("POS_X", "50")),
        "POS_Y": int(os.getenv("POS_Y", "30")),
        "BLINK_ENABLE": os.getenv("BLINK_ENABLE", "true").lower() == "true",
        "BLINK_THRESHOLD": int(os.getenv("BLINK_THRESHOLD", "160")),
        "ROW_SPACING": int(os.getenv("ROW_SPACING", "0")),  # 行间距，0表示默认
    }

    return config


def extract_channel_id(hyperate_url):
    """从URL中提取channelId"""
    try:
        # 从HYPERATE_URL中提取id参数
        if "id=" in hyperate_url:
            channel_id = hyperate_url.split("id=")[1]
            # 移除可能的后缀
            if "&" in channel_id:
                channel_id = channel_id.split("&")[0]
            if "#" in channel_id:
                channel_id = channel_id.split("#")[0]
            return channel_id
    except Exception as e:
        print(f"提取channelId失败: {e}")
    return "internal-testing"  # 默认值


class ConfigWatcher:
    """配置监视线程类"""

    def __init__(self):
        self.env_file_mtime = 0
        self._update_env_file_mtime()

    def _update_env_file_mtime(self):
        """更新.env文件的修改时间记录"""
        try:
            if os.path.exists(".env"):
                self.env_file_mtime = os.path.getmtime(".env")
        except Exception:
            pass

    def check_and_reload_env(self):
        """检查.env文件是否被修改，如果是则重新加载并更新显示"""
        try:
            if os.path.exists(".env"):
                current_mtime = os.path.getmtime(".env")
                if current_mtime > self.env_file_mtime:
                    print("检测到.env文件已修改，重新加载环境变量...")
                    load_dotenv(override=True)
                    self.env_file_mtime = current_mtime
                    return True
        except Exception as e:
            print(f"检查.env文件时出错: {e}")
        return False
