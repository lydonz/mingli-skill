"""Render auditable MingLi analysis data as a self-contained HTML report."""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Iterable, Mapping


REPORT_VERSION = "html-report-v2"
_ZIWEI_GRID_POSITIONS = {
    "巳": (1, 1), "午": (1, 2), "未": (1, 3), "申": (1, 4),
    "辰": (2, 1), "酉": (2, 4),
    "卯": (3, 1), "戌": (3, 4),
    "寅": (4, 1), "丑": (4, 2), "子": (4, 3), "亥": (4, 4),
}


def _text(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (list, tuple)):
        return "、".join(_text(item) for item in value) or "—"
    if isinstance(value, dict):
        return "；".join(f"{key}：{_text(item)}" for key, item in value.items()) or "—"
    return str(value)


def _cell(value: Any) -> str:
    return f"<td>{escape(_text(value))}</td>"


def _table(headers: Iterable[str], rows: Iterable[Iterable[Any]]) -> str:
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_html = "".join(
        "<tr>" + "".join(_cell(value) for value in row) + "</tr>"
        for row in rows
    )
    if not body_html:
        body_html = f"<tr><td colspan=\"{len(list(headers))}\">暂无数据</td></tr>"
    return (
        "<div class=\"table-wrap\"><table><thead><tr>"
        f"{header_html}</tr></thead><tbody>{body_html}</tbody></table></div>"
    )


def _section(title: str, content: str, note: str = "") -> str:
    note_html = f"<p class=\"note\">{escape(note)}</p>" if note else ""
    return (
        f"<section class=\"section\"><h2>{escape(title)}</h2>"
        f"{note_html}{content}</section>"
    )


def _mapping_rows(value: Mapping[str, Any], keys: Iterable[str]) -> list[list[Any]]:
    return [[key, value.get(key)] for key in keys if key in value]


def _ziwei_palace_grid(ziwei_raw: Any) -> str:
    """Render a fixed twelve-palace board from audited Ziwei data only."""
    if not isinstance(ziwei_raw, Mapping):
        return ""
    palaces = ziwei_raw.get("十二宫")
    if not isinstance(palaces, Mapping) or not palaces:
        return ""

    cells = []
    for palace_name, palace in palaces.items():
        if not isinstance(palace, Mapping):
            continue
        branch = palace.get("宫位地支")
        position = _ZIWEI_GRID_POSITIONS.get(branch)
        if position is None:
            continue
        row, column = position
        major_stars = palace.get("主星") or []
        minor_stars = palace.get("辅星") or []
        star_details = (
            list(palace.get("主星详情") or [])
            + list(palace.get("辅星详情") or [])
        )
        mutagens = [
            f"{detail.get('名称', '')}{detail.get('生年四化', '')}"
            for detail in star_details
            if isinstance(detail, Mapping) and detail.get("生年四化")
        ]
        tags = []
        if palace_name == "命宫":
            tags.append("命宫")
        if palace_name == ziwei_raw.get("身宫"):
            tags.append("身宫")
        star_text = "·".join(str(star) for star in major_stars) or "空宫"
        minor_text = "·".join(str(star) for star in minor_stars)
        detail_text = _text(palace.get("十年大限"))
        tag_html = "".join(
            f"<span class=\"ziwei-tag\">{escape(tag)}</span>" for tag in tags
        )
        mutagen_html = (
            f"<div class=\"ziwei-mutagens\">{escape('、'.join(mutagens))}</div>"
            if mutagens else ""
        )
        minor_html = (
            f"<div class=\"ziwei-minor\">{escape(minor_text)}</div>"
            if minor_text else ""
        )
        cells.append(
            f"<article class=\"ziwei-palace\" style=\"grid-row:{row};"
            f"grid-column:{column}\">"
            f"<div class=\"ziwei-palace-heading\">"
            f"<span>{escape(str(palace_name))}</span>"
            f"<span>{escape(str(branch))}</span></div>"
            f"<div class=\"ziwei-major\">{escape(star_text)}</div>"
            f"{minor_html}{mutagen_html}"
            f"<div class=\"ziwei-limit\">大限：{escape(detail_text)}</div>"
            f"<div class=\"ziwei-tags\">{tag_html}</div>"
            f"</article>"
        )

    if not cells:
        return ""
    audit = ziwei_raw.get("紫微审计", {})
    convention = (
        audit.get("zi_hour_convention", "benchmark")
        if isinstance(audit, Mapping) else "benchmark"
    )
    center = (
        "<div class=\"ziwei-center\">"
        "<strong>紫微十二宫</strong>"
        f"<span>五行局：{escape(_text(ziwei_raw.get('五行局')))}</span>"
        f"<span>子时约定：{escape(str(convention))}</span>"
        "</div>"
    )
    return (
        "<div class=\"ziwei-board-wrap\"><div class=\"ziwei-board\">"
        f"{''.join(cells)}{center}</div></div>"
    )


def render_html_report(
    analysis: Mapping[str, Any],
    title: str = "命理分析报告",
    subject_name: str = "",
) -> str:
    """Render a report from ``HybridMingliToolkit.analyze_question`` data."""
    if analysis.get("error"):
        raise ValueError(_text(analysis["error"]))

    bazi = analysis.get("bazi", {})
    birth_time = analysis.get("birth_time", {})
    pillars = bazi.get("四柱", {})
    element_scores = bazi.get("五行力量", {})
    element_percent = bazi.get("五行占比", {})
    assessment = analysis.get("strength_assessment", {})
    liunian = analysis.get("liunian") or {}
    ziwei_raw = analysis.get("ziwei_raw")

    subject = subject_name.strip() or "未署名"
    birth_rows = _mapping_rows(
        birth_time,
        (
            "time_basis",
            "civil_time",
            "effective_time",
            "calendar_time",
            "timezone",
            "calendar_timezone",
            "correction_minutes",
            "equation_of_time_minutes",
            "uncertainty_minutes",
        ),
    )
    if birth_time.get("place"):
        birth_rows.append(["place", birth_time["place"]])

    pillar_rows = [
        [name, pillar[0] if pillar else "—", pillar[1] if len(pillar) > 1 else "—", pillar]
        for name, pillar in pillars.items()
    ]
    element_rows = [
        [element, element_scores.get(element, 0), element_percent.get(element, "—")]
        for element in ("木", "火", "土", "金", "水")
    ]
    assessment_rows = _mapping_rows(
        assessment,
        ("version", "旺衰", "格局", "得令", "喜用神", "喜神", "忌神", "conflicts"),
    )

    dayun_rows = [
        [
            item.get("大运"),
            item.get("起运年龄文本", item.get("起运年龄")),
            item.get("起运日期"),
            item.get("止运日期"),
            item.get("天干五行"),
            item.get("地支五行"),
        ]
        for item in bazi.get("大运", [])
    ]
    liunian_rows = [
        [
            item.get("分析日期"),
            item.get("干支"),
            item.get("天干十神"),
            item.get("地支藏干十神"),
            item.get("大运"),
            item.get("标签"),
        ]
        for item in liunian.get("年份流年对比", [])
    ]
    month_rows = [
        [
            item.get("start"),
            item.get("end"),
            item.get("流年干支"),
            item.get("流月干支"),
            item.get("流月天干十神"),
            item.get("当前大运"),
        ]
        for item in liunian.get("流月分段", [])
    ]
    knowledge_rows = [
        [
            reference.get("pack_id"),
            reference.get("pack_version"),
            (
                f"{reference.get('source', {}).get('repository', '')}"
                f"@{reference.get('source', {}).get('revision', '')}"
            ),
            reference.get("file"),
            reference.get("section"),
            f"{reference.get('line_start')}–{reference.get('line_end')}",
            reference.get("excerpt"),
        ]
        for reference in analysis.get("knowledge_references", [])
        if isinstance(reference, Mapping)
    ]
    interpretation = analysis.get("interpretation", {})
    interpretation_document = (
        interpretation.get("document", {})
        if isinstance(interpretation, Mapping)
        and interpretation.get("status") == "ok"
        else {}
    )
    interpretation_rows = [
        [
            section.get("title"),
            section.get("body"),
            section.get("evidence_ids"),
            section.get("uncertainty"),
        ]
        for section in interpretation_document.get("sections", [])
        if isinstance(section, Mapping)
    ]
    ziwei_board = _ziwei_palace_grid(ziwei_raw)

    analyses = []
    for field, label in (
        ("career_analysis", "事业结构"),
        ("wealth_analysis", "财富结构"),
        ("marriage_analysis", "关系结构"),
        ("health_analysis", "健康倾向"),
    ):
        value = analysis.get(field)
        if not isinstance(value, Mapping):
            continue
        summary_keys = {
            "事业结构": ("格局倾向", "正官", "七杀", "印绶", "食伤", "财星"),
            "财富结构": ("财星五行", "财星力量", "财星占比", "财运提示"),
            "关系结构": ("配偶宫", "配偶星", "配偶星位置"),
            "健康倾向": ("医疗声明", "最弱五行", "最旺五行"),
        }[label]
        rows = _mapping_rows(value, summary_keys)
        analyses.append(_section(label, _table(("项目", "内容"), rows)))

    warning_rows = [[warning] for warning in analysis.get("data_quality_warnings", [])]
    component_rows = [
        [name, status.get("status"), status.get("backend"), status.get("code")]
        for name, status in analysis.get("component_status", {}).items()
        if isinstance(status, Mapping)
    ]
    uncertainty = assessment.get("conflicts", [])
    uncertainty_note = (
        "结果应结合出生时间准确度、地点解析、历法边界和现实信息理解。"
        "命理推演不构成确定性预测或专业建议。"
    )

    sections = [
        _section(
            "排盘前提",
            _table(("字段", "内容"), birth_rows),
            "有效排盘时间用于八字、大运、紫微和衍生分析。",
        ),
        _section("四柱", _table(("柱位", "天干", "地支", "干支"), pillar_rows)),
        _section("五行结构", _table(("五行", "力量", "占比"), element_rows)),
        _section("旺衰与喜忌", _table(("字段", "内容"), assessment_rows)),
        _section(
            "大运",
            _table(("大运", "起运年龄", "起运日期", "止运日期", "天干五行", "地支五行"), dayun_rows),
        ),
        _section(
            "流年",
            _table(("分析日期", "流年", "天干十神", "地支藏干十神", "大运", "标签"), liunian_rows),
            "未提供显式日期区间时，流年结果可能使用年度锚点。",
        ),
    ]
    if ziwei_board:
        sections.insert(
            4,
            _section(
                "紫微十二宫",
                ziwei_board,
                "仅展示 iztro 返回并保留在紫微审计数据中的宫位、星曜、四化与大限字段。",
            ),
        )
    if month_rows:
        sections.append(
            _section(
                "流月",
                _table(("开始", "结束", "流年", "流月", "流月天干十神", "大运"), month_rows),
                "流月按小寒、立春、惊蛰等十二个节气边界切分。",
            )
        )
    if knowledge_rows:
        knowledge_notice = (
            analysis.get("knowledge_context", {}).get("notice")
            or "引用仅作为传统命理的方法论与文化语境，不构成预测证据。"
        )
        sections.append(
            _section(
                "本地知识参考",
                _table(
                    ("知识包", "版本", "来源", "文件", "章节", "行号", "摘录"),
                    knowledge_rows,
                ),
                knowledge_notice,
            )
        )
    if interpretation_rows:
        sections.append(
            _section(
                "解释文本",
                _table(
                    ("标题", "解释", "结构化依据", "不确定性"),
                    interpretation_rows,
                ),
                (
                    interpretation.get("notice")
                    or "解释文本与排盘计算分离，且仅引用当前命盘允许的证据。"
                ),
            )
        )
    sections.extend(analyses)
    sections.extend([
        _section(
            "数据质量与不确定性",
            _table(("提示",), warning_rows)
            + _table(("组件", "状态", "后端", "错误码"), component_rows),
            uncertainty_note + (f" 当前模型冲突：{_text(uncertainty)}。" if uncertainty else ""),
        ),
        _section(
            "免责声明",
            (
                "<p class=\"disclaimer\">本报告用于传统文化研究与自我认知。"
                "它不构成医疗、心理、法律、金融、投资或职业建议，"
                "不应作为重大决策的唯一依据。</p>"
            ),
        ),
    ])

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="report-version" content="{REPORT_VERSION}">
<title>{escape(title)} - {escape(subject)}</title>
<style>
:root {{ color-scheme: light; --ink:#182235; --muted:#5d6778; --line:#d9dee7; --panel:#ffffff; --ground:#f5f7fa; --accent:#a33b45; --accent-2:#315f99; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--ground); color:var(--ink); font:16px/1.72 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
.report-shell {{ width:min(960px,calc(100% - 32px)); margin:32px auto 56px; }}
.hero {{ border-top:6px solid var(--accent); background:var(--panel); padding:32px; box-shadow:0 8px 28px rgba(24,34,53,.07); }}
h1 {{ margin:0; font-size:30px; line-height:1.25; letter-spacing:0; }}
h2 {{ margin:0 0 16px; font-size:21px; line-height:1.35; color:var(--accent-2); }}
.eyebrow {{ margin:8px 0 0; color:var(--muted); font-size:14px; }}
.section {{ margin-top:20px; background:var(--panel); padding:26px 28px; border:1px solid var(--line); }}
.table-wrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; min-width:560px; }}
th,td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
th {{ color:var(--muted); font-size:13px; font-weight:650; white-space:nowrap; }}
tr:last-child td {{ border-bottom:0; }}
.note {{ color:var(--muted); margin:-6px 0 14px; font-size:14px; }}
.disclaimer {{ margin:0; color:#6f2530; }}
.ziwei-board-wrap {{ overflow-x:auto; }}
.ziwei-board {{ display:grid; grid-template-columns:repeat(4,minmax(156px,1fr)); grid-template-rows:repeat(4,minmax(144px,auto)); gap:4px; min-width:740px; background:var(--line); border:1px solid var(--line); }}
.ziwei-palace {{ position:relative; min-height:144px; padding:10px; background:#fbfcfe; }}
.ziwei-palace-heading {{ display:flex; justify-content:space-between; gap:8px; color:var(--accent-2); font-size:13px; font-weight:650; }}
.ziwei-major {{ margin-top:12px; font-size:16px; font-weight:700; overflow-wrap:anywhere; }}
.ziwei-minor,.ziwei-mutagens,.ziwei-limit {{ margin-top:5px; color:var(--muted); font-size:12px; overflow-wrap:anywhere; }}
.ziwei-mutagens {{ color:#8f3d45; }}
.ziwei-tags {{ position:absolute; right:10px; bottom:9px; display:flex; gap:4px; }}
.ziwei-tag {{ border:1px solid #b8c4d6; color:var(--accent-2); padding:1px 5px; font-size:11px; }}
.ziwei-center {{ grid-area:2 / 2 / span 2 / span 2; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:7px; min-height:292px; padding:18px; background:#edf2f8; color:var(--accent-2); text-align:center; }}
.ziwei-center strong {{ color:var(--ink); font-size:20px; }}
.ziwei-center span {{ color:var(--muted); font-size:13px; }}
@media print {{ body {{ background:#fff; }} .report-shell {{ width:auto; margin:0; }} .hero,.section {{ box-shadow:none; break-inside:avoid; }} }}
@media (max-width:640px) {{ .report-shell {{ width:calc(100% - 20px); margin:10px auto 28px; }} .hero,.section {{ padding:20px; }} h1 {{ font-size:25px; }} }}
</style>
</head>
<body>
<main class="report-shell">
<header class="hero">
<h1>{escape(title)}</h1>
<p class="eyebrow">对象：{escape(subject)} · 命盘标识：{escape(_text(analysis.get("chart_id")))}</p>
</header>
{''.join(sections)}
</main>
</body>
</html>"""


def write_html_report(html: str, output_path: str | Path) -> Path:
    """Write a self-contained report only when the caller provides a path."""
    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")
    return destination
