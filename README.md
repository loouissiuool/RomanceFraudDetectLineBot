# Scam-Bot 詐騙偵測 LINE Bot

![LINE Bot](https://img.shields.io/badge/LINE-Bot-00C300?style=for-the-badge&logo=line&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Framework-black?style=for-the-badge&logo=flask&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-API-424242?style=for-the-badge&logo=openai&logoColor=white)
![Transformers](https://img.shields.io/badge/HuggingFace-Transformers-FFDD00?style=for-the-badge&logo=huggingface&logoColor=black)

## 專案簡介 (Project Introduction)

Scam-Bot 是一個結合 **NLP 詐騙偵測模型**與 **LINE Bot** 的現代化專案，旨在提供即時的詐騙風險分析和警示。它能夠分析用戶透過 LINE 發送的訊息，判斷潛在的詐騙階段和風險等級，並提供相應的建議和防範措施。專案採用清晰的分層架構，便於未來的維護與功能擴展。

* **主服務**: 負責處理 LINE Webhook 事件、訊息處理流程、詐騙偵測邏輯以及用戶回覆的生成。
* **模型訓練/推論**: 獨立於 `fraud_sentiment/` 目錄。主服務僅需載入 `models/` 目錄下的預訓練或微調好的模型進行推論。

## ✨ 特性 (Features)

* **LINE Messaging API 整合**: 無縫接收並處理來自 LINE 用戶的訊息，並實現雙向互動。
* **多源詐騙偵測策略**:
    * **本地規則偵測**: 快速基於預設的關鍵字和正則表達式進行基礎判斷。
    * **OpenAI LLM 深度分析 (已整合)**: 利用先進的 AI 模型對複雜語句進行詐騙階段判斷和標籤分類，提供更精準的分析結果。
    * **BERT 分類器推論 (支援擴充)**: 支援載入訓練好的 BERT 模型進行高效的文本分類推論。
* **豐富的 Flex Message 回覆**: 以互動性強、視覺效果佳的 LINE Flex Message 卡片形式展示分析結果、建議行動和相關防範資訊。
* **環境變數配置**: 通過 `.env` 文件靈活配置 LINE Bot、OpenAI API 憑證和偵測策略，提高安全性與易用性。
* **獨立模型訓練模組**: `fraud_sentiment/` 包含了用於模型訓練、微調和推論的獨立腳本和資料，便於模型的迭代和管理。
* **日誌記錄**: 詳盡的日誌輸出，方便開發者追蹤和調試應用程式行為。

## 📁 目錄結構 (Project Structure)

專案的根目錄為 `line-scam-detection-bot/` (或你本地的 `repo-main/`)，其內部結構如下：
line-scam-detection-bot/
├── app.py                      # 主應用程式入口 (Flask app)
├── requirements.txt            # Python 專案依賴列表
├── .env.example                # 環境變數範本 (請複製為 .env)
├── README.md                   # 專案主說明文件
│
├── bot/
│   └── line_webhook.py         # LINE Webhook 事件處理邏輯
│
├── clients/
│   ├── line_client.py          # 封裝 LINE Messaging API 呼叫的客戶端
│   └── analysis_api.py         # 外部分析服務（如 BERT 推論服務）的 API 客戶端（如果 BERT 模型獨立部署為 API）
│
├── services/
│   ├── conversation_service.py # 處理用戶對話邏輯，協調各服務
│   └── domain/
│       └── detection/          # 偵測策略模組
│           ├── init.py     # Python 包的必要文件
│           └── detection_service.py # 核心偵測邏輯（本地規則、LLM、BERT）
│
├── models/
│   └── finetuned_classifier/   # 存放訓練好的 BERT 模型檔案
│       ├── config.json
│       ├── pytorch_model.bin
│       └── ... (其他模型相關檔案)
│
├── data/
│   ├── scam_data.json          # 詐騙相關數據，可能用於本地規則或模型訓練
│   └── stage_definitions.json  # 詐騙階段定義和建議
│
├── utils/
│   ├── init.py             # Python 包的必要文件
│   ├── logger.py               # 日誌配置工具
│   └── error_handler.py        # 自定義錯誤處理類別
│
├── fraud_sentiment/            # 獨立的模型訓練、微調與推論腳本和相關資料
│   ├── train_classifier.py
│   ├── USAGE.md / README.md    # fraud_sentiment 模組的詳細使用說明
│   └── ... (其他訓練相關檔案)
│
└── tests/                      # 專案的單元測試腳本
└── ...




## 🚀 安裝與啟動 (Installation & Setup)

### 1. 克隆儲存庫 (Clone the repository)

打開終端機，導航到你希望存放專案的目錄，然後克隆專案：

```bash
git clone [https://github.com/kuan0415/line-scam-detection-bot.git](https://github.com/kuan0415/line-scam-detection-bot.git)
cd line-scam-detection-bot # 進入專案根目錄 (即你的 repo-main 資料夾)

2. 設置虛擬環境 (Set up Virtual Environment)
強烈建議使用虛擬環境來管理專案依賴，以避免與系統或其他專案的依賴衝突：

Bash

python3 -m venv venv
source venv/bin/activate # macOS/Linux
# 或在 Windows 上使用: venv\Scripts\activate

3. 安裝依賴 (Install Dependencies)
激活虛擬環境後，安裝所有必要的 Python 套件。首先，請確保你已經在專案根目錄下生成了 requirements.txt：

Bash

# 如果尚未生成，請在專案根目錄執行此命令
pip freeze > requirements.txt
然後安裝依賴：

Bash

pip install -r requirements.txt

4. 配置環境變數 (Configure Environment Variables)
在專案的根目錄 (line-scam-detection-bot/) 下，複製 .env.example 檔案並將其命名為 .env：

Bash

cp .env.example .env # macOS/Linux
# 或在 Windows 上使用: copy .env.example .env
然後打開 .env 檔案，填入你的 LINE Bot 和模型相關的憑證與設定：

程式碼片段

# .env 檔案範例 (請替換為你的實際值)
CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
CHANNEL_SECRET=your_line_channel_secret_here
OPENAI_API_KEY=your_openai_api_key_here # 如果使用 'openai' 偵測策略則需要
PORT=5080
DEBUG=True
LOG_LEVEL=INFO

# 偵測策略設定 (請選擇其中一種)
DETECTION_STRATEGY=openai # 'local', 'openai', 'bert', 'api'
BERT_MODEL_PATH=models/finetuned_classifier # 如果 DETECTION_STRATEGY='bert'，則指向本地模型路徑
ANALYSIS_API_URL= # 如果 DETECTION_STRATEGY='api'，則填寫外部推論服務的 URL
重要提示:

請將 your_line_channel_access_token_here、your_line_channel_secret_here 和 your_openai_api_key_here 替換為你在 LINE Developers Console 和 OpenAI Platform 上獲取的實際值。
.env 檔案已被 .gitignore 排除，所以它不會被提交到 GitHub，確保了你的敏感資訊安全。
5. 運行 ngrok (Run ngrok for Local Testing)
LINE Bot 需要一個公開可訪問的 URL 來接收 Webhook 事件。如果你在本地開發和測試，你需要使用 ngrok 將你的本地 Flask 服務暴露到互聯網。

打開一個新的終端機視窗，並運行 ngrok，將其指向你的應用程式端口 (預設為 5080)：

Bash

ngrok http 5080
ngrok 會給你一個類似 https://your-random-subdomain.ngrok-free.app 的 URL。請複製這個 URL，你將在下一步中使用它。

6. 配置 LINE Developers Webhook URL
登錄到 LINE Developers Console。
選擇你用於此機器人的 Provider 和 Channel。
進入 "Messaging API" 選項卡。
向下滾動到 "Webhook settings" 部分，點擊 "Edit" 按鈕。
將你從 ngrok 獲取的 URL 加上 /callback (例如：https://your-random-subdomain.ngrok-free.app/callback) 粘貼到 "Webhook URL" 字段中。
確保 "Use webhook" 是開啟的。
點擊 "Verify" 按鈕，確保 LINE 可以成功連接到你的本地服務。
7. 啟動服務 (Start the Application)
回到你最初的終端機視窗 (已經激活虛擬環境並在專案根目錄下)，運行 Flask 應用程式：

Bash

python app.py
如果一切順利，你將看到 Flask 服務啟動的訊息，類似 * Running on http://127.0.0.1:5080。

8. 測試機器人 (Test the Bot)
現在，你可以打開 LINE 應用程式，向你的機器人發送訊息，觀察終端機的日誌輸出，並檢查機器人的回覆是否符合預期。

🤖 模型訓練與更換 (Model Training & Replacement)
本專案將模型訓練邏輯與主服務分離，以便靈活管理。

進入 fraud_sentiment/ 目錄:
Bash

cd fraud_sentiment/
依據其內部指南訓練模型: 請參考 fraud_sentiment/README.md 或 USAGE.md 文件中的詳細說明來訓練或微調你的 BERT 分類器。
Bash

# 範例：
python train_classifier.py --data_path ../data/your_training_data.csv --output_dir ./my_finetuned_model
複製訓練好的模型: 訓練完成後，通常會在 fraud_sentiment/ 下生成一個類似 my_finetuned_model/ 的資料夾（或你指定的輸出路徑）。你需要將這個包含模型權重和配置的資料夾複製到主專案的 models/ 目錄下。 如果 models/finetuned_classifier/ 已經存在，建議先備份或移除，再複製新的模型。
Bash

# 範例：假設你在 fraud_sentiment/ 目錄下訓練出模型，並將其輸出到 ./my_finetuned_model
cp -r ./my_finetuned_model ../models/finetuned_classifier/
請確保 models/finetuned_classifier/ 內包含所有 BERT 模型所需的檔案（如 config.json, pytorch_model.bin, tokenizer_config.json, vocab.txt 等）。
配置主服務載入: 主服務會依據 .env 中 BERT_MODEL_PATH 的設定來載入模型。通常，如果你將模型放到 models/finetuned_classifier/，則確保 .env 中設置為 BERT_MODEL_PATH=models/finetuned_classifier。
重啟服務: 更新模型後，請重新啟動 app.py 以載入新的模型。
🕵️ 偵測策略切換 (Detection Strategy Switching)
你可以通過修改 .env 文件中的 DETECTION_STRATEGY 變數來切換詐騙偵測所使用的後端模型或方法：

DETECTION_STRATEGY=local: 使用 detection_service.py 中定義的本地正則表達式和關鍵字規則進行判斷。
DETECTION_STRATEGY=openai: 使用 OpenAI 的大型語言模型進行分類。需要配置 OPENAI_API_KEY。
DETECTION_STRATEGY=bert: 使用 models/finetuned_classifier 下的本地 BERT 分類器進行推論。需要確保模型已存在且 BERT_MODEL_PATH 指向正確路徑。
DETECTION_STRATEGY=api: 如果你的 BERT 模型或其他分析服務部署為獨立的 API，你可以將此設定指向該 API。需要配置 ANALYSIS_API_URL。
相關環境變數：
DETECTION_STRATEGY: 選擇偵測策略 (local, openai, bert, api)。
BERT_MODEL_PATH: 當 DETECTION_STRATEGY=bert 時，指向本地 BERT 模型資料夾的路徑。
ANALYSIS_API_URL: 當 DETECTION_STRATEGY=api 時，指向外部分析 API 的完整 URL。
訓練/微調/推論詳情 (fraud_sentiment/)
所有與模型訓練、微調和推論相關的腳本和資料都位於 fraud_sentiment/ 目錄下。

詳細操作: 請參閱 fraud_sentiment/ 目錄下的 README.md 或 USAGE.md 文件，其中會提供具體的命令行指令、數據準備指南和環境配置要求。
訓練資料格式: 訓練資料文件通常需要包含 text 欄位（文本內容）和 label 欄位（詐騙分類標籤）。
🧪 測試 (Testing)
建議補充 tests/ 目錄下的單元測試腳本，以確保各個模組的功能正確性。

可以使用 pytest 框架來執行測試：
Bash

pip install pytest
pytest tests/
❓ 常見問題與故障排除 (FAQ & Troubleshooting)
LineBotApiError: Invalid reply token: 這通常是因為 LLM (OpenAI 或 BERT) 處理時間過長，導致 LINE 的回覆令牌過期。優先解決模型推論速度或 API 錯誤問題。
ModuleNotFoundError: 確保你已經運行了 pip install -r requirements.txt，並且所有 Python 包目錄 (bot/, clients/, services/, services/domain/, services/domain/detection/, utils/) 都包含空的 __init__.py 文件，以確保 Python 正確識別為包。
openai.RateLimitError: Error code: 429 - insufficient_quota: 你的 OpenAI API 配額不足。請登錄 OpenAI Platform 檢查你的帳戶餘額或設置付費方式。這是導致機器人無法正常回覆的最常見原因。
模型無法載入: 請確認 models/finetuned_classifier/ 目錄內有完整的模型檔案（如 config.json, pytorch_model.bin 等），並且 .env 中的 BERT_MODEL_PATH 指向正確的路徑。
LINE webhook 無回應:
檢查 .env 中的 CHANNEL_SECRET 和 CHANNEL_ACCESS_TOKEN 是否正確填寫。
確認 LINE Developers 後台的 Webhook URL (例如 ngrok URL + /callback) 是否設置正確並已驗證。
確保你的 Flask 應用程式正在運行，並且 ngrok 服務正常。
Webhook URL 必須以 https:// 開頭。
Python/transformers 版本不符: 請依據 requirements.txt 和 fraud_sentiment/README.md 的建議，確保你的 Python 環境和所有相關套件版本兼容。
GitHub 推送失敗 (Authentication failed / 403 Forbidden): 請確保你使用了正確的 GitHub Personal Access Token (PAT) 來代替密碼，並且該 PAT 擁有 repo 權限。
📜 授權 (License)
本專案採用 MIT License，詳見 LICENSE 檔案。

🤝 聯絡與協作 (Contact & Contribution)
歡迎透過 GitHub 開啟 Issue 或 Pull Request 來回報問題、建議新功能或參與協作。
