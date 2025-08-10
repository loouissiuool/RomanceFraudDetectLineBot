# Romance-Scam Stage Detector (LINE Bot) / 愛情詐騙階段偵測 LINE 機器人

A production-style LINE bot that classifies conversation snippets into a 7-stage romance‑scam model, explains the reasoning (Why & Explain), and suggests prevention tips (Prevent). Built with **Flask (Python)**, LINE Messaging API, and **LLM (OpenAI, optional Gemini)**.  
以 7 階段愛情詐騙模型為核心的 LINE 機器人：可對對話片段做階段判定、提供可解釋理由（Why & Explain），並給出防範建議（Prevent）。後端以 **Flask (Python)** 建置，串接 LINE Messaging API 與 **LLM（OpenAI，可選 Gemini）**。

---

## Contents / 目錄
- [Features / 功能](#features--功能)
- [Architecture / 架構](#architecture--架構)
- [Requirements / 環境需求](#requirements--環境需求)
- [Setup / 安裝設定](#setup--安裝設定)
- [Run / 執行](#run--執行)
- [Environment Variables / 環境變數](#environment-variables--環境變數)
- [Project Structure / 專案結構](#project-structure--專案結構)
- [Stage Definitions / 階段定義](#stage-definitions--階段定義)
- [Notes / 備註](#notes--備註)
- [License / 授權](#license--授權)

---

## Features / 功能
**EN**
- Classifies text into a 7‑stage romance‑scam workflow.
- Generates **Why & Explain** (concise + detailed) and **Prevent** (3 tips + expandable details).
- Rich **LINE Flex Messages** UI (carousel: overview + triggers; separate explanation and prevention bubbles).
- Supports **context‑aware** recommended actions (one‑liner tailored to the latest message + stage).
- Switchable LLM backends (OpenAI; optional Google Gemini).
- Logs per‑user state and chat history for better continuity.

**繁中**
- 以 7 階段模型判定詐騙對話所處階段。
- 產生**理由說明**（精簡＋詳細）與**防範建議**（3 點＋可展開詳述）。
- 使用 **LINE Flex Message** 呈現（摘要＋觸發因子 carousel；另有 explain / prevent 卡片）。
- **情境式建議行動**：依目前訊息與階段動態產生一句建議。
- 可切換 LLM 後端（OpenAI；可選 Google Gemini）。
- 保存使用者狀態與歷史，利於後續互動。

---

## Architecture / 架構
**EN** – Event‑driven webhook with Flask:
1. LINE → **Webhook** (Flask) → `ConversationService.handle_message()` / `handle_postback()`  
2. `ConversationService` orchestrates modules: `DetectionService` (stage + triggers), LLM calls (explanations, tips), and `LineClient` (Flex messages).  
3. Results are rendered as Flex bubbles: **Overview** (+ dynamic Recommended Action) and **Details & Triggers**; users can tap **Why & Explain** or **Prevent** for further cards.

**繁中** – Flask Webhook 事件驅動：
1. LINE → **Webhook**（Flask）→ `ConversationService.handle_message()` / `handle_postback()`  
2. `ConversationService` 協調 `DetectionService`（階段＋觸發因子）、LLM（解釋與建議）、`LineClient`（Flex）等模組。  
3. 以 Flex 卡片呈現：**摘要卡**（含動態建議行動）與 **詳細卡**（Triggers）；使用者可點 **Why & Explain** 或 **Prevent** 取得更多卡片。

---

## Requirements / 環境需求
- Python 3.10+
- LINE Messaging API credentials
- OpenAI API key (required for LLM features)  
  Gemini API key (optional)

---

## Setup / 安裝設定
```bash
# 1) Clone
git clone https://github.com/<YOUR_USER>/<YOUR_REPO>.git
cd <YOUR_REPO>

# 2) (Optional) Create venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3) Install deps
pip install -r requirements.txt

# 4) Configure .env or environment variables (see below)
```

### LINE Webhook
- Set your webhook URL to `https://<your-domain>/callback` in LINE Developers Console.  
- Enable messaging permissions and add your bot as a friend for testing.

---

## Run / 執行
```bash
# Development
python app_main.py   # or: flask run
# Default port can be configured via PORT; common values: 5080 or 8000
```

For local testing with LINE, expose the port via **ngrok** or a reverse proxy:
```bash
ngrok http 5080
# then set the ngrok https URL as the LINE webhook
```

---

## Environment Variables / 環境變數
| Key | Description |
| --- | --- |
| `LINE_CHANNEL_SECRET` | LINE webhook signature verification |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API token |
| `OPENAI_API_KEY` | OpenAI key for LLM (explanations, prevention tips, dynamic recommended action) |
| `GEMINI_API_KEY` | (Optional) Google Gemini key |
| `PORT` | Flask listening port (e.g., 5080) |
| `FLASK_ENV` | `development` or `production` |

> Place them in `.env` or your hosting provider’s env panel.

---

## Project Structure / 專案結構
```
bot_prod/
├─ app_main.py                 # Flask entrypoint / Webhook server
├─ bot/
│  └─ line_webhook.py          # Event routing
├─ clients/
│  └─ line_client.py           # LINE API wrapper (reply_text, reply_flex, etc.)
├─ services/
│  ├─ conversation_service.py  # Orchestrates detection, LLM, and Flex UI
│  ├─ gemini_client.py         # Optional Gemini wrapper
│  └─ domain/
│     └─ detection/
│        └─ detection_service.py  # Stage detection + trigger labeling
├─ config.py                   # Config loader (env)
└─ stage_definitions.json      # 7-stage model metadata
```

---

## Stage Definitions / 階段定義
- The bot follows a 7‑stage romance‑scam model (e.g., **Find the Dream Mate → Contact via Fake Profile → Grooming → The Sting → Continuation → Sexual Exploitation → Re‑victimization**).  
- `stage_definitions.json` contains the **names**, **short descriptions**, and **pattern features** for UI/LLM prompts.  
- `DetectionService` returns `stage`, `labels`, and an internal `rationale` object; `ConversationService` renders them via Flex, and produces a **context‑aware one‑line Recommended Action** for the overview bubble.

---

## Notes / 備註
- If LLM quota is exhausted or API errors occur, the bot gracefully degrades (shows an error state in Flex).
- **Security**: Never log personal content verbatim in production; mask PII. Use HTTPS for webhook.
- **Limits**: Stage classification works best with sufficient context; a single very short message may be ambiguous.

---

## License / 授權
MIT License. See `LICENSE` if provided.
