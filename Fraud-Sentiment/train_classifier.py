import time
import uuid
import pandas as pd
from datasets import load_dataset, DatasetDict
from transformers import BertTokenizerFast, BertForSequenceClassification, Trainer, TrainingArguments
import numpy as np
import os
import shutil
for d in os.listdir('.'):
    if d.startswith('results_classifier'):
        try:
            shutil.rmtree(d)
        except Exception as e:
            print(f"無法刪除 {d}: {e}")

LABEL2ID = {
    "安全或初期探索": 0,
    "情感連結強化疑慮": 1,
    "高風險詐騙徵兆": 2
}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}

def preprocess_data(file_path: str):
    df = pd.read_csv(file_path)
    df['label'] = df['label'].map(LABEL2ID)
    return df

def main():
    # 載入資料
    train_df = preprocess_data("data/train.csv")
    test_df = preprocess_data("data/test.csv")
    dataset = DatasetDict({
        "train": load_dataset('csv', data_files='data/train.csv')['train'].map(lambda x: {"label": LABEL2ID[x["label"]]}),
        "test": load_dataset('csv', data_files='data/test.csv')['train'].map(lambda x: {"label": LABEL2ID[x["label"]]})
    })

    tokenizer = BertTokenizerFast.from_pretrained("bert-base-chinese")

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, padding="max_length", max_length=64)

    dataset = dataset.map(tokenize, batched=True)

    model = BertForSequenceClassification.from_pretrained("bert-base-chinese", num_labels=3, id2label=ID2LABEL, label2id=LABEL2ID)

    output_dir = f"results_classifier_{uuid.uuid4().hex}"

    # 主動刪除 output_dir（如果已存在）
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        logging_dir="./logs_classifier",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
    )

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        acc = (preds == labels).mean()
        return {"accuracy": acc}

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        compute_metrics=compute_metrics,
        tokenizer=tokenizer,
    )

    trainer.train()
    trainer.save_model("finetuned_classifier")
    tokenizer.save_pretrained("finetuned_classifier")

if __name__ == "__main__":
    main()