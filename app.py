# repo-main/app.py

print("👉 This is integratescambot-main version")

from flask import Flask, jsonify
from config import Config
from utils.logger import app_logger as logger
from utils.error_handler import AppError, ConfigError
from services.conversation_service import ConversationService
from services.domain.detection.detection_service import DetectionService
from clients.line_client import LineClient
from clients.analysis_api import AnalysisApiClient
from bot.line_webhook import line_webhook, LineWebhookHandler
from dotenv import load_dotenv 

print("👉 This is integratescambot-main version")

def create_app():
    app = Flask(__name__)

    # 載入 .env
    load_dotenv()

    # 初始化 line client
    line_client = LineClient(Config.LINE_CHANNEL_ACCESS_TOKEN)

    # 初始化分析 API client（可選）
    analysis_client = None
    if Config.ANALYSIS_API_URL:
        analysis_client = AnalysisApiClient(Config.ANALYSIS_API_URL)

    # 初始化 detection service (它內部會初始化 OpenAI 客戶端)
    detection_service = DetectionService(analysis_client=analysis_client) # 將 analysis_client 傳入

    # 初始化 conversation service
    conversation_service = ConversationService(detection_service=detection_service, line_client=line_client)

    # 初始化 webhook handler
    webhook_handler = LineWebhookHandler(conversation_service=conversation_service, channel_secret=Config.LINE_CHANNEL_SECRET)

    # 將 handler 實例設定到藍圖上，以便在藍圖的路由中訪問
    line_webhook.webhook_handler = webhook_handler # type: ignore

    # 註冊藍圖
    app.register_blueprint(line_webhook)

    # 錯誤處理器
    @app.errorhandler(AppError)
    def handle_app_error(error):
        logger.error(f"應用程式錯誤: {error.message}", exc_info=True)
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    # 健康檢查
    @app.route("/")
    def index():
        return "詐騙檢測機器人正在執行中!"

    @app.route("/health")
    def health_check():
        # 這裡可以添加更詳細的服務健康檢查
        return jsonify({
            "status": "ok",
            "services": {
                "line_client": "ok", # 假設初始化成功即為 ok
                "detection_service": "ok" if detection_service.is_llm_available() else "warning (LLM not available)"
            }
        })

    return app

# 啟動 Flask 應用程式
try:
    app = create_app()
except Exception as e:
    # 這裡使用從 utils.logger 導入的 logger
    logger.critical(f"無法創建應用程式: {str(e)}", exc_info=True)
    # 在無法創建應用程式時，直接退出，因為無法正常運行
    import sys
    sys.exit(1)

if __name__ == "__main__":
    port = Config.PORT
    debug = Config.DEBUG
    logger.info(f"詐騙檢測機器人啟動於埠口 {port} (除錯模式={debug})")
    try:
        app.run(host="0.0.0.0", port=port, debug=debug)
    except Exception as e:
        logger.critical(f"運行應用程式時發生錯誤: {str(e)}", exc_info=True)
        import sys
        sys.exit(1)
