from typing import Any, List, Dict, Optional
from transformers import BertTokenizer, BertForSequenceClassification
import torch

class ClassifierModule:
    """
    三階段分類模組，包裝你現有的 BERT/transformer 分類器
    """
    def __init__(self, model_dir: str = "finetuned_classifier"):
        self.tokenizer = BertTokenizer.from_pretrained("bert-base-chinese")
        self.model = BertForSequenceClassification.from_pretrained(model_dir)
        self.model.eval()

    def predict(self, text: str, keywords: List[str], sentiment: Dict[str, float], chat_history: Optional[List[str]]) -> str:
        """
        回傳三階段分類標籤
        """
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=64)
        with torch.no_grad():
            outputs = self.model(**inputs)
            pred = torch.argmax(outputs.logits, dim=-1).item()
        # 你現有的 label 對應
        id2label = {0: "安全或初期探索", 1: "情感連結強化疑慮", 2: "高風險詐騙徵兆"}
        return id2label.get(pred, "未知")