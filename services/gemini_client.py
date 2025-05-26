import google.generativeai as genai
import logging
from config import Config

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, api_key: str):
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-pro")
            logger.info("initialized Gemini Client successfully")
        except Exception as e:
            logger.error(f"init failed: {e}", exc_info=True)
            self.model = None

    def chat(self, prompt: str) -> str:
        if not self.model:
            return "Gemini init failed, please check logs"
        try:
            rsp = self.model.generate_content(prompt)
            return rsp.text.strip()
        except Exception as e:
            logger.error(f"Gemini res failed: {e}", exc_info=True)
            return "Gemini called failed, please check logs"