import json
import sys
import unittest

sys.path.insert(0, ".")

from tools import (
    ALL_TOOLKITS,
    BaziToolkit,
    ZiweiToolkit,
    LiuYaoToolkit,
    MeiHuaToolkit,
    QiMenToolkit,
    LiuRenToolkit,
    PhysiognomyToolkit,
    FengShuiToolkit,
)


def assert_success(test_case, payload):
    parsed = json.loads(payload)
    test_case.assertTrue(parsed.get("success"), parsed)


class ToolkitSmokeTests(unittest.TestCase):
    def test_all_public_toolkits_import_and_register(self):
        self.assertEqual(
            set(ALL_TOOLKITS),
            {"八字", "紫微斗数", "混合路由", "六爻", "梅花易数", "奇门遁甲", "大六壬", "面相手相", "风水"},
        )
        for toolkit_class in ALL_TOOLKITS.values():
            self.assertTrue(toolkit_class().name)

    def test_bazi_and_ziwei(self):
        assert_success(self, BaziToolkit().paipan(1990, 6, 15, 12, "女"))
        ziwei = json.loads(ZiweiToolkit().paipan(1990, 6, 15, 12, "女"))
        self.assertTrue(ziwei["success"])
        self.assertEqual(ziwei["排盘引擎"], "iztro")

    def test_divination_toolkits(self):
        assert_success(
            self,
            LiuYaoToolkit().cast_hexagram(
                coins="2,2,2;2,2,2;2,2,2;2,2,2;2,2,2;2,2,2"
            ),
        )
        assert_success(self, MeiHuaToolkit().cast_meihua(1, 2, 2026, 7, 20))
        assert_success(self, QiMenToolkit().build_qimen_pan(2026, 7, 20, 12))
        assert_success(self, LiuRenToolkit().build_liuren_pan(2026, 7, 20, 12))

    def test_reference_toolkits(self):
        assert_success(self, PhysiognomyToolkit().face_twelve_palaces("命宫"))
        assert_success(self, FengShuiToolkit().bazhai_minggua(1990, "女"))


if __name__ == "__main__":
    unittest.main()
