Scam-Bot 詐騙偵測 LINE Bot

專案簡介 (Project Introduction)

Scam-Bot 是一個結合 NLP 詐騙偵測模型與 LINE Bot 的現代化專案，旨在提供即時的詐騙風險分析和警示。它能夠分析用戶透過 LINE 發送的訊息，判斷潛在的詐騙階段和風險等級，並提供相應的建議和防範措施。專案採用清晰的分層架構，便於未來的維護與功能擴展。

主服務: 負責處理 LINE Webhook 事件、訊息處理流程、詐騙偵測邏輯以及用戶回覆的生成。

模型訓練/推論: 獨立於 fraud_sentiment/ 目錄。主服務僅需載入 models/ 目錄下的預訓練或微調好的模型進行推論。
