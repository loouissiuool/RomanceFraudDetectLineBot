from pipeline.pipeline import FraudDetectionPipeline
from pipeline.ws_module import WSModule
from pipeline.sentiment_module import SentimentModule
from pipeline.classifier_module import ClassifierModule
from pipeline.keyword_module import KeywordModule
from pipeline.stage_rule_module import StageRuleModule

def test_pipeline():
    ws = WSModule()
    sentiment = SentimentModule()
    classifier = ClassifierModule()
    keywords = KeywordModule({"匯款", "寶貝", "投資"})
    stage_rule = StageRuleModule()
    pipeline = FraudDetectionPipeline(ws, sentiment, classifier, keywords, stage_rule)

    text = "寶貝，你現在方便匯款嗎？"
    result = pipeline.run(text)
    assert "斷詞" in result
    assert "關鍵字" in result
    assert "情感" in result
    assert "三階段分類" in result
    assert "規則分類" in result
    print(result)