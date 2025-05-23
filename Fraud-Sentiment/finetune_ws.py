"""
BERT 中文斷詞模型微調腳本
- 讀取 BIO 格式資料
- 使用 transformers 進行 token classification 微調
- 適用於金融詐騙關鍵字強化
"""
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from transformers import BertTokenizerFast, BertForTokenClassification, Trainer, TrainingArguments
from datasets import Dataset
import argparse
import yaml

def read_bio_data(filepath: Path) -> Tuple[List[List[str]], List[List[str]]]:
    """讀取 BIO 格式資料，回傳字元序列與標籤序列。

    Args:
        filepath (Path): 資料檔案路徑
    Returns:
        Tuple[List[List[str]], List[List[str]]]: (字元序列, 標籤序列)
    """
    sentences, labels = [], []
    with filepath.open(encoding="utf-8") as f:
        chars, tags = [], []
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                if chars:
                    sentences.append(chars)
                    labels.append(tags)
                    chars, tags = [], []
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            c, t = parts
            chars.append(c)
            tags.append(t)
        if chars:
            sentences.append(chars)
            labels.append(tags)
    return sentences, labels

def bio_to_ids(labels: List[List[str]], label2id: Dict[str, int]) -> List[List[int]]:
    """將 BIO 標籤轉為 id。

    Args:
        labels (List[List[str]]): 標籤序列
        label2id (dict): 標籤到 id 的映射
    Returns:
        List[List[int]]: id 序列
    """
    return [[label2id[tag] for tag in seq] for seq in labels]

def load_config(config_path: Optional[str]) -> Dict[str, Any]:
    """讀取 YAML 設定檔，若無則回傳空 dict。

    Args:
        config_path (Optional[str]): 設定檔路徑
    Returns:
        dict: 設定內容
    """
    if config_path is None:
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def enforce_types(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """強制將訓練參數轉為正確型別。"""
    # 只轉換已知參數，避免 KeyError
    if "learning_rate" in cfg:
        cfg["learning_rate"] = float(cfg["learning_rate"])
    if "num_train_epochs" in cfg:
        cfg["num_train_epochs"] = float(cfg["num_train_epochs"])
    if "per_device_train_batch_size" in cfg:
        cfg["per_device_train_batch_size"] = int(cfg["per_device_train_batch_size"])
    if "per_device_eval_batch_size" in cfg:
        cfg["per_device_eval_batch_size"] = int(cfg["per_device_eval_batch_size"])
    if "weight_decay" in cfg:
        cfg["weight_decay"] = float(cfg["weight_decay"])
    if "logging_steps" in cfg:
        cfg["logging_steps"] = int(cfg["logging_steps"])
    if "save_steps" in cfg:
        cfg["save_steps"] = int(cfg["save_steps"])
    if "seed" in cfg:
        cfg["seed"] = int(cfg["seed"])
    return cfg

def main() -> None:
    """主程式：執行斷詞模型微調。"""
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default=None, help="YAML 設定檔路徑")
    args = parser.parse_args()

    # 預設參數
    default_cfg = {
        "data_path": "data/ws_finetune_sample.txt",
        "pretrained_model_path": "ckiplab/bert-base-chinese-ws",
        "output_dir": "finetuned_ws",
        "num_train_epochs": 10,
        "per_device_train_batch_size": 4,
        "per_device_eval_batch_size": 16,
        "learning_rate": 5e-5,
        "weight_decay": 0.0,
        "logging_steps": 5,
        "save_steps": 200,
        "save_strategy": "epoch",
        "evaluation_strategy": "steps",
        "report_to": [],
        "disable_tqdm": False,
        "seed": 42
    }
    # 讀取 YAML 設定檔
    user_cfg = load_config(args.config)
    cfg = {**default_cfg, **(user_cfg or {})}
    cfg = enforce_types(cfg)

    data_path = Path(cfg["data_path"])
    sentences, tags = read_bio_data(data_path)
    label_list = sorted({t for seq in tags for t in seq})
    label2id = {l: i for i, l in enumerate(label_list)}
    id2label = {i: l for l, i in label2id.items()}
    tokenizer = BertTokenizerFast.from_pretrained("bert-base-chinese")
    model = BertForTokenClassification.from_pretrained(
        cfg["pretrained_model_path"],
        num_labels=len(label_list),
        id2label=id2label,
        label2id=label2id,
        ignore_mismatched_sizes=True
    )
    # 編碼資料
    encodings = tokenizer(["".join(seq) for seq in sentences], is_split_into_words=False, return_offsets_mapping=True, padding=True, truncation=True)
    # labels 對齊 tokenizer word_ids
    aligned_labels = []
    for i, seq in enumerate(sentences):
        encoding = tokenizer("".join(seq), return_offsets_mapping=True)
        offsets = encoding["offset_mapping"]
        label_ids = []
        label_seq = tags[i]
        char_idx = 0
        for offset in offsets:
            if offset == (0, 0):  # special token
                label_ids.append(-100)
            else:
                if char_idx < len(label_seq):
                    label_ids.append(label2id[label_seq[char_idx]])
                else:
                    label_ids.append(-100)
                char_idx += 1
        aligned_labels.append(label_ids)
    # padding labels
    max_len = max(len(e) for e in encodings["input_ids"])
    for i in range(len(aligned_labels)):
        aligned_labels[i] = aligned_labels[i] + [-100] * (max_len - len(aligned_labels[i]))
    dataset = Dataset.from_dict({
        "input_ids": encodings["input_ids"],
        "attention_mask": encodings["attention_mask"],
        "labels": aligned_labels
    })
    # 微調參數
    training_args = TrainingArguments(
        output_dir=cfg["output_dir"],
        per_device_train_batch_size=cfg["per_device_train_batch_size"],
        per_device_eval_batch_size=cfg["per_device_eval_batch_size"],
        num_train_epochs=cfg["num_train_epochs"],
        learning_rate=cfg["learning_rate"],
        weight_decay=cfg["weight_decay"],
        logging_steps=cfg["logging_steps"],
        save_steps=cfg["save_steps"],
        save_strategy=cfg["save_strategy"],
        evaluation_strategy=cfg["evaluation_strategy"],
        report_to=cfg["report_to"],
        disable_tqdm=cfg["disable_tqdm"],
        seed=cfg["seed"]
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer
    )
    trainer.train()
    trainer.save_model(cfg["output_dir"])
    logging.info(f"微調完成，模型已儲存於 {cfg['output_dir']}/")

if __name__ == "__main__":
    main()