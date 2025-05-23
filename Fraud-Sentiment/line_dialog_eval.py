import logging
from typing import List, Set, Dict
from pathlib import Path
from ckip_transformers.nlp import CkipWordSegmenter
import re
from theory_stage_classifier import classify_stage

# 關鍵字清單
KEYWORDS: Set[str] = {
    "匯款", "帳戶", "金額", "投資", "虛擬貨幣", "穩賺不賠", "寶貝", "很急", "快點", "轉帳", "款項", "單身", "我只信你"
}

# 對話檔案路徑
DIALOG_FILES = [
    Path(r"c:/Users/l7475/Downloads/[LINE]簡單版對話.txt"),
    Path(r"c:/Users/l7475/Downloads/[LINE]複雜版對話 .txt")
]

def extract_dialog_lines(filepath: Path) -> List[str]:
    """讀取 txt 對話檔案，僅保留用戶訊息內容。"""
    lines = []
    with filepath.open(encoding="utf-8") as f:
        for line in f:
            # 跳過空行與日期行
            if not line.strip() or re.match(r"^\d{4}/\d{2}/\d{2}", line):
                continue
            # 只取冒號後的訊息內容
            if ":" in line:
                msg = line.split(" ", 1)[-1]
                if "\t" in msg:
                    msg = msg.split("\t", 1)[-1]
                if " " in msg:
                    msg = msg.split(" ", 1)[-1]
                msg = msg.strip()
                if msg:
                    lines.append(msg)
    return lines

def segment_sentences(sentences: List[str]) -> List[List[str]]:
    ws_driver = CkipWordSegmenter(model="bert-base", device=-1)
    return ws_driver(sentences)

def check_keywords(segmented: List[str], keywords: Set[str]) -> Set[str]:
    return {word for word in segmented if word in keywords}

def evaluate_dialogs(dialog_files: List[Path], keywords: Set[str]) -> Dict[str, int]:
    all_lines = []
    for file in dialog_files:
        all_lines.extend(extract_dialog_lines(file))
    ws_results = segment_sentences(all_lines)
    keyword_hits: Dict[str, int] = {k: 0 for k in keywords}
    stage_stats: Dict[str, int] = {}
    for seg in ws_results:
        found = check_keywords(seg, keywords)
        for k in found:
            keyword_hits[k] += 1
        # 新增：判斷詐騙階段
        stage = classify_stage(found)
        if stage:
            stage_stats[stage] = stage_stats.get(stage, 0) + 1
    return keyword_hits, stage_stats, len(ws_results)

def print_report(keyword_hits: Dict[str, int], stage_stats: Dict[str, int], total: int) -> None:
    print("\n=== LINE 對話資料關鍵字命中統計 ===")
    for k, v in keyword_hits.items():
        print(f"{k}: {v}/{total}")
    missed = [k for k, v in keyword_hits.items() if v == 0]
    print("\n=== 階段分布統計（理論依據） ===")
    for stage, count in stage_stats.items():
        print(f"{stage}: {count} 則訊息")
    print("\n=== 建議 ===")
    if len(missed) == 0:
        print("所有關鍵字皆可被正確切分，模型可直接用於真實 LINE 對話斷詞與階段判斷。")
    else:
        print(f"以下關鍵字未被正確切分：{missed}，建議進行模型微調或加強規則修正。")

if __name__ == "__main__":
    hits, stage_stats, total = evaluate_dialogs(DIALOG_FILES, KEYWORDS)
    print_report(hits, stage_stats, total) 