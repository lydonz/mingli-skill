"""
hybrid_tools.py — 混合路由工具包
工具只提供排盘数据 + 规则引擎建议，最终答案由 agent 推理决定。
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.toolkit_base import Toolkit
from tools.liunian_analyzer import integrate_year_analysis
from tools.birth_context import BirthContextError
from tools.chart_assessment import get_resolved_preference


class HybridMingliToolkit(Toolkit):
    """命理工具包：提供排盘数据和分析建议，agent 做最终推理。"""

    def __init__(self):
        super().__init__(name="hybrid_mingli")
        self._chart_cache = {}

    def analyze_question(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        gender: str,
        category: str,
        question: str,
        options_json: str = "[]",
        minute: int = 0,
        year_boundary: str = "lichun",
        second: int = 0,
        birth_context: dict | None = None,
        analysis_period: dict | None = None,
        knowledge_query: str | None = None,
        knowledge_packs: list[str] | None = None,
        interpretation_document: dict | None = None,
    ) -> str:
        """
        命理分析工具：返回完整排盘数据 + 规则引擎建议。
        最终答案必须由 agent 根据数据推理决定，不可直接采用建议。

        :param year: 出生年（公历）
        :param month: 出生月
        :param day: 出生日
        :param hour: 出生时（0-23）
        :param gender: 性别（男/女）
        :param category: 问题类别（事业/婚姻/财运/健康/子女/学业/家庭/性格/官非/灾劫/外貌/运势）
        :param question: 问题文本
        :param options_json: 选项 JSON，格式 [{"letter":"A","text":"..."},{"letter":"B","text":"..."}]
        :param birth_context: 结构化地点、时区、真太阳时和误差范围输入
        :param analysis_period: 显式流年日期区间
        :param knowledge_query: 可选本地知识库检索文本，未传入时不检索
        :param knowledge_packs: 可选本地知识包标识列表；传入时以问题文本检索
        :param interpretation_document: 可选的、与 chart_id 绑定的解读文本契约
        :return: JSON 字符串，包含排盘数据、证据、状态与规则引擎建议
        """
        options_warning = None
        try:
            parsed_options = json.loads(options_json or "[]")
        except (TypeError, json.JSONDecodeError):
            parsed_options = []
            options_warning = "options_json 无法解析；选择题预测已退役，已忽略该字段。"
        if not isinstance(parsed_options, list):
            options = []
            options_warning = "options_json 不是选项列表；选择题预测已退役，已忽略该字段。"
        else:
            options = []
            for index, option in enumerate(parsed_options):
                if (
                    not isinstance(option, dict)
                    or not isinstance(option.get("letter"), str)
                    or not option["letter"]
                    or not isinstance(option.get("text", ""), str)
                ):
                    options_warning = (
                        f"options_json 第 {index + 1} 项格式无效；"
                        "选择题预测已退役，已忽略该字段。"
                    )
                    options = []
                    break
                options.append({
                    "letter": option["letter"],
                    "text": option.get("text", ""),
                })
            letters = [option["letter"] for option in options]
            if len(letters) != len(set(letters)):
                options_warning = (
                    "options_json 存在重复选项编号；"
                    "选择题预测已退役，系统不会自动选择答案。"
                )
        normalized_options_json = json.dumps(
            options, ensure_ascii=False, separators=(",", ":")
        )

        birth_info = {
            "year": year, "month": month, "day": day,
            "hour": hour, "minute": minute, "second": second, "gender": gender,
            "year_boundary": year_boundary,
        }
        if birth_context is not None:
            birth_info["birth_context"] = birth_context
        import hashlib
        _case_id = hashlib.md5(
            json.dumps(birth_info, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        q = {
            "birth_info": birth_info,
            "category": category,
            "question": question,
            "options": options,
            "case_id": _case_id,
        }

        try:
            chart_data = self._build_chart_data(q)
        except BirthContextError as exc:
            return json.dumps({
                "success": False,
                "error": exc.as_dict(),
                "component_status": {
                    "birth_context": {"status": "error", **exc.as_dict()},
                },
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({
                "success": False,
                "error": {
                    "code": "chart_construction_failed",
                    "message": str(exc),
                },
                "component_status": {
                    "chart": {
                        "status": "error",
                        "code": "chart_construction_failed",
                        "message": str(exc),
                    },
                },
            }, ensure_ascii=False)
        warnings = chart_data.pop("_warnings", [])
        if options_warning:
            warnings.append(options_warning)
        rules_suggestion = self._get_rules_suggestion(
            q, chart_data.get("_chart")
        )
        chart_data.pop("_chart", None)

        liunian_data = None
        liunian_status = {
            "status": "skipped",
            "code": "no_target_period",
            "message": "未提供流年目标区间，已跳过流年分析。",
        }
        try:
            raw_ln = integrate_year_analysis(
                birth_info=birth_info,
                chart=chart_data.get("bazi_raw"),
                question=question,
                options_json=normalized_options_json,
                analysis_period=analysis_period,
            )
            ln_parsed = json.loads(raw_ln)
            liunian_data = ln_parsed
            liunian_status = ln_parsed.get(
                "component_status", {"status": "ok"}
            )
        except Exception as exc:
            liunian_data = {
                "success": False,
                "component_status": {
                    "status": "error",
                    "code": "liunian_analysis_failed",
                    "message": str(exc),
                },
            }
            liunian_status = liunian_data["component_status"]

        # 奇门必须以起问时间起局；用出生时间为多个流年重复起盘会制造
        # 看似精确、实则无效的数据，因此不再自动注入。
        qimen_data = None
        if liunian_data and liunian_data.get("检测到的年份"):
            warnings.append("未自动生成奇门流年盘：奇门应使用实际起问时间，而非出生时间。")

        knowledge_result = None
        knowledge_status = {
            "status": "skipped",
            "code": "not_requested",
            "backend": "local_knowledge",
            "network": "disabled",
        }
        if knowledge_query is not None or knowledge_packs is not None:
            try:
                from tools.knowledge_tools import search_local_knowledge

                knowledge_result = search_local_knowledge(
                    knowledge_query if knowledge_query is not None else question,
                    pack_ids=knowledge_packs,
                )
                knowledge_status = {
                    "status": knowledge_result["status"],
                    "code": knowledge_result["code"],
                    "backend": "local_knowledge",
                    "network": "disabled",
                }
                if knowledge_result["status"] != "ok":
                    warnings.append(
                        f"本地知识库检索状态：{knowledge_result['message']}"
                    )
            except Exception as exc:
                knowledge_result = {
                    "references": [],
                    "notice": (
                        "本地知识引用不可用；命盘计算和规则证据未受其影响。"
                    ),
                }
                knowledge_status = {
                    "status": "error",
                    "code": "knowledge_search_failed",
                    "backend": "local_knowledge",
                    "network": "disabled",
                    "message": str(exc),
                }
                warnings.append("本地知识库检索失败，未返回知识引用。")

        result = {
            "success": True,
            "status": "ok",
            "category": category,
            "bazi": chart_data.get("bazi", {}),
            "ziwei": chart_data.get("ziwei", {}),
            "ziwei_raw": chart_data.get("ziwei_raw"),
            "career_analysis": chart_data.get("career_analysis"),
            "marriage_analysis": chart_data.get("marriage_analysis"),
            "liunian": liunian_data,
            "qimen": qimen_data,
            "rules_suggestion": rules_suggestion,
            "data_quality_warnings": warnings,
            "component_status": {
                **chart_data.get("component_status", {}),
                "liunian": liunian_status,
                "knowledge": knowledge_status,
                "rules_suggestion": rules_suggestion["component_status"],
            },
            "chart_id": chart_data.get("chart_id"),
            "birth_time": chart_data.get("birth_time"),
            "strength_assessment": chart_data.get("strength_assessment"),
            "legacy_strength": chart_data.get("legacy_strength"),
            "note": "历法事实、传统结构和现实建议应分层表达；项目不再自动猜测选择题答案。",
        }
        if knowledge_result is not None:
            result["knowledge_references"] = knowledge_result["references"]
            result["knowledge_context"] = {
                "query": knowledge_result.get("query", knowledge_query),
                "notice": knowledge_result["notice"],
                "pack_statuses": knowledge_result.get("pack_statuses", []),
            }
        # Include all additional analyses from chart_data
        for key in ("health_analysis", "wealth_analysis", "education_analysis",
                     "huoyuan_analysis", "family_analysis"):
            if key in chart_data:
                result[key] = chart_data[key]
        try:
            from tools.interpretation_contract import (
                build_interpretation_brief,
                validate_interpretation_document,
            )

            interpretation_brief = build_interpretation_brief(result)
            result["interpretation_brief"] = interpretation_brief
            interpretation_status = {
                "status": "skipped",
                "code": "not_provided",
                "backend": "interpretation_contract",
            }
            if interpretation_document is not None:
                interpretation = validate_interpretation_document(
                    interpretation_document,
                    interpretation_brief,
                )
                result["interpretation"] = interpretation
                interpretation_status = {
                    "status": interpretation["status"],
                    "code": interpretation["code"] if "code" in interpretation else "validated",
                    "backend": "interpretation_contract",
                }
                if interpretation["status"] != "ok":
                    warnings.append(
                        f"解读文本契约状态：{interpretation['message']}"
                    )
        except Exception as exc:
            interpretation_status = {
                "status": "error",
                "code": "interpretation_contract_failed",
                "backend": "interpretation_contract",
                "message": str(exc),
            }
            warnings.append("解读文本契约不可用，未附加解释文本。")
        result["component_status"]["interpretation"] = interpretation_status
        result = {k: v for k, v in result.items() if v is not None}
        return json.dumps(result, ensure_ascii=False)

    def _build_chart_data(self, q: dict) -> dict:
        """构建完整排盘数据。"""
        from tools.tool_integration import build_tool_data
        from engine.run_tools_engine import compute_chart

        bi = q["birth_info"]
        y, m, d, h = bi["year"], bi["month"], bi["day"], bi.get("hour", 12)
        minute = bi.get("minute", 0)
        g = bi.get("gender", "男")

        chart = compute_chart(bi)
        tool_data = {}
        result = {"_warnings": [], "component_status": {}}
        tool_data = build_tool_data(y, m, d, h, g, chart=chart)
        result["component_status"].update(tool_data.get("component_status", {}))
        result["_warnings"].extend(tool_data.get("_warnings", []))
        result["_chart"] = chart

        if chart:
            preference = get_resolved_preference(chart)
            assessment = chart.get("strength_assessment", {})
            result["bazi"] = {
                "日主": chart.get("日主", ""),
                "日主五行": chart.get("日主五行", ""),
                "日主强弱": chart.get("日主强弱", ""),
                "旺衰": assessment.get("旺衰", chart.get("日主强弱", "")),
                "legacy_日主强弱": chart.get("legacy_strength", {}).get(
                    "value", chart.get("日主强弱", "")
                ),
                "五行力量": chart.get("五行力量", {}),
                "十神": chart.get("十神", {}),
                "喜用神": preference["喜用神"],
                "喜神": preference["喜神"],
                "忌神": preference["忌神"],
                "喜用神规则版本": preference["ruleset_version"],
                "legacy_喜用神": chart.get("喜用神", []),
                "legacy_忌神": chart.get("忌神", []),
                "空亡": chart.get("空亡", ""),
                "纳音": chart.get("纳音", ""),
                "四柱": chart.get("四柱", {}),
                "大运": chart.get("大运", []),
                "日主阴阳": chart.get("日主阴阳", ""),
                "五行占比": chart.get("五行占比", {}),
            }
            result["bazi_raw"] = chart
            result["chart_id"] = chart.get("chart_id")
            result["birth_time"] = chart.get("birth_time")
            result["strength_assessment"] = chart.get("strength_assessment")
            result["legacy_strength"] = chart.get("legacy_strength")
            result["component_status"]["chart"] = {
                "status": "ok",
                "backend": "calendar_engine",
                "chart_id": chart.get("chart_id"),
            }
            for warning in chart.get("birth_time", {}).get("warnings", []):
                result["_warnings"].append(warning.get("message", str(warning)))

        if tool_data.get("ziwei"):
            zw = tool_data["ziwei"]
            result["ziwei"] = {
                "命宫主星": tool_data.get("zw_命宫", []),
                "身宫": tool_data.get("zw_body_palace", ""),
                "五行局": tool_data.get("zw_ju", ""),
                "官禄宫主星": tool_data.get("zw_官禄", []),
                "夫妻宫主星": tool_data.get("zw_夫妻", []),
                "财帛宫主星": tool_data.get("zw_财帛", []),
                "疾厄宫主星": tool_data.get("zw_疾厄", []),
                "子女宫主星": tool_data.get("zw_子女", []),
                "迁移宫主星": tool_data.get("zw_迁移", []),
                "父母宫主星": tool_data.get("zw_父母", []),
                "田宅宫主星": tool_data.get("zw_田宅", []),
                "生年四化": zw.get("生年四化", []),
                "子时约定": zw.get("子时约定", {}),
            }
            result["ziwei_raw"] = zw
        elif tool_data.get("ziwei_status"):
            result["ziwei"] = tool_data["ziwei_status"]
            result["ziwei_raw"] = tool_data["ziwei_status"]

        if tool_data.get("bz_career"):
            result["career_analysis"] = tool_data["bz_career"]
        if tool_data.get("bz_marriage"):
            result["marriage_analysis"] = tool_data["bz_marriage"]
        if tool_data.get("bz_health"):
            result["health_analysis"] = tool_data["bz_health"]
        if tool_data.get("bz_wealth"):
            result["wealth_analysis"] = tool_data["bz_wealth"]
        if tool_data.get("bz_education"):
            result["education_analysis"] = tool_data["bz_education"]
        if tool_data.get("bz_huoyuan"):
            result["huoyuan_analysis"] = tool_data["bz_huoyuan"]

        # Generate family_analysis from chart data if category needs it
        if q.get("category") == "家庭" and chart:
            pillars = chart.get("四柱", {})
            tg = chart.get("十神", {})
            wx = chart.get("五行力量", {})
            day_gan = chart.get("日主", "")

            # Year pillar = ancestry/family background
            ygz = pillars.get("年柱", "")
            # Month pillar = parents
            mgz = pillars.get("月柱", "")

            # Find father star (偏财 for male, 正财 can also be father)
            father_positions = [k for k, v in tg.items() if v in ("偏财", "正财") and "年" in k]
            # Find mother star (正印 for male, 偏印 can be mother)
            mother_positions = [k for k, v in tg.items() if v in ("正印", "偏印") and ("年" in k or "月" in k)]

            result["family_analysis"] = {
                "年柱": ygz,
                "月柱": mgz,
                "父母星位置_父亲": father_positions,
                "父母星位置_母亲": mother_positions,
                "五行力量": wx,
                "日主强弱": chart.get("日主强弱", ""),
                "旺衰": chart.get("strength_assessment", {}).get(
                    "旺衰", chart.get("日主强弱", "")
                ),
                "喜用神": preference["喜用神"],
            }

        if chart.get("大运精度") != "solar-term":
            result["_warnings"].append("大运未使用精确节气计算，请检查 lunar-python 依赖。")
        return result

    def _get_rules_suggestion(self, q: dict, chart: dict | None = None) -> dict:
        """Return a visible disabled state for the retired answer predictor."""
        from engine.run_tools_engine import compute_chart
        from tools.safety_policy import assess_rules_suggestion_request

        bi = q["birth_info"]
        chart = chart or compute_chart(bi)
        options = q.get("options", [])
        policy = assess_rules_suggestion_request(
            q.get("category"),
            q.get("question"),
            options,
        )

        if not options:
            pred = None
            status = {
                "status": "skipped",
                "code": "rules_suggestion_no_options",
                "backend": "rules_engine",
                "message": "自由问答未提供选项，已跳过已退役的选择题规则引擎。",
            }
        elif policy["suppressed"]:
            pred = None
            status = {
                "status": "degraded",
                "code": policy["code"],
                "backend": "rules_engine",
                "message": policy["message"],
            }
        else:
            pred = None
            status = {
                "status": "disabled",
                "code": "rules_suggestion_retired",
                "backend": "rules_engine",
                "message": "历史事件选择题预测已停用；仅返回可审计排盘与结构化文化资料。",
            }

        if status["status"] != "ok":
            confidence = status["message"]
        else:
            confidence = "不适用"
        return {
            "suggested_answer": pred,
            "confidence": confidence,
            "日主": chart.get("日主", ""),
            "日主强弱": chart.get("日主强弱", ""),
            "旺衰": chart.get("strength_assessment", {}).get(
                "旺衰", chart.get("日主强弱", "")
            ),
            "喜用神": get_resolved_preference(chart)["喜用神"],
            "strength_assessment": chart.get("strength_assessment"),
            "component_status": status,
        }

    def get_bazi_chart(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        gender: str,
        minute: int = 0,
        year_boundary: str = "lichun",
        second: int = 0,
        birth_context: dict | None = None,
    ) -> str:
        """
        获取完整八字排盘数据。

        :param year: 出生年（公历）
        :param month: 出生月
        :param day: 出生日
        :param hour: 出生时（0-23）
        :param gender: 性别（男/女）
        :return: JSON 字符串，包含四柱、五行、十神、喜用神、大运等
        """
        from engine.run_tools_engine import compute_chart

        bi = {
            "year": year, "month": month, "day": day, "hour": hour,
            "minute": minute, "second": second, "year_boundary": year_boundary,
            "gender": gender,
        }
        if birth_context is not None:
            bi["birth_context"] = birth_context
        try:
            chart = compute_chart(bi)
        except BirthContextError as exc:
            return json.dumps({"error": exc.as_dict()}, ensure_ascii=False)
        if not chart:
            return json.dumps({"error": "无法排盘，请检查出生信息"}, ensure_ascii=False)
        preference = get_resolved_preference(chart)
        assessment = chart.get("strength_assessment", {})

        return json.dumps({
            "四柱": chart.get("四柱", {}),
            "日主": chart.get("日主", ""),
            "日主五行": chart.get("日主五行", ""),
            "日主强弱": chart.get("日主强弱", ""),
            "旺衰": assessment.get("旺衰", chart.get("日主强弱", "")),
            "legacy_日主强弱": chart.get("legacy_strength", {}).get(
                "value", chart.get("日主强弱", "")
            ),
            "strength_assessment": assessment,
            "legacy_strength": chart.get("legacy_strength", {}),
            "五行力量": chart.get("五行力量", {}),
            "十神": chart.get("十神", {}),
            "喜用神": preference["喜用神"],
            "喜神": preference["喜神"],
            "忌神": preference["忌神"],
            "喜用神规则版本": preference["ruleset_version"],
            "legacy_喜用神": chart.get("喜用神", []),
            "legacy_忌神": chart.get("忌神", []),
            "空亡": chart.get("空亡", ""),
            "纳音": chart.get("纳音", ""),
            "大运": chart.get("大运", []),
            "chart_id": chart.get("chart_id"),
            "birth_time": chart.get("birth_time"),
        }, ensure_ascii=False)

    def generate_html_report(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        gender: str,
        category: str,
        question: str,
        options_json: str = "[]",
        minute: int = 0,
        year_boundary: str = "lichun",
        second: int = 0,
        birth_context: dict | None = None,
        analysis_period: dict | None = None,
        knowledge_query: str | None = None,
        knowledge_packs: list[str] | None = None,
        interpretation_document: dict | None = None,
        title: str = "命理分析报告",
        subject_name: str = "",
        output_path: str | None = None,
    ) -> str:
        """Generate a self-contained HTML report from the audited analysis output.

        The report is returned inline by default.  A file is only written when
        ``output_path`` is explicitly supplied by the caller.
        """
        from tools.report_renderer import (
            REPORT_VERSION,
            render_html_report,
            write_html_report,
        )

        analysis = json.loads(self.analyze_question(
            year=year,
            month=month,
            day=day,
            hour=hour,
            gender=gender,
            category=category,
            question=question,
            options_json=options_json,
            minute=minute,
            year_boundary=year_boundary,
            second=second,
            birth_context=birth_context,
            analysis_period=analysis_period,
            knowledge_query=knowledge_query,
            knowledge_packs=knowledge_packs,
            interpretation_document=interpretation_document,
        ))
        if analysis.get("error"):
            return json.dumps({
                "success": False,
                "error": analysis["error"],
                "component_status": analysis.get("component_status", {}),
            }, ensure_ascii=False)

        html = render_html_report(
            analysis, title=title, subject_name=subject_name
        )
        result = {
            "success": True,
            "report_version": REPORT_VERSION,
            "chart_id": analysis.get("chart_id"),
            "html": html,
            "component_status": {
                "status": "ok",
                "backend": "report_renderer",
            },
        }
        if output_path:
            result["output_path"] = str(write_html_report(html, output_path))
        return json.dumps(result, ensure_ascii=False)
