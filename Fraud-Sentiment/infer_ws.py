from transformers import BertTokenizerFast, BertForTokenClassification
import torch
from typing import List
import numpy as np

# 測試句子
TEST_SENTENCES = [
    "寶貝，你現在方便匯款嗎？這是我的帳戶，金額是5000元，拜託快點，因為很急！",
    "我想你了，你在哪？最近有在投資虛擬貨幣嗎？聽說穩賺不賠喔。",
    "請將款項轉帳到我的帳戶，這筆投資保證穩賺不賠。",
    "很急，現在馬上需要你幫我匯款！",
    "你單身嗎？做什麼工作？",
    "我只信你，除了你我沒別人了。"
]

LABELS = ["B-KEYWORD", "I-KEYWORD", "O"]

# 載入微調後模型
model = BertForTokenClassification.from_pretrained("finetuned_ws")
tokenizer = BertTokenizerFast.from_pretrained("bert-base-chinese")
model.eval()

def predict(sentence: str) -> List[str]:
    tokens = tokenizer(sentence, return_tensors="pt", return_offsets_mapping=True, truncation=True)
    with torch.no_grad():
        outputs = model(**{k: v for k, v in tokens.items() if k in ["input_ids", "attention_mask"]})
        logits = outputs.logits
        preds = torch.argmax(logits, dim=-1).squeeze().tolist()
    offset_mapping = tokens["offset_mapping"].squeeze().tolist()
    # 將 BIO 標籤對齊原始字元
    result = []
    for idx, (start, end) in enumerate(offset_mapping):
        if start == 0 and end == 0:
            continue  # special token
        label = LABELS[preds[idx]] if preds[idx] < len(LABELS) else "O"
        word = sentence[start:end]
        result.append(f"{word}({label})")
    return result

if __name__ == "__main__":
    for sent in TEST_SENTENCES:
        print(f"原句: {sent}")
        print("斷詞預測:", " ".join(predict(sent)))
        print("-" * 40) 