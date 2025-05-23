"""
LINE 對話匯出格式驗證工具

此模組提供驗證輸入文字是否符合 LINE 對話匯出格式基本特徵的工具。
"""

from utils.logger import get_service_logger
from utils.error_handler import ValidationError
import re
from typing import List, Union

# 取得模組特定的日誌記錄器
logger = get_service_logger("formatter")

# 正規表示式，用於基本格式檢查
DATE_REGEX = re.compile(r'^\d{4}\.\d{2}\.\d{2}\s+[\u4e00-\u9fa5]+$', re.MULTILINE)
MESSAGE_REGEX = re.compile(r'^\d{1,2}:\d{2}\s+.+\s+.+$', re.MULTILINE) # 簡化，只檢查 時間<空格>發送者<空格>內容 的基本模式

def validate_line_export(text_input: Union[str, List[str]]) -> str:
    """
    驗證輸入是否為有效的 LINE 對話匯出格式，並返回原始字串。

    Args:
        text_input: 包含 LINE 對話匯出的單一字串，或包含單一該字串的列表。

    Returns:
        str: 原始的有效 LINE 對話匯出字串。

    Raises:
        ValidationError: 如果輸入格式無效。
    """
    # 確保輸入是單一字串
    if isinstance(text_input, list):
        if len(text_input) == 1 and isinstance(text_input[0], str):
            text = text_input[0]
        else:
            error_msg = "格式驗證失敗：輸入列表應只包含一個字串元素。"
            logger.warning(error_msg)
            raise ValidationError(error_msg, status_code=400)
    elif isinstance(text_input, str):
        text = text_input
    else:
        error_msg = "格式驗證失敗：輸入必須是字串或包含單一字串的列表。"
        logger.warning(error_msg)
        raise ValidationError(error_msg, status_code=400)

    # 執行驗證
    is_valid = _check_line_format(text)

    if not is_valid:
        error_msg = "格式驗證失敗：輸入不符合 LINE 對話匯出格式的基本特徵。"
        logger.warning(error_msg)
        raise ValidationError(error_msg, status_code=400)

    logger.info("LINE 對話匯出格式驗證通過。")
    return text # 返回原始字串

def _check_line_format(text: str) -> bool:
    """
    執行基本的 LINE 格式檢查。

    Args:
        text: 要檢查的文字。

    Returns:
        bool: 如果格式看起來有效則返回 True，否則返回 False。
    """
    if not text or not isinstance(text, str):
        logger.warning("輸入文字為空或類型不正確。")
        return False

    # 1. 必須包含換行符 (匯出的基本特徵)
    if "\n" not in text:
        logger.warning("輸入缺少換行符，不像 LINE 匯出格式。")
        return False

    # 2. 必須包含至少一個日期標記行
    if not DATE_REGEX.search(text):
        logger.warning("輸入未找到符合 'YYYY.MM.DD 星期X' 格式的日期標記行。")
        return False

    # 3. 必須包含至少一個看起來像訊息的行 (時間 發送者 內容)
    if not MESSAGE_REGEX.search(text):
        logger.warning("輸入未找到符合 'HH:MM Sender Content' 基本格式的訊息行。")
        return False

    # 如果所有基本檢查都通過
    return True
