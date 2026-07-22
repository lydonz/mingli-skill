import unittest

from tools.birth_context import BirthContextError, normalize_birth_context, resolve_place
from engine.run_tools_engine import compute_chart


class BirthContextTests(unittest.TestCase):
    def test_city_name_resolves_chinese_county_with_pinyin_fallback(self):
        place = resolve_place({"name": "广东省广州市", "country_code": "CN"})
        self.assertEqual(place.name, "Guangzhou")
        self.assertEqual(place.timezone, "Asia/Shanghai")
        self.assertAlmostEqual(place.longitude, 113.25, places=4)

    def test_ambiguous_city_requires_disambiguation(self):
        with self.assertRaises(BirthContextError) as raised:
            resolve_place({"name": "London"})
        self.assertEqual(raised.exception.code, "ambiguous_location")
        self.assertGreaterEqual(len(raised.exception.candidates), 2)

    def test_true_solar_uses_equation_and_longitude(self):
        normalized = normalize_birth_context(
            {"year": 1990, "month": 6, "day": 15, "hour": 22, "minute": 0},
            {"place": {"name": "Guangzhou", "country_code": "CN"}},
        )
        self.assertEqual(normalized.time_basis, "true_solar")
        self.assertLess(normalized.correction_minutes, 0)
        self.assertEqual(normalized.effective_time.hour, 20)
        self.assertEqual(normalized.place.name, "Guangzhou")

    def test_true_solar_can_cross_late_zi_hour_boundary(self):
        standard = compute_chart({
            "year": 1990, "month": 6, "day": 15, "hour": 23, "minute": 3,
            "gender": "女",
        })
        corrected = compute_chart({
            "year": 1990, "month": 6, "day": 15, "hour": 23, "minute": 3,
            "gender": "女",
            "birth_context": {
                "place": {"name": "Guangzhou", "country_code": "CN"},
            },
        })
        self.assertNotEqual(standard["四柱"]["时柱"], corrected["四柱"]["时柱"])
        self.assertEqual(corrected["birth_time"]["effective_time"][11:13], "21")

    def test_true_solar_can_cross_civil_date(self):
        chart = compute_chart({
            "year": 1990, "month": 6, "day": 15, "hour": 1, "minute": 0,
            "gender": "女",
            "birth_context": {
                "place": {
                    "name": "Kashgar",
                    "longitude": 75.9898,
                    "latitude": 39.4704,
                    "timezone": "Asia/Shanghai",
                },
            },
        })
        self.assertTrue(
            chart["birth_time"]["effective_time"].startswith("1990-06-14")
        )

    def test_uncertainty_returns_pillar_variants_when_boundary_is_crossed(self):
        chart = compute_chart({
            "year": 1990, "month": 6, "day": 15, "hour": 21, "minute": 30,
            "gender": "女",
            "birth_context": {
                "time_basis": "standard",
                "uncertainty_minutes": 60,
                "place": {
                    "name": "Beijing",
                    "longitude": 116.39723,
                    "latitude": 39.9075,
                    "timezone": "Asia/Shanghai",
                },
            },
        })
        stability = chart["birth_time"]["chart_stability"]
        self.assertFalse(stability["stable"])
        self.assertTrue(stability["candidate_charts"])

    def test_zi_hour_convention_is_validated_and_changes_chart_identity(self):
        common = {
            "year": 1990,
            "month": 6,
            "day": 15,
            "hour": 23,
            "minute": 10,
            "gender": "女",
            "birth_context": {
                "time_basis": "standard",
                "place": {
                    "name": "Beijing",
                    "longitude": 116.39723,
                    "latitude": 39.9075,
                    "timezone": "Asia/Shanghai",
                },
            },
        }
        early = compute_chart({
            **common,
            "birth_context": {
                **common["birth_context"],
                "zi_hour_convention": "early",
            },
        })
        late = compute_chart({
            **common,
            "birth_context": {
                **common["birth_context"],
                "zi_hour_convention": "late",
            },
        })

        self.assertEqual(early["birth_time"]["zi_hour_convention"], "early")
        self.assertEqual(late["birth_time"]["zi_hour_convention"], "late")
        self.assertNotEqual(early["chart_id"], late["chart_id"])

        with self.assertRaises(BirthContextError) as raised:
            compute_chart({
                **common,
                "birth_context": {
                    **common["birth_context"],
                    "zi_hour_convention": "invalid",
                },
            })
        self.assertEqual(raised.exception.code, "invalid_zi_hour_convention")


if __name__ == "__main__":
    unittest.main()
