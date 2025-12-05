#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
心率统计分析模块
计算心率数据的统计信息和分析图表
"""

import json
import os
import threading
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd


class HeartRateStats:
    """心率数据统计类"""

    def __init__(self, data_dir: str = "heart_rate_data", max_memory_size: int = 10000):
        """
        初始化心率统计

        Args:
            data_dir: 数据存储目录
            max_memory_size: 内存中最大存储的数据点数量
        """
        self.data_dir = data_dir
        self.max_memory_size = max_memory_size

        # 创建数据目录
        os.makedirs(self.data_dir, exist_ok=True)

        # 内存数据结构 - 使用双端队列以高效移除旧数据
        self.data_queue: deque = deque(maxlen=max_memory_size)

        # 当前日志文件相关
        self.current_date = None
        self.current_file = None
        self.file_handle = None

        # 数据锁，确保线程安全
        self.data_lock = threading.Lock()

        # 初始化日志文件
        self._init_log_file()

        # 获取当前目录下的所有日志文件
        print(f"数据存储目录: {os.path.abspath(self.data_dir)}")

    def _get_current_date(self) -> str:
        """获取当前日期字符串 (YYYY-MM-DD格式)"""
        return datetime.now().strftime("%Y-%m-%d")

    def _get_log_filename(self, date: str) -> str:
        """获取指定日期的日志文件名"""
        return os.path.join(self.data_dir, f"heart_rate_{date}.csv")

    def _init_log_file(self):
        """初始化日志文件"""
        current_date = self._get_current_date()

        # 如果日期变了，关闭旧文件
        if self.current_date != current_date:
            if self.file_handle:
                self.file_handle.close()
                self.file_handle = None

            self.current_date = current_date
            self.current_file = self._get_log_filename(current_date)

            # 打开新文件进行追加，写入CSV头部（如果文件不存在）
            try:
                file_exists = os.path.exists(self.current_file)
                self.file_handle = open(self.current_file, "a", encoding="utf-8")

                # 如果是新文件，写入CSV头部
                if not file_exists:
                    self.file_handle.write(
                        "timestamp,heart_rate,datetime,readable_time\n"
                    )

                print(f"心率日志文件已创建: {self.current_file}")
            except Exception as e:
                print(f"创建日志文件失败: {e}")

    def _ensure_correct_log_file(self, timestamp: float):
        """确保正在使用正确的日志文件（按日期）"""
        dt = datetime.fromtimestamp(timestamp)
        file_date = dt.strftime("%Y-%m-%d")

        if file_date != self.current_date:
            # 需要切换到新的日期文件
            if self.file_handle:
                self.file_handle.close()
                self.file_handle = None

            self.current_date = file_date
            self.current_file = self._get_log_filename(file_date)

            try:
                self.file_handle = open(self.current_file, "a", encoding="utf-8")
                print(f"切换到新日期日志文件: {self.current_file}")
            except Exception as e:
                print(f"创建新日期日志文件失败: {e}")

    def add_heart_rate(self, heart_rate: int, timestamp: Optional[float] = None):
        """
        添加心率数据点并立即写入日志文件

        Args:
            heart_rate: 心率值 (BPM)
            timestamp: 时间戳，如果未提供则使用当前时间
        """
        if timestamp is None:
            timestamp = time.time()

        # 确保使用正确的日志文件
        self._ensure_correct_log_file(timestamp)

        # 格式化数据行 (CSV格式)
        dt = datetime.fromtimestamp(timestamp)
        readable_time = dt.strftime("%Y年%m月%d日 %H:%M:%S")
        data_line = f"{timestamp:.6f},{heart_rate},{dt.isoformat()},{readable_time}"

        # 添加到内存队列
        data_point = {
            "timestamp": timestamp,
            "heart_rate": heart_rate,
            "datetime": dt.isoformat(),
        }

        with self.data_lock:
            self.data_queue.append(data_point)

            # 立即写入文件
            if self.file_handle:
                try:
                    self.file_handle.write(data_line + "\n")
                    self.file_handle.flush()  # 立即刷新到磁盘
                except Exception as e:
                    print(f"写入心率数据失败: {e}")

    def get_recent_data(self, minutes: int = 5) -> List[Dict]:
        """
        获取最近指定分钟的数据

        Args:
            minutes: 时间范围（分钟）

        Returns:
            心率数据点列表
        """
        cutoff_time = time.time() - (minutes * 60)

        with self.data_lock:
            return [
                point for point in self.data_queue if point["timestamp"] >= cutoff_time
            ]

    def get_all_data(self) -> List[Dict]:
        """获取所有数据"""
        with self.data_lock:
            return list(self.data_queue)

    def calculate_stats(self, data_points: List[Dict]) -> Dict:
        """
        计算心率统计信息

        Args:
            data_points: 心率数据点列表

        Returns:
            统计信息字典
        """
        if not data_points:
            return {}

        heart_rates = [point["heart_rate"] for point in data_points]
        timestamps = [point["timestamp"] for point in data_points]

        # 基本统计
        stats = {
            "count": len(heart_rates),
            "min": min(heart_rates),
            "max": max(heart_rates),
            "avg": round(sum(heart_rates) / len(heart_rates), 1),
            "median": sorted(heart_rates)[len(heart_rates) // 2],
        }

        # 心率变异性（标准差）
        if len(heart_rates) > 1:
            mean = stats["avg"]
            variance = sum((hr - mean) ** 2 for hr in heart_rates) / (
                len(heart_rates) - 1
            )
            stats["std_dev"] = round(variance**0.5, 2)
        else:
            stats["std_dev"] = 0.0

        # 时间范围
        if timestamps:
            time_span = max(timestamps) - min(timestamps)
            stats["duration_seconds"] = time_span
            stats["duration_minutes"] = round(time_span / 60, 1)

        # 心率区间统计
        ranges = {
            "very_low": len([hr for hr in heart_rates if hr < 50]),
            "low": len([hr for hr in heart_rates if 50 <= hr < 60]),
            "normal": len([hr for hr in heart_rates if 60 <= hr < 100]),
            "elevated": len([hr for hr in heart_rates if 100 <= hr < 140]),
            "high": len([hr for hr in heart_rates if hr >= 140]),
        }
        stats["ranges"] = ranges

        # 心率变化趋势（最近10个数据点的简单线性回归斜率）
        if len(heart_rates) >= 10:
            recent_data = heart_rates[-10:]
            n = len(recent_data)
            x = list(range(n))
            slope = self._calculate_slope(x, recent_data)
            stats["trend_slope"] = round(slope, 3)
            stats["trend"] = self._interpret_trend(slope)

        return stats

    def get_recent_stats(self, minutes: int = 5) -> Dict:
        """获取最近指定分钟的统计信息"""
        return self.calculate_stats(self.get_recent_data(minutes))

    def get_overall_stats(self) -> Dict:
        """获取总体统计信息"""
        return self.calculate_stats(self.get_all_data())

    def clear_data(self):
        """清空所有数据"""

        # 关闭当前文件句柄
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None

        with self.data_lock:
            self.data_queue.clear()

            # 删除所有日志文件
            try:
                for filename in os.listdir(self.data_dir):
                    if filename.startswith("heart_rate_") and filename.endswith(".csv"):
                        file_path = os.path.join(self.data_dir, filename)
                        os.remove(file_path)
                        print(f"删除日志文件: {filename}")
            except Exception as e:
                print(f"删除日志文件时出错: {e}")

            print("心率数据已清空")

            # 重新初始化日志文件
            self._init_log_file()

    def export_data(
        self, filepath: str, format: str = "csv", minutes: Optional[int] = None
    ):
        """
        导出数据到文件

        Args:
            filepath: 导出文件路径
            format: 导出格式 ('csv', 'json', 'txt')
            minutes: 导出最近N分钟的数据，None表示全部数据
        """
        data = self.get_recent_data(minutes) if minutes else self.get_all_data()

        if not data:
            print("没有数据可导出")
            return

        # 转换为DataFrame方便导出
        df = pd.DataFrame(data)

        try:
            if format.lower() == "csv":
                df.to_csv(filepath, index=False, encoding="utf-8")
            elif format.lower() == "json":
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            elif format.lower() == "txt":
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("时间戳,心率(BPM),日期时间\n")
                    for point in data:
                        dt = datetime.fromtimestamp(point["timestamp"])
                        f.write(f"{point['timestamp']},{point['heart_rate']},{dt}\n")

            print(
                f"数据已导出到 {filepath}\n格式: {format.upper()}, 数据点数量: {len(data)}"
            )

        except Exception as e:
            print(f"导出数据失败: {e}")

    def _calculate_slope(self, x: List[int], y: List[int]) -> float:
        """计算线性回归斜率"""
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi**2 for xi in x)

        denominator = n * sum_x2 - sum_x**2
        if denominator == 0:
            return 0

        return (n * sum_xy - sum_x * sum_y) / denominator

    def _interpret_trend(self, slope: float) -> str:
        """解释趋势斜率"""
        if slope > 0.5:
            return "上升中"
        elif slope < -0.5:
            return "下降中"
        elif slope > 0.1:
            return "缓慢上升"
        elif slope < -0.1:
            return "缓慢下降"
        else:
            return "稳定"

    def __del__(self):
        """析构函数，确保文件句柄被正确关闭"""
        if self.file_handle:
            try:
                self.file_handle.close()
            except Exception:
                pass


def format_stats_display(stats: Dict) -> str:
    """
    将统计信息格式化为易读的显示文本

    Args:
        stats: 统计信息字典

    Returns:
        格式化的文本
    """
    if not stats:
        return "暂无数据"

    lines = []
    lines.append("=== 心率统计分析 ===")
    lines.append(f"数据点数量: {stats.get('count', 0)}")
    lines.append(f"持续时间: {stats.get('duration_minutes', 0)} 分钟")

    lines.append("--- 心率范围 ---")
    lines.append(f"最低心率: {stats.get('min', '--')} BPM")
    lines.append(f"最高心率: {stats.get('max', '--')} BPM")
    lines.append(f"平均心率: {stats.get('avg', '--')} BPM")
    lines.append(f"中位心率: {stats.get('median', '--')} BPM")
    lines.append(f"标准差: {stats.get('std_dev', '0.0')} BPM")

    if "ranges" in stats:
        ranges = stats["ranges"]
        lines.append("--- 心率区间统计 ---")
        lines.append(f"极低(<50): {ranges.get('very_low', 0)} 次")
        lines.append(f"偏低(50-59): {ranges.get('low', 0)} 次")
        lines.append(f"正常(60-99): {ranges.get('normal', 0)} 次")
        lines.append(f"偏高(100-139): {ranges.get('elevated', 0)} 次")
        lines.append(f"过高(≥140): {ranges.get('high', 0)} 次")

    if "trend" in stats:
        lines.append("--- 心率趋势 ---")
        lines.append(f"当前趋势: {stats['trend']}")

    return "\n".join(lines)
