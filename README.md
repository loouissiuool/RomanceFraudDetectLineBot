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

