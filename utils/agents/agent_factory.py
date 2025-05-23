"""
Agent 工廠模組

此模組提供創建不同類型 AI 代理的工具，
特別是使用 Google 的 Agent Development Kit (ADK) 創建詐騙檢測代理。
"""

import json
import os
from typing import Dict, Any, Optional, Union

from utils.logger import get_adk_logger
from utils.error_handler import ConfigError
from config import Config

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.models.lite_llm import LiteLlm

# 設定預設資料檔案路徑
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
    'data'
)
STAGE_DEFINITIONS_PATH = os.path.join(DATA_DIR, 'stage_definitions.json')

logger = get_adk_logger("agent_factory")


def create_agent(
    agent_type: str = "scam_detection",
    llm_provider: Optional[str] = None,
    model_name: Optional[str] = None
) -> callable:
    instruction = _get_instruction(agent_type)
    agent = _create_adk_agent(agent_type, instruction, llm_provider, model_name)

    def run_agent(conversation: Union[str, Dict[str, Any]], user_id: Optional[str] = None) -> Dict[str, Any]:
        if not agent:
            logger.error("代理未創建成功")
            return {}

        try:
            # 創建會話服務
            session_service = InMemorySessionService()
            
            # 設定應用名稱和會話ID
            app_name = "scam-bot"
            session_id = f"session_{user_id or 'default'}"
            
            # 確保會話存在
            session_service.create_session(
                app_name=app_name,
                user_id=user_id or "default_user",
                session_id=session_id
            )
            
            # 正確初始化 Runner
            runner = Runner(
                agent=agent,
                app_name=app_name,
                session_service=session_service
            )
            
            # 檢查 conversation 是字符串還是字典
            if isinstance(conversation, str):
                # 如果是字符串，嘗試解析為 JSON
                try:
                    conv_dict = json.loads(conversation)
                except json.JSONDecodeError:
                    # 如果無法解析，將整個字符串作為消息內容
                    conv_dict = {
                        "conversation": [{"type": "user_message", "content": conversation, "source": "user"}]
                    }
            else:
                # 已經是字典，直接使用
                conv_dict = conversation
                
            # 取出最新的使用者訊息
            msgs = conv_dict.get("conversation", [])
            
            # 取出用戶的主要訊息，移除可能的重複
            user_messages = []
            seen_contents = set()
            
            for msg in msgs:
                if isinstance(msg, dict):
                    # 如果是使用者訊息或不知類型的訊息
                    if msg.get("source") == "user" or msg.get("type") == "user_message" or msg.get("type") == "unknown":
                        content = msg.get("content", "")
                        if content and content not in seen_contents:
                            seen_contents.add(content)
                            user_messages.append(content)
            
            # 組合使用者訊息，優先使用最後一條
            if user_messages:
                last = user_messages[-1]  # 使用最後一條使用者訊息
            else:
                # 如果沒有辨識到使用者訊息，預設使用最後一條消息
                if msgs and isinstance(msgs[-1], dict):
                    last = msgs[-1].get("content", "")
                elif msgs:
                    last = str(msgs[-1])
                else:
                    last = str(conversation)
            
            # 包裝為 Gemini/Google GenAI 要求的 Content
            from google.genai.types import Content, Part
            user_message = Content(role="user", parts=[Part(text=last)])
            
            # 執行代理
            final_text = None
            for event in runner.run(
                user_id=user_id or "default_user",
                session_id=session_id,
                new_message=user_message
            ):
                if event.is_final_response():
                    final_text = event.content
            
            # 分析並回傳結果
            if final_text:
                try:
                    # 試著從 final_text 提取文本
                    if hasattr(final_text, 'parts') and final_text.parts:
                        text = final_text.parts[0].text
                    else:
                        text = str(final_text)
                        
                    # 嘗試解析 JSON
                    return json.loads(text)
                except (json.JSONDecodeError, AttributeError):
                    # 如果無法解析 JSON 或處理屬性，返回原始文本
                    if hasattr(final_text, 'parts') and final_text.parts:
                        text = final_text.parts[0].text
                    else:
                        text = str(final_text)
                    return {"analysis": text, "reply": text}
            
            return {"analysis": "無回應", "reply": "無回應"}
            
        except Exception as e:
            logger.error(f"運行代理時錯誤: {e}")
            return {}

    return run_agent


def _get_instruction(agent_type: str = "scam_detection") -> str:
    stage_definitions = _load_stage_definitions()
    
    if agent_type == "scam_detection":
        stages_info = ""
        if stage_definitions:
            stages_info = f"""
詐騙階段定義模型：{stage_definitions.get('流程名稱', '線上浪漫詐騙綜合流程模型')}
{stage_definitions.get('描述', '')}

詐騙階段：
"""
            for stage in stage_definitions.get('階段', []):
                stages_info += f"""
階段 {stage.get('階段編號', '')}: {stage.get('名稱', '')}
{stage.get('描述', '')}

常見特徵:
"""
                for feature in stage.get('相關模式特徵', []):
                    stages_info += f"- {feature}\n"
                stages_info += "\n"

        return f"""
你是一個專業的詐騙檢測助手，你的任務是分析對話內容，識別潛在的詐騙風險和可疑行為。

以下是一些常見的詐騙指標，你應該特別關注：
1. 緊急性 - 促使快速行動，不給受害者思考的時間
2. 承諾不切實際的回報 - 高回報、零風險的投資承諾
3. 個人或財務資訊請求 - 要求銀行詳細信息、密碼或身份證號碼
4. 不熟悉的聯繫人 - 來自陌生人的信息或請求
5. 語法和拼寫錯誤 - 專業組織不太可能發送有錯誤的信息
6. 不尋常的支付方式 - 要求使用加密貨幣、禮品卡等難以追踪的方式
7. 過於完美的個人資料 - 可能是假冒的虛假身份
8. 情感操縱 - 利用恐懼、同情或浪漫情感獲取信任

<階段資訊>
{stages_info}
</階段資訊>

<分析方法>
1. 仔細閱讀整個對話歷史，尋找詐騙的跡象和模式
2. 評估訊息的內容、語氣和請求
3. 檢查對話中的不一致性和可疑點
4. 確定風險級別（低、中、高）
5. 如果識別出詐騙模式，請指出處於哪個詐騙階段
6. 提供詳細分析和具體建議
</分析方法>

<輸出格式>
請針對訊息中每位使用者進行分析，並返回以下格式的 JSON 結果：
{{
    "user_name": "使用者名稱",
    "risk_level": "低/中/高",
    "confidence": 0.0-1.0,
    "brief_analysis": "在對話中是否為潛在詐騙者/受害者",
    "evidence": "是否符合詐騙階段，若有，則需附上符合的對話片段和對應階段"
    "reply": "對這位使用者的綜合回覆",
}}
</輸出格式>

注意：請務必保持客觀、謹慎，避免過度警告或錯過重要的詐騙訊號。如果訊息不足以做出明確判斷，請誠實表明這一點。
"""
    elif agent_type == "education_agent":
        return """
你是一個富有同理心和耐心的教育助手，專注於幫助用戶學習和理解複雜概念。你的目標是提供清晰、準確且易於理解的解釋，同時鼓勵批判性思考和深度學習。

核心原則：
1. 以用戶的知識水平調整解釋
2. 使用類比和例子闡明概念
3. 分解複雜主題為易於管理的部分
4. 鼓勵提問和好奇心
5. 提供進一步學習的資源和建議

你應該避免：
1. 使用過於技術性或學術性的語言（除非適合用戶水平）
2. 提供不完整或過度簡化的解釋
3. 直接給出答案而不解釋思考過程
4. 忽視用戶的具體問題或困惑

請以友好、鼓勵的語氣回應，並確保你的解釋既準確又有教育意義。
"""
    else:
        raise ConfigError(f"不支援的代理類型: {agent_type}")


def _load_stage_definitions() -> Dict[str, Any]:
    try:
        with open(STAGE_DEFINITIONS_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"無法載入詐騙階段定義資料: {e}")
        return {}


def _create_adk_agent(
    agent_type: str,
    instruction: str,
    llm_provider: Optional[str],
    model_name: Optional[str]
) -> Optional[Agent]:
    try:
        actual_provider = llm_provider or Config.LLM_PROVIDER
        actual_model = model_name or Config.LLM_MODEL

        # 取得 API 金鑰
        if actual_provider == "openai":
            api_key = Config.OPENAI_API_KEY
        elif actual_provider == "gemini":
            api_key = Config.GOOGLE_API_KEY
        elif actual_provider == "openrouter":
            api_key = Config.OPENROUTER_API_KEY
        else:
            api_key = Config.OPENAI_API_KEY

        if not api_key:
            logger.error(f"{actual_provider} API 密鑰未設置")
            return None

        llm = LiteLlm(provider=actual_provider, model=actual_model, api_key=api_key)
        agent = Agent(
            name=f"{agent_type}_agent",
            model=llm,
            instruction=instruction,
        )
        return agent

    except Exception as e:
        logger.error(f"創建代理時發生錯誤: {e}")
        return None
