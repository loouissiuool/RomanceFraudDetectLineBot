# Scam-Bot 詐騙偵測 LINE Bot

## 專案簡介

Scam-Bot 是一個結合 NLP 詐騙偵測模型與 LINE Bot 的現代化專案，能即時分析用戶訊息、判斷詐騙風險，並給予警示或建議。專案分層明確，易於維護與擴充。

- **主服務**：LINE webhook、訊息處理、詐騙偵測、回覆
- **模型訓練/推論**：獨立於 fraud_sentiment/，主服務僅需載入 models/ 下的模型

---

## 目錄結構

```
scam-bot/
├── app.py                  # 主入口
├── requirements.txt        # 依賴
├── .env.example            # 環境變數範本
├── README.md               # 主說明
│
├── bot/
│   └── webhook.py          # LINE webhook 處理
│
├── clients/
│   ├── line_client.py      # LINE API 客戶端
│   └── analysis_api.py     # 外部分析 API 客戶端
│
├── services/
│   ├── conversation_service.py
│   └── domain/detection/   # 偵測策略（local/api/bert）
│
├── models/
│   └── finetuned_classifier/ # 訓練好的 BERT 模型
│
├── data/
│   ├── scam_data.json
│   └── stage_definitions.json
│
├── utils/
│   ├── logger.py
│   └── error_handler.py
│
├── fraud_sentiment/        # 訓練/微調/推論腳本與資料
│
└── tests/                  # 單元測試
```

---

## 安裝與啟動

1. 安裝依賴
   ```bash
   pip install -r requirements.txt
   ```
2. 複製 `.env.example` 為 `.env` 並填入 LINE 與模型設定
3. 啟動服務
   ```bash
   python app.py
   ```

---

## .env.example 範例

```
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
DETECTION_STRATEGY=bert
BERT_MODEL_PATH=models/finetuned_classifier
ANALYSIS_API_URL=
```

---

## 模型訓練與更換

1. 進入 fraud_sentiment/ 目錄，依 USAGE.md 或 README.md 訓練模型：
   ```bash
   python train_classifier.py
   ```
2. 訓練完成後，將 `finetuned_classifier/` 複製到 `scam-bot/models/` 下。
3. 主服務會自動載入最新模型。

---

## 偵測策略切換

- 編輯 .env：
  - `DETECTION_STRATEGY=local` # 本地規則
  - `DETECTION_STRATEGY=api` # 外部 API
  - `DETECTION_STRATEGY=bert` # BERT 分類器（推薦）
- `BERT_MODEL_PATH` 指向模型資料夾

---

## LINE webhook 串接

- 啟動服務後，/callback 為 webhook endpoint。
- 在 LINE Developers 後台設置 Webhook URL，例如：
  ```
  https://your-server-domain/callback
  ```
- Channel access token/secret 請填入 .env

---

## 訓練/微調/推論（fraud_sentiment/）

- 所有訓練、微調、推論腳本與資料皆在 fraud_sentiment/ 目錄下
- 詳細操作請見 fraud_sentiment/README.md 或 USAGE.md
- 訓練資料格式需包含 `text` 和 `label` 欄位

---

## 測試

- 建議補充 tests/ 下的單元測試腳本
- 可用 pytest 執行

---

## 常見問題

- **模型無法載入**：請確認 models/finetuned_classifier/ 內有完整模型檔案
- **LINE webhook 無回應**：請檢查 .env 設定、LINE Developers 後台 Webhook URL
- **Python/transformers 版本不符**：請依 fraud_sentiment/README.md 建議安裝

---

## 授權

本專案採用 MIT License，詳見 LICENSE 檔案。

---

## 聯絡/協作

如需協作、回報問題或有新功能建議，請於 GitHub 開 issue 或聯絡專案負責人。

```

```
# repo
