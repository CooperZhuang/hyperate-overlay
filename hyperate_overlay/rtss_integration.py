#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RTSS集成模块
使用Saku RTSS CLI DLL在RTSS OSD中显示心率数据
"""

import ctypes
import logging
from ctypes import POINTER, c_bool, c_char_p, c_float, c_int, c_uint
from pathlib import Path

from .config import HeartRateConfig

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
DLL_PATH = SCRIPT_DIR.parent / "lib" / "Saku RTSS CLI.dll"


class RTSSIntegration:
    """RTSS集成类"""

    def __init__(self, config: HeartRateConfig) -> None:
        self.config = config
        self.dll_loaded = False
        self.dll = None
        self.enabled = config.display_mode in ("both", "rtss")

        if not self.enabled:
            logger.info("RTSS集成已禁用")
            return

        self._load_dll()

    def _load_dll(self) -> None:
        """加载 Saku RTSS CLI DLL"""
        try:
            if not DLL_PATH.exists():
                logger.error("找不到DLL文件: %s", DLL_PATH)
                self.enabled = False
                return

            logger.info("加载DLL: %s", DLL_PATH)
            self.dll = ctypes.CDLL(str(DLL_PATH))

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
            logger.info("RTSS DLL加载成功")

            clients_num = self.get_clients_num()
            logger.info("RTSS客户端数量: %d", clients_num)

        except Exception:
            logger.exception("加载RTSS DLL失败")
            self.enabled = False
            self.dll_loaded = False

    def is_enabled(self) -> bool:
        """检查RTSS集成是否启用"""
        return self.enabled and self.dll_loaded

    def update_heart_rate(self, current: str, max_hr: str, min_hr: str) -> None:
        """更新RTSS OSD显示的心率数据"""
        if not self.is_enabled():
            return

        try:
            display_format = self.config.rtss_display_format
            text = display_format.format(current=current, max=max_hr, min=min_hr)
            success = self.update_osd(text)
            if not success:
                logger.warning("RTSS OSD更新失败")
        except Exception:
            logger.exception("更新RTSS显示失败")

    def clear_display(self) -> None:
        """清除RTSS OSD显示"""
        if not self.is_enabled():
            return

        try:
            self.release_osd()
            logger.info("RTSS OSD显示已清除")
        except Exception:
            logger.exception("清除RTSS显示失败")

    # DLL 函数封装

    def change_osd_text(self, text: str) -> None:
        if not self.is_enabled():
            return
        self.dll.displayText(text.encode("utf-8"))  # pyright: ignore[reportOptionalMemberAccess]

    def reset_osd_text(self) -> None:
        if not self.is_enabled():
            return
        self.dll.ReleaseOSD()  # pyright: ignore[reportOptionalMemberAccess]

    def refresh(self) -> int:
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
    ) -> int:
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

    def get_clients_num(self) -> int:
        if not self.is_enabled():
            return 0
        return self.dll.GetClientsNum()  # pyright: ignore[reportOptionalMemberAccess]

    def get_shared_memory_version(self) -> int:
        if not self.is_enabled():
            return 0
        return self.dll.GetSharedMemoryVersion()  # pyright: ignore[reportOptionalMemberAccess]

    def update_osd(self, text: str) -> bool:
        if not self.is_enabled():
            return False
        return self.dll.UpdateOSD(text.encode("utf-8"))  # pyright: ignore[reportOptionalMemberAccess]

    def release_osd(self) -> int:
        if not self.is_enabled():
            return -1
        return self.dll.ReleaseOSD()  # pyright: ignore[reportOptionalMemberAccess]


def test_rtss() -> None:
    """测试RTSS集成"""
    logger.info("测试RTSS集成...")

    config = HeartRateConfig(display_mode="both")
    rtss = RTSSIntegration(config)

    if rtss.is_enabled():
        logger.info("RTSS集成测试成功")
        rtss.change_osd_text("RTSS集成测试 - 心率监控")
        rtss.update_heart_rate("75", "120", "60")

        import time
        time.sleep(2)

        rtss.clear_display()
        logger.info("测试完成")
    else:
        logger.warning("RTSS集成测试失败")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    test_rtss()
