# repo-main/utils/error_handler.py

class AppError(Exception):
    """
    應用程式自定義基礎錯誤類別。
    """
    status_code = 500

    def __init__(self, message, status_code=None, original_error=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.original_error = original_error # 儲存原始錯誤，方便追蹤

    def to_dict(self):
        """將錯誤轉換為字典格式，用於 API 回覆。"""
        return {"message": self.message}

class ConfigError(AppError):
    """
    配置相關的錯誤。
    """
    def __init__(self, message, original_error=None):
        super().__init__(f"[CONFIG] {message}", status_code=500, original_error=original_error)

class LineClientError(AppError):
    """
    LINE Client 相關的錯誤。
    """
    def __init__(self, message, status_code=500, original_error=None):
        super().__init__(f"[LINE Client] {message}", status_code=status_code, original_error=original_error)

class DetectionError(AppError):
    """
    檢測服務相關的錯誤。
    """
    def __init__(self, message, status_code=500, original_error=None):
        super().__init__(f"[DETECTION] {message}", status_code=status_code, original_error=original_error)

class ValidationError(AppError):
    """
    輸入驗證相關的錯誤。
    """
    def __init__(self, message, original_error=None):
        super().__init__(f"[VALIDATION] {message}", status_code=400, original_error=original_error)