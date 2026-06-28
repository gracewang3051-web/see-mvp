"""兼容层 — 转发到新引擎模块。保留旧导入路径 from engine.rule_engine import process。"""

from engine.orchestrator import CognitiveEngine, process

# 保持旧函数签名兼容
def extract_metrics(ocr_text):
    from engine.extractor import extract_metrics as _extract
    return _extract(ocr_text)

def apply_rules(metrics):
    from engine.rules import apply_rules as _apply
    return _apply(metrics)
