# Fraud-Sentiment

> **重要環境相容性提醒：本專案建議使用 Python 3.10 或 3.11，transformers==4.37.2。請勿使用 Python 3.13 或 transformers 4.51.3 以上版本，否則將出現 API 不相容問題。**

## 專案定位與分工

本倉庫為 [scam-bot](https://github.com/Hina-Lin/scam-bot) 專案的「模型分析與串接」子模組，**專責於金融詐騙對話的中文斷詞、關鍵字標註與理論階段分類模型的微調、推論與批次測試**。  
本倉庫**不包含 API/Linebot 前端與伺服器整合**，僅聚焦於模型本身的訓練、推論與分析，並提供明確的串接介面與資料格式，供主系統（如 scam-bot）呼叫。

---

## 專案目標

- 提供高精度的中文金融詐騙對話斷詞與關鍵字標註模型
- 基於學術理論自動分類詐騙對話階段
- 支援批次資料測試與自動化報告產生
- 明確定義與主系統串接的資料格式與呼叫方式

---

## 主要功能

- **中文斷詞與關鍵字標註**：自動辨識金融詐騙高風險詞彙，支援 BIO 格式資料微調。
- **理論階段分類**：依據詐騙七階段/五階段理論，自動分類對話所屬詐騙流程。
- **批次推論與報告**：可對大量對話資料自動批次分析與分類，產生報告。
- **單元測試**：高覆蓋率 pytest 測試，確保斷詞與關鍵字偵測品質。

---

## 與 scam-bot 的串接關係

- **scam-bot**：負責 LINE Bot 前端、API 伺服器、Webhook、用戶互動
- **Fraud-Sentiment（本倉庫）**：負責模型微調、推論、批次分析，並提供標準化的分析腳本與資料格式
- **串接方式**：主系統將對話資料（JSON 格式）傳遞給本倉庫的推論腳本，取得斷詞、關鍵字標註與理論階段分類結果

---

## 串接資料格式（建議）

主系統應傳遞如下 JSON 給模型分析腳本：

| 欄位名稱        | 型別            | 說明                                   |
| --------------- | --------------- | -------------------------------------- |
| current_message | string          | 使用者此輪傳送的訊息                   |
| chat_history    | list of strings | 此使用者過去的對話紀錄，依序儲存為陣列 |

### 範例 JSON

```json
{
  "current_message": "最近我對投資有點興趣",
  "chat_history": [
    "你好呀！",
    "你平常都做什麼工作？",
    "你看起來很專業欸",
    "我最近對理財有點好奇",
    "最近我對投資有點興趣"
  ]
}
```

---

## 目錄結構

```plaintext
Fraud-Sentiment/
├── pipeline/
│   ├── __init__.py
│   ├── pipeline.py                # 主 pipeline 類別
│   ├── ws_module.py               # 斷詞模組
│   ├── sentiment_module.py        # 情感分析模組
│   ├── classifier_module.py       # 三階段分類模組
│   ├── keyword_module.py          # 關鍵字標註模組
│   ├── stage_rule_module.py       # 規則分類模組
├── tests/                       # 單元測試
│   ├── test_pipeline.py           # pipeline 自動化測試
├── infer_ws.py                  # 單句斷詞與關鍵字標註推論
├── batch_infer.py               # 批次推論與理論階段分類
├── theory_stage_classifier.py   # 理論階段分類模組
├── finetune_ws.py               # 斷詞模型微調腳本
├── word_segmentation_eval.py    # 斷詞評估腳本
├── line_dialog_eval.py          # 模擬對話資料分析腳本
├── finetuned_ws/                # 微調後模型與 tokenizer
├── data/                        # 測試與微調資料
├── requirements.txt             # 依賴管理
├── .gitignore
├── README.md
├── LICENSE
```

---

## Pipeline 架構與說明

### 架構概述

本專案採用模組化 pipeline 設計，將各核心功能串接為一條可擴充、可維護的資料處理流程。每個模組皆可 plug-in 你現有或新訓練的模型，主流程如下：

```
原始對話 → 斷詞 → 關鍵字標註 → 情感分析 → 三階段分類 → 規則分類 → 輸出結果
```

---

### 各模組說明

| 模組名稱           | 功能簡述                                                       |
| ------------------ | -------------------------------------------------------------- |
| `WSModule`         | 中文斷詞，提升關鍵字與情感詞命中率（CKIP BERT 斷詞）           |
| `KeywordModule`    | 比對斷詞結果，標註高風險詐騙詞彙                               |
| `SentimentModule`  | 判斷每句對話的情感極性（正/負/中性），偵測詐騙話術中的情緒操控 |
| `ClassifierModule` | 結合斷詞、關鍵字、情感分數等特徵，判斷對話所處三階段           |
| `StageRuleModule`  | 根據命中關鍵字進行理論階段分類，補強模型盲點                   |

---

### Pipeline 主流程範例

```python
from pipeline.pipeline import FraudDetectionPipeline
from pipeline.ws_module import WSModule
from pipeline.sentiment_module import SentimentModule
from pipeline.classifier_module import ClassifierModule
from pipeline.keyword_module import KeywordModule
from pipeline.stage_rule_module import StageRuleModule

# 初始化各模組
ws = WSModule()
sentiment = SentimentModule()
classifier = ClassifierModule()
keywords = KeywordModule({"匯款", "寶貝", "投資"})
stage_rule = StageRuleModule()

# 建立 pipeline
pipeline = FraudDetectionPipeline(ws, sentiment, classifier, keywords, stage_rule)

# 執行完整流程
text = "寶貝，你現在方便匯款嗎？"
result = pipeline.run(text)
print(result)
```

---

### Pipeline 測試方式

```bash
pytest tests/test_pipeline.py
```

---

### 模組替換與擴充

- 每個模組皆可 plug-in 你現有或新訓練的模型。
- 只需實作對應的 class 並傳入 pipeline，即可無縫替換。
- 例如：可將現有的 BERT 斷詞、finetuned_classifier、theory_stage_classifier 直接納入對應模組。

---

## 安裝與環境建議

- **建議 Python 版本：3.10.x 或 3.11.x**
- 請勿使用 3.13（transformers 及部分依賴尚未完全支援）
- 建議使用 venv 或 conda 建立虛擬環境

```bash
# 建立虛擬環境（以 Python 3.10 為例，請依實際安裝路徑調整）
C:\Users\l7475\AppData\Local\Programs\Python\Python310\python.exe -m venv venv
# 啟動虛擬環境
venv\Scripts\activate
# 升級 pip
python -m pip install --upgrade pip
# 安裝依賴
pip install -r requirements.txt
```

必要套件（部分範例）：

- ckip-transformers>=0.3.2
- transformers==4.37.2
- torch>=2.0.0
- datasets>=2.0.0
- pandas>=1.0.0
- accelerate==0.23.0
- fsspec==2025.3.0

---

## 使用方式

請參考 [USAGE.md](USAGE.md) 取得完整的安裝、訓練、推論、資料格式與常見問題排解流程。

---

## 串接建議

- 建議主系統以 JSON 格式呼叫本倉庫的推論腳本，並解析回傳的標註與分類結果
- 如需 API 介面，請於主系統自行包裝（本倉庫僅提供模型與分析腳本）

---

## 技術與工具

- Python 3.10/3.11
- Hugging Face Transformers 4.37.2
- PyTorch
- pandas
- pytest
- ruff

---

## 注意事項

- **請務必使用 Python 3.10/3.11，transformers==4.37.2。**
- 本倉庫僅聚焦於模型與分析流程，**不包含 API/Linebot 整合**
- 大型模型檔案請勿直接上傳 GitHub，建議使用 git-lfs 或雲端連結

---

## 授權

本專案採用 MIT License，詳見 LICENSE 檔案。

---

如需與 scam-bot 進行串接或有其他協作需求，請參考主倉庫說明或聯絡專案負責人。
