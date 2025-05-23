"""
本地檢測策略

此模組實現了基於本地規則的詐騙檢測策略。
使用 ADK agent 進行詐騙檢測。
"""

from typing import Dict, List, Any, Optional, Union
import json
import os
import re
from pathlib import Path

from .base import DetectionStrategy
from utils.logger import get_service_logger
from utils.error_handler import DetectionError, ValidationError, with_error_handling
from utils.validator import validate_line_export
from utils.agents.agent_factory import create_agent

# 設定預設資料檔案路徑
PROJECT_ROOT = os.path.abspath(os.path.join(__file__, '../../../..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
SCAM_DATA_PATH = os.path.join(DATA_DIR, 'scam_data.json')

# 取得模組特定的日誌記錄器
logger = get_service_logger("local_detection")

# 加載詐騙範本資料
def _load_scam_data() -> Dict[str, Any]:
    """
    載入詐騙範本資料，包含範例和關鍵字。
    
    Returns:
        Dict[str, Any]: 詐騙範例和關鍵字數據
    """
    try:
        with open(SCAM_DATA_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"無法載入詐騙範本資料: {str(e)}")
        # 返回預設的最小資料
        return {
            "scam_examples": [],
            "keywords": []
        }

class LocalDetectionStrategy(DetectionStrategy):
    """
    基於本地規則和 agent 的檢測策略。
    """
    def detect(self, text: str) -> dict:
        # 你可以先寫一個假的回傳，之後再串模型邏輯
        print(f"[偵測中] 收到訊息：{text}")
        return {
            "label": "normal",
            "score": 0.1,
            "stage": 1
        }
    
    def __init__(self):
        """初始化本地檢測策略。"""
        # 載入詐騙樣本和關鍵詞資料
        self.data = _load_scam_data()
        self.keywords = self.data.get("keywords", [])
        
        logger.info(f"載入了 {len(self.keywords)} 個關鍵詞")
        
        # 初始化詐騙檢測 agent
        self.agent = create_agent(agent_type="scam_detection")
        logger.info("本地檢測策略初始化完成，已載入詐騙檢測 agent")
    
    def _keyword_analysis(self, message_text: str) -> Dict[str, Any]:
        """
        基於關鍵詞分析訊息，檢查詐騙指標。
        
        Args:
            message_text: 要分析的文字
            
        Returns:
            Dict: 包含檢測到的關鍵詞和評分的分析結果
        """
        # 計算詐騙關鍵詞的出現次數
        keyword_count = 0
        found_keywords = []
        
        # 檢查每個關鍵詞
        for keyword in self.keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', message_text, re.IGNORECASE):
                keyword_count += 1
                found_keywords.append(keyword)
        
        # 計算關鍵詞密度（關鍵詞數量 / 總字數）
        total_words = len(message_text.split())
        keyword_density = keyword_count / max(total_words, 1)
        
        # 基於關鍵詞密度和數量的風險評估
        risk_score = min(1.0, (keyword_count * 0.1) + (keyword_density * 2))
        
        logger.info(f"關鍵詞分析完成，找到 {keyword_count} 個關鍵詞，風險評分: {risk_score:.2f}")
        
        return {
            "found_keywords": found_keywords,
            "keyword_count": keyword_count,
            "keyword_density": keyword_density,
            "risk_score": risk_score
        }
    
    @with_error_handling(reraise=True)
    def analyze(self, message_text: str, user_id: Optional[str] = None,
                user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        使用本地規則和 agent 分析訊息。
        主要處理看起來像 LINE 匯出格式的文字輸入。

        Args:
            message_text: 要分析的文字 (預期是 LINE 匯出格式)
            user_id: 可選的使用者 ID 作為上下文
            user_profile: 可選的使用者資料

        Returns:
            dict: 包含標籤、可信度和回覆的分析結果
            
        Raises:
            DetectionError: 如果檢測過程中發生錯誤
        """
        logger.info(f"開始分析訊息，用戶ID: {user_id}")
        
        # 檢查輸入
        if not message_text or not isinstance(message_text, str):
            error_msg = "訊息文本必須是非空字串"
            logger.error(error_msg)
            raise DetectionError(error_msg, status_code=400)

        try:
            # 步驟 1: 驗證輸入是否為 LINE 匯出格式
            try:
                validated_text = validate_line_export(message_text)
                logger.debug("LINE 匯出格式驗證通過。")
            except ValidationError as ve:
                logger.warning(f"輸入格式驗證失敗: {str(ve)}")
                raise 

            # 步驟 2: (可選) 基於關鍵詞的快速掃描 
            keyword_result = self._keyword_analysis(validated_text)

            # 步驟 3: 使用 agent 進行深度分析，直接傳遞驗證後的原始文字
            logger.debug("將驗證後的原始文字傳遞給 agent 進行分析。")
            agent_result_list = self.agent(validated_text, user_id) # agent 返回的是列表

            return agent_result_list
        except ValidationError as ve:
            logger.warning(f"輸入格式驗證失敗，向上拋出錯誤: {str(ve)}")
            raise
        except Exception as e:
            error_msg = f"本地檢測過程中發生未預期錯誤: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise DetectionError(error_msg, original_error=e)
