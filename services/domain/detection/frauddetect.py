"""
FraudSentimentDetectionStrategy

將 BERT 詐騙分類器（finetuned_classifier）包裝成服務策略，供 DetectionService 調用。
"""

from typing import Dict, Any, Optional
from transformers import BertTokenizerFast, BertForSequenceClassification
import torch
import os
from utils.logger import get_service_logger
from utils.error_handler import DetectionError, with_error_handling
from .base import DetectionStrategy

LABELS = ["安全或初期探索", "情感連結強化疑慮", "高風險詐騙徵兆"]

logger = get_service_logger("fraud_sentiment_detection")

class FraudSentimentDetectionStrategy:
    """
    使用 BERT 詐騙分類器進行訊息分類。
    """
    def __init__(self, model_path: Optional[str] = None):
        """
        Args:
            model_path: finetuned_classifier 的資料夾路徑
        """
        self.model_path = model_path or os.getenv("BERT_MODEL_PATH", "models/finetuned_classifier")
        logger.info(f"載入 BERT 模型與 tokenizer，路徑: {self.model_path}")
        try:
            self.tokenizer = BertTokenizerFast.from_pretrained(self.model_path)
            self.model = BertForSequenceClassification.from_pretrained(self.model_path)
            self.model.eval()
        except Exception as e:
            logger.error(f"載入 BERT 模型失敗: {str(e)}")
            raise DetectionError(f"BERT 模型載入失敗: {str(e)}")

    @with_error_handling(reraise=True)
    def analyze(self, message_text: str, user_id: Optional[str] = None, user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        使用 BERT 模型分析訊息。
        Args:
            message_text: 要分析的文字
            user_id: 可選，使用者 ID
            user_profile: 可選，使用者資料
        Returns:
            dict: 包含 label、confidence、reply
        """
        logger.info(f"BERT 分析訊息: {message_text[:30]}...")
        try:
            inputs = self.tokenizer(message_text, return_tensors="pt", truncation=True, padding=True, max_length=64)
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                pred = torch.argmax(logits, dim=1).item()
                confidence = torch.softmax(logits, dim=1)[0, pred].item()
            label = LABELS[pred]
            reply = self._generate_reply(label, confidence)
            return {
                "label": label,
                "confidence": confidence,
                "reply": reply
            }
        except Exception as e:
            logger.error(f"BERT 分析失敗: {str(e)}")
            raise DetectionError(f"BERT 分析失敗: {str(e)}")

    def _generate_reply(self, label: str, confidence: float) -> str:
        """
        根據分類結果產生回覆。
        """
        if label == "高風險詐騙徵兆":
            return f"⚠️ 警告：此訊息疑似詐騙（信心值 {confidence:.2f}）。請提高警覺！"
        elif label == "情感連結強化疑慮":
            return f"❗ 注意：此訊息有潛在風險（信心值 {confidence:.2f}）。請小心求證。"
        else:
            return f"✅ 此訊息暫無明顯詐騙徵兆（信心值 {confidence:.2f}）。"