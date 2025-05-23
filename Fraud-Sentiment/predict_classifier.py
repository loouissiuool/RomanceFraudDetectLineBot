from transformers import BertTokenizerFast, BertForSequenceClassification
import torch
import sys

LABELS = ["安全或初期探索", "情感連結強化疑慮", "高風險詐騙徵兆"]

def predict(text: str):
    tokenizer = BertTokenizerFast.from_pretrained("finetuned_classifier")
    model = BertForSequenceClassification.from_pretrained("finetuned_classifier")
    model.eval()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=64)
    with torch.no_grad():
        outputs = model(**inputs)
        pred = torch.argmax(outputs.logits, dim=1).item()
    return LABELS[pred]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("請輸入要分類的對話內容")
        sys.exit(1)
    text = sys.argv[1]
    label = predict(text)
    print(f"分類結果：{label}")