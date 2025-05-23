from typing import List
from theory_stage_classifier import classify_stage

class StageRuleModule:
    """
    規則分類模組，包裝你現有的理論階段分類
    """
    def classify(self, keywords: List[str]) -> str:
        """
        回傳理論階段分類標籤
        """
        return classify_stage(set(keywords))