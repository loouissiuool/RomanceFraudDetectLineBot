# repo-main/clients/analysis_api.py

import requests
import json
import logging
from utils.error_handler import AppError # 導入自定義錯誤

logger = logging.getLogger(__name__)

class AnalysisApiClient:
    """
    用於與外部分析 API 互動的客戶端。
    """
    def __init__(self, api_url: str):
        if not api_url:
            raise AppError("Analysis API URL isn't set.")
        self.api_url = api_url
        logger.info(f"AnalysisApiClient initialized successfully, API URL: {api_url}")

    def analyze(self, data: dict) -> dict:
        """
        傳送資料到外部 API 伺服器並接收分析結果。
        """
        try:
            headers = {"Content-Type": "application/json"}
            res = requests.post(self.api_url, headers=headers, data=json.dumps(data), timeout=5)
            if res.status_code == 200:
                logger.info(f"API response content: {res.json()}")
                return res.json()
            else:
                logger.warning(f"API response error: {res.status_code}, content: {res.text}")
                return {"label": "unknown", "confidence": 0.0, "reply": "The system is currently busy, please try again later."}
        except requests.exceptions.RequestException as e:
            logger.error(f"A network error occurred while sending the API：{e}", exc_info=True)
            raise AppError("A network error occurred while sending the API.", original_error=e)
        except Exception as e:
            logger.error(f"An unknown error occurred while sending the API：{e}", exc_info=True)
            raise AppError("An unknown error occurred while sending the API.", original_error=e)