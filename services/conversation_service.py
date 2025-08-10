# repo-main/services/conversation_service.py

import logging
import json
import re
from typing import Dict, List, Any, Optional
from collections import defaultdict
from openai import OpenAI
from config import Config
from services.domain.detection.detection_service import DetectionService
from services.gemini_client import GeminiClient
from clients.line_client import LineClient, COMMON_QR
from linebot.models import FlexSendMessage, QuickReply # <--- 將 QuickReply 添加到這裡

logger = logging.getLogger(__name__)


RECOMMENDED_ACTIONS = {
    0: "Be cautious. Don't share personal info yet; observe the conversation.",
    1: "Do not send money. Ask for real-time verification like webcam or voice call.",
    2: "Slow down. Confirm identity independently before proceeding.",
    3: "Refuse money requests. Seek external confirmation and stop escalation.",
    4: "Stop transfers. Report the suspicious request and verify via other channels.",
    5: "Do not share private/sexual content. Beware of blackmail.",
    6: "Be skeptical of repeat contact; the scam may be resurfacing."
}


class ConversationService:
    """
    負責管理用戶對話流程、狀態和生成回覆。
    協調檢測服務和 LINE 客戶端。
    """
    def __init__(self, detection_service: DetectionService, line_client: LineClient):
        self.detection_service = detection_service
        self.line_client = line_client
        self.gemini_client = None
        if Config.GEMINI_API_KEY:
            try:
                self.gemini_client = GeminiClient(api_key=Config.GEMINI_API_KEY)
            except Exception as e:
                logger.error(f"Gemini init failed: {e}", exc_info=True)

        # 用於儲存每個用戶的當前會話狀態，例如最後的檢測結果
        self.STATE = defaultdict(lambda: {"risk": 0, "money_calls": 0, "last_result": {}})
        # 用於儲存用戶聊天歷史
        self.user_chat_history = defaultdict(list)

        self.openai_client = None
        if Config.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
                logger.info("ConversationService: OpenAI client initialized successfully.")
            except Exception as e:
                logger.error(f"ConversationService: Failed to initialize OpenAI client：{e}", exc_info=True)
                self.openai_client = None
        else:
            logger.warning("ConversationService: OPENAI_API_KEY isn't set. LLM related functions cannot be used.")

    def _format_detection_summary(self, result: dict) -> str:
        input_type_raw = result.get("input_type", "dialogue")
        stage_num = result.get("stage", 0)
        stage_name, stage_desc = self.detection_service.get_stage_info(stage_num)
        labels = result.get("labels", [])
        rationale = result.get("rationale", {})

        # 細節用的 normalization（將 alias 統一成 canonical）
        def normalize_label(lab: str) -> str:
            alias_map = {
                "identity": "identity_inconsistency",
                # 以後有別的 alias 再加進來
            }
            return alias_map.get(lab, lab)

        # 去重
        seen = set()
        dedup_labels = []
        for lab in labels:
            if lab not in seen:
                seen.add(lab)
                dedup_labels.append(lab)

        parts = []
        input_type_reason = (rationale.get("input_type") or "").strip()
        stage_reason = (rationale.get("stage") or "").strip()

        # humanized input type 表示
        display_input_type = "Personal experience" if input_type_raw == "experience" else "Dialogue"
        if input_type_raw == "dialogue" and input_type_reason:
            parts.append(f"Input type: Dialogue (contains wording that resembles personal experience: {input_type_reason})")
        elif input_type_raw == "experience" and input_type_reason:
            parts.append(f"Input type: Personal experience: {input_type_reason}")
        else:
            parts.append(f"Input type: {display_input_type}")

        parts.append(f"Stage: {stage_name} ({stage_num})")
        if stage_reason:
            parts.append(f"Stage reasoning: {stage_reason}")
        parts.append("Scam triggers:")

        # 只顯示前 3 個 trigger，避免太長
        max_show = 3
        shown = dedup_labels[:max_show]
        for lab in shown:
            norm = normalize_label(lab)
            title, detail = self.detection_service.get_label_desc(norm)
            label_reason = (rationale.get("labels", {}) or {}).get(lab, "")
            line = f"- {title}: {detail}"
            if label_reason:
                line += f" (Reason: {label_reason})"
            parts.append(line)

        if len(dedup_labels) > max_show:
            parts.append(f"...and {len(dedup_labels) - max_show} more triggers")

        return "\n".join(parts)



    def handle_message(self, user_id: str, message_text: str, reply_token: str):
        """
        處理接收到的文字訊息。
        """
        logger.info(f"處理訊息: User ID={user_id}, Message='{message_text}'")

        # --- 特殊指令處理：「下一段偵測」---
        if message_text == "Next detection":
            self.STATE[user_id]["last_result"] = {} # 重置上一個檢測結果
            self.STATE[user_id]["last_result"]["raw_text"] = message_text
            self.user_chat_history[user_id].clear() # 清除聊天歷史
            logger.info(f"User {user_id} reset detection status.")
            reset_bubble_content = {
              "type":"bubble",
              "body":{"type":"box","layout":"vertical","contents":[
                {"type":"text",
                 "text":"📩 Please send the next conversation and I will start detecting again.",
                 "wrap":True, "align":"center"}
              ]}
            }
            self.line_client.reply_flex(reply_token, self._build_flex_message_from_content(
                alt_text="Reset Detection", contents=reset_bubble_content, quick_reply=COMMON_QR))
            return
            
        if message_text in ["Use OpenAI", "Use Gemini"]:
            model = "openai" if "OpenAI" in message_text else "gemini"
            self.STATE[user_id]["model"] = model
            logger.info(f"User {user_id} switch model to {model}")
            self.line_client.reply_text(reply_token, f"✅ Switched to {model.upper()} ")
            return

        # --- 特殊指令處理：「聊聊更多」---
        if message_text == "Chat more":
            logger.info(f"User {user_id} request to chat more.")
            history = self.user_chat_history.get(user_id, [])
            if not history:
                self.line_client.reply_text(reply_token, "There is currently no chat history that can be extended!")
                return

            if not self.openai_client:
                logger.warning("The OpenAI client is not initialized or the API Key is invalid, so the 'Chat More' function cannot be provided.")
                self.line_client.reply_text(reply_token, "Sorry, AI features are currently unavailable. Please check your API Key or quota.")
                return

            prompt_history = "\n".join(history[-5:]) # 只取最近的 5 條訊息
            prompt = "The following is a record of the conversation between me and the other party：\n" + prompt_history + "\n please continue chatting with me based on this content."

            try:
                rsp = self.openai_client.chat.completions.create(
                  model="gpt-4o-mini",
                  messages=[{"role":"user","content":prompt}]
                )
                self.line_client.reply_text(reply_token, rsp.choices[0].message.content)
            except Exception as e:
                logger.error(f"ChatGPT 'Chat More' failed：{e}", exc_info=True)
                self.line_client.reply_text(reply_token, "Sorry, no further conversation is available at this time. Please confirm that your OpenAI API Key or quota is in good condition.")
            return


        # --- 主要訊息分析流程 ---
        self.user_chat_history[user_id].append(message_text) # 儲存當前訊息

        result = self.detection_service.analyze_message(message_text)
        self.STATE[user_id]["last_result"] = result

        # log 出來方便開發看
        logger.debug(f"[DEBUG] user={user_id} last_result labels={result.get('labels')} stage={result.get('stage')} rationale={result.get('rationale')}")

        flex_message_to_send = self._build_detection_flex_message(result)
        self.line_client.reply_flex(reply_token, flex_message_to_send)



    def handle_postback(self, user_id: str, data: str, reply_token: str):
        """
        處理接收到的 Postback 事件。
        """
        logger.info(f"處理 Postback: User ID={user_id}, Data={data}")

        last_result = self.STATE[user_id].get("last_result", {})
        if not last_result or last_result.get("stage") is None:
            logger.warning(f"Postback received but last_result is invalid for user {user_id}. Sending prompt.")
            self.line_client.reply_text(reply_token, "Sorry, please send a conversation first so that I can analyze it and provide you with judgment basis or prevention suggestions.")
            return

        if data == "action=explain":
            flex = self.build_explanation_flex(user_id)
            self.line_client.reply_flex(reply_token, flex)
        elif data == "action=prevent":
            flex = self.build_prevention_flex(user_id)
            self.line_client.reply_flex(reply_token, flex)
        elif data == "action=explain_more":
            detailed = self._explain_more(user_id)
            self.line_client.reply_text(reply_token, detailed)
        elif data == "action=prevent_more":
            flex = self.build_prevention_detail_flex(user_id)
            self.line_client.reply_flex(reply_token, flex)


    def _generate_recommendation_action(self, message_text: str, stage_num: int, labels: List[str]) -> str:
        """
        動態產出一句 Recommended Action。
        利用 LLM，根據原始訊息、stage 與觸發 labels，產出一句操作建議。
        """
        if not self.openai_client:
            return "Unable to generate recommendation at this time."

        # 將 labels 轉成人可讀文字
        triggers = ", ".join(self.detection_service.get_label_desc(l)[0] for l in labels)

        prompt = (
            f"You are a fraud-detection assistant. "
            f"For the user message: \"{message_text}\" "
            f"you have classified it as stage {stage_num} and detected triggers: {triggers}. "
            "Write one concise, practical recommended action in a single sentence."
        )
        try:
            rsp = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user", "content": prompt}],
                timeout=10
            )
            return rsp.choices[0].message.content.strip().replace("\n", " ")
        except Exception as e:
            logger.warning(f"Recommendation generation failed: {e}")
            return "Consider verifying identity before proceeding."



    def _explain_classification(self, user_id: str) -> str:
        last = self.STATE[user_id].get("last_result", {})
        if not last or last.get("stage") is None:
            return "Sorry, I can't find the last test result. Please send a message for analysis."

        # 先用 rationale 組解釋
        rationale = last.get("rationale", {})
        if rationale:
            parts = []
            input_type_reason = rationale.get("input_type", "")
            stage_reason = rationale.get("stage", "")
            label_reasons = rationale.get("labels", {})

            if input_type_reason:
                parts.append(input_type_reason)
            if stage_reason:
                parts.append(f"Stage reasoning: {stage_reason}")
            # 前兩個 label 的理由
            cnt = 0
            for lab, reason in label_reasons.items():
                title, _ = self.detection_service.get_label_desc(lab)
                parts.append(f"{title}: {reason}")
                cnt += 1
                if cnt >= 2:
                    break
            return " ".join(parts)

        # fallback to original LLM-style explanation if no rationale
        if self.gemini_client:
            # existing gemini logic...
            return self.gemini_client.chat(f"...")  # you can keep original prompt here
        elif self.openai_client:
            try:
                stage_num = last.get("stage", 0)
                stage_name_for_explain = self.detection_service.get_stage_info(stage_num)[0]
                trigger_factors = "、".join([
                    self.detection_service.get_label_desc(lab)[0]
                    for lab in last.get("labels", [])
                ]) or "none"
                prompt = (
                    f"I just detected a message, classified as stage {stage_num} ({stage_name_for_explain}), "
                    f"the trigger factors are {trigger_factors}. Please use 2 to 3 sentences to briefly explain why you made such a judgment."
                )
                rsp = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                return rsp.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"OpenAI judgment explanation failed: {e}", exc_info=True)
        return "Description is currently unavailable, please try again later."


    def _get_structured_prevention_suggestions(self, last_result: dict) -> List[str]:
        stage_num = last_result.get("stage", 0)
        stage_name = self.detection_service.get_stage_info(stage_num)[0]
        labels = last_result.get("labels", []) or []
        trigger_names = ", ".join([self.detection_service.get_label_desc(lab)[0] for lab in labels]) or "none"

        prompt = (
            f"Given fraud stage {stage_num} ({stage_name}) and trigger factors {trigger_names}, "
            "provide exactly three practical prevention suggestions. "
            "Return them as a numbered list, each in one sentence."
        )
        lines = []
        if self.openai_client:
            try:
                rsp = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}]
                )
                text = rsp.choices[0].message.content.strip()
                for line in text.splitlines():
                    if not line.strip():
                        continue
                    cleaned = re.sub(r'^\s*\d+\.\s*', '', line).strip()
                    if cleaned:
                        lines.append(cleaned)
                # 去重
                unique = []
                for l in lines:
                    if l not in unique:
                        unique.append(l)
                lines = unique
            except Exception:
                logger.warning("Structured prevention suggestions failed, falling back.")

        # 補足到三條（fallback + 保險）
        if len(lines) < 3:
            base = RECOMMENDED_ACTIONS.get(stage_num, "Be cautious and verify independently.")
            extras = []
            # 先放 base
            if base not in lines:
                extras.append(base)
            # 補兩個 generic
            generic_candidates = [
                "Verify identity through an independent channel before trusting requests.",
                "Do not send money or sensitive data until you confirm authenticity.",
                "Take a break and reassess the situation; avoid pressure-driven decisions."
            ]
            for cand in generic_candidates:
                if len(lines) + len(extras) >= 3:
                    break
                if cand not in lines and cand not in extras:
                    extras.append(cand)
            lines.extend(extras[: max(0, 3 - len(lines))])

        # 最後保證最多三條
        return lines[:3]

    def _get_detailed_prevention_explanations(self, last_result: dict, summaries: List[str]) -> List[str]:
        stage_num = last_result.get("stage", 0)
        stage_name = self.detection_service.get_stage_info(stage_num)[0]
        trigger_names = ", ".join([self.detection_service.get_label_desc(lab)[0] for lab in (last_result.get("labels") or [])]) or "none"

        summary_list_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(summaries))
        prompt = (
            f"Earlier you gave three concise prevention suggestions for fraud stage {stage_num} ({stage_name}) "
            f"based on the trigger factors: {trigger_names}:\n"
            f"{summary_list_text}\n"
            "Please expand each of the three suggestions into a detailed explanation. "
            "For each one, explain why it's important and how to implement it in practice, using 2 to 3 sentences per item. "
            "Keep the numbering (1., 2., 3.) and return only a numbered list; do not add extra introductory or closing paragraphs."
        )

        if self.openai_client:
            try:
                rsp = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}]
                )
                text = rsp.choices[0].message.content.strip()
                lines = []
                for line in text.splitlines():
                    if not line.strip():
                        continue
                    cleaned = re.sub(r'^\s*\d+\.\s*', '', line).strip()
                    if cleaned:
                        lines.append(cleaned)
                # 保留前三條（萬一有多）
                if len(lines) >= 3:
                    return lines[:3]
                if lines:
                    return lines
            except Exception:
                logger.warning("Detailed prevention explanations failed, falling back.")
        # fallback: 把 summary 原封不動回去
        return summaries[:3]


    def _prevention_suggestions(self, user_id: str) -> str:
        """
        根據用戶上次的詐騙檢測結果，生成防範建議文本。
        """
        if not self.openai_client:
            logger.warning("The OpenAI client is not initialized or the API Key is invalid. No prevention suggestions can be provided.")
            return "Sorry, AI features are currently unavailable. Please check your API Key or quota."

        last = self.STATE[user_id].get("last_result")
        if not last or last.get("stage") is None:
            logger.warning(f"_prevention_suggestions: User {user_id} last_result is invalid or missing stage.")
            return "Sorry, the last test result was not found and I cannot provide any preventive advice. Please send me a message for analysis."

        # 確保 stage 在 STAGE_INFO 中存在，否則使用預設值
        stage_num = last.get("stage", 0)
        # 從 detection_service 獲取 stage_name
        stage_name_for_prevent = self.detection_service.get_stage_info(stage_num)[0]

        # 組合觸發因子名稱，如果沒有則顯示「無」
        trigger_factors = "、".join([
            self.detection_service.get_label_desc(lab)[0]
            for lab in last.get("labels", [])
        ]) or "無"

        prompt = (
          f"According to the fraud stage {stage_num} ({stage_name_for_prevent}），"
          f"Trigger factors {trigger_factors}，"
          "Please list 3 of the most practical prevention suggestions."
        )
        try:
            rsp = self.openai_client.chat.completions.create(
              model="gpt-4o-mini",
              messages=[{"role":"user", "content":prompt}]
            )
            return rsp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Failed to provide prevention advice: {e}", exc_info=True)
            return "Sorry, we cannot provide any prevention suggestions at this time. Please check if your OpenAI API Key or quota is normal."


    def _explain_more(self, user_id: str) -> str:
        last = self.STATE[user_id].get("last_result", {})
        if not last or last.get("stage") is None:
            return "Sorry, I can't find the previous analysis results. Please send me a message first so I can analyze it."

        stage_num = last.get("stage", 0)
        stage_name = self.detection_service.get_stage_info(stage_num)[0]
        labels = last.get("labels", [])
        input_type = last.get("input_type", "dialogue")
        rationale = last.get("rationale", {})

        trigger_names = ", ".join([self.detection_service.get_label_desc(lab)[0] for lab in labels]) or "none"
        prompt = (
            f"I previously classified a message as stage {stage_num} ({stage_name}) with input type '{input_type}'. "
            f"The detected triggers are: {trigger_names}. "
            f"Existing brief rationale: input_type: {rationale.get('input_type','')}; "
            f"stage: {rationale.get('stage','')}; labels: {rationale.get('labels',{})}. "
            "Please provide a more detailed explanation (4-5 sentences) of why this classification makes sense, "
            "including how the combination of signals supports the stage and any caveats or uncertainties."
        )

        if self.gemini_client:
            return self.gemini_client.chat(prompt)
        elif self.openai_client:
            try:
                rsp = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                return rsp.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Explain more failed: {e}", exc_info=True)
                return "Sorry, failed to get a more detailed explanation, please try again later."
        return "The explain feature is currently unavailable."


    def _build_flex_message_from_content(self, alt_text: str, contents: dict, quick_reply: Optional[QuickReply] = None) -> FlexSendMessage:
        """
        輔助函數：從內容字典構建 FlexSendMessage。
        """
        return FlexSendMessage(alt_text=alt_text, contents=contents, quick_reply=quick_reply)

    # repo-main/services/conversation_service.py

        # ... 其他程式碼 ...
    def _build_detection_flex_message(self, result: dict) -> FlexSendMessage:
        stage_num = result.get("stage", 0)
        s_name, stage_desc = self.detection_service.get_stage_info(stage_num)
        rationale = result.get("rationale", {}) or {}
        labels = result.get("labels", []) or []

        # recommended actions 
        raw = result.get("raw_text", "")
        labels = result.get("labels", [])
        recommended_actions_text = self._generate_recommendation_action(raw, stage_num, labels)

        # 處理 LLM error
        if result.get("llm_error"):
            stage_display_title = "❌ Analysis Exception"
            color = "#FF0000"
            recommended_actions_text = (
                f"AI features temporarily unavailable. Reason: {result.get('error_message', 'Unknown error')}. Please try again later."
            )
        else:
            stage_display_title = f"🔎 Current stage: "
            color = "#1DB446" if stage_num <= 1 else "#FF0000" if stage_num >= 3 else "#FFBB00"

        # 第一個 bubble：核心判定 + 推薦動作
        bubble_main = {
            "type": "bubble",
            "body": {
                "type": "box", "layout": "vertical", "spacing": "md", "contents": [
                    {"type": "text", "text": "🔎 Current Stage", "weight": "bold", "size": "xl", "color": color, "wrap": True},
                    {"type": "text", "text": f"Stage {stage_num} {s_name}", "weight": "bold", "size": "lg", "color": color, "wrap": True, "margin": "sm"},
                    {"type": "text", "text": stage_desc, "size": "sm", "wrap": True, "margin": "sm"},
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": f"👉 Recommended Actions: {recommended_actions_text}", "wrap": True, "margin": "md", "size": "sm"},
                ],
            },
            "footer": {
                "type": "box", "layout": "horizontal", "contents": [
                    {"type": "button", "style": "link", "height": "sm", "flex": 1,"action": {"type": "postback", "label": "Why & Explain", "data": "action=explain"}},
                    { "type": "button", "style": "link", "height": "sm", "flex": 1,"action": {"type": "postback", "label": "Prevent", "data": "action=prevent"}},
                ]
            },
        }

        # 第二個 bubble：triggers + rationale（每個 trigger 用小卡片模擬）
        # 去重
        seen = set()
        dedup_labels = []
        for lab in labels:
            if lab not in seen:
                seen.add(lab)
                dedup_labels.append(lab)

        def normalize_label(lab: str) -> str:
            alias_map = {
                "identity": "identity_inconsistency",
            }
            return alias_map.get(lab, lab)

        trigger_boxes = []
        for lab in dedup_labels:
            norm = normalize_label(lab)
            title, detail = self.detection_service.get_label_desc(norm)
            label_reason = (rationale.get("labels", {}) or {}).get(lab, "")
            # 每個 trigger 小卡
            trigger_box = {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "margin": "sm",
                "cornerRadius": "8px",
                "borderColor": "#E0E0E0",
                "borderWidth": "1px",
                "backgroundColor": "#FAFAFC",
                "contents": [
                    {
                        "type": "text",
                        "text": f"🔸 {title}",
                        "weight": "bold",
                        "size": "sm",
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": detail + (f" (Reason: {label_reason})" if label_reason else ""),
                        "size": "xs",
                        "wrap": True,
                        "margin": "xs",
                    },
                ],
            }
            trigger_boxes.append(trigger_box)

        # 如果 trigger 太多，可以加個總結
        if len(dedup_labels) > len(trigger_boxes):
            trigger_boxes.append(
                {
                    "type": "text",
                    "text": f"...and {len(dedup_labels) - len(trigger_boxes)} more triggers",
                    "size": "xs",
                    "wrap": True,
                    "margin": "sm",
                }
            )

        bubble_triggers = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "🔍 Details & Triggers",
                        "weight": "bold",
                        "size": "md",
                        "wrap": True,
                    },
                    {"type": "separator", "margin": "md"},
                    *trigger_boxes,
                ],
            },
        }

        # carousel 包兩張
        flex_contents = {
            "type": "carousel",
            "contents": [bubble_main, bubble_triggers],
        }

        return self._build_flex_message_from_content(
            alt_text="Fraud Detection Results", contents=flex_contents, quick_reply=COMMON_QR
        )
        
        
    def build_explanation_flex(self, user_id: str) -> FlexSendMessage:
        last = self.STATE[user_id].get("last_result", {})
        if not last or last.get("stage") is None:
            bubble = {
                "type": "bubble",
                "body": {
                    "type": "box", "layout": "vertical", "spacing": "md", "contents": [
                        {"type": "text", "text": "No previous result to explain.", "wrap": True}
                    ],
                },
            }
            return FlexSendMessage(alt_text="Explanation", contents=bubble)

        stage_num = last.get("stage", 0)
        stage_name, stage_desc = self.detection_service.get_stage_info(stage_num)

        # 短解釋 + 深度解釋
        short_explanation = self._explain_classification(user_id)
        detailed_full = self._explain_more(user_id)

        # 拆前 2~3 句作為 condensed detailed
        detailed_sentences = re.split(r'(?<=[.!?])\s+', detailed_full)
        detailed_short = " ".join(detailed_sentences[:3]).strip()
        if len(detailed_short) > 300:  # 防太長
            detailed_short = detailed_short[:300].rstrip() + "..."
            
        color = "#1DB446" if stage_num <= 1 else "#FF0000" if stage_num >= 3 else "#FFBB00"
        
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box", "layout": "vertical", "spacing": "md",
                "contents": [
                    {"type": "text", "text": "🔍 Why & Explain", "weight": "bold", "size": "xl","color":color, "wrap": True},
                    {"type": "text", "text": f"Stage {stage_num} {stage_name}", "weight": "bold", "size": "lg", "margin": "sm","color":color, "wrap": True},
                    {"type": "text", "text": stage_desc, "size": "sm", "wrap": True, "margin": "sm"},
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": "Summary:", "weight": "bold", "size": "sm", "wrap": True, "margin": "sm"},
                    {"type": "text", "text": short_explanation, "size": "sm", "wrap": True, "margin": "xs"},
                    {"type": "text", "text": "Detailed reasoning:", "weight": "bold", "size": "sm", "wrap": True, "margin": "sm"},
                    {"type": "text", "text": detailed_short, "size": "sm", "wrap": True, "margin": "xs"},
                ],
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button", "style": "link", "height": "sm",
                        "action": {"type": "postback", "label": "More", "data": "action=explain_more"}
                    }
                ]
            }
        }
        return FlexSendMessage(alt_text="Explanation", contents=bubble)


    def build_prevention_flex(self, user_id: str) -> FlexSendMessage:
        last = self.STATE[user_id].get("last_result", {})
        if not last or last.get("stage") is None:
            bubble = {
                "type": "bubble",
                "body": {"type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": "No previous result to base prevention tips on.", "wrap": True}
                ]},
            }
            return FlexSendMessage(alt_text="Prevention", contents=bubble)

        stage_num = last.get("stage", 0)
        stage_name = self.detection_service.get_stage_info(stage_num)[0]
        summaries = self._get_structured_prevention_suggestions(last)  # 簡短三點

        # 把 summary 條列
        items = []
        for idx, s in enumerate(summaries):
            items.append({
                "type": "box",
                "layout": "baseline",
                "margin": "sm",
                "contents": [
                    {"type": "text", "text": f"{idx+1}.", "weight": "bold", "size": "sm", "flex": 0},
                    {"type": "text", "text": s, "size": "sm", "wrap": True, "margin": "xs"}
                ]
            })

        bubble = {
            "type": "bubble",
            "body": {
                "type": "box", "layout": "vertical", "spacing": "md",
                "contents": [
                    {"type": "text", "text": "🛡 Prevention Tips", "weight": "bold", "size": "lg"},
                    {"type": "text", "text": f"Stage {stage_num} {stage_name}", "weight": "bold", "size": "md", "margin": "sm"},
                    *items,
                ],
            },
            "footer": {
                "type": "box", "layout": "horizontal", "contents": [
                    {
                        "type": "button", "style": "link", "height": "sm",
                        "action": {"type": "postback", "label": "More", "data": "action=prevent_more"}
                    }
                ]
            }
        }
        return FlexSendMessage(alt_text="Prevention", contents=bubble)

    def build_prevention_detail_flex(self, user_id: str) -> FlexSendMessage:
        last = self.STATE[user_id].get("last_result", {})
        if not last or last.get("stage") is None:
            bubble = {"type": "bubble", "body": {"type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": "No previous result to expand prevention tips.", "wrap": True}
            ]}}
            return FlexSendMessage(alt_text="Prevention Details", contents=bubble)

        stage_num = last.get("stage", 0)
        stage_name = self.detection_service.get_stage_info(stage_num)[0]
        summaries = self._get_structured_prevention_suggestions(last)
        detailed = self._get_detailed_prevention_explanations(last, summaries)

        # 每條展開成一個小段
        contents = [
            {"type": "text", "text": "🛡 Prevention Tips (Detailed)", "weight": "bold", "size": "lg"},
            {"type": "text", "text": f"Stage {stage_num} {stage_name}", "weight": "bold", "size": "md", "margin": "sm"},
        ]
        for idx, detail in enumerate(detailed):
            contents.append({
                "type": "box",
                "layout": "vertical",
                "margin": "sm",
                "contents": [
                    {"type": "text", "text": f"{idx+1}.", "weight": "bold", "size": "sm"},
                    {"type": "text", "text": detail, "size": "sm", "wrap": True, "margin": "xs"},
                ]
            })

        bubble = {
            "type": "bubble",
            "body": {
                "type": "box", "layout": "vertical", "spacing": "md", "contents": contents
            }
        }
        return FlexSendMessage(alt_text="Prevention Details", contents=bubble)

