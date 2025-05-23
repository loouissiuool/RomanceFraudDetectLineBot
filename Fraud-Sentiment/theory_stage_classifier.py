from typing import Set, Dict, List

# 七階段/五階段詐騙理論對應表
STAGE_MAPPING: List[Dict] = [
    {
        "stage": "尋找夢中情人 / 客戶招募",
        "keywords": {"單身", "做什麼工作", "自我介紹", "加好友", "你在哪"}
    },
    {
        "stage": "犯罪者接觸 / 客戶招募",
        "keywords": {"群組", "邀請", "認識", "加你"}
    },
    {
        "stage": "培養感情 / 客戶培養",
        "keywords": {"寶貝", "想你", "親愛的", "我只信你", "很想你", "關心", "聊天", "自拍"}
    },
    {
        "stage": "金錢要求 / 初步索取",
        "keywords": {"匯款", "帳戶", "金額", "投資", "轉帳", "款項", "虛擬貨幣", "穩賺不賠", "借錢", "幫忙匯款"}
    },
    {
        "stage": "突破門檻 / 持續詐騙",
        "keywords": {"再匯一次", "還有費用", "保證金", "手續費", "驗證", "解鎖", "升級", "急需"}
    },
    {
        "stage": "性剝削 / 升級勒索",
        "keywords": {"裸照", "威脅", "勒索", "不雅照", "影片"}
    },
    {
        "stage": "再次受害 / 升級勒索",
        "keywords": {"再借一次", "再幫一次", "還有一筆"}
    }
]

def classify_stage(keywords: Set[str]) -> str:
    """
    根據命中關鍵字自動判斷對話所屬詐騙階段。
    若多個階段同時命中，回傳最進階階段。
    """
    matched_stage = None
    for stage_info in reversed(STAGE_MAPPING):  # 由高階段往低階段比對
        if stage_info["keywords"] & keywords:
            matched_stage = stage_info["stage"]
            break
    return matched_stage or "未明確分類"

if __name__ == "__main__":
    # 測試範例
    test_keywords = {"匯款", "帳戶", "金額"}
    print(f"命中階段: {classify_stage(test_keywords)}") 