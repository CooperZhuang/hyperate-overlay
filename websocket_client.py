#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""WebSocket 客户端模块 - 处理与 Hyperate 服务器的 WebSocket 连接"""

import asyncio
import json
import logging
import random
import re
import threading
import time

import requests
import websockets

from config import HeartRateConfig, extract_channel_id

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_INITIAL_RETRY_DELAY = 1.0
_MAX_RETRY_DELAY = 60.0
_RETRY_BACKOFF = 2.0
_RETRY_JITTER = 0.5


class WebSocketClient:
    """WebSocket 客户端"""

    def __init__(self, config: HeartRateConfig, update_callback) -> None:
        self.config = config
        self.update_callback = update_callback
        self.ws_connected = False
        self.message_ref = 1
        self.channel_id: str | None = None
        self.websocket_key: str | None = None
        self._retry_delay = _INITIAL_RETRY_DELAY

    def fetch_websocket_key(self) -> str:
        """从网页中动态获取 websocketKey"""
        headers = {"User-Agent": USER_AGENT}
        url = self.config.hyperate_url
        if not url:
            raise ValueError("HYPERATE_URL 未设置")

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html = response.text

        pattern = r"websocketKey\s*=\s*['\"]([^'\"]+)['\"]"
        match = re.search(pattern, html)

        if match:
            websocket_key = match.group(1)
            logger.info("成功获取websocketKey: %s...", websocket_key[:30])
            return websocket_key

        raise ValueError("未在网页中找到 websocketKey")

    def start(self) -> None:
        """启动 WebSocket 连接线程"""
        self.channel_id = extract_channel_id(self.config.hyperate_url)
        logger.info("连接到WebSocket，Channel ID: %s", self.channel_id)
        threading.Thread(target=self._websocket_loop, daemon=True).start()

    def _websocket_loop(self) -> None:
        """WebSocket 连接循环 (带指数退避)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            try:
                loop.run_until_complete(self._websocket_handler())
                self._retry_delay = _INITIAL_RETRY_DELAY
            except Exception:
                logger.exception("WebSocket连接错误")
                delay = self._retry_delay
                jitter = random.uniform(0, _RETRY_JITTER * delay)
                total_delay = delay + jitter
                logger.info("%.1f秒后重试...", total_delay)
                time.sleep(total_delay)
                self._retry_delay = min(
                    delay * _RETRY_BACKOFF, _MAX_RETRY_DELAY
                )

    async def _websocket_handler(self) -> None:
        """处理 WebSocket 连接"""
        self.websocket_key = self.fetch_websocket_key()
        ws_url = (
            f"wss://app.hyperate.io/socket/websocket"
            f"?token={self.websocket_key}"
        )

        logger.info(
            "WebSocket URL: wss://app.hyperate.io/socket/websocket?token=%s...",
            self.websocket_key[:30],
        )

        async with websockets.connect(ws_url) as websocket:
            self.ws_connected = True
            logger.info("WebSocket连接成功")

            join_message = {
                "topic": f"hr:{self.channel_id}",
                "event": "phx_join",
                "payload": {},
                "ref": self.message_ref,
            }
            self.message_ref += 1
            await websocket.send(json.dumps(join_message))
            logger.info("已加入频道: hr:%s", self.channel_id)

            heartbeat_task = asyncio.create_task(
                self._send_heartbeat(websocket)
            )

            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if "payload" in data and "hr" in data["payload"]:
                            self.update_callback(data["payload"]["hr"])
                    except json.JSONDecodeError:
                        pass
                    except Exception:
                        logger.exception("处理消息错误")
            finally:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                self.ws_connected = False

    async def _send_heartbeat(self, websocket) -> None:
        """发送 Phoenix 心跳消息"""
        while self.ws_connected:
            try:
                heartbeat_message = {
                    "topic": "phoenix",
                    "event": "heartbeat",
                    "payload": {},
                    "ref": self.message_ref,
                }
                self.message_ref += 1
                await websocket.send(json.dumps(heartbeat_message))
                await asyncio.sleep(30)
            except Exception:
                logger.exception("发送心跳失败")
                break
