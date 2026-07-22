"""High-risk boundaries for optional rules-engine suggestions.

Calendar and chart data can remain available for cultural research.  This
module only decides whether the multiple-choice rules engine may select an
answer; it does not modify the underlying chart.
"""
from __future__ import annotations

import re
from typing import Any, Iterable


_CATEGORY_SUPPRESSIONS = {
    "健康": (
        "健康问题不生成规则选项预测；请以合格医疗专业人员的评估为准。"
    ),
    "灾劫": (
        "伤害、灾害和事故问题不生成规则选项预测；请优先采取现实安全措施。"
    ),
    "官非": (
        "法律和诉讼问题不生成规则选项预测；请咨询合格法律专业人员。"
    ),
}
_HIGH_RISK_TERMS = re.compile(
    r"死亡|去世|早亡|自杀|自伤|癌|肿瘤|手术|开刀|用药|住院|"
    r"投资|股票|基金|期货|借贷|贷款|保险|赌博|破产|负债|融资|"
    r"离婚|怀孕|流产"
)


def assess_rules_suggestion_request(
    category: Any,
    question: Any,
    options: Iterable[dict] | None,
) -> dict:
    """Return a visible suppression reason for unsafe option prediction."""
    if category in _CATEGORY_SUPPRESSIONS:
        return {
            "suppressed": True,
            "code": "rules_suggestion_high_risk_category",
            "message": _CATEGORY_SUPPRESSIONS[category],
        }

    texts = [str(question or "")]
    if options:
        texts.extend(
            str(option.get("text", ""))
            for option in options
            if isinstance(option, dict)
        )
    matched = _HIGH_RISK_TERMS.search("\n".join(texts))
    if matched:
        return {
            "suppressed": True,
            "code": "rules_suggestion_high_risk_content",
            "message": (
                f"检测到高风险主题“{matched.group(0)}”，"
                "不生成规则选项预测。"
            ),
        }
    return {"suppressed": False}
