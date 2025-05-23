from typing import List
from ckip_transformers.nlp import CkipWordSegmenter

class WSModule:
    """
    中文斷詞模組，包裝 CKIP BERT 斷詞
    """
    def __init__(self, model_name: str = "bert-base", device: int = -1):
        self.ws_driver = CkipWordSegmenter(model=model_name, device=device)

    def segment(self, text: str) -> List[str]:
        """
        將輸入句子斷詞
        """
        return self.ws_driver([text])[0]