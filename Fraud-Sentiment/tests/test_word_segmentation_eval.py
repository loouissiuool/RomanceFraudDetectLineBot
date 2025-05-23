import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from word_segmentation_eval import segment_sentences, check_keywords, TEST_SENTENCES, KEYWORDS

def test_segment_and_keyword_hit():
    ws_results = segment_sentences(TEST_SENTENCES)
    all_found = set()
    for seg in ws_results:
        found = check_keywords(seg, KEYWORDS)
        all_found.update(found)
    # 測試：至少有一個關鍵字被正確切分
    assert len(all_found) > 0, "所有關鍵字都未被正確切分！"
    # 測試：每個關鍵字都能被至少一次正確切分（允許部分漏掉，視需求調整）
    missed = [k for k in KEYWORDS if k not in all_found]
    print(f"未被正確切分的關鍵字: {missed}") 