"""
API 檢測策略

此模組實現了基於外部 API 的詐騙檢測策略。
"""

from .base import DetectionStrategy
from utils.logger import get_service_logger
from utils.error_handler import DetectionError, with_error_handling

# 取得模組特定的日誌記錄器
logger = get_service_logger("api_detection")

class ApiDetectionStrategy(DetectionStrategy):
    """使用外部 API 的檢測策略"""
    
    def __init__(self, analysis_client):
        """
        初始化 API 檢測策略。
        
        Args:
            analysis_client: 外部分析 API 客戶端
        """
        self.analysis_client = analysis_client
    
    @with_error_handling(reraise=True)
    def analyze(self, message_text, user_id=None, user_profile=None):
        """
        使用外部 API 分析訊息。

        Args:
            message_text: 要分析的文字
            user_id: 可選的使用者 ID 作為上下文
            user_profile: 可選的使用者資料

        Returns:
            dict: 包含標籤、可信度和回覆的分析結果
            
        Raises:
            DetectionError: 如果檢測過程中發生錯誤
        """
        logger.info("使用外部 API 檢測策略")
        
        # 檢查輸入
        if not message_text or not isinstance(message_text, str):
            error_msg = "訊息文本必須是非空字串"
            logger.error(error_msg)
            raise DetectionError(error_msg, status_code=400)
        
        # 準備 API 的數據
        analysis_data = {
            "user_id": user_id,
            "message": message_text,
            "user_profile": user_profile
        }

        try:
            # 呼叫外部 API
            return self.analysis_client.analyze_text(analysis_data)
        except Exception as e:
            error_msg = f"API 檢測過程中發生錯誤: {str(e)}"
            logger.error(error_msg)
            raise DetectionError(error_msg, original_error=e)
