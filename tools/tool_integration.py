"""
Integrate ZiweiToolkit and BaziToolkit into the rules engine.
Call tools directly and use their results for scoring.
"""
from __future__ import annotations

import json, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.ziwei_tools import ZiweiToolkit, PALACE_ORDER
from tools.bazi_tools import (
    BaziToolkit,
    analyze_career_chart,
    analyze_health_chart,
    analyze_huoyuan_chart,
    analyze_marriage_chart,
    analyze_wealth_chart,
    analyze_yin_shou_chart,
)


_zw = ZiweiToolkit()
_bz = BaziToolkit()


def get_ziwei_chart(
    year,
    month,
    day,
    hour,
    gender="男",
    zi_hour_convention="benchmark",
    chart=None,
):
    """Get a Ziwei chart from the shared ComputedChart when available."""
    result = _zw.paipan(
        year,
        month,
        day,
        hour,
        gender,
        zi_hour_convention=zi_hour_convention,
        computed_chart=chart,
    )
    return json.loads(result)


def get_ziwei_personality(ming_stars):
    """Get personality traits from 命宫 stars."""
    result = _zw.analyze_personality(json.dumps(ming_stars, ensure_ascii=False))
    return json.loads(result)


def get_ziwei_career(guanlu_stars, ming_stars):
    """Get career traits from 官禄宫 + 命宫 stars."""
    result = _zw.analyze_career(
        json.dumps(guanlu_stars, ensure_ascii=False),
        json.dumps(ming_stars, ensure_ascii=False),
    )
    return json.loads(result)


def get_ziwei_marriage(couple_stars):
    """Get marriage traits from 夫妻宫 stars."""
    result = _zw.analyze_marriage(json.dumps(couple_stars, ensure_ascii=False))
    return json.loads(result)


def get_ziwei_wealth(caibo_stars):
    """Get wealth traits from 财帛宫 stars."""
    result = _zw.analyze_wealth(json.dumps(caibo_stars, ensure_ascii=False))
    return json.loads(result)


def get_ziwei_health(jie_stars):
    """Get health traits from 疾厄宫 stars."""
    result = _zw.analyze_health(json.dumps(jie_stars, ensure_ascii=False))
    return json.loads(result)


def get_bazi_shensha(year_ganzhi, month_ganzhi, day_ganzhi, hour_ganzhi):
    """Get shensha from BaziToolkit."""
    result = _bz.find_shensha(year_ganzhi, month_ganzhi, day_ganzhi, hour_ganzhi)
    return json.loads(result)


def get_bazi_career(year, month, day, hour, gender="男"):
    """Get career analysis from BaziToolkit."""
    result = _bz.analyze_career(year, month, day, hour, gender)
    return json.loads(result)


def get_bazi_marriage(year, month, day, hour, gender="男"):
    """Get marriage analysis from BaziToolkit."""
    result = _bz.analyze_marriage(year, month, day, hour, gender)
    return json.loads(result)


# Ziwei star → personality keyword mapping
ZIWEI_PERSONALITY_KEYWORDS = {
    "紫微": ["威严", "领袖", "大方", "领导", "高贵", "有主见", "强势", "大方"],
    "天机": ["聪明", "善变", "灵活", "思考", "机智", "多谋", "善变"],
    "太阳": ["热情", "大方", "乐于助人", "阳光", "正义", "开朗"],
    "武曲": ["刚毅", "果断", "重实际", "实干", "决断", "重义"],
    "天同": ["温和", "随和", "享受", "乐观", "懒", "安逸"],
    "廉贞": ["能干", "好胜", "多才", "争强", "傲", "精明"],
    "天府": ["稳重", "保守", "理财", "守成", "可靠", "踏实"],
    "太阴": ["温柔", "敏感", "重感情", "细腻", "多愁", "浪漫"],
    "贪狼": ["多才多艺", "交际", "欲望", "桃花", "喜欢结交", "好动"],
    "巨门": ["口才", "多疑", "分析", "直言", "啰嗦", "多嘴"],
    "天相": ["随和", "协调", "形象", "服务", "圆滑"],
    "天梁": ["正直", "慈悲", "为人师", "老成", "稳重", "有原则"],
    "七杀": ["勇敢", "独立", "冲劲", "好胜", "霸气", "不服输"],
    "破军": ["破坏", "善变", "不守成规", "叛逆", "开创", "折腾"],
}

# Ziwei career star → profession keywords
ZIWEI_CAREER_KEYWORDS = {
    "紫微": ["管理", "领导", "老板", "高管", "政府"],
    "天机": ["技术", "策划", "研究", "咨询", "谋略"],
    "太阳": ["政治", "公关", "服务", "教育", "公益"],
    "武曲": ["金融", "银行", "投资", "财", "实业"],
    "天同": ["服务", "休闲", "餐饮", "娱乐", "文职"],
    "廉贞": ["法律", "军事", "竞争", "技术", "创业"],
    "天府": ["银行", "会计", "管理", "稳定", "财务"],
    "太阴": ["艺术", "设计", "房地产", "文化", "女性"],
    "贪狼": ["销售", "公关", "演艺", "媒体", "交际"],
    "巨门": ["律师", "教师", "口才", "评论", "研究"],
    "天相": ["行政", "秘书", "公关", "服务", "协调"],
    "天梁": ["医生", "教育", "宗教", "公益", "监督"],
    "七杀": ["军警", "执法", "创业", "运动", "冒险"],
    "破军": ["创业", "变革", "运输", "开拓", "冒险"],
}

# Ziwei marriage star → trait keywords
ZIWEI_MARRIAGE_KEYWORDS = {
    "romantic": ["桃花", "恋爱", "浪漫", "多情", "风流"],
    "stable": ["稳定", "和睦", "恩爱", "美满", "白头"],
    "volatile": ["波折", "离", "分手", "争吵", "变故"],
}

# Ziwei health star → organ keywords
ZIWEI_HEALTH_ORGANS = {
    "紫微": ["脾胃", "胃", "脾", "消化"],
    "天机": ["肝", "胆", "神经", "头"],
    "太阳": ["心", "眼", "血液"],
    "武曲": ["肺", "呼吸", "鼻", "皮毛"],
    "天同": ["泌尿", "肾", "膀胱"],
    "廉贞": ["心血管", "心", "血"],
    "天府": ["脾胃", "胃", "脾"],
    "太阴": ["肾", "眼", "目"],
    "贪狼": ["肝", "胆", "泌尿"],
    "巨门": ["口", "喉", "呼吸道", "咽"],
    "天相": ["皮肤", "肠胃", "肠"],
    "天梁": ["骨", "骨骼", "关节"],
    "七杀": ["肺", "呼吸", "外伤", "伤"],
    "破军": ["肾", "泌尿", "生殖"],
}

ZIWEI_STAR_MARRIAGE_TYPE = {
    "紫微": "stable",
    "天府": "stable",
    "天相": "stable",
    "天梁": "stable",
    "天同": "stable",
    "贪狼": "romantic",
    "廉贞": "romantic",
    "破军": "volatile",
    "太阴": "romantic",
    "七杀": "volatile",
    "巨门": "volatile",
    "天机": "volatile",
    "太阳": "stable",
    "武曲": "stable",
}


def build_tool_data(year, month, day, hour, gender="男", chart=None):
    """Build derived data from one already-computed chart when available."""
    data = {"component_status": {}}
    if chart is None:
        from engine.run_tools_engine import compute_chart

        chart = compute_chart({
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "gender": gender,
        })
        data["component_status"]["bazi"] = {
            "status": "degraded",
            "code": "chart_reconstructed_from_legacy_arguments",
            "message": "未提供共享命盘，已从完整出生参数构建一份 ComputedChart。",
        }
    else:
        data["component_status"]["bazi"] = {
            "status": "ok",
            "backend": "shared-computed-chart",
        }

    data["chart_id"] = chart.get("chart_id")
    effective_year = chart.get("birth_year", year)
    effective_month = chart.get("birth_month", month)
    effective_day = chart.get("birth_day", day)
    effective_hour = chart.get("birth_hour", hour)
    zi_hour_convention = chart.get("birth_time", {}).get(
        "zi_hour_convention", "benchmark"
    )

    try:
        ziwei = get_ziwei_chart(
            effective_year,
            effective_month,
            effective_day,
            effective_hour,
            gender,
            zi_hour_convention,
            chart,
        )
    except Exception as exc:
        ziwei = {"success": False, "error": str(exc)}
    if ziwei.get("success"):
        ziwei["chart_id"] = data.get("chart_id")
        data["ziwei"] = ziwei
        palaces = ziwei.get("十二宫", {})
        for pname in PALACE_ORDER:
            p = palaces.get(pname, {})
            data[f"zw_{pname}"] = p.get("主星", [])
        data["zw_body_palace"] = ziwei.get("身宫", "命宫")
        data["zw_ju"] = ziwei.get("五行局", "")
        backend_status = ziwei.get("后端状态", {})
        ziwei_status = backend_status.get("status", "ok")
        data["zw_precision"] = (
            "iztro"
            if ziwei_status == "ok" and ziwei.get("排盘引擎") == "iztro"
            else "approximate"
        )
        data["component_status"]["ziwei"] = {
            "status": ziwei_status,
            "backend": ziwei.get("排盘引擎", "unknown"),
            "input_precision": "hour",
            "zi_hour_convention": zi_hour_convention,
        }
        if ziwei_status != "ok":
            data["component_status"]["ziwei"].update({
                "code": backend_status.get(
                    "code", "ziwei_approximate_fallback"
                ),
                "message": backend_status.get(
                    "message", "紫微后端已降级为近似盘。"
                ),
                "fallback": backend_status.get("fallback"),
            })
    else:
        data["component_status"]["ziwei"] = {
            "status": "error",
            "code": "ziwei_unavailable",
            "message": ziwei.get("error", "紫微排盘未返回成功结果。"),
        }

    analyzers = {
        "bz_career": lambda: analyze_career_chart(chart),
        "bz_marriage": lambda: analyze_marriage_chart(chart, gender),
        "bz_health": lambda: analyze_health_chart(chart),
        "bz_wealth": lambda: analyze_wealth_chart(chart),
        "bz_education": lambda: analyze_yin_shou_chart(chart),
        "bz_huoyuan": lambda: analyze_huoyuan_chart(chart),
    }
    for key, analyzer in analyzers.items():
        try:
            data[key] = analyzer()
        except Exception as exc:
            data[key] = {
                "success": False,
                "component_status": {
                    "status": "error",
                    "code": "derived_analysis_failed",
                    "message": str(exc),
                },
            }
            data["component_status"][key] = data[key]["component_status"]
        else:
            data["component_status"][key] = data[key]["component_status"]

    return data
