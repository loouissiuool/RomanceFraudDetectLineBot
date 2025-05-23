"""
儲存服務 - 基礎設施服務層(棄用)

此服務負責儲存和檢索聊天歷史。
當前實現使用記憶體儲存，但未來可以擴展為使用
資料庫或檔案儲存。
"""

from utils.logger import get_service_logger

# 取得模組特定的日誌記錄器
logger = get_service_logger("storage")

# === 主要入口點 ===
class StorageService:
    """管理對話儲存的服務，目前實現記憶體儲存"""
    
    def __init__(self):
        """初始化儲存服務，建立空的聊天歷史。"""
        self.chat_history = {}  # user_id -> 訊息列表
    
    def add_message(self, user_id, message):
        """
        將訊息添加到使用者的聊天歷史中。
        
        Args:
            user_id: 使用者的 ID
            message: 要儲存的訊息文字
            
        Returns:
            None
        """
        if user_id not in self.chat_history:
            self.chat_history[user_id] = []
            
        self.chat_history[user_id].append(message)
        logger.info(f"已儲存使用者 {user_id} 的訊息")
        
        # 限制歷史大小以防止記憶體問題
        if len(self.chat_history[user_id]) > 100:  # 只保留最後 100 條訊息
            self.chat_history[user_id] = self.chat_history[user_id][-100:]
            logger.info(f"裁剪使用者 {user_id} 的歷史記錄（保留最後 100 條）")
    
    def get_chat_history(self, user_id, limit=None):
        """
        獲取使用者的聊天歷史。
        
        Args:
            user_id: 使用者的 ID
            limit: 可選的返回訊息的最大數量
            
        Returns:
            list: 使用者的聊天歷史作為訊息列表
        """
        if user_id not in self.chat_history:
            logger.info(f"使用者 {user_id} 沒有聊天歷史")
            return []
            
        history = self.chat_history[user_id]
        
        if limit is not None and limit > 0:
            history = history[-limit:]
            
        logger.info(f"檢索使用者 {user_id} 的聊天歷史（{len(history)} 條訊息）")
        return history
    
    def clear_history(self, user_id):
        """
        清除使用者的聊天歷史。
        
        Args:
            user_id: 使用者的 ID
            
        Returns:
            None
        """
        if user_id in self.chat_history:
            self.chat_history[user_id] = []
            logger.info(f"已清除使用者 {user_id} 的聊天歷史")
