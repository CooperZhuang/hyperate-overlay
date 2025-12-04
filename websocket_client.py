#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebSocket 客户端模块
处理与 Hyperate 服务器的 WebSocket 连接
"""

import asyncio
import json
import re
import threading
import time

import requests
import websockets


class WebSocketClient:
    """WebSocket 客户端类"""

    def __init__(self, config, update_callback):
        """
        初始化 WebSocket 客户端

        Args:
            config: 配置字典
            update_callback: 心率更新回调函数
        """
        self.config = config
        self.update_callback = update_callback
        self.ws_connected = False
        self.message_ref = 1
        self.channel_id = None
        self.websocket_key = None

    def fetch_websocket_key(self):
        """从网页中动态获取websocketKey"""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            hyperate_url = self.config["HYPERATE_URL"]
            if not hyperate_url:
                raise ValueError("HYPERATE_URL 环境变量未设置")

            response = requests.get(hyperate_url, headers=headers, timeout=10)
            response.raise_for_status()
            html = response.text

            # 使用正则表达式提取websocketKey
            pattern = r"websocketKey\s*=\s*['\"]([^'\"]+)['\"]"
            match = re.search(pattern, html)

            if match:
                websocket_key = match.group(1)
                print(f"成功获取websocketKey: {websocket_key[:30]}...")
                return websocket_key
            else:
                raise ValueError("未在网页中找到websocketKey")

        except Exception as e:
            print(f"获取websocketKey失败: {e}")
            raise  # 重新抛出异常，让调用者处理

    def start(self):
        """启动 WebSocket 连接线程"""
        from config import extract_channel_id

        self.channel_id = extract_channel_id(self.config["HYPERATE_URL"])
        print(f"连接到WebSocket，Channel ID: {self.channel_id}")

        # 启动 WebSocket 线程
        threading.Thread(target=self.websocket_loop, daemon=True).start()

    def websocket_loop(self):
        """WebSocket连接循环"""
        # 创建新的事件循环用于线程
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            try:
                loop.run_until_complete(self.websocket_handler())
            except Exception as e:
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] WebSocket连接错误: {e}")
                print("5秒后重试...")
                time.sleep(5)

    async def websocket_handler(self):
        """处理WebSocket连接"""
        # 动态获取websocketKey
        self.websocket_key = self.fetch_websocket_key()
        websocket_url = (
            f"wss://app.hyperate.io/socket/websocket?token={self.websocket_key}"
        )

        print(
            f"使用WebSocket URL: wss://app.hyperate.io/socket/websocket?token={self.websocket_key[:30]}..."
        )

        async with websockets.connect(websocket_url) as websocket:
            self.ws_connected = True
            print("WebSocket连接成功")

            # 加入频道
            join_message = {
                "topic": f"hr:{self.channel_id}",
                "event": "phx_join",
                "payload": {},
                "ref": self.message_ref,
            }
            self.message_ref += 1
            await websocket.send(json.dumps(join_message))
            print(f"已加入频道: hr:{self.channel_id}")

            # 创建心跳任务
            heartbeat_task = asyncio.create_task(self.send_heartbeat(websocket))

            # 接收消息
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if "payload" in data and "hr" in data["payload"]:
                            heart_rate = data["payload"]["hr"]
                            self.update_callback(heart_rate)
                    except json.JSONDecodeError:
                        pass  # 忽略非JSON消息
                    except Exception as e:
                        print(f"处理消息错误: {e}")
            finally:
                # 取消心跳任务
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                self.ws_connected = False

    async def send_heartbeat(self, websocket):
        """发送心跳消息"""
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
                await asyncio.sleep(30)  # 每30秒发送一次心跳
            except Exception as e:
                print(f"发送心跳失败: {e}")
                break
