from typing import Any, Dict, Optional, List
from .ws_module import WSModule
from .sentiment_module import SentimentModule
from .classifier_module import ClassifierModule
from .keyword_module import KeywordModule
from .stage_rule_module import StageRuleModule

class FraudDetectionPipeline:
    """
    金融詐騙情感分析主流程
    """
    def __init__(
        self,
        ws_module: WSModule,
        sentiment_module: SentimentModule,
        classifier_module: ClassifierModule,
        keyword_module: KeywordModule,
        stage_rule_module: StageRuleModule
    ):
        self.ws_module = ws_module
        self.sentiment_module = sentiment_module
        self.classifier_module = classifier_module
        self.keyword_module = keyword_module
        self.stage_rule_module = stage_rule_module

    def run(self, text: str, chat_history: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        執行完整詐騙偵測流程
        """
        words = self.ws_module.segment(text)
        keywords = self.keyword_module.match(words)
        sentiment = self.sentiment_module.predict(text)
        stage = self.classifier_module.predict(text, keywords, sentiment, chat_history)
        rule_stage = self.stage_rule_module.classify(keywords)
        return {
            "斷詞": words,
            "關鍵字": keywords,
            "情感": sentiment,
            "三階段分類": stage,
            "規則分類": rule_stage
        }