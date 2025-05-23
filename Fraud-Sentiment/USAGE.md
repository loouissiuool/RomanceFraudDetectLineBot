# 使用與測試流程說明

## 1. 建立虛擬環境與安裝依賴

```cmd
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. 單句斷詞與關鍵字推論（推薦先執行，驗證環境與流程）

```cmd
python infer_ws.py --text "請輸入待分析對話"
```
- 輸出每句話的斷詞與關鍵字標註。

---

## 3. 斷詞模型微調（可選，需有 BIO 格式資料）

```cmd
python finetune_ws.py --config configs/finetune.yaml
```
- 需先準備 BIO 格式資料於 `data/ws_finetune_sample`。
- 預設模型儲存於 `finetuned_ws/`。
- **如遇 PermissionError，請每次訓練用不同 output_dir 或手動刪除舊資料夾。**

---

## 4. 用微調後模型再次推論（可選，驗證微調效果）

```cmd
python infer_ws.py --text "請輸入待分析對話"
```
- 請確認 infer_ws.py 載入的是最新微調模型。

---

## 5. 批次斷詞與理論階段分類

```cmd
python batch_infer.py --input data/complex_dialog --output results/complex_report.csv
python batch_infer.py --input data/simple_dialog --output results/simple_report.csv
```
- `complex_dialog`、`simple_dialog`：每行一則對話的純文字檔。

---

## 6. 斷詞與關鍵字自動評估

```cmd
python word_segmentation_eval.py
```
- 自動統計關鍵字命中率，給出微調建議。

---

## 7. 模擬對話資料分析（可選）

```cmd
python line_dialog_eval.py --input data/sample_dialog.json
```
- 分析模擬對話資料，產生標註與分類結果。

---

## 8. 金融詐騙三階段分類模型訓練與推論（進階，需有標註資料）

### 標註資料格式
- `data/train.csv`、`data/test.csv`  
  - 欄位：`text`（對話內容）、`label`（三階段標籤）

### 訓練模型
```cmd
python train_classifier.py
```
- 預設模型儲存於 `finetuned_classifier/`。
- **如遇 PermissionError，請每次訓練用不同 output_dir 或手動刪除舊資料夾。**

### 單句分類推論
```cmd
python predict_classifier.py "請幫我匯款到這個帳戶"
```
- 終端會輸出分類結果（如：高風險詐騙徵兆）

---

## 9. 單元測試與 HTML 報告產生

```cmd
pytest tests/
```
建議安裝 pytest-html 以產生可分享的測試報告：

```bash
pip install pytest-html
pytest tests/ --html=pytest_report.html
```

- 這會在專案目錄下產生 `pytest_report.html`，可直接分享給組員或老師瀏覽測試結果。

---

## 資料格式說明

- `ws_finetune_sample`：BIO 格式，每行一字一標籤，空行分隔句子。
- `complex_dialog`、`simple_dialog`：每行一則對話純文字。
- `train.csv`、`test.csv`：CSV 格式，欄位為 `text`、`label`。

---

## 注意事項
- 請先依照本文件建立正確的 Python/venv/依賴環境。
- 執行前請確認所需資料與模型已放置於正確目錄。
- 如遇錯誤，請先查閱「常見問題排解」區塊。
- 嚴格依 requirements.txt 安裝指定版本，避免相容性問題。

---

## 常見問題排解

- **PermissionError: [WinError 5] ... checkpoint-1**  
  每次訓練前請刪除舊的 results_classifier* 或 finetuned_classifier* 目錄，或每次訓練用不同 output_dir（如 `finetuned_classifier_20240512/`）。
- **transformers/accelerate 版本衝突**  
  嚴格依 requirements.txt 安裝指定版本。
- **fsspec 版本警告**  
  請降級至 2025.3.0。
