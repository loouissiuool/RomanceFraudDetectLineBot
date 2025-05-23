# repo-main/utils/logger.py

import logging
import os
from config import Config # 導入 Config 以獲取日誌級別

# 定義日誌輸出格式
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

def get_app_logger(name: str) -> logging.Logger:
    """
    獲取一個配置好的日誌記錄器。
    Args:
        name: 日誌記錄器的名稱 (通常是模組名稱，如 __name__)
    Returns:
        配置好的 logging.Logger 物件
    """
    logger = logging.getLogger(name)
    # 防止重複添加 handler，避免日誌重複輸出
    if not logger.handlers:
        handler = logging.StreamHandler() # 輸出到控制台
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(Config.LOG_LEVEL) # 設定日誌等級從 Config 獲取
    return logger

# 為整個應用程式提供一個通用的日誌記錄器實例
app_logger = get_app_logger("app_main")