# repo-main/services/domain/detection/detection_service.py

import os
import logging
import re
import json
from typing import Dict, Tuple
from typing import Dict, List, Any, Optional
from openai import OpenAI # 導入新版 OpenAI 客戶端
from config import Config # 導入 Config 獲取 OpenAI Key
from utils.error_handler import DetectionError # 導入自定義錯誤

logger = logging.getLogger(__name__)

def _safe_load_json(text: str) -> Optional[dict]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 嘗試抓最像 JSON 的區塊再 parse
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return None


# --- 詐騙模式和 LLM Prompt (從你提供的單一檔案 app.py 移過來) ---
SCAM_PATTERNS = [
    (re.compile(r"醫(藥)?費|醫療|急需|救急"), "crisis"),
    (re.compile(r"帳戶(被)?凍結"), "crisis"),
    (re.compile(r"(轉|匯|借)[^\d]{0,3}(\d{3,})(元|塊|台幣)"), "payment"),
    (re.compile(r"這是.*帳[戶號]"), "payment"),
    (re.compile(r"\bdoctor\b|\bmedical\b|\burgent\b|\bemergency\b", re.IGNORECASE), "crisis"),
    (re.compile(r"\baccount (?:frozen|locked)\b", re.IGNORECASE), "crisis"),
    (re.compile(r"\b(send|transfer|loan)[^\d]{0,3}(\d{3,})\$?", re.IGNORECASE), "payment"),
    (re.compile(r"\bthis is my account\b", re.IGNORECASE), "payment"),
    (re.compile(r"\bcan't talk on webcam\b|\bno webcam\b|\bcan't call\b", re.IGNORECASE), "unverified_communication"),
    (re.compile(r"\blie(d|s)?\b|\binconsistent\b|\bfake\b", re.IGNORECASE), "identity_inconsistency"),
    (re.compile(r"\bsend more money\b|\bwant more money\b", re.IGNORECASE), "money_request"),
]

NARRATIVE_PATTERNS = [
    (re.compile(r"\bI once\b", re.IGNORECASE), "self_experience"),
    (re.compile(r"\bI have experienced\b", re.IGNORECASE), "self_experience"),
    (re.compile(r"\bI fell in love with\b", re.IGNORECASE), "self_experience"),
    (re.compile(r"\bfound out the hard way\b", re.IGNORECASE), "self_experience"),
    (re.compile(r"\bMy experience\b", re.IGNORECASE), "self_experience"),
    (re.compile(r"\bI encountered\b", re.IGNORECASE), "self_experience"),
    (re.compile(r"\bI was talking to\b", re.IGNORECASE), "self_experience"),
]

SYSTEM_PROMPT = """
You are an expert romance-scam detection assistant based on Witty et al.’s seven-stage framework. Given a user message (which may be either a pure dialogue snippet or a user describing their personal experience), do the following:

1. Decide whether the message is a personal experience description or pure dialogue. ("experience" vs "dialogue")
2. Identify which scam stage the message best fits into. Use the integer mapping:
   0: Find the Dream Mate
   1: Contact via fake profile
   2: Grooming
   3: The Sting
   4: Continuation of the Scam
   5: Sexual Exploitation
   6: Re-victimization
3. Extract all relevant scam-related labels/triggers present (e.g., payment, urgency, identity_inconsistency, unverified_communication, romance, authority, crisis, money_request, sexual_request, friendly, geolocation, etc.).
4. For each of the above (input_type, each label, and stage), provide a concise rationale citing exact phrases, contradictions, or patterns in the message that justify your classification.

Output **only valid JSON** following this schema:

{
  "input_type": "experience" | "dialogue",
  "stage": <int 0-6>,
  "labels": [ "<label1>", "<label2>", ... ],
  "rationale": {
    "input_type": "<why it is experience or dialogue, quoting evidence>",
    "labels": {
       "<label1>": "<reason with quoted evidence>",
       "<label2>": "...",
       ...
    },
    "stage": "<reasoning for chosen stage, referencing progression or combination of triggers>"
  }
}

Examples:

<dialog>
User: Hi—can I get to know you? I live in Taipei too!  
Assistant: {
  "input_type": "dialogue",
  "stage": 1,
  "labels": ["friendly", "geolocation"],
  "rationale": {
    "input_type": "Detected as dialogue because the user is asking a casual question without recounting past experience.",
    "labels": {
      "friendly": "Phrase 'Hi—can I get to know you?' indicates initial outreach and friendliness.",
      "geolocation": "'I live in Taipei too' reveals shared location used to build rapport."
    },
    "stage": "Personalized outreach and shared interest aligns with 'Contact and Entice' (stage 1)."
  }
}
</dialog>

<dialog>
User: I really like you—we talk every day and I think I’m falling for you.  
Assistant: {
  "input_type": "dialogue",
  "stage": 2,
  "labels": ["romance", "bonding"],
  "rationale": {
    "input_type": "Dialogue: no autobiographical past-tense phrasing detected.",
    "labels": {
      "romance": "Phrase 'I really like you' and 'falling for you' shows intimacy building.",
      "bonding": "'We talk every day' indicates regular emotional connection being established."
    },
    "stage": "Building trust and emotional closeness corresponds to 'Grooming' (stage 2)."
  }
}
</dialog>

<dialog>
User: Here’s my account number 123-456. Please transfer the money tonight or I’ll be in trouble.  
Assistant: {
  "input_type": "dialogue",
  "stage": 4,
  "labels": ["payment", "urgency"],
  "rationale": {
    "input_type": "Dialogue: no self-experience phrasing.",
    "labels": {
      "payment": "'Here’s my account number 123-456' and request to transfer money indicates financial extraction.",
      "urgency": "'Tonight' and 'I’ll be in trouble' impose pressure to act immediately."
    },
    "stage": "Explicit money request with crisis framing fits 'Continuation of the Scam' (stage 4)."
  }
}
</dialog>

<dialog>
User: I once fell in love with the lady who said she was in the military. She asked me to send $1200 for paperwork and then another $3000, refused webcam calls, and gave conflicting base locations.  
Assistant: {
  "input_type": "experience",
  "stage": 4,
  "labels": ["self_experience", "money_request", "identity_inconsistency", "unverified_communication"],
  "rationale": {
    "input_type": "Detected personal experience: phrase 'I once fell in love with the lady who said she was in the military' is autobiographical.",
    "labels": {
      "self_experience": "'I once fell in love...' indicates the user is recounting an event that happened to them.",
      "money_request": "Requests of '$1200 for paperwork' then 'another $3000' show escalating financial demands beyond initial agreement.",
      "identity_inconsistency": "Conflicting location claims about the military base (claiming to be in Iraq while only British soldiers were present) indicate misinformation.",
      "unverified_communication": "Refusal or excuses to use webcam/voice call shows avoidance of real-time verification."
    },
    "stage": "Multiple money requests with emotional leverage and crisis framing place this in 'Continuation of the Scam' (stage 4)."
  }
}
</dialog>

"""




# 關鍵字規則字典，用於 infer_stage_counter 函數
RULES = {
    "greeting":        ["嗨", "你好", "您好", "哈囉", "hi", "hello", "hey", "morning", "evening"],
    "friendly":        ["可以認識你", "交個朋友", "你也住哪", "你人真好", "請問你多大", "住哪"],
    "shared_interest": ["我也喜歡", "我也會", "一樣", "也這樣", "也喜歡", "me too", "same", "also", "just like you"],
    "compliment":      ["你很漂亮", "好帥", "太有魅力", "真好看", "超正", "cute", "beautiful", "handsome", "gorgeous"],
    "romance":         ["寶貝", "親愛的", "想你", "喜歡你", "愛你", "my love", "miss you", "sweetheart", "darling"],
    "bonding":         ["我們好有緣", "註定在一起", "天注定", "這是命運", "soulmate", "destiny", "perfect match"],
    "crisis":          ["醫院", "急診", "生病", "車禍", "手術", "家人生病", "出事", "hospital", "surgery", "accident", "operation", "my mom is sick"],
    "emotion":         ["我很難過", "我快撐不下去", "我需要幫忙", "你不幫我就沒人了", "I’m crying", "so sad", "desperate", "helpless", "please"],
    "payment":         ["匯款", "轉帳", "帳號", "幫我轉", "這是帳戶", "給我錢", "atm", "transfer", "bank account", "send money", "western union", "wire"],
    "urgency":         ["快點", "立刻", "現在", "馬上", "很急", "不能等", "immediately", "urgent", "asap", "right now"],
    "sexual_request":  ["裸照", "性感", "裸體", "不穿", "拍張照片", "給我看看", "nude", "sexy", "pic", "photo", "send me something", "just for me"],
    "repetition":      ["再轉一次", "不夠", "還需要", "再給我", "上次的還沒解決", "又出問題了", "again", "still not enough", "another payment", "one more time"],
    "pressure":        ["不給就完了", "你不幫我我就死", "只剩你了", "我相信你", "我只能靠你", "only you", "I trust you", "no one else", "just you", "you’re my last hope"]
}

# 文獻對照資訊：詐騙階段和標籤描述
STAGE_INFO = {
    0: (
        "Find the Dream Mate",
        "Scammers browse profiles and scan for potential victims without yet initiating any direct contact."
    ),
    1: (
        "Contact via Fake Profile",
        "The scammer reaches out with a fabricated identity—often using flattery, shared interests, or a false background to elicit a response."
    ),
    2: (
        "Grooming",
        "Through frequent, affectionate dialogue the scammer builds emotional rapport and trust, sharing personal stories or compliments."
    ),
    3: (
        "The Sting",
        "A sudden crisis or emotional emergency is manufactured to pressure the victim into providing money or sensitive information."
    ),
    4: (
        "Continuation of the Scam",
        "Following the initial transfer, the scammer repeatedly invents new urgent needs or excuses to extract further funds."
    ),
    5: (
        "Sexual Exploitation",
        "Leveraging established trust, the scammer coerces the victim into sending private or sexual content and may threaten exposure (sextortion)."
    ),
    6: (
        "Re-victimization",
        "The same victim or a new target is approached again (often under the guise of a refund agent or investigator), restarting the scam cycle."
    ),
}


LABEL_DESC: Dict[str, Tuple[str, str]] = {
    "crisis":      ("Emotional Trigger: Fear/Compassion", "Crisis narratives like ‘white knight’ scenarios or urgent medical needs"),
    "payment":     ("Economic Extraction: Money Demand", "Providing account details or requesting transfers"),
    "urgency":     ("Cognitive Bias: Scarcity/Urgency", "Use of words like ‘hurry’, ‘right now’, ‘immediately’"),
    "authority":   ("Cognitive Bias: Authority Compliance", "Impersonating government or banks to increase credibility"),
    "similarity":  ("Cognitive Bias: Empathy/Similarity", "Highlighting shared traits to build rapport"),
    "romance":     ("Emotional Manipulation: Intimacy Building", "Using pet names or sweet talk"),
    "scarcity":    ("Cognitive Bias: Scarcity", "Emphasizing one-time opportunities or limited availability"),
    "termination": ("Closure Signal: Disengagement", "Phrases like ‘goodbye’, ‘wish you well’ signalling end of conversation"),
    "recycle":     ("Role Switch: Repackaged Approach", "Re-contacting under a new identity (e.g., friend, lawyer) for another scam attempt"),
    "none":        ("None", "No clear scam indicators detected"),
    "self_experience": ("Context Type: Personal Experience", "User is describing something that happened to them (e.g., 'I once...', 'I fell in love with...')"),
    "unverified_communication": ("Red Flag: Unverified Communication", "Avoiding real-time verification like webcam/voice calls or giving excuses to not speak live"),
    "identity_inconsistency": ("Red Flag: Identity Inconsistency", "Conflicting or fabricated identity details, lying about location/status"),
    "money_request": ("Economic Extraction: Additional Money", "Requests for more money beyond the initial agreement or unexpected fees"),
    "bonding": ("Cognitive Bias: Relationship Building", "Repeated interaction or shared emotional investment to build rapport."),
    "friendly": ("Engagement: Friendly Outreach", "Casual or warm initial messages to initiate connection."),
    "shared_interest": ("Similarity Cue", "Highlighting common interests to build affinity."),
    "compliment": ("Flattery", "Using praise to lower guard and create goodwill."),
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

    def _classify_llm(self, text: str, timeout: int = 15) -> Dict[str, Any]:
        if not self.openai_client:
            logger.warning("OpenAI client not initialized; falling back to rule-based.")
            rule_labels = [lab for pat, lab in SCAM_PATTERNS if pat.search(text)]
            rule_stage = self._infer_stage_counter(rule_labels)
            input_type = "experience" if any(pat.search(text) for pat, _ in NARRATIVE_PATTERNS) else "dialogue"
            narrative_reason = (
                f"Matched pattern /{[pat.pattern for pat, l in NARRATIVE_PATTERNS if pat.search(text)][0]}/"
                if input_type == "experience"
                else "No narrative patterns matched"
            )
            return {
                "input_type": input_type,
                "stage": rule_stage,
                "labels": rule_labels or ["none"],
                "rationale": {
                    "input_type": narrative_reason,
                    "labels": {lab: f"Fallback pattern match for '{lab}'" for lab in rule_labels},
                    "stage": f"Fallback: inferred stage {rule_stage}"
                },
                "llm_error": True
            }

        try:
            rsp = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                timeout=timeout
            )
            content = rsp.choices[0].message.content
            data = _safe_load_json(content)

            # rule-based baseline, 用於 fallback
            rule_labels = [lab for pat, lab in SCAM_PATTERNS if pat.search(text)]
            rule_stage = self._infer_stage_counter(rule_labels)
            input_type_fallback = "experience" if any(pat.search(text) for pat, _ in NARRATIVE_PATTERNS) else "dialogue"
            narrative_reason_fallback = (
                f"Matched pattern /{[pat.pattern for pat, l in NARRATIVE_PATTERNS if pat.search(text)][0]}/"
                if input_type_fallback == "experience"
                else "No narrative patterns matched"
            )

            if not data:
                logger.warning("LLM returned invalid JSON, using rule-based fallback.")
                return {
                    "input_type": input_type_fallback,
                    "stage": rule_stage,
                    "labels": rule_labels or ["none"],
                    "rationale": {
                        "input_type": narrative_reason_fallback,
                        "labels": {lab: f"Fallback pattern match for '{lab}'" for lab in rule_labels},
                        "stage": f"Fallback: inferred stage {rule_stage}"
                    }
                }

            # --- 新增：處理 stage 可能不是整數的情況，並保留原始說明 ---
            raw_stage = data.get("stage", rule_stage)
            stage_num = rule_stage
            stage_reasoning = ""
            if isinstance(raw_stage, int):
                stage_num = raw_stage
            else:
                # 嘗試從字串抓 0~6 的數字
                m = re.search(r"\b([0-6])\b", str(raw_stage))
                if m:
                    stage_num = int(m.group(1))
                # 原始文字當作 reasoning
                stage_reasoning = str(raw_stage)

            # 準備 rationale（fallback 補齊）
            rationale = data.get("rationale", {}) if isinstance(data.get("rationale", {}), dict) else {}
            if "input_type" not in rationale:
                rationale["input_type"] = narrative_reason_fallback
            if "stage" not in rationale or not rationale.get("stage"):
                if stage_reasoning:
                    rationale["stage"] = stage_reasoning
                else:
                    rationale["stage"] = f"Inferred stage {stage_num}"
            if "labels" not in rationale or not isinstance(rationale.get("labels"), dict):
                rationale["labels"] = {lbl: f"Matched pattern for '{lbl}'" for lbl in (data.get("labels") or rule_labels or ["none"])}

            # 組最終結果（優先用 LLM 給的 label / input_type，但 stage 固定為整數）
            result = {
                "input_type": data.get("input_type", input_type_fallback),
                "stage": stage_num,
                "labels": data.get("labels", rule_labels or ["none"]),
                "rationale": rationale,
            }
            return result

        except Exception as e:
            logger.error(f"LLM classification failed: {e}", exc_info=True)
            # fallback to rule-based
            rule_labels = [lab for pat, lab in SCAM_PATTERNS if pat.search(text)]
            rule_stage = self._infer_stage_counter(rule_labels)
            input_type = "experience" if any(pat.search(text) for pat, _ in NARRATIVE_PATTERNS) else "dialogue"
            narrative_reason = (
                f"Matched pattern /{[pat.pattern for pat, l in NARRATIVE_PATTERNS if pat.search(text)][0]}/"
                if input_type == "experience"
                else "No narrative patterns matched"
            )
            return {
                "input_type": input_type,
                "stage": rule_stage,
                "labels": rule_labels or ["none"],
                "rationale": {
                    "input_type": narrative_reason,
                    "labels": {lab: f"Fallback pattern match for '{lab}'" for lab in rule_labels},
                    "stage": f"Fallback: inferred stage {rule_stage}"
                },
                "llm_error": True
        }

    def _detect_scam_stage(self, message_text: str) -> Dict[str, Any]:
        
        # 1. rule-based baseline：抓 labels，推 stage
        rule_labels = [lab for pat, lab in SCAM_PATTERNS if pat.search(message_text)]
        rule_stage = self._infer_stage_counter(rule_labels)

        # 2. 呼叫 LLM
        llm_result = self._classify_llm(message_text)

        # 3. 合併：優先用 LLM 的結果，沒有則 fallback 到 rule-based
        final_stage = llm_result.get("stage", rule_stage)
        final_labels = llm_result.get("labels") if llm_result.get("labels") else (rule_labels or ["none"])
        rationale = llm_result.get("rationale", {})

        # 4. 補齊 rationale 裡可能缺的欄位
        # input_type fallback
        if "input_type" not in rationale:
            if any(pat.search(message_text) for pat, _ in NARRATIVE_PATTERNS):
                matched = next((pat.pattern for pat, lab in NARRATIVE_PATTERNS if pat.search(message_text)), "")
                rationale["input_type"] = f"Matched pattern /{matched}/"
            else:
                rationale["input_type"] = "No narrative patterns matched"
        # stage reasoning fallback
        if "stage" not in rationale:
            rationale["stage"] = f"Fallback: inferred stage {final_stage}"
        # labels reasoning fallback
        if "labels" not in rationale or not isinstance(rationale["labels"], dict):
            rationale["labels"] = {lbl: f"Matched pattern for '{lbl}'" for lbl in final_labels}

        return {
            "stage": final_stage,
            "labels": final_labels,
            "rationale": rationale
    }

    """
    def analyze_message(self, message_text: str) -> Dict[str, Any]:
        
        #分析輸入文本，判斷詐騙階段和觸發標籤。
        #優先使用正則表達式匹配，如果沒有匹配到，則使用 LLM。
        
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
    """
    
    def analyze_message(self, message_text: str) -> dict:
        # 偵測是否為「自身經驗敘述」
        narrative_label = None
        narrative_reason = "No narrative patterns matched"
        for pat, lab in NARRATIVE_PATTERNS:
            if pat.search(message_text):
                narrative_label = lab
                narrative_reason = f"Matched pattern /{pat.pattern}/"
                break

        # 走原本 scam stage + label 偵測邏輯（封裝成 helper）
        stage_result = self._detect_scam_stage(message_text)  
        labels = stage_result.get("labels", [])

        # 把 experience label 加進去
        if narrative_label:
            labels.append(narrative_label)
            input_type = "experience"
        else:
            input_type = "dialogue"

        # 組成結果
        result = {
            "input_type": input_type,
            "narrative_reason": narrative_reason,
            **stage_result,  
            "labels": labels,
        }
        return result
    
    def _infer_stage_counter(self, lbls: List[str]) -> int:
        """
        根據匹配到的關鍵字標籤計數，推斷詐騙階段。
        優先回傳最晚出現的行為（數字越大越後期）。
        """
        stage_priority = {
            6: {"repetition"},
            5: {"sexual_request"},
            4: {"payment"},
            3: {"crisis", "emotion", "urgency", "pressure"},
            2: {"romance", "bonding"},
            1: {"friendly", "shared_interest", "compliment"},
            0: {"greeting"}
    }

        # 依照優先順序（從高到低）檢查是否出現
        for stage, keywords in stage_priority.items():
            if any(label in keywords for label in lbls):
                return stage

        return 0  

    """ 
    def _infer_stage_counter(self, lbls: List[str]) -> int:
        
        根據匹配到的關鍵字標籤計數，推斷詐騙階段。
        
        c = {k: 0 for k in RULES.keys()}
        for l in lbls:
            if l in c:
                c[l] += 1

        if c["termination"] >= 1 or c["recycle"] >= 1:
            return 6
        if c["payment"] >= 1:
            return 4
        if c["crisis"] >= 1:
            return 3
        return 0
    """

    def get_stage_info(self, stage_num: int) -> tuple:
        """獲取特定詐騙階段的名稱和建議。"""
        return STAGE_INFO.get(stage_num, ("未知階段", "請留意對話內容"))

    def get_label_desc(self, label: str) -> tuple:
        """獲取特定標籤的描述。"""
        return LABEL_DESC.get(label, (label, ""))

    def is_llm_available(self) -> bool:
        """檢查 LLM 功能是否可用。"""
        return self.openai_client is not None