# repo-main/config.py

import os
from dotenv import load_dotenv

# 確保 .env 檔案被載入 (在 create_app() 中也會呼叫一次，但這裡是為了 Config.validate() 能夠讀取)
load_dotenv()

class Config:
    # LINE Bot API 憑證
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN") # 替換為 CHANNEL_ACCESS_TOKEN
    LINE_CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")         # 替換為 CHANNEL_SECRET

    # OpenAI API Key
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # 外部分析 API URL (如果專案有使用，請在 .env 中設定)
    ANALYSIS_API_URL = os.getenv("ANALYSIS_API_URL") # 保持不變

    # Flask 應用程式配置
    PORT = int(os.getenv("PORT", 5080)) # 預設埠口 5080
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t") # 預設為 False

    # 日誌級別 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    @staticmethod
    def validate():
        """
        驗證所有必要的環境變數是否已設定。
        """
        if not Config.LINE_CHANNEL_ACCESS_TOKEN:
            raise ValueError("CHANNEL_ACCESS_TOKEN 是必要的")
        if not Config.LINE_CHANNEL_SECRET:
            raise ValueError("CHANNEL_SECRET 是必要的")
        # 如果 OpenAI API Key 是必要功能，也在此處驗證
        # if not Config.OPENAI_API_KEY:
        #     raise ValueError("OPENAI_API_KEY 是必要的")

        # 可以在這裡添加其他必要的配置驗證
        pass