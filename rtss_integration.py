#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RTSS集成模块
使用Saku RTSS CLI DLL在RTSS OSD中显示心率数据
"""

import ctypes
import os
from ctypes import POINTER, c_bool, c_char_p, c_float, c_int, c_uint


class RTSSIntegration:
    """RTSS集成类"""

    def __init__(self, config):
        """
        初始化RTSS集成

        Args:
            config: 配置字典
        """
        self.config = config
        self.dll_loaded = False
        self.dll = None

        # 根据DISPLAY_MODE决定是否启用RTSS
        display_mode = self.config.get("DISPLAY_MODE", "both")
        self.enabled = display_mode in ["both", "rtss"]

        if not self.enabled:
            print("RTSS集成已禁用")
            return

        self.load_dll()

    def load_dll(self):
        """加载Saku RTSS CLI DLL"""
        try:
            dll_path = "Saku RTSS CLI.dll"
            # 获取绝对路径
            dll_abs_path = os.path.abspath(dll_path)

            if not os.path.exists(dll_abs_path):
                print(f"错误: 找不到DLL文件: {dll_abs_path}")
                self.enabled = False
                return

            print(f"加载DLL: {dll_abs_path}")
            # 加载DLL - 使用绝对路径
            self.dll = ctypes.CDLL(dll_abs_path)

            # 设置函数参数类型
            self.dll.displayText.argtypes = [c_char_p]
            self.dll.displayText.restype = None

            self.dll.Refresh.argtypes = []
            self.dll.Refresh.restype = c_int

            self.dll.EmbedGraph.argtypes = [
                c_uint,
                POINTER(c_float),
                c_uint,
                c_uint,
                c_int,
                c_int,
                c_int,
                c_float,
                c_float,
                c_uint,
            ]
            self.dll.EmbedGraph.restype = c_uint

            self.dll.GetClientsNum.argtypes = []
            self.dll.GetClientsNum.restype = c_uint

            self.dll.GetSharedMemoryVersion.argtypes = []
            self.dll.GetSharedMemoryVersion.restype = c_uint

            self.dll.UpdateOSD.argtypes = [c_char_p]
            self.dll.UpdateOSD.restype = c_bool

            self.dll.ReleaseOSD.argtypes = []
            self.dll.ReleaseOSD.restype = c_int

            self.dll_loaded = True
            print("RTSS DLL加载成功")

            # 测试连接
            clients_num = self.get_clients_num()
            print(f"RTSS客户端数量: {clients_num}")

        except Exception as e:
            print(f"加载RTSS DLL失败: {e}")
            self.enabled = False
            self.dll_loaded = False

    def is_enabled(self):
        """检查RTSS集成是否启用"""
        return self.enabled and self.dll_loaded

    def update_heart_rate(self, current, max_hr, min_hr):
        """
        更新RTSS OSD显示的心率数据

        Args:
            current: 当前心率
            max_hr: 最高心率
            min_hr: 最低心率
        """
        if not self.is_enabled():
            return

        try:
            # 使用配置中的显示格式
            display_format = self.config.get(
                "RTSS_DISPLAY_FORMAT", "BPM {current} ({max}/{min})"
            )

            # 替换变量
            text = display_format.format(current=current, max=max_hr, min=min_hr)

            # 更新OSD
            success = self.update_osd(text)
            if not success:
                print("RTSS OSD更新失败")

        except Exception as e:
            print(f"更新RTSS显示失败: {e}")

    def clear_display(self):
        """清除RTSS OSD显示"""
        if not self.is_enabled():
            return

        try:
            self.release_osd()
            print("RTSS OSD显示已清除")
        except Exception as e:
            print(f"清除RTSS显示失败: {e}")

    # DLL函数封装

    def change_osd_text(self, text):
        """更改OSD文本"""
        if not self.is_enabled():
            return
        self.dll.displayText(text.encode("utf-8"))  # pyright: ignore[reportOptionalMemberAccess]

    def reset_osd_text(self):
        """重置OSD文本"""
        if not self.is_enabled():
            return
        self.dll.ReleaseOSD()  # pyright: ignore[reportOptionalMemberAccess]

    def refresh(self):
        """刷新RTSS显示"""
        if not self.is_enabled():
            return -1
        return self.dll.Refresh()  # pyright: ignore[reportOptionalMemberAccess]

    def embed_graph(
        self,
        dw_offset,
        buffer,
        dw_buffer_pos,
        dw_buffer_size,
        dw_width,
        dw_height,
        dw_margin,
        flt_min,
        flt_max,
        dw_flags,
    ):
        """嵌入图形到RTSS OSD"""
        if not self.is_enabled():
            return 0

        float_array_type = c_float * len(buffer)
        lp_buffer = float_array_type(*buffer)
        return self.dll.EmbedGraph(  # pyright: ignore[reportOptionalMemberAccess]
            dw_offset,
            lp_buffer,
            dw_buffer_pos,
            dw_buffer_size,
            dw_width,
            dw_height,
            dw_margin,
            flt_min,
            flt_max,
            dw_flags,
        )

    def get_clients_num(self):
        """获取RTSS客户端数量"""
        if not self.is_enabled():
            return 0
        return self.dll.GetClientsNum()  # pyright: ignore[reportOptionalMemberAccess]

    def get_shared_memory_version(self):
        """获取共享内存版本"""
        if not self.is_enabled():
            return 0
        return self.dll.GetSharedMemoryVersion()  # pyright: ignore[reportOptionalMemberAccess]

    def update_osd(self, text):
        """更新OSD显示"""
        if not self.is_enabled():
            return False
        return self.dll.UpdateOSD(text.encode("utf-8"))  # pyright: ignore[reportOptionalMemberAccess]

    def release_osd(self):
        """释放OSD显示"""
        if not self.is_enabled():
            return -1
        return self.dll.ReleaseOSD()  # pyright: ignore[reportOptionalMemberAccess]


def test_rtss():
    """测试RTSS集成"""
    print("测试RTSS集成...")

    # 创建测试配置 - 使用DISPLAY_MODE来决定是否启用RTSS
    config = {"DISPLAY_MODE": "both"}

    rtss = RTSSIntegration(config)

    if rtss.is_enabled():
        print("RTSS集成测试成功")

        # 测试显示文本
        rtss.change_osd_text("RTSS集成测试 - 心率监控")

        # 测试更新心率
        rtss.update_heart_rate("75", "120", "60")

        # 等待一会儿
        import time

        time.sleep(2)

        # 清除显示
        rtss.clear_display()

        print("测试完成")
    else:
        print("RTSS集成测试失败")


if __name__ == "__main__":
    test_rtss()
