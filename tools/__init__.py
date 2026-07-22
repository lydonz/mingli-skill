"""Public toolkit exports without eager cross-imports.

The previous module imported HybridMingliToolkit at package import time.
HybridMingliToolkit imports the rules engine, which imports
``tools.calendar_engine``; importing the calendar module therefore created a
circular import.  Lazy exports keep the low-level calendar and engine layers
independent.
"""

from importlib import import_module

from .calendar_engine import (
    TIANGAN, DIZHI, TIANGAN_IDX, DIZHI_IDX,
    WUXING_GAN, WUXING_ZHI, WUXING_SHENG, WUXING_KE,
    build_four_pillars, build_dayun, build_dayun_precise, build_liunian,
    calculate_dayun_start, year_ganzhi, day_ganzhi_from_date, hour_ganzhi,
    day_ganzhi_from_datetime, month_ganzhi, shi_shen, five_element_strength,
    nayin, solar_to_lunar,
)
from .report_renderer import render_html_report, write_html_report
from .interpretation_contract import (
    INTERPRETATION_SCHEMA_VERSION,
    build_interpretation_brief,
    validate_interpretation_document,
)


_LAZY_EXPORTS = {
    "BaziToolkit": (".bazi_tools", "BaziToolkit"),
    "ZiweiToolkit": (".ziwei_tools", "ZiweiToolkit"),
    "HybridMingliToolkit": (".hybrid_tools", "HybridMingliToolkit"),
    "KnowledgeToolkit": (".knowledge_tools", "KnowledgeToolkit"),
    "LiuYaoToolkit": (".divination_tools", "LiuYaoToolkit"),
    "MeiHuaToolkit": (".divination_tools", "MeiHuaToolkit"),
    "QiMenToolkit": (".divination_tools", "QiMenToolkit"),
    "LiuRenToolkit": (".divination_tools", "LiuRenToolkit"),
    "PhysiognomyToolkit": (".physiognomy_tools", "PhysiognomyToolkit"),
    "FengShuiToolkit": (".fengshui_tools", "FengShuiToolkit"),
}


def __getattr__(name):
    if name == "ALL_TOOLKITS":
        toolkits = {
            "八字": __getattr__("BaziToolkit"),
            "紫微斗数": __getattr__("ZiweiToolkit"),
            "混合路由": __getattr__("HybridMingliToolkit"),
            "六爻": __getattr__("LiuYaoToolkit"),
            "梅花易数": __getattr__("MeiHuaToolkit"),
            "奇门遁甲": __getattr__("QiMenToolkit"),
            "大六壬": __getattr__("LiuRenToolkit"),
            "面相手相": __getattr__("PhysiognomyToolkit"),
            "风水": __getattr__("FengShuiToolkit"),
        }
        globals()[name] = toolkits
        return toolkits
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value


__all__ = [
    *_LAZY_EXPORTS,
    "ALL_TOOLKITS",
    "TIANGAN",
    "DIZHI",
    "TIANGAN_IDX",
    "DIZHI_IDX",
    "WUXING_GAN",
    "WUXING_ZHI",
    "WUXING_SHENG",
    "WUXING_KE",
    "build_four_pillars",
    "build_dayun",
    "build_dayun_precise",
    "build_liunian",
    "calculate_dayun_start",
    "year_ganzhi",
    "day_ganzhi_from_date",
    "day_ganzhi_from_datetime",
    "hour_ganzhi",
    "month_ganzhi",
    "shi_shen",
    "five_element_strength",
    "nayin",
    "solar_to_lunar",
    "render_html_report",
    "write_html_report",
    "INTERPRETATION_SCHEMA_VERSION",
    "build_interpretation_brief",
    "validate_interpretation_document",
]
