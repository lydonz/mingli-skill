from __future__ import annotations

import math
from datetime import datetime, date, timedelta
import calendar
from typing import Dict, List, Optional, Tuple

try:
    from lunar_python import Lunar as _LunarPython
    from lunar_python import Solar as _SolarPython
except ImportError:
    _LunarPython = None
    _SolarPython = None

TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
TIANGAN_IDX = {g: i for i, g in enumerate(TIANGAN)}
DIZHI_IDX = {z: i for i, z in enumerate(DIZHI)}

WUXING_GAN = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
WUXING_ZHI = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

YINYANG_GAN = {g: ("阳" if i % 2 == 0 else "阴") for i, g in enumerate(TIANGAN)}
YINYANG_ZHI = {z: ("阳" if i % 2 == 0 else "阴") for i, z in enumerate(DIZHI)}

WUXING_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
WUXING_BEING_SHENG = {v: k for k, v in WUXING_SHENG.items()}
WUXING_BEING_KE = {v: k for k, v in WUXING_KE.items()}

NAYIN_TABLE = {
    ("甲子", "乙丑"): "海中金", ("丙寅", "丁卯"): "炉中火",
    ("戊辰", "己巳"): "大林木", ("庚午", "辛未"): "路旁土",
    ("壬申", "癸酉"): "剑锋金", ("甲戌", "乙亥"): "山头火",
    ("丙子", "丁丑"): "涧下水", ("戊寅", "己卯"): "城头土",
    ("庚辰", "辛巳"): "白蜡金", ("壬午", "癸未"): "杨柳木",
    ("甲申", "乙酉"): "泉中水", ("丙戌", "丁亥"): "屋上土",
    ("戊子", "己丑"): "霹雳火", ("庚寅", "辛卯"): "松柏木",
    ("壬辰", "癸巳"): "长流水", ("甲午", "乙未"): "砂石金",
    ("丙申", "丁酉"): "山下火", ("戊戌", "己亥"): "平地木",
    ("庚子", "辛丑"): "壁上土", ("壬寅", "癸卯"): "金箔金",
    ("甲辰", "乙巳"): "覆灯火", ("丙午", "丁未"): "天河水",
    ("戊申", "己酉"): "大驿土", ("庚戌", "辛亥"): "钗钏金",
    ("壬子", "癸丑"): "桑柘木", ("甲寅", "乙卯"): "大溪水",
    ("丙辰", "丁巳"): "沙中土", ("戊午", "己未"): "天上火",
    ("庚申", "辛酉"): "石榴木", ("壬戌", "癸亥"): "大海水",
}

ZHI_CANG_GAN = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"],
    "卯": ["乙"], "辰": ["戊", "乙", "癸"], "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"], "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"],
    "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}

SHISHEN_MAP = {
    "比肩": "同我者", "劫财": "异我同五行",
    "食神": "我生者同性", "伤官": "我生者异性",
    "偏财": "我克者同性", "正财": "我克者异性",
    "七杀": "克我者同性", "正官": "克我者异性",
    "偏印": "生我者同性", "正印": "生我者异性",
}

CHANGSHENG_12 = [
    "长生", "沐浴", "冠带", "临官", "帝旺", "衰",
    "病", "死", "墓", "绝", "胎", "养",
]

CHANGSHENG_POS = {
    "木": {"甲": 0, "乙": 6, "丙": 10, "丁": 4, "戊": 0, "己": 6, "庚": 8, "辛": 2, "壬": 8, "癸": 2},
    "火": {"甲": 10, "乙": 4, "丙": 0, "丁": 6, "戊": 2, "己": 8, "庚": 6, "辛": 0, "壬": 4, "癸": 10},
    "土": {"甲": 0, "乙": 6, "丙": 2, "丁": 8, "戊": 0, "己": 6, "庚": 8, "辛": 2, "壬": 8, "癸": 2},
    "金": {"甲": 8, "乙": 2, "丙": 6, "丁": 0, "戊": 8, "己": 2, "庚": 0, "辛": 6, "壬": 2, "癸": 8},
    "水": {"甲": 8, "乙": 2, "丙": 4, "丁": 10, "戊": 8, "己": 2, "庚": 2, "辛": 8, "壬": 0, "癸": 6},
}

LUNAR_MONTH_DAYS = {
    1900: [0, 29, 30, 29, 29, 30, 29, 30, 29, 30, 29, 30, 29],
    1901: [0, 30, 29, 30, 29, 30, 29, 29, 30, 29, 30, 29, 30],
    1902: [0, 29, 30, 29, 30, 29, 29, 30, 29, 30, 29, 30, 29],
    1903: [0, 30, 29, 30, 29, 30, 29, 29, 30, 29, 30, 29, 30],
    1904: [0, 29, 30, 29, 30, 30, 29, 29, 30, 29, 30, 29, 29],
    1905: [0, 30, 29, 30, 29, 30, 30, 29, 29, 30, 29, 29, 30],
    1906: [0, 29, 30, 29, 29, 30, 30, 29, 30, 29, 29, 30, 29],
    1907: [0, 30, 29, 30, 29, 29, 30, 29, 30, 29, 30, 29, 30],
    1908: [0, 29, 30, 29, 30, 29, 29, 30, 29, 30, 29, 30, 29],
    1909: [0, 30, 29, 30, 29, 29, 30, 29, 30, 29, 30, 29, 30],
    1910: [0, 29, 30, 29, 30, 29, 29, 30, 29, 30, 29, 30, 29],
}

LUNAR_LEAP_MONTHS = {1900: 8, 1903: 5, 1906: 4, 1909: 2, 1911: 6,
                     1914: 5, 1917: 2, 1920: 7, 1922: 5, 1925: 4,
                     1928: 2, 1930: 6, 1933: 5, 1936: 3, 1938: 7,
                     1941: 6, 1944: 4, 1947: 2, 1949: 7, 1952: 5,
                     1955: 3, 1957: 8, 1960: 6, 1963: 4, 1966: 3,
                     1968: 7, 1971: 5, 1974: 4, 1976: 8, 1979: 6,
                     1982: 4, 1984: 10, 1987: 6, 1990: 5, 1993: 3,
                     1995: 8, 1998: 5, 2001: 4, 2004: 2, 2006: 7,
                     2009: 5, 2012: 4, 2014: 9, 2017: 6, 2020: 4,
                     2023: 2, 2025: 6, 2028: 5, 2031: 3, 2033: 7,
                     2036: 6, 2039: 5, 2042: 2, 2044: 7, 2047: 5}


def ganzhi_from_offset(offset: int) -> str:
    return TIANGAN[offset % 10] + DIZHI[offset % 12]


# ============================================================
# Solar term calculation
# ============================================================

SOLAR_TERM_NAMES = [
    "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
    "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑",
    "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至",
]

_solar_term_cache = {}
_solar_term_datetime_cache = {}


def _calendar_backend_error() -> RuntimeError:
    return RuntimeError(
        "精确历法功能需要安装 lunar-python，请运行 "
        "`python3 -m pip install -r requirements.txt`。"
    )


def solar_to_lunar(
    year: int,
    month: int,
    day: int,
    hour: int = 12,
    minute: int = 0,
    second: int = 0,
) -> Dict:
    """Convert a Gregorian datetime to lunar date data.

    The skill accepts Gregorian birth data by default.  Keeping this
    conversion in one place prevents the Ziwei calculator from accidentally
    treating Gregorian month/day values as lunar values.
    """
    if _SolarPython is None:
        raise _calendar_backend_error()
    solar = _SolarPython.fromYmdHms(year, month, day, hour, minute, second)
    lunar = solar.getLunar()
    lunar_month = lunar.getMonth()
    return {
        "year": lunar.getYear(),
        "month": abs(lunar_month),
        "day": lunar.getDay(),
        "is_leap_month": lunar_month < 0,
        "year_ganzhi": lunar.getYearInGanZhiExact(),
        "month_ganzhi": lunar.getMonthInGanZhiExact(),
        "day_ganzhi": lunar.getDayInGanZhiExact(),
        "hour_ganzhi": lunar.getTimeInGanZhi(),
    }


def _solar_term_datetime(year: int, term_index: int) -> datetime:
    """Return the local civil datetime of a solar term.

    lunar-python provides astronomical term times.  The old implementation
    retained only month/day, which is insufficient near a term boundary.
    """
    cache_key = (year, term_index)
    if cache_key in _solar_term_datetime_cache:
        return _solar_term_datetime_cache[cache_key]

    if _SolarPython is None:
        raise _calendar_backend_error()

    probe = _SolarPython.fromYmdHms(year, 6, 15, 12, 0, 0).getLunar()
    term_name = SOLAR_TERM_NAMES[term_index]
    table = probe.getJieQiTable()
    term = table.get(term_name)
    if term is None:
        # The table also exposes aliases for terms around the year boundary.
        aliases = {
            0: "DONG_ZHI", 1: "小寒", 2: "大寒", 3: "立春",
            4: "雨水", 5: "惊蛰", 6: "春分", 7: "清明",
            8: "谷雨", 9: "立夏", 10: "小满", 11: "芒种",
            12: "夏至", 13: "小暑", 14: "大暑", 15: "立秋",
            16: "处暑", 17: "白露", 18: "秋分", 19: "寒露",
            20: "霜降", 21: "立冬", 22: "小雪", 23: "大雪",
        }
        term = table.get(aliases.get(term_index, ""))
    if term is None:
        raise RuntimeError(f"无法取得 {year} 年 {term_name} 的节气时刻")

    y, m, d = term.getYear(), term.getMonth(), term.getDay()
    hh, mm, ss = term.getHour(), term.getMinute(), term.getSecond()
    value = datetime(y, m, d, hh, mm, ss)
    _solar_term_datetime_cache[cache_key] = value
    return value


def solar_term_datetime(year: int, term_index: int) -> datetime:
    """Expose precise solar-term instants for auditable period analysis."""
    return _solar_term_datetime(year, term_index)


def _get_solar_term_date(year: int, term_index: int) -> Tuple[int, int]:
    """Return (month, day) for the given solar term in the given year.
    term_index: 0=小寒, 1=大寒, 2=立春, ..., 23=冬至
    Uses the same precise lunar-python backend as all other solar-term APIs.
    """
    cache_key = (year, term_index)
    if cache_key in _solar_term_cache:
        return _solar_term_cache[cache_key]

    dt_obj = _solar_term_datetime(year, term_index)
    result = (dt_obj.month, dt_obj.day)

    _solar_term_cache[cache_key] = result
    return result

def _get_bazi_month(
    year: int,
    month: int,
    day: int,
    hour: int = 12,
    minute: int = 0,
    second: int = 0,
) -> int:
    """Return Bazi month index (0=寅, 1=卯, ..., 11=丑) based on solar terms.
    Each Bazi month spans two solar terms, e.g. 寅月 = 立春~惊蛰.
    """
    dt = datetime(year, month, day, hour, minute, second)
    # Bazi months change at the 12 "jie" boundaries, not at lunar new moons.
    boundaries = [
        (year - 1, 22, 10),  # 大雪 -> 子月
        (year, 0, 11),       # 小寒 -> 丑月
        (year, 2, 0),        # 立春 -> 寅月
        (year, 4, 1),        # 惊蛰 -> 卯月
        (year, 6, 2),        # 清明 -> 辰月
        (year, 8, 3),        # 立夏 -> 巳月
        (year, 10, 4),       # 芒种 -> 午月
        (year, 12, 5),       # 小暑 -> 未月
        (year, 14, 6),       # 立秋 -> 申月
        (year, 16, 7),       # 白露 -> 酉月
        (year, 18, 8),       # 寒露 -> 戌月
        (year, 20, 9),       # 立冬 -> 亥月
        (year, 22, 10),      # 大雪 -> 子月
        (year + 1, 0, 11),   # 小寒 -> 丑月
    ]
    current_month = 11
    for boundary_year, term_index, month_index in boundaries:
        boundary = _solar_term_datetime(boundary_year, term_index)
        if dt >= boundary:
            current_month = month_index
        else:
            break
    return current_month


def _get_bazi_year(
    year: int,
    month: int,
    day: int,
    hour: int = 12,
    minute: int = 0,
    second: int = 0,
) -> int:
    """Return the Bazi year (adjusted for 立春 boundary).
    If the date is before 立春, it belongs to the previous year in Bazi terms."""
    birth = datetime(year, month, day, hour, minute, second)
    lichun = _solar_term_datetime(year, 2)
    if birth < lichun:
        return year - 1
    return year


def year_ganzhi(
    year: int,
    month: Optional[int] = None,
    day: Optional[int] = None,
    hour: int = 12,
    minute: int = 0,
    second: int = 0,
) -> str:
    """Return the Bazi year pillar.

    With no birth date, this returns the conventional annual label for the
    year after 立春.  Birth-chart callers must pass month/day/hour so a date
    before 立春 is assigned to the previous Bazi year.
    """
    if month is None or day is None:
        bazi_year = year
    else:
        bazi_year = _get_bazi_year(year, month, day, hour, minute, second)
    idx = (bazi_year - 4) % 60
    return ganzhi_from_offset(idx)


MONTH_GAN_BASE = {
    "甲": 2, "己": 2, "乙": 4, "庚": 4, "丙": 6, "辛": 6,
    "丁": 8, "壬": 8, "戊": 0, "癸": 0,
}


def month_ganzhi(year_gan: str, month_idx: int) -> str:
    """Return month pillar for Bazi month index (0=寅, 1=卯, ..., 11=丑)."""
    start = MONTH_GAN_BASE[year_gan]
    gan_idx = (start + month_idx) % 10
    zhi_idx = (month_idx + 2) % 12
    return TIANGAN[gan_idx] + DIZHI[zhi_idx]


def day_ganzhi_from_date(dt: date) -> str:
    """Return the day pillar using the astronomical calendar backend.

    Noon avoids the 23:00 day-boundary convention; callers that need a
    different late-Zi convention should pass a pre-adjusted civil date.
    """
    if _SolarPython is not None:
        return _SolarPython.fromYmdHms(
            dt.year, dt.month, dt.day, 12, 0, 0
        ).getLunar().getDayInGanZhiExact()
    ref = date(1900, 1, 1)
    delta = (dt - ref).days
    return ganzhi_from_offset(delta % 60 + 10)


def day_ganzhi_from_datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 12,
    minute: int = 0,
    zi_hour_changes_day: bool = True,
    second: int = 0,
) -> str:
    """Return a day pillar with an explicit late-Zi convention.

    ``zi_hour_changes_day=True`` follows the common 23:00 boundary convention
    used by iztro and by the MingLi-Bench reference charts.
    """
    if _SolarPython is not None:
        if zi_hour_changes_day:
            return _SolarPython.fromYmdHms(
                year, month, day, hour, minute, second
            ).getLunar().getDayInGanZhiExact()
        return day_ganzhi_from_date(date(year, month, day))
    if zi_hour_changes_day and hour >= 23:
        return day_ganzhi_from_date(date(year, month, day) + timedelta(days=1))
    return day_ganzhi_from_date(date(year, month, day))


def hour_ganzhi(day_gan: str, hour: int) -> str:
    zhi_idx = _hour_to_zhi(hour)
    day_gan_idx = TIANGAN_IDX[day_gan]
    gan_idx = (day_gan_idx % 5 * 2 + zhi_idx) % 10
    return TIANGAN[gan_idx] + DIZHI[zhi_idx]


def _hour_to_zhi(hour: int) -> int:
    if 23 <= hour or hour < 1:
        return 0
    return (hour + 1) // 2


def shi_shen(day_gan: str, other_gan: str) -> str:
    if other_gan == day_gan:
        return "比肩"
    dw = WUXING_GAN[day_gan]
    ow = WUXING_GAN[other_gan]
    same_yinyang = (TIANGAN_IDX[day_gan] % 2) == (TIANGAN_IDX[other_gan] % 2)

    if WUXING_SHENG.get(dw) == ow:
        return "食神" if same_yinyang else "伤官"
    if WUXING_KE.get(dw) == ow:
        return "偏财" if same_yinyang else "正财"
    if WUXING_SHENG.get(ow) == dw:
        return "偏印" if same_yinyang else "正印"
    if WUXING_KE.get(ow) == dw:
        return "七杀" if same_yinyang else "正官"
    if dw == ow:
        return "比肩" if same_yinyang else "劫财"
    return "未知"


def changsheng_state(day_gan: str, zhi: str) -> str:
    """Return the standard twelve-growth phase for a stem and branch."""
    starts = {
        "甲": "亥", "乙": "午", "丙": "寅", "丁": "酉", "戊": "寅",
        "己": "酉", "庚": "巳", "辛": "子", "壬": "申", "癸": "卯",
    }
    start_idx = DIZHI_IDX[starts[day_gan]]
    zhi_idx = DIZHI_IDX[zhi]
    forward = TIANGAN_IDX[day_gan] % 2 == 0
    offset = (zhi_idx - start_idx) % 12 if forward else (start_idx - zhi_idx) % 12
    return CHANGSHENG_12[offset]


def nayin(ganzhi: str) -> str:
    for pair, name in NAYIN_TABLE.items():
        if ganzhi in pair:
            return name
    return "未知"


def kong_wang(day_ganzhi: str) -> List[str]:
    gan_idx = TIANGAN_IDX[day_ganzhi[0]]
    zhi_idx = DIZHI_IDX[day_ganzhi[1]]
    start = zhi_idx + 1
    result = []
    for i in range(10):
        gi = (gan_idx + i + 1) % 10
        zi = (start + i) % 12
        if gi >= zhi_idx + 1 or (gan_idx + i + 1) % 10 != (start + i) % 12:
            pass
    xun_head_gan = gan_idx
    xun_head_zhi = (zhi_idx - gan_idx) % 12
    if xun_head_zhi < 0:
        xun_head_zhi += 12
    void1 = (xun_head_zhi + 10) % 12
    void2 = (xun_head_zhi + 11) % 12
    return [DIZHI[void1], DIZHI[void2]]


def five_element_strength(pillars: Dict[str, str]) -> Dict[str, int]:
    scores = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for pillar_name, ganzhi in pillars.items():
        if not ganzhi or len(ganzhi) < 2:
            continue
        gan = ganzhi[0]
        zhi = ganzhi[1]
        scores[WUXING_GAN[gan]] += 1.0
        cang = ZHI_CANG_GAN.get(zhi, [])
        for ci, cg in enumerate(cang):
            weight = 1.0 if ci == 0 else (0.5 if ci == 1 else 0.3)
            scores[WUXING_GAN[cg]] += weight
    return {k: round(v, 1) for k, v in scores.items()}


def wuxing_relation(wx1: str, wx2: str) -> str:
    if wx1 == wx2:
        return "比助"
    if WUXING_SHENG.get(wx1) == wx2:
        return "我生"
    if WUXING_KE.get(wx1) == wx2:
        return "我克"
    if WUXING_SHENG.get(wx2) == wx1:
        return "生我"
    if WUXING_KE.get(wx2) == wx1:
        return "克我"
    return "无关"


def animal_year(year: int) -> str:
    animals = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
    return animals[(year - 4) % 12]


def build_four_pillars(
    year: int,
    month: int,
    day: int,
    hour: int,
    is_lunar: bool = False,
    gender: str = "男",
    minute: int = 0,
    is_leap_month: bool = False,
    year_boundary: str = "lichun",
    second: int = 0,
) -> Dict:
    if is_lunar:
        if _LunarPython is None:
            raise _calendar_backend_error()
        lunar_month = -month if is_leap_month else month
        solar = _LunarPython.fromYmdHms(
            year, lunar_month, day, hour, minute, second
        ).getSolar()
        year, month, day = solar.getYear(), solar.getMonth(), solar.getDay()

    solar_year_gz = year_ganzhi(year, month, day, hour, minute, second)
    if year_boundary == "lichun":
        ygz = solar_year_gz
    elif year_boundary == "lunar_new_year":
        if _SolarPython is None:
            raise _calendar_backend_error()
        lunar_year = _SolarPython.fromYmdHms(
            year, month, day, hour, minute, second
        ).getLunar().getYear()
        ygz = ganzhi_from_offset((lunar_year - 4) % 60)
    else:
        raise ValueError("year_boundary 必须是 'lichun' 或 'lunar_new_year'")
    bazi_month = _get_bazi_month(year, month, day, hour, minute, second)
    day_gz = day_ganzhi_from_datetime(
        year, month, day, hour, minute, second=second
    )
    # 月柱一律依节气年干计算；一些紫微/农历年兼容模式仅改变年柱。
    ygan = solar_year_gz[0]
    mgz = month_ganzhi(ygan, bazi_month)
    hgz = hour_ganzhi(day_gz[0], hour)

    pillars = {"年柱": ygz, "月柱": mgz, "日柱": day_gz, "时柱": hgz}
    day_gan = day_gz[0]

    ten_gods = {}
    for pname, gz in pillars.items():
        if pname == "日柱":
            continue
        ten_gods[pname + "天干"] = shi_shen(day_gan, gz[0])
        for ci, cg in enumerate(ZHI_CANG_GAN.get(gz[1], [])):
            label = "本气" if ci == 0 else ("中气" if ci == 1 else "余气")
            ten_gods[f"{pname}地支{label}"] = shi_shen(day_gan, cg)

    wuxing_score = five_element_strength(pillars)
    day_wx = WUXING_GAN[day_gan]

    total = sum(wuxing_score.values()) or 1
    wx_percent = {k: round(v / total * 100, 1) for k, v in wuxing_score.items()}

    strong = wuxing_score.get(day_wx, 0) >= total / 5
    if strong:
        xi = WUXING_KE[day_wx]
        yong = WUXING_KE[day_wx]
    else:
        xi = WUXING_SHENG[day_wx]
        yong = WUXING_BEING_SHENG.get(day_wx, day_wx)

    void = kong_wang(day_gz)

    changsheng_map = {}
    for pname, gz in pillars.items():
        changsheng_map[pname] = changsheng_state(day_gan, gz[1])

    nayin_map = {}
    for pname, gz in pillars.items():
        nayin_map[pname] = nayin(gz)

    return {
        "四柱": pillars,
        "日主": day_gan,
        "日主五行": day_wx,
        "日主阴阳": YINYANG_GAN[day_gan],
        "生肖": animal_year(
            _get_bazi_year(year, month, day, hour, minute, second)
            if year_boundary == "lichun" else lunar_year
        ),
        "十神": ten_gods,
        "五行力量": wuxing_score,
        "五行占比": wx_percent,
        "日主强弱": "身强" if strong else "身弱",
        "喜用神": yong,
        "喜神": xi,
        "忌神": WUXING_KE.get(yong, "未知"),
        "空亡": void,
        "十二长生": changsheng_map,
        "纳音": nayin_map,
        "日柱换日规则": "晚子时（23:00起）换日",
        "年柱换年规则": "立春" if year_boundary == "lichun" else "农历新年",
        "地支藏干": {pname: ZHI_CANG_GAN.get(gz[1], []) for pname, gz in pillars.items()},
    }


def build_dayun(gender: str, year_ganzhi: str, month_ganzhi: str,
                start_age: int = 1) -> List[Dict]:
    yin_yang = TIANGAN_IDX[year_ganzhi[0]] % 2
    male = gender in ("男", "M", "male")
    forward = (male and yin_yang == 0) or (not male and yin_yang == 1)

    month_gan_idx = TIANGAN_IDX[month_ganzhi[0]]
    month_zhi_idx = DIZHI_IDX[month_ganzhi[1]]

    dayun_list = []
    for i in range(8):
        if forward:
            g = (month_gan_idx + i + 1) % 10
            z = (month_zhi_idx + i + 1) % 12
        else:
            g = (month_gan_idx - i - 1) % 10
            z = (month_zhi_idx - i - 1) % 12
        age_start = start_age + i * 10
        age_end = age_start + 9
        dayun_list.append({
            "大运": TIANGAN[g] + DIZHI[z],
            "起运年龄": age_start,
            "止运年龄": age_end,
            "天干五行": WUXING_GAN[TIANGAN[g]],
            "地支五行": WUXING_ZHI[DIZHI[z]],
        })
    return dayun_list


def _add_calendar_years_months(
    value: datetime,
    years: int = 0,
    months: int = 0,
    days: int = 0,
) -> datetime:
    """Calendar arithmetic without requiring dateutil."""
    total_month = value.year * 12 + (value.month - 1) + years * 12 + months
    new_year, month_index = divmod(total_month, 12)
    new_month = month_index + 1
    new_day = min(value.day, calendar.monthrange(new_year, new_month)[1])
    return value.replace(year=new_year, month=new_month, day=new_day) + timedelta(days=days)


def calculate_dayun_start(
    year: int,
    month: int,
    day: int,
    hour: int,
    gender: str,
    minute: int = 0,
    second: int = 0,
) -> Dict:
    """Calculate the civil start datetime of the first Da Yun.

    lunar-python implements the standard three-days-per-year convention and
    calculates from the actual preceding/following ``jie`` boundary.  The
    explicit date lets callers handle transitions inside a Gregorian year.
    """
    ygz = year_ganzhi(year, month, day, hour, minute, second)
    forward = (
        (gender in ("男", "M", "male") and TIANGAN_IDX[ygz[0]] % 2 == 0)
        or (gender not in ("男", "M", "male") and TIANGAN_IDX[ygz[0]] % 2 == 1)
    )
    if _LunarPython is None:
        return {
            "start_datetime": None,
            "forward": forward,
            "precision": "coarse",
            "reason": "lunar-python未安装，无法计算节气间隔",
        }

    lunar = _SolarPython.fromYmdHms(
        year, month, day, hour, minute, second
    ).getLunar()
    yun = lunar.getEightChar().getYun(
        1 if gender in ("男", "M", "male") else 0,
        1,
    )
    start_solar = yun.getStartSolar()
    start = datetime(
        start_solar.getYear(),
        start_solar.getMonth(),
        start_solar.getDay(),
        start_solar.getHour(),
        start_solar.getMinute(),
        start_solar.getSecond(),
    )
    return {
        "start_datetime": start,
        "forward": yun.isForward(),
        "years": yun.getStartYear(),
        "months": yun.getStartMonth(),
        "days": yun.getStartDay(),
        "precision": "solar-term",
    }


def build_dayun_precise(
    year: int,
    month: int,
    day: int,
    hour: int,
    gender: str,
    minute: int = 0,
    second: int = 0,
    year_boundary: str = "lichun",
) -> List[Dict]:
    """Build Da Yun with actual transition dates and a quality marker."""
    chart = build_four_pillars(
        year,
        month,
        day,
        hour,
        gender=gender,
        minute=minute,
        second=second,
        year_boundary=year_boundary,
    )
    start_info = calculate_dayun_start(
        year, month, day, hour, gender, minute, second
    )
    start_dt = start_info["start_datetime"]
    if start_dt is None:
        result = build_dayun(gender, chart["四柱"]["年柱"], chart["四柱"]["月柱"], 1)
        for item in result:
            item["精度"] = "coarse"
        return result

    year_gz = chart["四柱"]["年柱"]
    month_gz = chart["四柱"]["月柱"]
    yin_yang = TIANGAN_IDX[year_gz[0]] % 2
    male = gender in ("男", "M", "male")
    forward = (male and yin_yang == 0) or (not male and yin_yang == 1)
    mg = TIANGAN_IDX[month_gz[0]]
    mz = DIZHI_IDX[month_gz[1]]
    result = []
    for i in range(8):
        g = (mg + i + 1) % 10 if forward else (mg - i - 1) % 10
        z = (mz + i + 1) % 12 if forward else (mz - i - 1) % 12
        item_start = _add_calendar_years_months(start_dt, years=i * 10)
        item_end = _add_calendar_years_months(start_dt, years=(i + 1) * 10)
        age_years = item_start.year - year
        age_months = item_start.month - month
        if age_months < 0:
            age_years -= 1
            age_months += 12
        result.append({
            "大运": TIANGAN[g] + DIZHI[z],
            "起运年龄": round(age_years + age_months / 12, 2),
            "止运年龄": round(
                (item_end.year - year) + (item_end.month - month) / 12, 2
            ),
            "起运年龄文本": f"{age_years}岁{age_months}个月",
            "起运日期": item_start.strftime("%Y-%m-%d"),
            "止运日期": item_end.strftime("%Y-%m-%d"),
            "天干五行": WUXING_GAN[TIANGAN[g]],
            "地支五行": WUXING_ZHI[DIZHI[z]],
            "精度": "solar-term",
        })
    return result


def build_liunian(year: int, count: int = 10) -> List[Dict]:
    result = []
    for i in range(count):
        y = year + i
        # A standalone annual label refers to the post-Li Chun Bazi year.
        gz = year_ganzhi(y)
        result.append({
            "年份": y,
            "流年干支": gz,
            "天干五行": WUXING_GAN[gz[0]],
            "地支五行": WUXING_ZHI[gz[1]],
            "生肖": animal_year(y),
        })
    return result


HEXAGRAMS = {
    1: "乾", 2: "坤", 3: "屯", 4: "蒙", 5: "需", 6: "讼", 7: "师", 8: "比",
    9: "小畜", 10: "履", 11: "泰", 12: "否", 13: "同人", 14: "大有", 15: "谦", 16: "豫",
    17: "随", 18: "蛊", 19: "临", 20: "观", 21: "噬嗑", 22: "贲", 23: "剥", 24: "复",
    25: "无妄", 26: "大畜", 27: "颐", 28: "大过", 29: "坎", 30: "离", 31: "咸", 32: "恒",
    33: "遯", 34: "大壮", 35: "晋", 36: "明夷", 37: "家人", 38: "睽", 39: "蹇", 40: "解",
    41: "损", 42: "益", 43: "夬", 44: "姤", 45: "萃", 46: "升", 47: "困", 48: "井",
    49: "革", 50: "鼎", 51: "震", 52: "艮", 53: "渐", 54: "归妹", 55: "丰", 56: "旅",
    57: "巽", 58: "兑", 59: "涣", 60: "节", 61: "中孚", 62: "小过", 63: "既济", 64: "未济",
}

BAGUA = {
    "乾": {"数": 1, "五行": "金", "象": "天", "方位": "西北"},
    "兑": {"数": 2, "五行": "金", "象": "泽", "方位": "西"},
    "离": {"数": 3, "五行": "火", "象": "火", "方位": "南"},
    "震": {"数": 4, "五行": "木", "象": "雷", "方位": "东"},
    "巽": {"数": 5, "五行": "木", "象": "风", "方位": "东南"},
    "坎": {"数": 6, "五行": "水", "象": "水", "方位": "北"},
    "艮": {"数": 7, "五行": "土", "象": "山", "方位": "东北"},
    "坤": {"数": 8, "五行": "土", "象": "地", "方位": "西南"},
}

LIUYAO_LIUQIN = ["父母", "兄弟", "子孙", "妻财", "官鬼"]
LIUYAO_LIUSHEN = ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"]

WUXING_LIUYIN = {"木": "寅卯", "火": "巳午", "土": "辰戌丑未", "金": "申酉", "水": "亥子"}
