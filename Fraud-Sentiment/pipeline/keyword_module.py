from typing import List, Set

class KeywordModule:
    """
    關鍵字標註模組
    """
    def __init__(self, keywords: Set[str]):
        self.keywords = keywords

    def match(self, words: List[str]) -> List[str]:
        """
        回傳斷詞結果中命中的關鍵字
        """
        return [w for w in words if w in self.keywords]