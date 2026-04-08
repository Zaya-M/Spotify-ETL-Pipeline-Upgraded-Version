# ============================================================
# 文件：src/utils/logger.py
# 作用：统一日志配置，项目所有模块都用这个 logger
# 环境：任何 Python 环境
# 为什么不用 print：print 没有时间戳、没有级别、不能写文件
# ============================================================

import logging
import os
from datetime import datetime

# ============================================================
# 任务：配置一个既在控制台打印、又写入文件的 logger
# 要求：
#   1. 日志格式包含：时间 | 级别 | 模块名 | 消息
#   2. 日志文件按日期命名，存在 logs/ 目录下
#   3. 控制台只显示 INFO 以上，文件记录 DEBUG 以上
# ============================================================


def get_logger(name: str) -> logging.Logger:
    """
    获取统一配置的 logger
    用法：
        from src.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("开始采集数据")
        logger.error("采集失败", exc_info=True)
    """

    # TODO: 创建 logs/ 目录（如果不存在）
    # 提示：os.makedirs(path, exist_ok=True)
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # TODO: 配置日志格式
    # 格式示例：2024-01-15 10:30:25 | INFO | spotify_client | 开始采集播放历史
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    # TODO: 创建 logger 对象，设置名称为传入的 name
    logger = logging.getLogger(name)

    # TODO:  防止重复添加 Handler（单例模式思想）
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # TODO: 添加 StreamHandler（控制台输出），级别 INFO
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # TODO: 添加 FileHandler（文件输出），文件名用今天日期
        # 文件名示例：logs/etl_2024-01-15.log
        # 级别 DEBUG
        today = datetime.now().strftime("%Y-%m-%d")
        file_handler = logging.FileHandler(
            f"{log_dir}/etl_{today}.log", encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # TODO: 返回配置好的 logger
    return logger
