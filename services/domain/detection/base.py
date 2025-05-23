from abc import ABC, abstractmethod

class DetectionStrategy(ABC):
    @abstractmethod
    def detect(self, text: str) -> dict:
        """
        分析輸入文字，回傳包含標籤與風險分數的 dict 結果
        """
        pass