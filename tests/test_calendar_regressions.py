import json
import sys
import unittest
from datetime import date, datetime

sys.path.insert(0, ".")

from lunar_python import Solar
from engine.run_tools_engine import compute_chart, eval_year
from tools.calendar_engine import (
    build_four_pillars,
    build_liunian,
    calculate_dayun_start,
    day_ganzhi_from_date,
    solar_to_lunar,
    year_ganzhi,
)
from tools.ziwei_tools import ZiweiToolkit


class CalendarRegressionTests(unittest.TestCase):
    def test_annual_labels_do_not_use_january_first(self):
        self.assertEqual(year_ganzhi(2026), "丙午")
        self.assertEqual(year_ganzhi(2026, 1, 31), "乙巳")
        self.assertEqual(year_ganzhi(2026, 2, 5), "丙午")
        self.assertEqual(
            [item["流年干支"] for item in build_liunian(2026, 4)],
            ["丙午", "丁未", "戊申", "己酉"],
        )

    def test_annual_labels_match_astronomical_backend_across_supported_years(self):
        for year in range(1900, 2100):
            expected = Solar.fromYmd(year, 7, 1).getLunar().getYearInGanZhiExact()
            self.assertEqual(year_ganzhi(year), expected, year)

    def test_solar_to_lunar_and_day_pillar_match_backend(self):
        samples = [
            (1900, 1, 31, 12),
            (1949, 10, 1, 8),
            (1990, 6, 15, 12),
            (2024, 2, 4, 16),
            (2099, 12, 31, 23),
        ]
        for year, month, day, hour in samples:
            solar = Solar.fromYmdHms(year, month, day, hour, 0, 0)
            lunar = solar.getLunar()
            converted = solar_to_lunar(year, month, day, hour)
            self.assertEqual(converted["year"], lunar.getYear())
            self.assertEqual(converted["month"], abs(lunar.getMonth()))
            self.assertEqual(converted["day"], lunar.getDay())
            self.assertEqual(
                day_ganzhi_from_date(date(year, month, day)),
                Solar.fromYmdHms(year, month, day, 12, 0, 0)
                .getLunar()
                .getDayInGanZhiExact(),
            )

    def test_four_pillars_and_precise_dayun_boundary(self):
        chart = compute_chart({
            "year": 1990,
            "month": 6,
            "day": 15,
            "hour": 12,
            "gender": "女",
        })
        self.assertEqual(
            chart["四柱"],
            {"年柱": "庚午", "月柱": "壬午", "日柱": "辛亥", "时柱": "甲午"},
        )
        self.assertEqual(chart["大运"][3]["大运"], "戊寅")
        self.assertEqual(chart["大运"][3]["起运日期"], "2023-07-15")
        self.assertEqual(chart["大运"][4]["大运"], "丁丑")
        self.assertEqual(chart["大运"][4]["起运日期"], "2033-07-15")
        self.assertEqual(eval_year(chart, 2033)["du"]["ganzhi"], "戊寅")
        self.assertEqual(eval_year(chart, 2034)["du"]["ganzhi"], "丁丑")

    def test_lunar_new_year_compatibility_mode(self):
        chart = build_four_pillars(
            1988, 2, 15, 16, gender="女", minute=50,
            year_boundary="lunar_new_year",
        )
        self.assertEqual(
            chart["四柱"],
            {"年柱": "丁卯", "月柱": "甲寅", "日柱": "庚子", "时柱": "甲申"},
        )
        self.assertEqual(chart["年柱换年规则"], "农历新年")

    def test_dayun_start_matches_calendar_backend_for_multiple_genders(self):
        samples = [
            (1990, 6, 15, 12, "女"),
            (1992, 6, 15, 12, "女"),
            (2001, 2, 5, 8, "男"),
        ]
        for year, month, day, hour, gender in samples:
            lunar = Solar.fromYmdHms(year, month, day, hour, 0, 0).getLunar()
            yun = lunar.getEightChar().getYun(1 if gender == "男" else 0, 1)
            expected = yun.getStartSolar()
            actual = calculate_dayun_start(year, month, day, hour, gender)
            self.assertEqual(
                actual["start_datetime"],
                datetime(
                    expected.getYear(), expected.getMonth(), expected.getDay(),
                    expected.getHour(), expected.getMinute(), expected.getSecond(),
                ),
            )

    def test_ziwei_converts_gregorian_to_lunar_before_placing_palaces(self):
        samples = [
            (1990, 6, 15, 12, "女"),
            (1992, 6, 15, 12, "女"),
            (2024, 2, 10, 8, "男"),
        ]
        for year, month, day, hour, gender in samples:
            result = json.loads(ZiweiToolkit().paipan(year, month, day, hour, gender))
            lunar = solar_to_lunar(year, month, day, hour)
            self.assertTrue(result["success"])
            self.assertEqual(result["农历数值"]["year"], lunar["year"])
            self.assertEqual(result["农历数值"]["month"], lunar["month"])
            self.assertEqual(result["农历数值"]["day"], lunar["day"])
            self.assertEqual(result["历法输入"], "公历转农历")
            self.assertEqual(result["排盘引擎"], "iztro")

        known = json.loads(ZiweiToolkit().paipan(1990, 6, 15, 12, "女"))
        self.assertEqual(known["命宫"]["地支"], "子")
        self.assertEqual(len(known["十二宫"]), 12)
        self.assertEqual(len(known["生年四化"]), 4)
        self.assertEqual(
            known["紫微审计"],
            {
                "schema_version": "ziwei-audit-v1",
                "calendar_input": "公历转农历",
                "solar_date": "1990-6-15",
                "lunar_date": "一九九〇年五月廿三",
                "hour": 12,
                "zi_hour_convention": "benchmark",
                "iztro_hour_index": 6,
                "palace_count": 12,
            },
        )
        self.assertIn("亮度", known["十二宫"]["命宫"]["主星详情"][0])

    def test_ziwei_early_and_late_zi_are_explicit(self):
        early = json.loads(ZiweiToolkit().paipan(
            1990,
            6,
            15,
            23,
            "女",
            zi_hour_convention="early",
        ))
        late = json.loads(ZiweiToolkit().paipan(
            1990,
            6,
            15,
            23,
            "女",
            zi_hour_convention="late",
        ))

        self.assertEqual(early["子时约定"]["iztro_hour_index"], 0)
        self.assertEqual(late["子时约定"]["iztro_hour_index"], 12)
        self.assertNotEqual(
            early["十二宫"]["命宫"]["主星"],
            late["十二宫"]["命宫"]["主星"],
        )


if __name__ == "__main__":
    unittest.main()
