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
            raise AppError("Analysis API URL 未設定。")
        self.api_url = api_url
        logger.info(f"AnalysisApiClient 初始化成功，API URL: {api_url}")

    def analyze(self, data: dict) -> dict:
        """
        傳送資料到外部 API 伺服器並接收分析結果。
        """
        try:
            headers = {"Content-Type": "application/json"}
            res = requests.post(self.api_url, headers=headers, data=json.dumps(data), timeout=5)
            if res.status_code == 200:
                logger.info(f"API 回傳內容: {res.json()}")
                return res.json()
            else:
                logger.warning(f"API 回應錯誤：{res.status_code}, 內容: {res.text}")
                return {"label": "unknown", "confidence": 0.0, "reply": "目前系統繁忙，請稍後再試。"}
        except requests.exceptions.RequestException as e:
            logger.error(f"傳送 API 發生網路錯誤：{e}", exc_info=True)
            raise AppError("傳送 API 發生網路錯誤。", original_error=e)
        except Exception as e:
            logger.error(f"傳送 API 發生未知錯誤：{e}", exc_info=True)
            raise AppError("傳送 API 發生未知錯誤。", original_error=e)