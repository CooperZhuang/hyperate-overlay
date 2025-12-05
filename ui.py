#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI 模块
处理 Tkinter 界面和显示
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import font as tkfont


class HeartRateUI:
    """心率显示界面类"""

    def __init__(self, config):
        """
        初始化 UI

        Args:
            config: 配置字典
        """
        self.config = config
        self.current = "--"
        self.max_hr = "--"
        self.min_hr = "--"
        self.blinking = False
        self.heart_rate_history = []  # 存储心率历史用于计算最高/最低
        self.max_history_size = 100  # 最大历史记录数

        self.root = tk.Tk()

        # 设置DPI缩放为1.5，提高渲染质量
        self.root.tk.call("tk", "scaling", 1.5)

        self.root.title("Hyperate Triple")
        self.root.overrideredirect(True)  # 无边框
        self.root.attributes("-topmost", True)  # 始终置顶
        self.root.attributes("-alpha", self.config["OPACITY"])

        bg_color = "black" if not self.config["BG_TRANSPARENT"] else "black"
        self.root.configure(bg=bg_color)
        if self.config["BG_TRANSPARENT"]:
            self.root.attributes("-transparentcolor", "black")

        self.root.geometry(f"+{self.config['POS_X']}+{self.config['POS_Y']}")

        # 字体 - 添加抗锯齿和字体平滑优化
        self.font_current = tkfont.Font(
            family="Arial Black",
            size=self.config["CURRENT_FONT_SIZE"],
            weight="bold",  # UNIT_SIZE的两倍
        )
        self.font_unit = tkfont.Font(
            family="Arial",
            size=self.config["UNIT_SIZE"],
            weight="bold",  # Max/Min字体大小（70%）
        )

        # Windows特定的ClearType字体平滑设置
        if sys.platform == "win32":
            # 设置字体平滑选项
            try:
                # 在Tkinter中，字体平滑通常通过系统设置自动处理
                # 我们可以尝试设置窗口的字体平滑属性
                self.root.attributes("-alpha", self.config["OPACITY"])

                # 对于Windows，可以尝试设置字体平滑
                try:
                    # 尝试使用Tk的字体配置
                    self.root.tk.eval("""
                        if {[tk windowingsystem] eq "win32"} {
                            # Windows特定的字体平滑设置
                            option add *Font [font actual TkDefaultFont]
                            option add *font [font actual TkDefaultFont]
                        }
                    """)
                except Exception:
                    pass

                print("Windows字体平滑优化已应用")
            except Exception as e:
                print(f"设置字体平滑时出错: {e}")

        # 紧凑布局：当前心率 + 最高/最低心率
        main_frame = tk.Frame(self.root, bg=bg_color)
        main_frame.pack()

        # 当前心率数值（大字体）
        self.label_current = tk.Label(
            main_frame,
            text="--",
            font=self.font_current,
            fg=self.config["CURRENT_COLOR"],
            bg=bg_color,
        )
        self.label_current.pack(side=tk.LEFT, padx=(0, 5))

        # 最高/最低心率（紧凑排列在右侧）
        right_frame = tk.Frame(main_frame, bg=bg_color)
        right_frame.pack(side=tk.LEFT)

        # 最高心率行
        max_frame = tk.Frame(right_frame, bg=bg_color)
        max_frame.pack(anchor="w", pady=(0, 0))

        self.label_max = tk.Label(
            max_frame,
            text="--",
            font=self.font_unit,
            fg=self.config["MAX_COLOR"],
            bg=bg_color,
        )
        self.label_max.pack(side=tk.LEFT)

        self.label_max_text = tk.Label(
            max_frame,
            text="Max",
            font=self.font_unit,
            fg=self.config["MAX_COLOR"],
            bg=bg_color,
        )
        self.label_max_text.pack(side=tk.LEFT)

        # 最低心率行
        min_frame = tk.Frame(right_frame, bg=bg_color)
        min_frame.pack(anchor="w", pady=(0, 0))

        self.label_min = tk.Label(
            min_frame,
            text="--",
            font=self.font_unit,
            fg=self.config["MIN_COLOR"],
            bg=bg_color,
        )
        self.label_min.pack(side=tk.LEFT)

        self.label_min_text = tk.Label(
            min_frame,
            text="Min",
            font=self.font_unit,
            fg=self.config["MIN_COLOR"],
            bg=bg_color,
        )
        self.label_min_text.pack(side=tk.LEFT)

        # 拖动支持（包含所有文本标签）
        for widget in (
            self.label_max,
            self.label_max_text,
            self.label_current,
            self.label_min,
            self.label_min_text,
        ):
            widget.bind("<Button-1>", self.start_move)
            widget.bind("<B1-Motion>", self.do_move)
            widget.bind("<ButtonRelease-1>", self.stop_move)

        # 右键退出
        self.root.bind("<Button-3>", lambda e: sys.exit(0))

        # 闪烁线程
        if self.config["BLINK_ENABLE"]:
            threading.Thread(target=self.blink_loop, daemon=True).start()

    def start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def do_move(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

        # 更新配置中的位置
        self.config["POS_X"] = x
        self.config["POS_Y"] = y

    def stop_move(self, event):
        """鼠标松开时保存位置到 .env 文件"""
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.save_position_to_env(x, y)

    def save_position_to_env(self, pos_x, pos_y):
        """保存窗口位置到 .env 文件"""
        try:
            env_file = ".env"
            if not os.path.exists(env_file):
                print(f"警告: {env_file} 文件不存在")
                return

            # 读取文件内容
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 更新 POS_X 和 POS_Y 的值
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith("POS_X="):
                    lines[i] = f"POS_X={pos_x}\n"
                    updated = True
                elif line.strip().startswith("POS_Y="):
                    lines[i] = f"POS_Y={pos_y}\n"
                    updated = True

            # 写入文件
            if updated:
                with open(env_file, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                print(f"位置已保存到 .env: POS_X={pos_x}, POS_Y={pos_y}")
            else:
                print("警告: 未找到 POS_X 或 POS_Y 配置项")

        except Exception as e:
            print(f"保存位置到 .env 文件时出错: {e}")

    def update_heart_rate(self, heart_rate, update_display=True):
        """
        更新心率数据并计算最高/最低值

        Args:
            heart_rate: 心率值
            update_display: 是否更新显示（默认True）
        """
        if not heart_rate:
            return

        try:
            hr_int = int(heart_rate)
            old_current = self.current
            old_max = self.max_hr
            old_min = self.min_hr

            # 更新当前心率
            self.current = str(hr_int)

            # 添加到历史记录
            self.heart_rate_history.append(hr_int)
            if len(self.heart_rate_history) > self.max_history_size:
                self.heart_rate_history.pop(0)

            # 计算最高和最低心率
            if self.heart_rate_history:
                self.max_hr = str(max(self.heart_rate_history))
                self.min_hr = str(min(self.heart_rate_history))

            # 打印日志（如果值有变化）
            if (
                old_current != self.current
                or old_max != self.max_hr
                or old_min != self.min_hr
            ):
                timestamp = time.strftime("%H:%M:%S")
                print(
                    f"[{timestamp}] 当前: {self.current} BPM, 最高: {self.max_hr} BPM, 最低: {self.min_hr} BPM"
                )

            # 更新显示（如果需要）
            if update_display:
                self.label_current.configure(text=self.current)
                self.label_max.configure(text=self.max_hr)
                self.label_min.configure(text=self.min_hr)

        except ValueError:
            pass  # 忽略非数字值

    def blink_loop(self):
        while True:
            if (
                self.current.isdigit()
                and int(self.current) > self.config["BLINK_THRESHOLD"]
                and not self.blinking
            ):
                self.blinking = True
                threading.Thread(target=self.blink_effect, daemon=True).start()
            time.sleep(0.5)

    def blink_effect(self):
        while (
            self.current.isdigit()
            and int(self.current) > self.config["BLINK_THRESHOLD"]
        ):
            self.label_current.configure(fg="white")
            time.sleep(0.15)
            self.label_current.configure(fg=self.config["CURRENT_COLOR"])
            time.sleep(0.15)
        self.label_current.configure(fg=self.config["CURRENT_COLOR"])
        self.blinking = False

    def update_display(self):
        """更新显示内容"""
        self.label_current.configure(text=self.current)
        self.label_max.configure(text=self.max_hr)
        self.label_min.configure(text=self.min_hr)
        self.root.after(100, self.update_display)

    def run(self):
        """运行 UI 主循环"""
        self.update_display()
        self.root.mainloop()

    def update_config(self, new_config):
        """更新配置（热重载）"""
        try:
            self.config = new_config

            # 更新窗口位置
            self.root.geometry(f"+{self.config['POS_X']}+{self.config['POS_Y']}")

            # 更新窗口透明度
            self.root.attributes("-alpha", self.config["OPACITY"])

            # 更新背景透明
            bg_color = "black" if not self.config["BG_TRANSPARENT"] else "black"
            self.root.configure(bg=bg_color)
            if self.config["BG_TRANSPARENT"]:
                self.root.attributes("-transparentcolor", "black")
            else:
                self.root.attributes("-transparentcolor", "")

            # 更新字体大小
            self.font_current.configure(size=self.config["CURRENT_FONT_SIZE"])
            self.font_unit.configure(size=self.config["UNIT_SIZE"])

            # 更新颜色
            self.label_current.configure(fg=self.config["CURRENT_COLOR"])
            self.label_max.configure(fg=self.config["MAX_COLOR"])
            self.label_min.configure(fg=self.config["MIN_COLOR"])
            self.label_max_text.configure(fg=self.config["MAX_COLOR"])
            self.label_min_text.configure(fg=self.config["MIN_COLOR"])

            # 更新背景颜色
            for widget in [
                self.label_current,
                self.label_max,
                self.label_max_text,
                self.label_min,
                self.label_min_text,
            ]:
                widget.configure(bg=bg_color)

            print(
                f"显示配置已更新: 大小={self.config['CURRENT_SIZE']}(单位{self.config['UNIT_SIZE']}), "
                f"位置={self.config['POS_X']},{self.config['POS_Y']}, 透明度={self.config['OPACITY']}"
            )

        except Exception as e:
            print(f"更新显示配置时出错: {e}")
