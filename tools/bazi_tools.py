from __future__ import annotations

import json
from datetime import date
from typing import Optional

from .toolkit_base import Toolkit

from .calendar_engine import (
    TIANGAN, DIZHI, TIANGAN_IDX, DIZHI_IDX,
    WUXING_GAN, WUXING_ZHI, YINYANG_GAN,
    WUXING_SHENG, WUXING_KE, WUXING_BEING_SHENG, WUXING_BEING_KE,
    ZHI_CANG_GAN, NAYIN_TABLE, CHANGSHENG_12,
    build_four_pillars, build_dayun, build_liunian,
    shi_shen, five_element_strength, nayin, changsheng_state,
    wuxing_relation, animal_year, year_ganzhi, day_ganzhi_from_date,
    hour_ganzhi, month_ganzhi, ganzhi_from_offset, kong_wang,
)
from .chart_assessment import attach_strength_assessment


INTERPRETATION_RULESET_VERSION = "structured-evidence-v1"


def _build_analysis_chart(
    year: int,
    month: int,
    day: int,
    hour: int,
    gender: str = "男",
    minute: int = 0,
    second: int = 0,
    birth_context: Optional[dict] = None,
    year_boundary: str = "lichun",
) -> dict:
    """Use the canonical chart builder instead of a local hour-only rebuild."""
    from engine.run_tools_engine import compute_chart

    birth_info = {
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "minute": minute,
        "second": second,
        "gender": gender,
        "year_boundary": year_boundary,
    }
    if birth_context is not None:
        birth_info["birth_context"] = birth_context
    return compute_chart(birth_info)


def _with_evidence(chart: dict, payload: dict, signals: dict) -> dict:
    assessment = chart.get("strength_assessment") or attach_strength_assessment(chart)[
        "strength_assessment"
    ]
    payload["ruleset_version"] = INTERPRETATION_RULESET_VERSION
    payload["chart_id"] = chart.get("chart_id")
    payload["birth_time"] = chart.get("birth_time")
    payload["strength_assessment_version"] = assessment["version"]
    payload["preference_ruleset_version"] = assessment[
        "preference_ruleset_version"
    ]
    payload["evidence"] = {
        "signals": signals,
        "preference": {
            key: assessment[key] for key in ("喜用神", "喜神", "忌神")
        },
        "strength_conflicts": assessment.get("conflicts", []),
    }
    payload["component_status"] = {
        "status": "ok",
        "backend": "calendar_engine",
    }
    return payload


def _with_chart_audit(chart: dict, payload: dict) -> dict:
    """Attach the canonical-chart identity to direct personal analyses."""
    payload["chart_id"] = chart.get("chart_id")
    payload["birth_time"] = chart.get("birth_time")
    payload["component_status"] = {
        "status": "ok",
        "backend": "shared-computed-chart",
    }
    return payload


def analyze_huoyuan_chart(chart: dict) -> dict:
    assessment = chart.get("strength_assessment") or attach_strength_assessment(chart)[
        "strength_assessment"
    ]
    payload = {
        "success": True,
        "日主": chart["日主"],
        "日主五行": chart["日主五行"],
        "旺衰": assessment["旺衰"],
        "格局": assessment["格局"],
        "得令": assessment["得令"],
        "五行得分": assessment["五行得分"],
        "日主五行占比": f"{assessment['日主五行占比']:.1%}",
        "喜用神": assessment["喜用神"],
        "喜神": assessment["喜神"],
        "忌神": assessment["忌神"],
        "conflicts": assessment["conflicts"],
    }
    return _with_evidence(chart, payload, assessment["evidence"])


def analyze_career_chart(chart: dict) -> dict:
    ten_gods = chart["十神"]
    assessment = chart.get("strength_assessment") or attach_strength_assessment(chart)[
        "strength_assessment"
    ]
    guan = [key for key, value in ten_gods.items() if value == "正官"]
    sha = [key for key, value in ten_gods.items() if value == "七杀"]
    yin = [key for key, value in ten_gods.items() if value in ("正印", "偏印")]
    bi = [key for key, value in ten_gods.items() if value in ("比肩", "劫财")]
    shi = [key for key, value in ten_gods.items() if value in ("食神", "伤官")]
    cai = [key for key, value in ten_gods.items() if value in ("正财", "偏财")]
    if guan and yin:
        candidate_tendency = "官印相生"
    elif shi and cai:
        candidate_tendency = "食伤生财"
    elif sha and yin:
        candidate_tendency = "杀印相生"
    elif (
        cai
        and assessment["旺衰"] == "身旺"
        and not assessment.get("conflicts")
    ):
        candidate_tendency = "身旺任财"
    else:
        candidate_tendency = "待定"
    has_conflict = bool(assessment.get("conflicts"))
    payload = {
        "success": True,
        "正官": guan,
        "七杀": sha,
        "印绶": yin,
        "比劫": bi,
        "食伤": shi,
        "财星": cai,
        "喜用神": assessment["喜用神"],
        "格局倾向": "待定" if has_conflict else candidate_tendency,
        "候选结构标签": candidate_tendency,
        "解释状态": "degraded" if has_conflict else "ok",
    }
    return _with_evidence(
        chart,
        payload,
        {"正官": guan, "七杀": sha, "印绶": yin, "食伤": shi, "财星": cai},
    )


def analyze_marriage_chart(chart: dict, gender: str = "男") -> dict:
    day_zhi = chart["四柱"]["日柱"][1]
    day_gan = chart["日主"]
    canggan = ZHI_CANG_GAN.get(day_zhi, [])
    canggan_shishen = [shi_shen(day_gan, cg) for cg in canggan]
    if gender in ("男", "M", "male"):
        spouse_star = "财星"
        spouse_gods = ["正财", "偏财"]
    else:
        spouse_star = "官星"
        spouse_gods = ["正官", "七杀"]
    spouse_positions = [
        key for key, value in chart["十神"].items() if value in spouse_gods
    ]
    payload = {
        "success": True,
        "配偶宫": day_zhi,
        "配偶宫藏干": canggan,
        "配偶宫藏干十神": canggan_shishen,
        "配偶星": spouse_star,
        "配偶星位置": spouse_positions,
        "日支五行": WUXING_ZHI[day_zhi],
    }
    return _with_evidence(
        chart,
        payload,
        {"配偶宫": day_zhi, "配偶星位置": spouse_positions},
    )


def analyze_health_chart(chart: dict) -> dict:
    wx = chart["五行力量"]
    organ_map = {
        "木": ("肝", "胆", "筋", "目"),
        "火": ("心", "小肠", "脉", "舌"),
        "土": ("脾", "胃", "肉", "口"),
        "金": ("肺", "大肠", "皮毛", "鼻"),
        "水": ("肾", "膀胱", "骨", "耳"),
    }
    total = sum(wx.values()) or 1
    analysis = {}
    for element, organs in organ_map.items():
        score = wx.get(element, 0)
        ratio = score / total
        if ratio < 0.1:
            status = "相对偏弱"
        elif ratio > 0.35:
            status = "相对偏旺"
        else:
            status = "相对均衡"
        analysis[element] = {
            "五行": element,
            "传统对应范畴": list(organs),
            "力量": score,
            "占比": f"{ratio:.1%}",
            "五行符号状态": status,
        }
    payload = {
        "success": True,
        "医疗声明": (
            "五行与脏腑的对应属于传统文化类比，不构成健康评估、"
            "医疗诊断、治疗或用药建议。出现症状时请咨询合格医疗专业人员。"
        ),
        "五行健康分析": analysis,
        "最弱五行": min(wx, key=wx.get),
        "最旺五行": max(wx, key=wx.get),
    }
    return _with_evidence(chart, payload, {"五行力量": wx})


def analyze_wealth_chart(chart: dict) -> dict:
    assessment = chart.get("strength_assessment") or attach_strength_assessment(chart)[
        "strength_assessment"
    ]
    day_wx = chart["日主五行"]
    cai_wx = WUXING_KE.get(day_wx, "未知")
    wx = chart["五行力量"]
    total = sum(wx.values()) or 1
    cai_strength = wx.get(cai_wx, 0)
    if assessment.get("conflicts"):
        prompt = "旺衰模型存在冲突，已抑制确定性财运模板。"
    elif cai_strength < total * 0.1:
        prompt = "财星力量偏弱，需结合现实现金流判断。"
    else:
        prompt = "财星存在，收入判断需结合现实职业、现金流与风险。"
    payload = {
        "success": True,
        "日主五行": day_wx,
        "财星五行": cai_wx,
        "财星力量": cai_strength,
        "财星占比": f"{cai_strength / total:.1%}",
        "财星位置": [
            key for key, value in chart["十神"].items()
            if value in ("正财", "偏财")
        ],
        "喜用神": assessment["喜用神"],
        "财运提示": prompt,
    }
    return _with_evidence(
        chart,
        payload,
        {
            "财星五行": cai_wx,
            "财星力量": cai_strength,
            "财星位置": payload["财星位置"],
        },
    )


def analyze_yin_shou_chart(chart: dict) -> dict:
    ten_gods = chart["十神"]
    zheng_yin = [key for key, value in ten_gods.items() if value == "正印"]
    pian_yin = [key for key, value in ten_gods.items() if value == "偏印"]
    payload = {
        "success": True,
        "正印位置": zheng_yin,
        "偏印位置": pian_yin,
        "印星总数": len(zheng_yin) + len(pian_yin),
    }
    return _with_evidence(
        chart,
        payload,
        {"正印位置": zheng_yin, "偏印位置": pian_yin},
    )


class BaziToolkit(Toolkit):
    def __init__(self, **kwargs):
        tools = [
            self.paipan,
            self.analyze_dayun,
            self.analyze_liunian,
            self.analyze_liuyue,
            self.analyze_liuyue_by_date,
            self.analyze_liuri,
            self.check_chong_he,
            self.find_shensha,
            self.analyze_huoyuan,
            self.analyze_guan_sha,
            self.analyze_cai_xing,
            self.analyze_yin_shou,
            self.analyze_marriage,
            self.analyze_career,
            self.analyze_health,
            self.analyze_wealth,
            self.ganzhi_query,
        ]
        super().__init__(name="bazi_tools", tools=tools, **kwargs)

    def paipan(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        gender: str = "男",
        minute: int = 0,
        second: int = 0,
        birth_context: Optional[dict] = None,
        year_boundary: str = "lichun",
    ) -> str:
        """
        排八字命盘：根据公历出生时间排出四柱八字命盘，包含十神、五行、纳音、十二长生等完整信息。

        Args:
            year: 公历年份 (如 1990)
            month: 公历月份 (1-12)
            day: 公历日期 (1-31)
            hour: 出生时辰 (0-23 小时制，子时为 23 或 0)
            gender: 性别 ("男" 或 "女")
        """
        try:
            result = _build_analysis_chart(
                year,
                month,
                day,
                hour,
                gender,
                minute,
                second,
                birth_context,
                year_boundary,
            )
            result["性别"] = gender
            result["出生公历"] = (
                f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
            )
            return json.dumps({"success": True, "data": result}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_dayun(self, year_ganzhi: str, month_ganzhi: str,
                      gender: str, start_age: int = 1) -> str:
        """
        排大运：根据年柱、月柱干支和性别排出八步大运。

        Args:
            year_ganzhi: 年柱干支 (如 "庚午")
            month_ganzhi: 月柱干支 (如 "戊寅")
            gender: 性别 ("男" 或 "女")
            start_age: 起运年龄 (默认 1)
        """
        try:
            dayun_list = build_dayun(gender, year_ganzhi, month_ganzhi, start_age)
            return json.dumps({
                "success": True,
                "大运": dayun_list,
                "component_status": {
                    "status": "degraded",
                    "code": "raw_pillar_input",
                    "message": "该低层工具只接收年柱和月柱，未关联 ComputedChart。",
                },
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_liunian(self, start_year: int, count: int = 10) -> str:
        """
        排流年：列出指定起始年份开始的若干年流年干支。

        Args:
            start_year: 起始年份
            count: 排列年数 (默认 10)
        """
        try:
            result = build_liunian(start_year, count)
            return json.dumps({"success": True, "流年": result}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_liuyue(self, year_gan: str, month: int) -> str:
        """
        排流月：根据年干和农历月份排出该月干支。

        Args:
            year_gan: 年干 (如 "庚")
            month: 农历月份 (1-12)
        """
        try:
            mgz = month_ganzhi(year_gan, month - 1)
            return json.dumps({
                "success": True,
                "月份": month,
                "月柱干支": mgz,
                "天干五行": WUXING_GAN[mgz[0]],
                "地支五行": WUXING_ZHI[mgz[1]],
                "component_status": {
                    "status": "degraded",
                    "code": "legacy_lunar_month_mapping",
                    "message": (
                        "该兼容接口按农历月序映射，不处理节气边界；"
                        "精确流月请使用 analyze_liuyue_by_date。"
                    ),
                },
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_liuyue_by_date(
        self,
        year: int,
        month: int,
        day: int,
        hour: int = 12,
        minute: int = 0,
        second: int = 0,
        year_boundary: str = "lichun",
        birth_context: Optional[dict] = None,
    ) -> str:
        """Return the exact Bazi flow month for a concrete civil date/time."""
        try:
            chart = _build_analysis_chart(
                year,
                month,
                day,
                hour,
                minute=minute,
                second=second,
                birth_context=birth_context,
                year_boundary=year_boundary,
            )
            return json.dumps({
                "success": True,
                "流年干支": chart["四柱"]["年柱"],
                "流月干支": chart["四柱"]["月柱"],
                "目标时间": chart["birth_time"]["effective_time"],
                "calendar_time": chart["birth_time"]["calendar_time"],
                "chart_id": chart["chart_id"],
                "birth_time": chart["birth_time"],
                "component_status": {
                    "status": "ok",
                    "backend": "shared-computed-chart",
                },
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_liuri(self, year: int, month: int, day: int) -> str:
        """
        查日柱干支：根据公历日期查出日柱干支。

        Args:
            year: 公历年份
            month: 公历月份
            day: 公历日期
        """
        try:
            dgz = day_ganzhi_from_date(date(year, month, day))
            return json.dumps({
                "success": True,
                "日期": f"{year}-{month:02d}-{day:02d}",
                "日柱干支": dgz,
                "日干五行": WUXING_GAN[dgz[0]],
                "日支五行": WUXING_ZHI[dgz[1]],
                "纳音": nayin(dgz),
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def check_chong_he(self, zhi1: str, zhi2: str) -> str:
        """
        查地支冲合：检查两个地支之间的六合、六冲、三合、三会、相害、相刑关系。

        Args:
            zhi1: 第一个地支 (如 "子")
            zhi2: 第二个地支 (如 "午")
        """
        try:
            liu_he = [("子", "丑"), ("寅", "亥"), ("卯", "戌"), ("辰", "酉"),
                      ("巳", "申"), ("午", "未")]
            liu_chong = [("子", "午"), ("丑", "未"), ("寅", "申"), ("卯", "酉"),
                         ("辰", "戌"), ("巳", "亥")]
            san_he = [("申", "子", "辰"), ("亥", "卯", "未"), ("寅", "午", "戌"),
                      ("巳", "酉", "丑")]
            san_hui = [("寅", "卯", "辰"), ("巳", "午", "未"), ("申", "酉", "戌"),
                       ("亥", "子", "丑")]
            xiang_hai = [("子", "未"), ("丑", "午"), ("寅", "巳"), ("卯", "辰"),
                         ("申", "亥"), ("酉", "戌")]
            xiang_xing = [("寅", "巳"), ("巳", "申"), ("申", "寅"),
                          ("丑", "戌"), ("戌", "未"), ("未", "丑"),
                          ("子", "卯"), ("卯", "子"), ("辰", "辰"),
                          ("午", "午"), ("酉", "酉"), ("亥", "亥")]

            relations = []
            pair_sorted = tuple(sorted([zhi1, zhi2]))

            for a, b in liu_he:
                if pair_sorted == tuple(sorted([a, b])):
                    relations.append("六合")
            for a, b in liu_chong:
                if pair_sorted == tuple(sorted([a, b])):
                    relations.append("六冲")
            for trio in san_he:
                if zhi1 in trio and zhi2 in trio:
                    relations.append(f"三合({'+'.join(trio)})")
                    break
            for trio in san_hui:
                if zhi1 in trio and zhi2 in trio:
                    relations.append(f"三会({'+'.join(trio)})")
                    break
            for a, b in xiang_hai:
                if pair_sorted == tuple(sorted([a, b])):
                    relations.append("相害")
            for item in xiang_xing:
                if zhi1 == zhi2 and zhi1 == item[0] and item[0] == item[1]:
                    relations.append("自刑")
                    break
                if pair_sorted == tuple(sorted([item[0], item[1]])):
                    relations.append("相刑")
                    break

            if not relations:
                relations.append("无明显关系")

            return json.dumps({
                "success": True,
                "地支1": zhi1,
                "地支2": zhi2,
                "关系": relations,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def find_shensha(self, year_ganzhi: str, month_ganzhi: str,
                     day_ganzhi: str, hour_ganzhi: str) -> str:
        """
        查神煞：根据四柱干支查找常见神煞（天乙贵人、太极贵人、文昌贵人、驿马、桃花、华盖、将星等）。

        Args:
            year_ganzhi: 年柱干支
            month_ganzhi: 月柱干支
            day_ganzhi: 日柱干支
            hour_ganzhi: 时柱干支
        """
        try:
            day_gan = day_ganzhi[0]
            year_zhi = year_ganzhi[1]

            tianyi_map = {
                "甲": ["丑", "未"], "乙": ["子", "申"], "丙": ["亥", "酉"],
                "丁": ["亥", "酉"], "戊": ["丑", "未"], "己": ["子", "申"],
                "庚": ["丑", "未"], "辛": ["午", "寅"], "壬": ["卯", "巳"],
                "癸": ["卯", "巳"],
            }
            wenchang_map = {
                "甲": "巳", "乙": "午", "丙": "申", "丁": "酉", "戊": "申",
                "己": "酉", "庚": "亥", "辛": "子", "壬": "寅", "癸": "卯",
            }
            taohua_map = {
                "子": "酉", "午": "卯", "卯": "子", "酉": "午",
                "寅": "卯", "申": "酉", "巳": "午", "亥": "子",
                "辰": "酉", "戌": "卯", "丑": "午", "未": "子",
            }
            yima_map = {
                "子": "寅", "午": "申", "卯": "巳", "酉": "亥",
                "寅": "申", "申": "寅", "巳": "亥", "亥": "巳",
                "辰": "寅", "戌": "申", "丑": "亥", "未": "巳",
            }
            huagai_map = {
                "子": "辰", "午": "戌", "卯": "未", "酉": "丑",
                "寅": "戌", "申": "辰", "巳": "丑", "亥": "未",
                "辰": "辰", "戌": "戌", "丑": "丑", "未": "未",
            }

            all_zhi = [gz[1] for gz in [year_ganzhi, month_ganzhi, day_ganzhi, hour_ganzhi]]
            shensha = {}

            tianyi = tianyi_map.get(day_gan, [])
            found_ty = [z for z in all_zhi if z in tianyi]
            if found_ty:
                shensha["天乙贵人"] = found_ty

            wc = wenchang_map.get(day_gan, "")
            if wc in all_zhi:
                shensha["文昌贵人"] = [wc]

            th = taohua_map.get(year_zhi, "")
            if th in all_zhi:
                shensha["桃花"] = [th]

            ym = yima_map.get(year_zhi, "")
            if ym in all_zhi:
                shensha["驿马"] = [ym]

            hg = huagai_map.get(year_zhi, "")
            if hg in all_zhi:
                shensha["华盖"] = [hg]

            return json.dumps({"success": True, "神煞": shensha}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_huoyuan(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        gender: str = "男",
        minute: int = 0,
        second: int = 0,
        birth_context: Optional[dict] = None,
        year_boundary: str = "lichun",
    ) -> str:
        """
        分析火候（格局）：根据八字排盘判断日主旺衰，分析命局格局。

        Args:
            year: 公历年份
            month: 公历月份
            day: 公历日期
            hour: 出生时辰
            gender: 性别
        """
        try:
            chart = _build_analysis_chart(
                year,
                month,
                day,
                hour,
                gender,
                minute,
                second,
                birth_context,
                year_boundary,
            )
            return json.dumps(analyze_huoyuan_chart(chart), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_guan_sha(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        gender: str = "男",
        minute: int = 0,
        second: int = 0,
        birth_context: Optional[dict] = None,
        year_boundary: str = "lichun",
    ) -> str:
        """
        分析官杀：分析八字中正官、七杀的分布及对命主的影响。

        Args:
            year: 公历年份
            month: 公历月份
            day: 公历日期
            hour: 出生时辰
        """
        try:
            chart = _build_analysis_chart(
                year,
                month,
                day,
                hour,
                gender,
                minute,
                second,
                birth_context,
                year_boundary,
            )
            ten_gods = chart["十神"]
            guan_positions = []
            sha_positions = []
            for key, val in ten_gods.items():
                if val == "正官":
                    guan_positions.append(key)
                elif val == "七杀":
                    sha_positions.append(key)

            return json.dumps(_with_chart_audit(chart, {
                "success": True,
                "正官位置": guan_positions,
                "七杀位置": sha_positions,
                "官杀数量": len(guan_positions) + len(sha_positions),
                "正官数量": len(guan_positions),
                "七杀数量": len(sha_positions),
                "提示": "官杀混杂" if guan_positions and sha_positions else "清纯",
            }), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_cai_xing(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        gender: str = "男",
        minute: int = 0,
        second: int = 0,
        birth_context: Optional[dict] = None,
        year_boundary: str = "lichun",
    ) -> str:
        """
        分析财星：分析八字中正财、偏财的分布。

        Args:
            year: 公历年份
            month: 公历月份
            day: 公历日期
            hour: 出生时辰
        """
        try:
            chart = _build_analysis_chart(
                year,
                month,
                day,
                hour,
                gender,
                minute,
                second,
                birth_context,
                year_boundary,
            )
            ten_gods = chart["十神"]
            zheng_cai = []
            pian_cai = []
            for key, val in ten_gods.items():
                if val == "正财":
                    zheng_cai.append(key)
                elif val == "偏财":
                    pian_cai.append(key)

            return json.dumps(_with_chart_audit(chart, {
                "success": True,
                "正财位置": zheng_cai,
                "偏财位置": pian_cai,
                "财星总数": len(zheng_cai) + len(pian_cai),
            }), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_yin_shou(
        self, year: int, month: int, day: int, hour: int,
        minute: int = 0, second: int = 0,
        gender: str = "男",
        birth_context: Optional[dict] = None,
        year_boundary: str = "lichun",
    ) -> str:
        """
        分析印绶：分析八字中正印、偏印的分布。

        Args:
            year: 公历年份
            month: 公历月份
            day: 公历日期
            hour: 出生时辰
        """
        try:
            chart = _build_analysis_chart(
                year,
                month,
                day,
                hour,
                gender,
                minute,
                second,
                birth_context,
                year_boundary,
            )
            return json.dumps(analyze_yin_shou_chart(chart), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_marriage(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        gender: str = "男",
        minute: int = 0,
        second: int = 0,
        birth_context: Optional[dict] = None,
        year_boundary: str = "lichun",
    ) -> str:
        """
        分析婚姻宫：分析日支（配偶宫）及财/官星对婚姻的影响。

        Args:
            year: 公历年份
            month: 公历月份
            day: 公历日期
            hour: 出生时辰
            gender: 性别
        """
        try:
            chart = _build_analysis_chart(
                year,
                month,
                day,
                hour,
                gender,
                minute,
                second,
                birth_context,
                year_boundary,
            )
            return json.dumps(
                analyze_marriage_chart(chart, gender), ensure_ascii=False
            )
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_career(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        gender: str = "男",
        minute: int = 0,
        second: int = 0,
        birth_context: Optional[dict] = None,
        year_boundary: str = "lichun",
    ) -> str:
        """
        分析事业：分析官杀、印绶对事业发展的影响。

        Args:
            year: 公历年份
            month: 公历月份
            day: 公历日期
            hour: 出生时辰
            gender: 性别
        """
        try:
            chart = _build_analysis_chart(
                year,
                month,
                day,
                hour,
                gender,
                minute,
                second,
                birth_context,
                year_boundary,
            )
            return json.dumps(analyze_career_chart(chart), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_health(
        self, year: int, month: int, day: int, hour: int,
        minute: int = 0, second: int = 0,
        gender: str = "男",
        birth_context: Optional[dict] = None,
        year_boundary: str = "lichun",
    ) -> str:
        """
        分析健康：根据五行偏缺分析潜在健康倾向。五行对应五脏：木-肝、火-心、土-脾、金-肺、水-肾。

        Args:
            year: 公历年份
            month: 公历月份
            day: 公历日期
            hour: 出生时辰
        """
        try:
            chart = _build_analysis_chart(
                year,
                month,
                day,
                hour,
                gender,
                minute,
                second,
                birth_context,
                year_boundary,
            )
            return json.dumps(analyze_health_chart(chart), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_wealth(
        self, year: int, month: int, day: int, hour: int,
        minute: int = 0, second: int = 0,
        gender: str = "男",
        birth_context: Optional[dict] = None,
        year_boundary: str = "lichun",
    ) -> str:
        """
        分析财运：分析财星力量、位置及与日主的关系。

        Args:
            year: 公历年份
            month: 公历月份
            day: 公历日期
            hour: 出生时辰
        """
        try:
            chart = _build_analysis_chart(
                year,
                month,
                day,
                hour,
                gender,
                minute,
                second,
                birth_context,
                year_boundary,
            )
            return json.dumps(analyze_wealth_chart(chart), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def ganzhi_query(self, ganzhi: str) -> str:
        """
        查询干支信息：查询指定干支的五行、阴阳、纳音、藏干等基础信息。

        Args:
            ganzhi: 天干地支组合 (如 "甲子")
        """
        try:
            if len(ganzhi) < 2:
                return json.dumps({"success": False, "error": "干支格式错误，需两个字符"})

            gan = ganzhi[0]
            zhi = ganzhi[1]
            info = {
                "干支": ganzhi,
                "天干": gan,
                "地支": zhi,
                "天干五行": WUXING_GAN.get(gan, "未知"),
                "天干阴阳": YINYANG_GAN.get(gan, "未知"),
                "地支五行": WUXING_ZHI.get(zhi, "未知"),
                "地支阴阳": YINYANG_GAN.get(gan, "未知"),
                "纳音": nayin(ganzhi),
                "地支藏干": ZHI_CANG_GAN.get(zhi, []),
                "生肖": animal_year(4 + (TIANGAN_IDX.get(gan, 0) * 12 + DIZHI_IDX.get(zhi, 0)) // 2) if False else "",
            }

            return json.dumps({"success": True, "data": info}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
