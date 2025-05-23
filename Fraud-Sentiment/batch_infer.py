from transformers import BertTokenizerFast, BertForTokenClassification
import torch
from pathlib import Path
from theory_stage_classifier import classify_stage
from typing import List

LABELS = ["B-KEYWORD", "I-KEYWORD", "O"]
MODEL_DIR = "finetuned_ws"

model = BertForTokenClassification.from_pretrained(MODEL_DIR)
tokenizer = BertTokenizerFast.from_pretrained("bert-base-chinese")
model.eval()

def predict(sentence: str) -> List[str]:
    tokens = tokenizer(sentence, return_tensors="pt", return_offsets_mapping=True, truncation=True)
    with torch.no_grad():
        outputs = model(**{k: v for k, v in tokens.items() if k in ["input_ids", "attention_mask"]})
        logits = outputs.logits
        preds = torch.argmax(logits, dim=-1).squeeze().tolist()
    offset_mapping = tokens["offset_mapping"].squeeze().tolist()
    result = []
    for idx, (start, end) in enumerate(offset_mapping):
        if start == 0 and end == 0:
            continue
        label = LABELS[preds[idx]] if preds[idx] < len(LABELS) else "O"
        word = sentence[start:end]
        result.append((word, label))
    return result

def batch_infer(input_path: Path, output_path: Path):
    with input_path.open(encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    with output_path.open("w", encoding="utf-8") as out:
        for i, line in enumerate(lines):
            pred = predict(line)
            keywords = {w for w, l in pred if l.startswith("B") or l.startswith("I")}
            stage = classify_stage(keywords)
            out.write(f"[{i+1}] 原句: {line}\n")
            out.write("斷詞標註: " + " ".join([f"{w}({l})" for w, l in pred]) + "\n")
            out.write(f"理論階段分類: {stage}\n")
            out.write("-" * 40 + "\n")
            # 同時也 print 到終端
            print(f"[{i+1}] 原句: {line}")
            print("斷詞標註:", " ".join([f"{w}({l})" for w, l in pred]))
            print(f"理論階段分類: {stage}")
            print("-" * 40)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="輸入檔案路徑")
    parser.add_argument("--output", type=str, required=True, help="輸出檔案路徑")
    args = parser.parse_args()

    batch_infer(Path(args.input), Path(args.output))