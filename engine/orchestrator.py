"""Cognitive Engine — 统一认知入口

编排流程:
  OCR → Extract → Rules → Retrieve → Interpret → Prompt → (LLM) → Validate
"""

from engine.extractor import extract_metrics
from engine.rules import apply_rules, rule_summary
from engine.retrieval import retrieve
from engine.interpreter import interpret
from engine.prompts import build_prompt
from engine.validator import validate


class CognitiveEngine:
    """认知系统编排器"""

    def run(self, ocr_text, report_type='learning', style='gentle', age=None, target='self'):
        """完整认知 pipeline。

        Args:
            ocr_text: OCR 提取的文本
            report_type: 报告类型 (learning/portrait/emotion/potential/communication/career/action)
            style: 咨询师风格 (gentle/direct/parent/educator/coach)
            age: 年龄(必填)
            target: 报告对象 (self/parent/other/global)

        Returns:
            dict: {
                system_prompt, user_prompt: 发送给 LLM 的 prompt
                debug: {metrics, structure, knowledge, meaning, validation}  调试信息
            }
        """
        # Layer 0: 提取
        metrics = extract_metrics(ocr_text)

        # Layer 1: 规则
        structure = apply_rules(metrics)

        # Layer 1.5: 检索
        knowledge = retrieve(structure, report_type)

        # Layer 2: 解释
        meaning = interpret(structure, ocr_text)

        # Layer 3: 表达
        system_prompt, user_prompt = build_prompt(
            structure=structure,
            meaning=meaning,
            knowledge=knowledge,
            report_type=report_type,
            style=style,
            age=age,
            target=target,
        )

        return {
            'system_prompt': system_prompt,
            'user_prompt': user_prompt,
            'debug': {
                'metrics': _clean_metrics(metrics),
                'structure_summary': rule_summary(structure),
                'structure': structure,
                'insights_count': len(knowledge.get('insights', [])),
                'narratives_count': len(knowledge.get('narratives', [])),
                'interventions_count': len(knowledge.get('interventions', [])),
                'style': style,
            }
        }


def _clean_metrics(m):
    """净化 debug 输出，避免过深嵌套。"""
    clean = {}
    for k, v in m.items():
        if isinstance(v, dict):
            clean[k] = {kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}
        else:
            clean[k] = v
    return clean


# ============================================================
# 兼容旧版 process() 函数
# ============================================================
def process(ocr_text, report_type='learning', structured_data=None, style='gentle'):
    """兼容旧版 engine.rule_engine.process() 的调用签名。

    Returns:
        dict with keys: system_prompt, user_prompt, debug
    """
    engine = CognitiveEngine()
    result = engine.run(ocr_text, report_type, style)
    # 兼容旧版 debug 格式
    result['debug']['rule_outputs'] = [
        {'label': r['label'], 'traits': r.get('traits', []), 'risks': r.get('risks', []), 'supports': r.get('supports', [])}
        for r in [result['debug']['structure'].get('trc'), result['debug']['structure'].get('atd'),
                  {'label': f"{result['debug']['structure'].get('channel',{}).get('label','')}", 'traits': []}]
        if r
    ]
    return result
