from typing import Dict
from transformers import BertTokenizer, BertForSequenceClassification
import torch

class SentimentModule:
    """
    中文情感分析模組，預設用 IDEA-CCNL/Erlangshen-Roberta-330M-Sentiment
    """
    def __init__(self, model_name: str = 'IDEA-CCNL/Erlangshen-Roberta-330M-Sentiment'):
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.model = BertForSequenceClassification.from_pretrained(model_name)
        self.model.eval()

    def predict(self, text: str) -> Dict[str, float]:
        """
        回傳情感分數（positive/negative）
        """
        inputs = self.tokenizer(text, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1).squeeze().tolist()
        return {"negative": probs[0], "positive": probs[1]}