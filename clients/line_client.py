# repo-main/clients/line_client.py

import os
import logging
import requests # 新增導入 requests
from linebot import LineBotApi
from linebot.models import (
    TextSendMessage,
    FlexSendMessage,
    QuickReply, QuickReplyButton, MessageAction
)
from config import Config # 導入 Config 以獲取 LINE Token
from utils.error_handler import LineClientError # 導入自定義錯誤

# 獲取日誌記錄器
logger = logging.getLogger(__name__)

# 定義 Quick Reply 按鈕 (全局可用)
COMMON_QR = QuickReply(items=[
    QuickReplyButton(action=MessageAction(label="Use OpenAI", text="Use OpenAI")),
    QuickReplyButton(action=MessageAction(label="Use Gemini", text="Use Gemini")),
    QuickReplyButton(action=MessageAction(label="Next Detection", text="Next Detection")),
    QuickReplyButton(action=MessageAction(label="Chat more", text="Chat more")),
])

class LineClient:
    """
    負責與 LINE Messaging API 互動的客戶端。
    """
    def __init__(self, channel_access_token: str):
        if not channel_access_token:
            raise LineClientError("CHANNEL_ACCESS_TOKEN isn't set。") # 修改為 CHANNEL_ACCESS_TOKEN
        self.line_bot_api = LineBotApi(channel_access_token)
        logger.info("LineClient initialized successfully。")

    def reply_text(self, reply_token: str, text: str):
        """
        回覆純文字訊息給 LINE 用戶。
        """
        try:
            msg = TextSendMessage(text=text, quick_reply=COMMON_QR)
            self.line_bot_api.reply_message(reply_token, msg)
            logger.info(f"Successfully replied to text message: '{text[:30]}...'")
        except Exception as e:
            logger.error(f"Failed to reply to text message: {e}", exc_info=True)
            raise LineClientError(f"Failed to reply to text message", original_error=e)

    def reply_flex(self, reply_token: str, flex_message_object: FlexSendMessage):
        """
        回覆 Flex Message 給 LINE 用戶。
        """
        try:
            self.line_bot_api.reply_message(reply_token, flex_message_object)
            logger.info(f"Successfully replied to Flex Message: '{flex_message_object.alt_text}'")
        except Exception as e:
            logger.error(f"Failed to replied to Flex Message 失敗: {e}", exc_info=True)
            raise LineClientError(f"Faield to replied to Flex Message ", original_error=e)

    def get_user_profile(self, user_id: str) -> dict:
        """
        從 LINE 獲取用戶的公開資料。
        """
        try:
            url = f"https://api.line.me/v2/bot/profile/{user_id}"
            headers = {
                "Authorization": f"Bearer {Config.LINE_CHANNEL_ACCESS_TOKEN}"
            }
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                logger.debug(f"Successfully obtained the information of user {user_id}")
                return res.json()
            else:
                logger.warning(f"Failed to obtain user {user_id} information, status code: {res.status_code}, content: {res.text}")
        except Exception as e:
            logger.error(f"[get_user_profile error]: {e}", exc_info=True)
        return {}