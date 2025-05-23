import logging
import os
from typing import List, Set, Dict

from ckip_transformers.nlp import CkipWordSegmenter

# 設定 logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 測試句子與關鍵字（可改為讀取 data/ 目錄下檔案）
TEST_SENTENCES: List[str] = [
    "寶貝，你現在方便匯款嗎？這是我的帳戶，金額是5000元，拜託快點，因為很急！",
    "我想你了，你在哪？最近有在投資虛擬貨幣嗎？聽說穩賺不賠喔。",
    "請將款項轉帳到我的帳戶，這筆投資保證穩賺不賠。",
    "很急，現在馬上需要你幫我匯款！",
    "你單身嗎？做什麼工作？",
    "我只信你，除了你我沒別人了。"
]

KEYWORDS: Set[str] = {
    "匯款", "帳戶", "金額", "投資", "虛擬貨幣", "穩賺不賠", "寶貝", "很急", "快點", "轉帳", "款項", "單身", "我只信你"
}

def segment_sentences(sentences: List[str]) -> List[List[str]]:
    """使用 CKIP 斷詞模型對句子列表進行斷詞。"""
    ws_driver = CkipWordSegmenter(model="bert-base", device=-1)
    return ws_driver(sentences)

def check_keywords(segmented: List[str], keywords: Set[str]) -> Set[str]:
    """比對斷詞結果中出現的關鍵字。"""
    return {word for word in segmented if word in keywords}

def evaluate_model(sentences: List[str], keywords: Set[str]) -> Dict[str, int]:
    """自動化斷詞與關鍵字比對，並統計命中情況。"""
    ws_results = segment_sentences(sentences)
    keyword_hits: Dict[str, int] = {k: 0 for k in keywords}
    for idx, (sentence, seg) in enumerate(zip(sentences, ws_results)):
        found = check_keywords(seg, keywords)
        logging.info(f"原句{idx+1}: {sentence}")
        logging.info(f"斷詞: {seg}")
        logging.info(f"命中關鍵字: {found}")
        for k in found:
            keyword_hits[k] += 1
    return keyword_hits

def print_report(keyword_hits: Dict[str, int], total: int) -> None:
    """輸出命中統計與建議。"""
    print("\n=== 關鍵字命中統計 ===")
    for k, v in keyword_hits.items():
        print(f"{k}: {v}/{total}")
    missed = [k for k, v in keyword_hits.items() if v == 0]
    print("\n=== 建議 ===")
    if len(missed) == 0:
        print("所有關鍵字皆可被正確切分，模型可直接用於金融詐騙斷詞。")
    else:
        print(f"以下關鍵字未被正確切分：{missed}，建議進行模型微調或加強規則修正。")

def save_report(keyword_hits: Dict[str, int], total: int, filename: str = "results/segmentation_report.txt") -> None:
    """將命中統計與建議寫入文字檔。"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write("=== 關鍵字命中統計 ===\n")
        for k, v in keyword_hits.items():
            f.write(f"{k}: {v}/{total}\n")
        missed = [k for k, v in keyword_hits.items() if v == 0]
        f.write("\n=== 建議 ===\n")
        if len(missed) == 0:
            f.write("所有關鍵字皆可被正確切分，模型可直接用於金融詐騙斷詞。\n")
        else:
            f.write(f"以下關鍵字未被正確切分：{missed}，建議進行模型微調或加強規則修正。\n")

if __name__ == "__main__":
    hits = evaluate_model(TEST_SENTENCES, KEYWORDS)
    print_report(hits, len(TEST_SENTENCES))
    save_report(hits, len(TEST_SENTENCES))
