# repo-main/services/domain/detection/detection_service.py

import os
import logging
import re
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI # 導入新版 OpenAI 客戶端
from config import Config # 導入 Config 獲取 OpenAI Key
from utils.error_handler import DetectionError # 導入自定義錯誤

logger = logging.getLogger(__name__)

# --- 詐騙模式和 LLM Prompt (從你提供的單一檔案 app.py 移過來) ---
SCAM_PATTERNS = [
    (re.compile(r"醫(藥)?費|醫療|急需|救急"), "crisis"),
    (re.compile(r"帳戶(被)?凍結"), "crisis"),
    (re.compile(r"(轉|匯|借)[^\d]{0,3}(\d{3,})(元|塊|台幣)"), "payment"),
    (re.compile(r"這是.*帳[戶號]"), "payment"),
]

SYSTEM_PROMPT = """
你是一個詐騙對話階段分類助手。
[Stage definitions]
0 Discovery: 發現目標。初步接觸和簡單交流，獲取基本資訊。
1 Bonding/Grooming: 建立信任和情感連結。透過共同點或浪漫關係拉近距離。
2 Testing Trust: 測試信任程度。可能提出小請求，觀察受害者反應。
3 Crisis Story: 製造危機和緊急情況。通常涉及醫療、法律或財務問題，以激發受害者同情或恐懼。
4 Payment Coaching: 引導付款。提供具體轉帳方式、帳戶資訊或要求購買禮物卡。
5 Aftermath/Repeat: 詐騙成功或失敗後的處理。可能要求更多金錢，或消失、重啟新詐騙。

[輸出格式]
{"stage": <int>, "labels": ["urgency","crisis"]}

[Examples]
<dialog>
User: 嗨～可以認識你嗎？我也住台北！
Assistant: {"stage":1,"labels":["similarity","romance"]}
</dialog>
<dialog>
User: 我急需 5000 付媽媽醫藥費…拜託你幫我！
Assistant: {"stage":3,"labels":["urgency","crisis"]}
</dialog>
<dialog>
User: 這是銀行帳號 000-123-456，現在轉過去就能解凍！
Assistant: {"stage":4,"labels":["payment","urgency"]}
</dialog>
"""

# 關鍵字規則字典，用於 infer_stage_counter 函數
RULES = {
    "authority":  ["officer", "bank", "agent", "official", "protocol"],
    "similarity": ["me too", "same", "also", "just like you"],
    "scarcity":   ["last chance", "only today", "limited", "rare"],
    "urgency":    ["urgent", "immediately", "asap", "now", "right away", "快點", "馬上", "立刻"],
    "romance":    ["sweetheart", "my love", "miss you", "never felt", "親愛的", "想你", "寶貝"],
    "crisis":     ["hospital", "surgery", "accident", "fees", "visa", "customs", "醫院", "急診", "手術", "車禍"],
    "payment":    ["transfer", "wire", "crypto", "bitcoin", "gift card", "account number", "匯款", "轉帳", "帳號", "比特幣", "禮物卡"]
}

# 文獻對照資訊：詐騙階段和標籤描述
STAGE_INFO = {
    0: ("關係建立期", "暫無異常，保持正常互動"),
    1: ("情感操控期", "對方正在加速拉近距離，可嘗試要求視訊驗證"),
    2: ("信任測試期", "可能開始測試你的服從度，避免透露隱私/證件"),
    3: ("危機敘事期", "進入情緒勒索，先暫停匯款並與親友討論"),
    4: ("付款引導期", "金錢索求已出現，建議立即停止匯款並求助 165"),
    5: ("重複索求期", "高度疑似詐騙，蒐證後報警"),
}

LABEL_DESC = {
    "crisis"   : ("情緒觸發：恐懼/同情",   "白騎士情境、醫療急需等危機敘事"),
    "payment"  : ("經濟榨取：金錢索求", "提供帳戶或要求匯款"),
    "urgency"  : ("認知偏誤：稀缺/緊迫", "出現『快點』『立刻』等字眼"),
    "authority": ("認知偏誤：權威依從", "冒充政府/銀行增加可信度"),
    "similarity":("認知偏誤：同理心", "用相同特徵拉近關係"),
    "romance":  ("情感操控：建立親密感", "使用親暱稱呼、甜言蜜語"),
    "scarcity": ("認知偏誤：稀缺/緊迫", "強調機會難得，錯過不再有"),
    "無異常": ("無", "未偵測到明確的詐騙特徵")
}

class DetectionService:
    """
    詐騙檢測服務，負責分析訊息並檢測潛在的詐騙。
    整合了基於規則的檢測和 LLM (OpenAI) 的分類功能。
    """
    def __init__(self, analysis_client: Optional[Any] = None):
        """
        初始化檢測服務。
        Args:
            analysis_client: 可選的外部分析 API 客戶端實例。
                             在此重構中，我們直接使用 OpenAI，所以這個參數可能不直接用於核心檢測。
        """
        self.analysis_client = analysis_client # 如果有外部 API 需求，可以保留

        self.openai_client = None
        if Config.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
                logger.info("DetectionService: OpenAI 客戶端初始化成功。")
            except Exception as e:
                logger.error(f"DetectionService: 初始化 OpenAI 客戶端失敗：{e}", exc_info=True)
                self.openai_client = None
        else:
            logger.warning("DetectionService: OPENAI_API_KEY 未設定，LLM 功能將無法使用。")

    def _classify_llm(self, text: str, timeout: int = 5) -> Dict[str, Any]:
        """
        呼叫 OpenAI API 對文本進行詐騙階段和標籤分類。
        """
        if not self.openai_client:
            logger.warning("OpenAI 客戶端未初始化，無法呼叫 GPT。返回預設分類。")
            return {"stage": 0, "labels": ["LLM_UNAVAILABLE"]} # 新增一個標籤表示LLM不可用
        try:
            rsp = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                timeout=timeout
            )
            return json.loads(rsp.choices[0].message.content)
        except Exception as e:
            logger.error(f"GPT 分類失敗：{e}", exc_info=True)
            # 當 LLM 失敗時，直接返回一個預設結果，而不是拋出異常。
            # 這樣主流程可以繼續，並告訴用戶 LLM 功能無法使用。
            return {"stage": 0, "labels": ["LLM_ERROR"], "error_message": str(e)}

    def analyze_message(self, message_text: str) -> Dict[str, Any]:
        """
        分析輸入文本，判斷詐騙階段和觸發標籤。
        優先使用正則表達式匹配，如果沒有匹配到，則使用 LLM。
        """
        try:
            labels = [lab for pat, lab in SCAM_PATTERNS if pat.search(message_text)]

            if labels:
                stage = self._infer_stage_counter(labels)
                logger.info(f"關鍵字匹配結果: Stage={stage}, Labels={labels}")
                return {"stage": stage or 0, "labels": labels}
            else:
                llm_result = self._classify_llm(message_text)
                # 如果 LLM 呼叫返回了錯誤信息，則將其添加到結果中
                if "error_message" in llm_result:
                    logger.warning(f"LLM 呼叫失敗，將使用預設分類。錯誤：{llm_result['error_message']}")
                    return {"stage": llm_result.get("stage", 0), "labels": llm_result.get("labels", []), "llm_error": True}
                else:
                    stage = llm_result.get("stage", 0)
                    labels = llm_result.get("labels", [])
                    logger.info(f"LLM 分類結果: Stage={stage}, Labels={labels}")
                    return {"stage": stage, "labels": labels}
        # 這裡就不再捕捉 DetectionError，因為 _classify_llm 不再拋出它
        except Exception as e:
            logger.error(f"分析訊息時發生未知錯誤: {e}", exc_info=True)
            return {"stage": 0, "labels": ["分析失敗"], "error": "未知錯誤"}


    def analyze_message(self, message_text: str) -> Dict[str, Any]:
        """
        分析輸入文本，判斷詐騙階段和觸發標籤。
        優先使用正則表達式匹配，如果沒有匹配到，則使用 LLM。
        """
        try:
            labels = [lab for pat, lab in SCAM_PATTERNS if pat.search(message_text)]

            if labels:
                stage = self._infer_stage_counter(labels)
                logger.info(f"關鍵字匹配結果: Stage={stage}, Labels={labels}")
                return {"stage": stage or 0, "labels": labels} # 確保 stage 有值 (至少為 0)
            else:
                llm_result = self._classify_llm(message_text)
                stage = llm_result.get("stage", 0)
                labels = llm_result.get("labels", [])
                logger.info(f"LLM 分類結果: Stage={stage}, Labels={labels}")
                return {"stage": stage, "labels": labels}
        except DetectionError as e: # 捕捉 LLM 呼叫失敗拋出的錯誤
            logger.error(f"分析訊息時發生檢測錯誤: {e}", exc_info=True)
            # 在這裡返回一個包含錯誤信息的結果，以便上層可以處理
            return {"stage": 0, "labels": ["分析失敗"], "error": str(e)}
        except Exception as e:
            logger.error(f"分析訊息時發生未知錯誤: {e}", exc_info=True)
            return {"stage": 0, "labels": ["分析失敗"], "error": "未知錯誤"}

    def _infer_stage_counter(self, lbls: List[str]) -> int:
        """
        根據匹配到的關鍵字標籤計數，推斷詐騙階段。
        """
        c = {k: 0 for k in RULES.keys()}
        for l in lbls:
            if l in c:
                c[l] += 1

        if c["payment"] >= 1: return 4
        if c["crisis"] >= 1: return 3
        return 0

    def get_stage_info(self, stage_num: int) -> tuple:
        """獲取特定詐騙階段的名稱和建議。"""
        return STAGE_INFO.get(stage_num, ("未知階段", "請留意對話內容"))

    def get_label_desc(self, label: str) -> tuple:
        """獲取特定標籤的描述。"""
        return LABEL_DESC.get(label, (label, ""))

    def is_llm_available(self) -> bool:
        """檢查 LLM 功能是否可用。"""
        return self.openai_client is not None