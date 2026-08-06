import json
import unittest

from engine.run_tools_engine import compute_chart
from tools import HybridMingliToolkit
from tools.divination_tools import LiuYaoToolkit, MeiHuaToolkit, QiMenToolkit
from tools.fengshui_tools import FengShuiToolkit
from tools.physiognomy_tools import PhysiognomyToolkit


class ProductRegressionTests(unittest.TestCase):
    def test_midnight_is_not_replaced_with_noon(self):
        chart = compute_chart({
            "year": 1990,
            "month": 6,
            "day": 15,
            "hour": 0,
            "gender": "男",
        })
        hybrid = json.loads(HybridMingliToolkit().analyze_question(
            1990, 6, 15, 0, "男", "事业", "", "[]"
        ))

        self.assertEqual(chart["birth_hour"], 0)
        self.assertEqual(chart["四柱"]["时柱"], "戊子")
        self.assertEqual(hybrid["bazi"]["四柱"]["时柱"], "戊子")
        self.assertEqual(hybrid["ziwei_raw"]["时干支"], "戊子")

    def test_option_letters_must_be_unique(self):
        result = json.loads(HybridMingliToolkit().analyze_question(
            1990,
            6,
            15,
            12,
            "男",
            "事业",
            "",
            '[{"letter":"A","text":"技术"},{"letter":"A","text":"行政"}]',
        ))

        self.assertEqual(result["error"]["code"], "options_json_duplicate_letter")

    def test_liuyao_keeps_raw_coin_groups_and_supports_seeded_replay(self):
        toolkit = LiuYaoToolkit()
        first = json.loads(toolkit.cast_hexagram(random_seed=42))
        second = json.loads(toolkit.cast_hexagram(random_seed=42))

        self.assertTrue(first["success"])
        self.assertEqual(first["原始摇币"], second["原始摇币"])
        self.assertEqual(first["六爻"], second["六爻"])
        self.assertEqual(first["随机审计"]["source"], "seeded_prng")
        self.assertEqual(len(first["原始摇币"]), 6)

    def test_meihua_rejects_invalid_moving_line(self):
        for value in (0, 7, -1):
            result = json.loads(
                MeiHuaToolkit().analyze_ti_yong("乾", "坤", value)
            )
            self.assertFalse(result["success"])

    def test_disabled_and_high_risk_low_level_tools_fail_closed(self):
        disease = json.loads(LiuYaoToolkit().find_yong_shen("疾病"))
        qimen = json.loads(QiMenToolkit().find_qimen_keji("疾病"))
        face = json.loads(PhysiognomyToolkit().face_five_organs("眼"))
        star = json.loads(FengShuiToolkit().star_meaning(5))

        self.assertEqual(
            disease["capability_status"], "high_risk_suppressed"
        )
        self.assertEqual(qimen["capability_status"], "experimental_disabled")
        self.assertEqual(face["capability_status"], "cultural_reference_only")
        self.assertIn("使用边界", face)
        self.assertEqual(star["capability_status"], "cultural_reference_only")


if __name__ == "__main__":
    unittest.main()
