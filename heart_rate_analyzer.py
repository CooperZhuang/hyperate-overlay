#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
心率数据分析工具
读取心率CSV数据，进行统计分析和可视化
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# 检查matplotlib是否可用
try:
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    from typing import Any

    plt: Any = None  # 避免undefined错误
    HAS_MATPLOTLIB = False


def load_heart_rate_data_from_log(log_file):
    """
    从CSV/TSV日志文件加载心率数据，支持有/无头部格式
    """
    try:
        # 检查文件第一行是否包含CSV头部
        with open(log_file, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()

        has_header = "timestamp" in first_line.lower()

        if has_header:
            # 有头部，使用pandas直接读取
            df = pd.read_csv(log_file, encoding="utf-8")
            print(f"检测到CSV头部，成功加载日志文件: {log_file}")
        else:
            # 无头部，手动解析每一行
            data = []
            with open(log_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    # 按逗号分割并期望3个或4个字段
                    parts = [part.strip() for part in line.split(",")]
                    if len(parts) >= 3:
                        try:
                            timestamp = float(parts[0])
                            heart_rate = int(parts[1])
                            datetime_iso = parts[2]

                            data_point = {
                                "timestamp": timestamp,
                                "heart_rate": heart_rate,
                                "datetime": datetime_iso,
                            }

                            # 如果有第4个字段（readable_time）
                            if len(parts) >= 4:
                                data_point["readable_time"] = ",".join(parts[3:])

                            data.append(data_point)
                        except ValueError as e:
                            print(f"警告: 第{line_num}行数据格式错误，跳过: {e}")
                            continue
                    else:
                        print(f"警告: 第{line_num}行字段数量不足，跳过: {line}")
                        continue

            if not data:
                print("日志文件为空或无有效数据")
                sys.exit(1)

            df = pd.DataFrame(data)
            print(f"无头部日志文件解析完成: {log_file}")

        print(f"数据点总数: {len(df)}")

        # 确保必要的列存在
        if "timestamp" not in df.columns or "heart_rate" not in df.columns:
            print("数据格式错误，缺少timestamp或heart_rate列")
            sys.exit(1)

        # 转换数据类型
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df["heart_rate"] = pd.to_numeric(df["heart_rate"], errors="coerce").astype(int)

        # 删除无效数据
        original_count = len(df)
        df = df.dropna()
        cleaned_count = len(df)

        if cleaned_count < original_count:
            print(f"清理无效数据: {original_count - cleaned_count} 行已移除")

        print(f"最终有效数据点: {len(df)}")

        return df

    except FileNotFoundError:
        print(f"文件未找到: {log_file}")
        sys.exit(1)
    except Exception as e:
        print(f"加载日志文件失败: {e}")
        sys.exit(1)


def load_heart_rate_data_from_dir(data_dir, days=7):
    """
    从数据目录加载最近N天的所有心率数据
    """
    try:
        from pathlib import Path

        data_dir_path = Path(data_dir)
        if not data_dir_path.exists():
            print("Data directory not found: " + str(data_dir))
            sys.exit(1)

        import datetime as dt

        # 查找最近N天的日志文件
        all_data = []
        for i in range(days):
            date = dt.date.today() - dt.timedelta(days=i)
            log_file = data_dir_path / f"heart_rate_{date.strftime('%Y-%m-%d')}.csv"

            if log_file.exists():
                print("Loading: " + str(log_file.name))
                daily_data = load_heart_rate_data_from_log(str(log_file))
                all_data.append(daily_data)

        if not all_data:
            print("No data files found in directory: " + str(data_dir))
            sys.exit(1)

        # 合并所有数据
        combined_df = pd.concat(all_data, ignore_index=True)

        # 按时间排序
        combined_df = combined_df.sort_values("timestamp").reset_index(drop=True)

        print("Successfully loaded data from directory: " + str(data_dir))
        print("Total data points: " + str(len(combined_df)))
        print(
            "Date range: "
            + str(combined_df["timestamp"].min())
            + " to "
            + str(combined_df["timestamp"].max())
        )

        return combined_df

    except Exception as e:
        print("Failed to load data from directory: " + str(e))
        sys.exit(1)


def load_heart_rate_data(csv_file):
    """
    加载心率数据CSV文件
    """
    try:
        df = pd.read_csv(csv_file)
        print("Successfully loaded data file: " + str(csv_file))
        print("Data points: " + str(len(df)))

        # 检查必要列
        if "timestamp" not in df.columns or "heart_rate" not in df.columns:
            print("ERROR: CSV must contain 'timestamp' and 'heart_rate' columns")
            sys.exit(1)

        # 转换数据类型
        df["timestamp"] = pd.to_numeric(df["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df["heart_rate"] = df["heart_rate"].astype(int)

        # 排序
        df = df.sort_values("timestamp").reset_index(drop=True)

        print(
            "Time range: "
            + str(df["timestamp"].min())
            + " - "
            + str(df["timestamp"].max())
        )

        return df

    except FileNotFoundError:
        print("ERROR: File not found: " + str(csv_file))
        sys.exit(1)
    except Exception as e:
        print("ERROR: Failed to load data: " + str(e))
        sys.exit(1)


def calculate_comprehensive_stats(df):
    """
    计算综合统计信息
    """
    stats = {}

    # 基本统计
    stats["total_points"] = len(df)
    stats["min_hr"] = int(df["heart_rate"].min())
    stats["max_hr"] = int(df["heart_rate"].max())
    stats["mean_hr"] = round(df["heart_rate"].mean(), 1)
    stats["median_hr"] = int(df["heart_rate"].median())
    stats["std_hr"] = round(df["heart_rate"].std(), 2)

    # 时间统计
    time_span = df["timestamp"].max() - df["timestamp"].min()
    stats["duration_seconds"] = time_span.total_seconds()
    stats["duration_minutes"] = round(time_span.total_seconds() / 60, 1)
    stats["duration_hours"] = round(time_span.total_seconds() / 3600, 1)

    # 心率区间统计
    hr_ranges = {
        "very_low": len(df[df["heart_rate"] < 50]),
        "low": len(df[(df["heart_rate"] >= 50) & (df["heart_rate"] < 60)]),
        "normal": len(df[(df["heart_rate"] >= 60) & (df["heart_rate"] < 100)]),
        "elevated": len(df[(df["heart_rate"] >= 100) & (df["heart_rate"] < 140)]),
        "high": len(df[df["heart_rate"] >= 140]),
    }
    stats["ranges"] = hr_ranges

    # 心率变异性指标
    if len(df) > 1:
        stats["cv"] = round(
            (df["heart_rate"].std() / df["heart_rate"].mean()) * 100, 1
        )  # 变异系数

        # 需要numpy计算RMSSD
        try:
            import numpy as np

            stats["rmssd"] = round(
                np.sqrt(np.mean(np.diff(df["heart_rate"]) ** 2)), 2
            )  # RMSSD
        except ImportError:
            stats["rmssd"] = 0.0  # 如果没有numpy，使用默认值
    else:
        stats["cv"] = 0.0
        stats["rmssd"] = 0.0

    # 分位数
    stats["q25"] = int(df["heart_rate"].quantile(0.25))
    stats["q75"] = int(df["heart_rate"].quantile(0.75))
    stats["iqr"] = round(stats["q75"] - stats["q25"], 1)

    # 异常值界限
    iqr = stats["iqr"]
    stats["outlier_low"] = max(int(stats["q25"] - 1.5 * iqr), 0)
    stats["outlier_high"] = int(stats["q75"] + 1.5 * iqr)

    return stats


def plot_heart_rate_trend(df, output_dir="."):
    """
    绘制心率趋势图
    """
    if not HAS_MATPLOTLIB:
        return

    assert plt is not None  # tell type checker plt is available

    plt.figure(figsize=(15, 10))

    # 创建子图
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 10))

    # 原始心率数据
    ax1.plot(df["timestamp"], df["heart_rate"], "b-", alpha=0.7, linewidth=1)
    ax1.set_title("Heart Rate Trend")
    ax1.set_ylabel("Heart Rate (BPM)")
    ax1.grid(True, alpha=0.3)

    # 心率直方图
    ax3.hist(df["heart_rate"], bins=30, edgecolor="black", alpha=0.7)
    mean_hr = df["heart_rate"].mean()
    median_hr = df["heart_rate"].median()
    ax3.axvline(
        mean_hr,
        color="red",
        linestyle="--",
        linewidth=2,
        label="Mean: {:.1f}".format(mean_hr),
    )
    ax3.axvline(
        median_hr,
        color="green",
        linestyle="--",
        linewidth=2,
        label="Median: {:.1f}".format(median_hr),
    )
    ax3.set_title("Heart Rate Distribution")
    ax3.set_xlabel("Heart Rate (BPM)")
    ax3.set_ylabel("Frequency")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 简单趋势线
    ax2.plot(
        df["timestamp"],
        df["heart_rate"].rolling(window=10, min_periods=1).mean(),
        "r-",
        linewidth=2,
        label="10-point moving average",
    )
    ax2.set_title("Heart Rate Trend (Moving Average)")
    ax2.set_ylabel("Heart Rate (BPM)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = str(output_dir) + "/heart_rate_trend.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print("Chart saved to: " + output_path)


def plot_heart_rate_zones(df, output_dir="."):
    """
    绘制心率区间分析图
    """
    if not HAS_MATPLOTLIB:
        return

    assert plt is not None  # tell type checker plt is available

    # 计算心率区间
    zones = [
        ("Very Low", "< 50 BPM", len(df[df["heart_rate"] < 50])),
        (
            "Low",
            "50-59 BPM",
            len(df[(df["heart_rate"] >= 50) & (df["heart_rate"] < 60)]),
        ),
        (
            "Normal",
            "60-99 BPM",
            len(df[(df["heart_rate"] >= 60) & (df["heart_rate"] < 100)]),
        ),
        (
            "Elevated",
            "100-139 BPM",
            len(df[(df["heart_rate"] >= 100) & (df["heart_rate"] < 140)]),
        ),
        ("High", ">= 140 BPM", len(df[df["heart_rate"] >= 140])),
    ]

    zone_names = [z[0] for z in zones]
    zone_counts = [z[2] for z in zones]
    zone_ranges = [z[1] for z in zones]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

    # 饼图
    colors = ["lightblue", "lightgreen", "green", "orange", "red"]
    ax1.pie(
        zone_counts, labels=zone_names, autopct="%1.1f%%", colors=colors, startangle=90
    )
    ax1.set_title("Heart Rate Zone Distribution", fontsize=14)

    # 条形图
    bars = ax2.barh(range(len(zone_names)), zone_counts, color=colors, alpha=0.7)
    ax2.set_yticks(range(len(zone_names)))
    ax2.set_yticklabels(
        [name + "\n(" + zone + ")" for name, zone in zip(zone_names, zone_ranges)]
    )
    ax2.set_xlabel("Count")
    ax2.set_title("Heart Rate Zone Statistics", fontsize=14)
    ax2.grid(True, alpha=0.3)

    # 添加数值标签
    for i, (bar, count) in enumerate(zip(bars, zone_counts)):
        ax2.text(count + max(zone_counts) * 0.01, i, str(count), va="center")

    plt.tight_layout()
    output_path = str(output_dir) + "/heart_rate_zones.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print("Zone analysis saved to: " + output_path)


def generate_analysis_report(df, stats, output_dir="."):
    """
    生成分析报告
    """
    output_path = str(output_dir) + "/analysis_report.txt"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("心率数据分析报告\n")
        f.write("=" * 60 + "\n\n")

        f.write("数据概览:\n")
        f.write("数据点总数: {}\n".format(stats["total_points"]))
        f.write(
            "持续时间: {:.1f} 分钟 ({:.1f} 小时)\n".format(
                stats["duration_minutes"], stats["duration_hours"]
            )
        )
        f.write("心率范围: {} - {} BPM\n\n".format(stats["min_hr"], stats["max_hr"]))

        f.write("统计指标:\n")
        f.write("平均心率: {:.1f} BPM\n".format(stats["mean_hr"]))
        f.write("中位心率: {} BPM\n".format(stats["median_hr"]))
        f.write("标准差: {:.2f} BPM\n".format(stats["std_hr"]))
        f.write("变异系数: {:.1f}%\n".format(stats["cv"]))
        f.write("RMSSD: {:.2f}\n\n".format(stats["rmssd"]))

        # 心率区间统计
        ranges = stats["ranges"]
        total = stats["total_points"]
        f.write("心率区间分布:\n")
        f.write(
            "极低心率(<50 BPM): {} 次 ({:.1f}%)\n".format(
                ranges["very_low"], ranges["very_low"] / total * 100
            )
        )
        f.write(
            "偏低心率(50-59 BPM): {} 次 ({:.1f}%)\n".format(
                ranges["low"], ranges["low"] / total * 100
            )
        )
        f.write(
            "正常心率(60-99 BPM): {} 次 ({:.1f}%)\n".format(
                ranges["normal"], ranges["normal"] / total * 100
            )
        )
        f.write(
            "偏高心率(100-139 BPM): {} 次 ({:.1f}%)\n".format(
                ranges["elevated"], ranges["elevated"] / total * 100
            )
        )
        f.write(
            "过高心率(≥140 BPM): {} 次 ({:.1f}%)\n\n".format(
                ranges["high"], ranges["high"] / total * 100
            )
        )

        # 时间范围
        f.write("时间范围:\n")
        f.write(
            "开始时间: {}\n".format(df["timestamp"].min().strftime("%Y-%m-%d %H:%M:%S"))
        )
        f.write(
            "结束时间: {}\n".format(df["timestamp"].max().strftime("%Y-%m-%d %H:%M:%S"))
        )

        f.write("\n" + "=" * 60 + "\n")

    print("分析报告保存至: " + output_path)


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description="Heart Rate Data Analysis Tool")
    parser.add_argument(
        "input_path",
        help="Path to heart rate data (CSV file, log file, or data directory)",
    )
    parser.add_argument(
        "-o", "--output", default=".", help="Output directory (default: current)"
    )
    parser.add_argument("--no-plots", action="store_true", help="Skip generating plots")
    parser.add_argument(
        "-d",
        "--days",
        type=int,
        default=7,
        help="Days to include when analyzing directory (default: 7)",
    )

    args = parser.parse_args()

    # 检查输入路径
    input_path = Path(args.input_path)
    if not input_path.exists():
        print("ERROR: Input path not found: {}".format(input_path))
        sys.exit(1)

    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        print("Starting heart rate data analysis...")

        # 根据输入路径类型加载数据
        if input_path.is_file():
            if input_path.suffix.lower() == ".csv":
                # 单个日志文件
                df = load_heart_rate_data_from_log(str(input_path))
            else:
                # CSV文件
                df = load_heart_rate_data(str(input_path))
        elif input_path.is_dir():
            # 数据目录，加载最近几天的数据
            df = load_heart_rate_data_from_dir(str(input_path), args.days)
        else:
            print("ERROR: Invalid input path")
            sys.exit(1)

        # 计算统计信息
        stats = calculate_comprehensive_stats(df)

        # 生成报告
        generate_analysis_report(df, stats, str(output_dir))

        # 生成图表
        if not args.no_plots:
            if HAS_MATPLOTLIB:
                plot_heart_rate_trend(df, str(output_dir))
                plot_heart_rate_zones(df, str(output_dir))
            else:
                print("WARNING: matplotlib not available, skipping chart generation")

        print("Analysis completed successfully!")

    except KeyboardInterrupt:
        print("Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print("ERROR during analysis: {}".format(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
