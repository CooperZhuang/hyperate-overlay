#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UI 模块 - Tkinter 界面和显示"""

import logging
import sys
import threading
import time
import tkinter as tk
from collections import deque
from queue import Queue
from tkinter import font as tkfont

from config import ENV_FILE, HeartRateConfig

logger = logging.getLogger(__name__)


class HeartRateUI:
    """心率显示界面"""

    def __init__(self, config: HeartRateConfig) -> None:
        self.config = config
        self.current = "--"
        self.max_hr = "--"
        self.min_hr = "--"
        self._heart_rate_history: deque[int] = deque(maxlen=100)
        self._update_queue: Queue = Queue()

        self.root = tk.Tk()
        self.root.tk.call("tk", "scaling", 1.5)
        self.root.title("Hyperate Triple")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.config.opacity)

        bg_color = "black"
        self.root.configure(bg=bg_color)
        if self.config.bg_transparent:
            self.root.attributes("-transparentcolor", "black")

        self.root.geometry(f"+{self.config.pos_x}+{self.config.pos_y}")

        self.font_current = tkfont.Font(
            family="Arial Black",
            size=self.config.current_font_size,
            weight="bold",
        )
        self.font_unit = tkfont.Font(
            family="Arial",
            size=self.config.unit_size,
            weight="bold",
        )

        self._build_ui(bg_color)

        self.root.bind("<Button-3>", lambda e: sys.exit(0))

        if self.config.blink_enable:
            threading.Thread(target=self._blink_loop, daemon=True).start()

    def _build_ui(self, bg_color: str) -> None:
        """构建 UI 组件"""
        main_frame = tk.Frame(self.root, bg=bg_color)
        main_frame.pack()

        # 当前心率 (大字体)
        self.label_current = tk.Label(
            main_frame,
            text="--",
            font=self.font_current,
            fg=self.config.current_color,
            bg=bg_color,
        )
        self.label_current.pack(side=tk.LEFT, padx=(0, 5))

        # 右侧最高 / 最低心率
        right_frame = tk.Frame(main_frame, bg=bg_color)
        right_frame.pack(side=tk.LEFT)

        max_frame = tk.Frame(right_frame, bg=bg_color)
        max_frame.pack(anchor="w")

        self.label_max = tk.Label(
            max_frame,
            text="--",
            font=self.font_unit,
            fg=self.config.max_color,
            bg=bg_color,
        )
        self.label_max.pack(side=tk.LEFT)

        self.label_max_text = tk.Label(
            max_frame,
            text="Max",
            font=self.font_unit,
            fg=self.config.max_color,
            bg=bg_color,
        )
        self.label_max_text.pack(side=tk.LEFT)

        min_frame = tk.Frame(right_frame, bg=bg_color)
        min_frame.pack(anchor="w")

        self.label_min = tk.Label(
            min_frame,
            text="--",
            font=self.font_unit,
            fg=self.config.min_color,
            bg=bg_color,
        )
        self.label_min.pack(side=tk.LEFT)

        self.label_min_text = tk.Label(
            min_frame,
            text="Min",
            font=self.font_unit,
            fg=self.config.min_color,
            bg=bg_color,
        )
        self.label_min_text.pack(side=tk.LEFT)

        # 拖动绑定
        for widget in (
            self.label_max,
            self.label_max_text,
            self.label_current,
            self.label_min,
            self.label_min_text,
        ):
            widget.bind("<Button-1>", self._start_move)
            widget.bind("<B1-Motion>", self._do_move)
            widget.bind("<ButtonRelease-1>", self._stop_move)

    # -- 拖动 --

    def _start_move(self, event: tk.Event) -> None:
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_move(self, event: tk.Event) -> None:
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")
        self.config.pos_x = x
        self.config.pos_y = y

    def _stop_move(self, event: tk.Event) -> None:
        self._save_position(self.root.winfo_x(), self.root.winfo_y())

    def _save_position(self, pos_x: int, pos_y: int) -> None:
        """保存窗口位置到 .env 文件"""
        try:
            if not ENV_FILE.exists():
                logger.warning("%s 文件不存在", ENV_FILE)
                return

            content = ENV_FILE.read_text(encoding="utf-8")
            lines = content.splitlines(keepends=True)

            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith("POS_X="):
                    lines[i] = f"POS_X={pos_x}\n"
                    updated = True
                elif line.strip().startswith("POS_Y="):
                    lines[i] = f"POS_Y={pos_y}\n"
                    updated = True

            if updated:
                ENV_FILE.write_text("".join(lines), encoding="utf-8")
                logger.info(
                    "位置已保存到 .env: POS_X=%d, POS_Y=%d", pos_x, pos_y
                )
            else:
                logger.warning("未找到 POS_X 或 POS_Y 配置项")
        except Exception:
            logger.exception("保存位置到 .env 文件时出错")

    # -- 心率更新 --

    def update_heart_rate(self, heart_rate: str, update_display: bool = True) -> None:
        """更新心率数据"""
        if not heart_rate:
            return

        try:
            hr_int = int(heart_rate)
        except ValueError:
            return

        old_current = self.current
        old_max = self.max_hr
        old_min = self.min_hr

        self.current = str(hr_int)
        self._heart_rate_history.append(hr_int)

        if self._heart_rate_history:
            self.max_hr = str(max(self._heart_rate_history))
            self.min_hr = str(min(self._heart_rate_history))

        if (
            old_current != self.current
            or old_max != self.max_hr
            or old_min != self.min_hr
        ):
            logger.info(
                "当前: %s BPM, 最高: %s BPM, 最低: %s BPM",
                self.current,
                self.max_hr,
                self.min_hr,
            )

        if update_display:
            self.root.after(0, self._update_labels)

    def _update_labels(self) -> None:
        """在主线程更新标签文字"""
        try:
            self.label_current.configure(text=self.current)
            self.label_max.configure(text=self.max_hr)
            self.label_min.configure(text=self.min_hr)
        except Exception:
            logger.exception("更新显示时出错")

    def get_display_values(self) -> tuple[str, str, str]:
        """返回当前显示的心率值 (current, max, min)"""
        return self.current, self.max_hr, self.min_hr

    # -- 闪烁 --

    def _blink_loop(self) -> None:
        """单一线程处理闪烁效果，避免线程泄漏"""
        while True:
            should_blink = (
                self.config.blink_enable
                and self.current.isdigit()
                and int(self.current) > self.config.blink_threshold
            )
            if should_blink:
                self.root.after(
                    0, lambda: self.label_current.configure(fg="white")
                )
                time.sleep(0.15)
                self.root.after(
                    0,
                    lambda: self.label_current.configure(
                        fg=self.config.current_color
                    ),
                )
                time.sleep(0.15)
            else:
                self.root.after(
                    0,
                    lambda: self.label_current.configure(
                        fg=self.config.current_color
                    ),
                )
                time.sleep(0.5)

    # -- 队列处理 --

    def _process_queue(self) -> None:
        """处理线程间通信队列"""
        while True:
            try:
                msg = self._update_queue.get_nowait()
                action, data = msg

                if action == "update_config":
                    self._apply_config(data)
                elif action == "show_window":
                    self.root.deiconify()
                elif action == "hide_window":
                    self.root.withdraw()
            except Exception:
                break

    def _process_queue_loop(self) -> None:
        """定期处理队列 (不负责更新标签文字)"""
        self._process_queue()
        self.root.after(100, self._process_queue_loop)

    # -- 配置热更新 --

    def update_config(self, new_config: HeartRateConfig) -> None:
        """线程安全的配置更新"""
        self._update_queue.put(("update_config", new_config))

    def show_window(self) -> None:
        self._update_queue.put(("show_window", None))

    def hide_window(self) -> None:
        self._update_queue.put(("hide_window", None))

    def _apply_config(self, new_config: HeartRateConfig) -> None:
        """在主线程应用新配置"""
        try:
            self.config = new_config
            self.root.geometry(
                f"+{self.config.pos_x}+{self.config.pos_y}"
            )
            self.root.attributes("-alpha", self.config.opacity)

            bg_color = "black"
            self.root.configure(bg=bg_color)
            if self.config.bg_transparent:
                self.root.attributes("-transparentcolor", "black")
            else:
                self.root.attributes("-transparentcolor", "")

            self.font_current.configure(size=self.config.current_font_size)
            self.font_unit.configure(size=self.config.unit_size)

            self.label_current.configure(fg=self.config.current_color)
            self.label_max.configure(fg=self.config.max_color)
            self.label_min.configure(fg=self.config.min_color)
            self.label_max_text.configure(fg=self.config.max_color)
            self.label_min_text.configure(fg=self.config.min_color)

            for widget in [
                self.label_current,
                self.label_max,
                self.label_max_text,
                self.label_min,
                self.label_min_text,
            ]:
                widget.configure(bg=bg_color)

            logger.info(
                "显示配置已更新: 大小=%d, 位置=%d,%d, 透明度=%.2f",
                self.config.current_size,
                self.config.pos_x,
                self.config.pos_y,
                self.config.opacity,
            )
        except Exception:
            logger.exception("更新显示配置时出错")

    # -- 运行 --

    def run(self) -> None:
        """启动 UI 主循环"""
        self._process_queue_loop()
        self.root.mainloop()
