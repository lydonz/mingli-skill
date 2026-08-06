from __future__ import annotations

import json
import math
import random
from typing import Dict, List, Optional, Tuple

from .toolkit_base import Toolkit

from .calendar_engine import (
    TIANGAN, DIZHI, WUXING_ZHI,
    BAGUA, HEXAGRAMS, LIUYAO_LIUSHEN,
)

# 爻序统一按“初爻在前、上爻在后”（自下而上）。
TRIGRAM_LINES = {
    "乾": [1, 1, 1], "兑": [1, 1, 0], "离": [1, 0, 1], "震": [1, 0, 0],
    "巽": [0, 1, 1], "坎": [0, 1, 0], "艮": [0, 0, 1], "坤": [0, 0, 0],
}

HEXAGRAM_BY_TRIGRAMS = {
    ("乾", "乾"): (1, "乾"), ("坤", "坤"): (2, "坤"),
    ("坎", "震"): (3, "屯"), ("艮", "坎"): (4, "蒙"),
    ("坎", "乾"): (5, "需"), ("乾", "坎"): (6, "讼"),
    ("坤", "坎"): (7, "师"), ("坎", "坤"): (8, "比"),
    ("巽", "乾"): (9, "小畜"), ("乾", "兑"): (10, "履"),
    ("坤", "乾"): (11, "泰"), ("乾", "坤"): (12, "否"),
    ("乾", "离"): (13, "同人"), ("离", "乾"): (14, "大有"),
    ("坤", "艮"): (15, "谦"), ("震", "坤"): (16, "豫"),
    ("兑", "震"): (17, "随"), ("艮", "巽"): (18, "蛊"),
    ("坤", "兑"): (19, "临"), ("巽", "坤"): (20, "观"),
    ("离", "震"): (21, "噬嗑"), ("艮", "离"): (22, "贲"),
    ("艮", "坤"): (23, "剥"), ("坤", "震"): (24, "复"),
    ("乾", "震"): (25, "无妄"), ("艮", "乾"): (26, "大畜"),
    ("艮", "震"): (27, "颐"), ("兑", "巽"): (28, "大过"),
    ("坎", "坎"): (29, "坎"), ("离", "离"): (30, "离"),
    ("兑", "艮"): (31, "咸"), ("震", "巽"): (32, "恒"),
    ("乾", "艮"): (33, "遯"), ("震", "乾"): (34, "大壮"),
    ("离", "坤"): (35, "晋"), ("坤", "离"): (36, "明夷"),
    ("巽", "离"): (37, "家人"), ("离", "兑"): (38, "睽"),
    ("坎", "艮"): (39, "蹇"), ("震", "坎"): (40, "解"),
    ("艮", "兑"): (41, "损"), ("巽", "震"): (42, "益"),
    ("兑", "乾"): (43, "夬"), ("乾", "巽"): (44, "姤"),
    ("兑", "坤"): (45, "萃"), ("坤", "巽"): (46, "升"),
    ("兑", "坎"): (47, "困"), ("坎", "巽"): (48, "井"),
    ("兑", "离"): (49, "革"), ("离", "巽"): (50, "鼎"),
    ("震", "震"): (51, "震"), ("艮", "艮"): (52, "艮"),
    ("巽", "艮"): (53, "渐"), ("震", "兑"): (54, "归妹"),
    ("震", "离"): (55, "丰"), ("离", "艮"): (56, "旅"),
    ("巽", "巽"): (57, "巽"), ("兑", "兑"): (58, "兑"),
    ("巽", "坎"): (59, "涣"), ("坎", "兑"): (60, "节"),
    ("巽", "兑"): (61, "中孚"), ("震", "艮"): (62, "小过"),
    ("坎", "离"): (63, "既济"), ("离", "坎"): (64, "未济"),
}

LIUYAO_PALACES = {
    "乾": ("乾", "姤", "遯", "否", "观", "剥", "晋", "大有"),
    "坤": ("坤", "复", "临", "泰", "大壮", "夬", "需", "比"),
    "震": ("震", "豫", "解", "恒", "升", "井", "大过", "随"),
    "巽": ("巽", "小畜", "家人", "益", "无妄", "噬嗑", "颐", "蛊"),
    "坎": ("坎", "节", "屯", "既济", "革", "丰", "明夷", "师"),
    "离": ("离", "旅", "鼎", "未济", "蒙", "涣", "讼", "同人"),
    "艮": ("艮", "贲", "大畜", "损", "睽", "履", "中孚", "渐"),
    "兑": ("兑", "困", "萃", "咸", "蹇", "谦", "小过", "归妹"),
}

YAO_SYMBOL = {0: "⚋", 1: "⚊", 2: "⚏"}

# 每个数组均按初、二、三、四、五、上爻顺序。
LIUYAO_NAJIA_GAN = {
    "乾": ["甲", "甲", "甲", "壬", "壬", "壬"],
    "坎": ["戊", "戊", "戊", "戊", "戊", "戊"],
    "艮": ["丙", "丙", "丙", "丙", "丙", "丙"],
    "震": ["庚", "庚", "庚", "庚", "庚", "庚"],
    "巽": ["辛", "辛", "辛", "辛", "辛", "辛"],
    "离": ["己", "己", "己", "己", "己", "己"],
    "坤": ["乙", "乙", "乙", "癸", "癸", "癸"],
    "兑": ["丁", "丁", "丁", "丁", "丁", "丁"],
}

LIUYAO_NAJIA_ZHI = {
    "乾": ["子", "寅", "辰", "午", "申", "戌"],
    "坎": ["寅", "辰", "午", "申", "戌", "子"],
    "艮": ["辰", "午", "申", "戌", "子", "寅"],
    "震": ["子", "寅", "辰", "午", "申", "戌"],
    "巽": ["丑", "亥", "酉", "未", "巳", "卯"],
    "离": ["卯", "丑", "亥", "酉", "未", "巳"],
    "坤": ["未", "巳", "卯", "丑", "亥", "酉"],
    "兑": ["巳", "卯", "丑", "亥", "酉", "未"],
}

LIUSHEN_START_BY_DAY_GAN = {
    "甲": 0, "乙": 0, "丙": 1, "丁": 1, "戊": 2,
    "己": 3, "庚": 4, "辛": 4, "壬": 5, "癸": 5,
}

class LiuYaoToolkit(Toolkit):
    def __init__(self, **kwargs):
        tools = [
            self.cast_hexagram,
            self.analyze_hexagram,
            self.load_najia,
            self.find_yong_shen,
            self.check_sheng_ke,
            self.interpret_result,
        ]
        super().__init__(name="liuyao_tools", tools=tools, **kwargs)

    def cast_hexagram(
        self,
        method: str = "三硬币法",
        coins: str = "",
        random_seed: int | None = None,
    ) -> str:
        """
        起六爻卦：使用三硬币法或数字法起出一个六爻卦象。

        Args:
            method: 起卦方法 ("三硬币法" 或 "数字法")
            coins: 六次摇币结果，每次三个数字用逗号分隔，六次用分号分隔。
                   数字仅作为硬币两面记号：2和3。每组三数相加后按6=老阴、7=少阳、8=少阴、9=老阳解释。
                   如 "2,2,3;2,2,3;2,3,3;2,2,2;3,3,3;2,2,3"。留空则自动随机生成。
        """
        try:
            if method != "三硬币法":
                return json.dumps({
                    "success": False,
                    "capability_status": "unsupported_method",
                    "error": "当前仅实现三硬币法。",
                }, ensure_ascii=False)
            generated_randomly = not coins.strip()
            coin_groups = []
            if coins.strip():
                groups = coins.split(";")
                if len(groups) != 6:
                    return json.dumps({"success": False, "error": "需要6组数据，用分号分隔"}, ensure_ascii=False)
                yao_values = []
                for g in groups:
                    nums = [int(x.strip()) for x in g.split(",")]
                    if len(nums) != 3 or any(value not in (2, 3) for value in nums):
                        return json.dumps({
                            "success": False,
                            "error": "每组必须恰好包含3个数字，且只能使用2或3",
                        }, ensure_ascii=False)
                    total = sum(nums)
                    coin_groups.append(nums)
                    yao_values.append(total)
            else:
                yao_values = []
                generator = (
                    random.Random(random_seed)
                    if random_seed is not None
                    else random.SystemRandom()
                )
                for _ in range(6):
                    coins_list = [generator.choice([2, 3]) for _ in range(3)]
                    coin_groups.append(coins_list)
                    yao_values.append(sum(coins_list))

            yaos = []
            yao_types = {
                6: ("阴", True, "老阴"),
                7: ("阳", False, "少阳"),
                8: ("阴", False, "少阴"),
                9: ("阳", True, "老阳"),
            }
            for val in yao_values:
                if val not in yao_types:
                    return json.dumps({
                        "success": False,
                        "error": f"无效爻值{val}，三硬币法只能得到6、7、8、9",
                    }, ensure_ascii=False)
                yao_type, is_changing, traditional_name = yao_types[val]
                yaos.append({
                    "value": val,
                    "type": yao_type,
                    "traditional_name": traditional_name,
                    "changing": is_changing,
                })

            lower = [1 if y["type"] == "阳" else 0 for y in yaos[:3]]
            upper = [1 if y["type"] == "阳" else 0 for y in yaos[3:]]
            lower_gua = self._match_trigram(lower)
            upper_gua = self._match_trigram(upper)

            hex_num, hex_name = HEXAGRAM_BY_TRIGRAMS[(upper_gua, lower_gua)]

            changed_yaos = [i for i, y in enumerate(yaos) if y["changing"]]
            if changed_yaos:
                changed_lower = list(lower)
                changed_upper = list(upper)
                for idx in changed_yaos:
                    if idx < 3:
                        changed_lower[idx] = 1 - changed_lower[idx]
                    else:
                        changed_upper[idx - 3] = 1 - changed_upper[idx - 3]
                changed_lower_gua = self._match_trigram(changed_lower)
                changed_upper_gua = self._match_trigram(changed_upper)
                changed_hex_num, changed_hex_name = HEXAGRAM_BY_TRIGRAMS[
                    (changed_upper_gua, changed_lower_gua)
                ]
            else:
                changed_hex_name = "无变卦"
                changed_hex_num = 0

            return json.dumps({
                "success": True,
                "capability_status": "partial_structural",
                "method_profile": "liuyao_basic_coin_cast",
                "input_mode": "simulated_random" if generated_randomly else "caller_supplied_coins",
                "原始摇币": [
                    {"爻位": index + 1, "coins": values}
                    for index, values in enumerate(coin_groups)
                ],
                "随机审计": {
                    "source": (
                        "seeded_prng"
                        if generated_randomly and random_seed is not None
                        else "system_random"
                        if generated_randomly
                        else "caller_supplied"
                    ),
                    "seed": random_seed if generated_randomly else None,
                },
                "本卦": hex_name,
                "卦序": hex_num,
                "上卦": upper_gua,
                "下卦": lower_gua,
                "变卦": changed_hex_name,
                "变卦序": changed_hex_num,
                "六爻": [{"爻位": i+1, **y} for i, y in enumerate(yaos)],
                "动爻位置": [i+1 for i, y in enumerate(yaos) if y["changing"]],
                "爻序规则": "初爻至上爻，自下而上",
                "算法状态": "基础卦象可用；纳甲、八宫、世应、伏神等须另行完整装卦",
                "解释边界": "起卦动作与选项答案判断相互独立；不得把模拟摇币当作现实事件证据。",
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_hexagram(self, hexagram_name: str, question_type: str = "通用") -> str:
        """
        分析卦象含义：查询六十四卦的基本含义。

        Args:
            hexagram_name: 卦名 (如 "乾", "泰", "既济")
            question_type: 问题类型 ("事业", "婚姻", "财运", "健康", "通用")
        """
        try:
            if question_type in {"健康", "疾病", "医疗", "官司", "法律"}:
                return json.dumps({
                    "success": False,
                    "capability_status": "high_risk_suppressed",
                    "error": "高风险现实问题不提供卦象吉凶判断。",
                    "allowed_use": "仅可查询卦名、卦象和传统术语。",
                }, ensure_ascii=False)
            hex_info = {
                "乾": {"象": "天行健，君子以自强不息", "吉凶": "吉", "含义": "刚健中正，万物之始"},
                "坤": {"象": "地势坤，君子以厚德载物", "吉凶": "吉", "含义": "柔顺包容，厚德载物"},
                "屯": {"象": "云雷屯，君子以经纶", "吉凶": "小凶", "含义": "初创艰难，需坚持"},
                "蒙": {"象": "山下出泉，蒙", "吉凶": "平", "含义": "启蒙教化，需引导"},
                "需": {"象": "云上于天，需", "吉凶": "平", "含义": "等待时机，守正则吉"},
                "讼": {"象": "天与水违行，讼", "吉凶": "凶", "含义": "争讼不宜，宜和解"},
                "泰": {"象": "天地交，泰", "吉凶": "大吉", "含义": "上下通泰，万物通"},
                "否": {"象": "天地不交，否", "吉凶": "大凶", "含义": "闭塞不通，需隐忍"},
                "既济": {"象": "水在火上，既济", "吉凶": "吉", "含义": "事已成就，守成为要"},
                "未济": {"象": "火在水上，未济", "吉凶": "平", "含义": "事未完成，仍需努力"},
            }
            info = hex_info.get(hexagram_name, {"象": "未收录", "吉凶": "未知", "含义": "待查"})

            return json.dumps({
                "success": True,
                "卦名": hexagram_name,
                "问题类型": question_type,
                **info,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def load_najia(self, upper_gua: str, lower_gua: str, day_ganzhi: str) -> str:
        """
        装卦纳甲：为六爻卦装配纳甲（天干地支）、六亲、六神。

        Args:
            upper_gua: 上卦名 (如 "乾", "坤")
            lower_gua: 下卦名 (如 "坎", "离")
            day_ganzhi: 测卦日的干支 (如 "甲子")
        """
        try:
            if upper_gua not in TRIGRAM_LINES or lower_gua not in TRIGRAM_LINES:
                raise ValueError("上卦和下卦必须是有效八卦名")
            if len(day_ganzhi) != 2 or day_ganzhi[0] not in TIANGAN or day_ganzhi[1] not in DIZHI:
                raise ValueError("测卦日干支格式错误，应如甲子")

            _, hexagram_name = HEXAGRAM_BY_TRIGRAMS[(upper_gua, lower_gua)]
            palace_gua = next(
                palace for palace, members in LIUYAO_PALACES.items()
                if hexagram_name in members
            )
            palace_wuxing = BAGUA[palace_gua]["五行"]
            liushen_start = LIUSHEN_START_BY_DAY_GAN[day_ganzhi[0]]

            lines = []
            for i in range(6):
                gua = lower_gua if i < 3 else upper_gua
                pos = i
                gan_list = LIUYAO_NAJIA_GAN[gua]
                zhi_list = LIUYAO_NAJIA_ZHI[gua]
                gan = gan_list[pos]
                zhi = zhi_list[pos]
                wx = WUXING_ZHI[zhi]

                liuqin = self._get_liuqin(palace_wuxing, wx)
                liushen = LIUYAO_LIUSHEN[(liushen_start + i) % 6]

                lines.append({
                    "爻位": i + 1,
                    "纳甲": f"{gan}{zhi}",
                    "地支": zhi,
                    "五行": wx,
                    "六亲": liuqin,
                    "六神": liushen,
                })

            return json.dumps({
                "success": True,
                "capability_status": "partial_structural",
                "method_profile": "liuyao_basic_najia",
                "本卦": hexagram_name,
                "八宫归属": palace_gua,
                "宫五行": palace_wuxing,
                "纳甲六爻": lines,
                "算法状态": "纳甲、八宫、六亲、六神基础装配可用；世应、伏神、旬空和旺衰尚未实现",
                "未实现字段": ["世应", "伏神", "旬空", "旺衰"],
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def find_yong_shen(self, question_type: str) -> str:
        """
        取用神：根据所问事项确定六爻预测中的用神（六亲）。

        Args:
            question_type: 问题类型 ("父母", "兄弟", "子孙", "妻财", "官鬼",
                          "事业", "婚姻女", "婚姻男", "考试", "疾病", "失物", "官司")
        """
        try:
            if question_type in {"疾病", "官司", "子嗣"}:
                return json.dumps({
                    "success": False,
                    "capability_status": "high_risk_suppressed",
                    "error": "医疗、法律和生育主题不提供自动取用神判断。",
                    "allowed_use": "可作为传统术语资料阅读，不用于现实决策。",
                }, ensure_ascii=False)
            yongshen_map = {
                "父母": "父母爻", "兄弟": "兄弟爻", "子孙": "子孙爻",
                "妻财": "妻财爻", "官鬼": "官鬼爻",
                "事业": "官鬼爻", "婚姻女": "官鬼爻", "婚姻男": "妻财爻",
                "考试": "父母爻", "疾病": "官鬼爻", "失物": "妻财爻",
                "官司": "官鬼爻", "房屋": "父母爻", "出行": "官鬼爻",
                "求财": "妻财爻", "子嗣": "子孙爻",
            }
            ys = yongshen_map.get(question_type, "官鬼爻")
            yuan_shen = {"父母爻": "兄弟爻", "兄弟爻": "父母爻", "子孙爻": "兄弟爻",
                         "妻财爻": "子孙爻", "官鬼爻": "妻财爻"}
            ji_shen = {"父母爻": "子孙爻", "兄弟爻": "官鬼爻", "子孙爻": "官鬼爻",
                       "妻财爻": "兄弟爻", "官鬼爻": "子孙爻"}

            return json.dumps({
                "success": True,
                "capability_status": "cultural_reference_only",
                "问题类型": question_type,
                "用神": ys,
                "原神": yuan_shen.get(ys, "未知"),
                "忌神": ji_shen.get(ys, "未知"),
                "仇神": "克原神、生忌神者",
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def check_sheng_ke(self, yong_wuxing: str, yao_wuxing: str) -> str:
        """
        查五行生克：判断用神与爻之间的五行生克关系。

        Args:
            yong_wuxing: 用神五行 (如 "木")
            yao_wuxing: 爻五行 (如 "金")
        """
        try:
            from .calendar_engine import WUXING_SHENG, WUXING_KE
            if yong_wuxing == yao_wuxing:
                rel = "比和"
            elif WUXING_SHENG.get(yao_wuxing) == yong_wuxing:
                rel = "爻生用神（有益）"
            elif WUXING_SHENG.get(yong_wuxing) == yao_wuxing:
                rel = "用神生爻（泄气）"
            elif WUXING_KE.get(yao_wuxing) == yong_wuxing:
                rel = "爻克用神（不利）"
            elif WUXING_KE.get(yong_wuxing) == yao_wuxing:
                rel = "用神克爻（有利）"
            else:
                rel = "无关"

            return json.dumps({
                "success": True,
                "用神五行": yong_wuxing,
                "爻五行": yao_wuxing,
                "关系": rel,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def interpret_result(self, yong_shen_status: str, dong_yao_count: int) -> str:
        """
        断卦原则：根据用神状态和动爻数量给出初步判断框架。

        Args:
            yong_shen_status: 用神状态 ("旺相", "休囚", "受克", "空亡", "伏藏")
            dong_yao_count: 动爻数量 (0-6)
        """
        try:
            if not isinstance(dong_yao_count, int) or not 0 <= dong_yao_count <= 6:
                return json.dumps({
                    "success": False,
                    "error": "dong_yao_count 必须是 0—6 的整数。",
                }, ensure_ascii=False)
            status_interpret = {
                "旺相": "用神有力，事可成",
                "休囚": "用神无力，需等待时机",
                "受克": "用神受克，事多阻碍",
                "空亡": "用神空亡，事多虚幻或延迟",
                "伏藏": "用神伏藏，需寻找方可成",
            }

            dong_interpret = {
                0: "无动爻，以卦辞断",
                1: "一个动爻，以该爻爻辞断",
                2: "两个动爻，以上面动爻爻辞为主",
                3: "三个动爻，以本卦卦辞为主",
                4: "四个动爻，以变卦中不变爻断",
                5: "五个动爻，以变卦中不变爻断",
                6: "六个动爻，乾坤特殊断法，余以变卦断",
            }

            return json.dumps({
                "success": True,
                "capability_status": "cultural_reference_only",
                "用神状态": yong_shen_status,
                "用神解读": status_interpret.get(yong_shen_status, "待分析"),
                "动爻数": dong_yao_count,
                "断卦法则": dong_interpret.get(dong_yao_count, "待分析"),
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _match_trigram(self, lines: List[int]) -> str:
        trigram_map = {tuple(pattern): name for name, pattern in TRIGRAM_LINES.items()}
        if tuple(lines) not in trigram_map:
            raise ValueError(f"无效三爻结构：{lines}")
        return trigram_map[tuple(lines)]

    def _trigrams_to_hexagram(self, upper: str, lower: str) -> int:
        try:
            return HEXAGRAM_BY_TRIGRAMS[(upper, lower)][0]
        except KeyError as exc:
            raise ValueError(f"无效上下卦组合：{upper}上{lower}下") from exc

    def _get_liuqin(self, palace_wuxing: str, yao_wuxing: str) -> str:
        from .calendar_engine import WUXING_SHENG, WUXING_KE

        if yao_wuxing == palace_wuxing:
            return "兄弟"
        if WUXING_SHENG.get(palace_wuxing) == yao_wuxing:
            return "子孙"
        if WUXING_KE.get(palace_wuxing) == yao_wuxing:
            return "妻财"
        if WUXING_KE.get(yao_wuxing) == palace_wuxing:
            return "官鬼"
        if WUXING_SHENG.get(yao_wuxing) == palace_wuxing:
            return "父母"
        return "未知"


class MeiHuaToolkit(Toolkit):
    def __init__(self, **kwargs):
        tools = [
            self.cast_meihua,
            self.analyze_ti_yong,
            self.interpret_wuxing_relation,
        ]
        super().__init__(name="meihua_tools", tools=tools, **kwargs)

    def cast_meihua(self, number1: int, number2: int, year: int = 0,
                    month: int = 0, day: int = 0) -> str:
        """
        梅花易数起卦：根据两个数字（或时间）起出上卦和下卦。

        Args:
            number1: 第一数（起上卦）
            number2: 第二数（起下卦）
            year: 年份（可选，用于计算动爻）
            month: 月份（可选）
            day: 日期（可选）
        """
        try:
            upper_idx = number1 % 8
            if upper_idx == 0:
                upper_idx = 8
            lower_idx = number2 % 8
            if lower_idx == 0:
                lower_idx = 8

            gua_map = {1: "乾", 2: "兑", 3: "离", 4: "震", 5: "巽", 6: "坎", 7: "艮", 8: "坤"}
            upper_gua = gua_map[upper_idx]
            lower_gua = gua_map[lower_idx]

            if year and month and day:
                dong_yao = (year + month + day + number1 + number2) % 6
                if dong_yao == 0:
                    dong_yao = 6
            else:
                dong_yao = (number1 + number2) % 6
                if dong_yao == 0:
                    dong_yao = 6

            upper_wx = BAGUA[upper_gua]["五行"]
            lower_wx = BAGUA[lower_gua]["五行"]

            return json.dumps({
                "success": True,
                "capability_status": "cultural_reference_only",
                "method_profile": "meihua_number_cast",
                "上卦": upper_gua,
                "上卦五行": upper_wx,
                "上卦象": BAGUA[upper_gua]["象"],
                "下卦": lower_gua,
                "下卦五行": lower_wx,
                "下卦象": BAGUA[lower_gua]["象"],
                "动爻": dong_yao,
                "上卦数": upper_idx,
                "下卦数": lower_idx,
                "解释边界": "梅花起卦的取数和外应存在流派差异，仅作传统文化参考。",
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_ti_yong(self, upper_gua: str, lower_gua: str, dong_yao: int) -> str:
        """
        分析体用关系：根据梅花易数的动爻确定体卦和用卦，分析体用五行生克。

        Args:
            upper_gua: 上卦名
            lower_gua: 下卦名
            dong_yao: 动爻位置 (1-6, 1-3为下卦，4-6为上卦)
        """
        try:
            if upper_gua not in BAGUA or lower_gua not in BAGUA:
                return json.dumps({
                    "success": False,
                    "error": "上卦和下卦必须是有效八卦名。",
                }, ensure_ascii=False)
            if not isinstance(dong_yao, int) or not 1 <= dong_yao <= 6:
                return json.dumps({
                    "success": False,
                    "error": "动爻位置必须是 1—6 的整数。",
                }, ensure_ascii=False)
            if dong_yao <= 3:
                ti_gua = upper_gua
                yong_gua = lower_gua
            else:
                ti_gua = lower_gua
                yong_gua = upper_gua

            ti_wx = BAGUA[ti_gua]["五行"]
            yong_wx = BAGUA[yong_gua]["五行"]

            from .calendar_engine import WUXING_SHENG, WUXING_KE
            if ti_wx == yong_wx:
                relation = "比和"
                judge = "中性，力量相当"
            elif WUXING_SHENG.get(yong_wx) == ti_wx:
                relation = "用生体"
                judge = "大吉，有助益"
            elif WUXING_KE.get(yong_wx) == ti_wx:
                relation = "用克体"
                judge = "不吉，有阻碍"
            elif WUXING_SHENG.get(ti_wx) == yong_wx:
                relation = "体生用"
                judge = "泄气，精力消耗"
            elif WUXING_KE.get(ti_wx) == yong_wx:
                relation = "体克用"
                judge = "劳而有获"
            else:
                relation = "无关"
                judge = "待分析"

            return json.dumps({
                "success": True,
                "capability_status": "cultural_reference_only",
                "method_profile": "meihua_tiyong_baseline",
                "体卦": ti_gua,
                "体卦五行": ti_wx,
                "用卦": yong_gua,
                "用卦五行": yong_wx,
                "体用关系": relation,
                "判断": judge,
                "动爻": dong_yao,
                "解释边界": "体用关系属于传统解释，不构成现实事件的确定判断。",
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def interpret_wuxing_relation(self, wx1: str, wx2: str) -> str:
        """
        解读五行关系：判断两个五行之间的生克关系。

        Args:
            wx1: 第一个五行 (如 "木")
            wx2: 第二个五行 (如 "火")
        """
        try:
            from .calendar_engine import WUXING_SHENG, WUXING_KE
            if wx1 == wx2:
                rel = "比和"
            elif WUXING_SHENG.get(wx1) == wx2:
                rel = f"{wx1}生{wx2}"
            elif WUXING_SHENG.get(wx2) == wx1:
                rel = f"{wx2}生{wx1}"
            elif WUXING_KE.get(wx1) == wx2:
                rel = f"{wx1}克{wx2}"
            elif WUXING_KE.get(wx2) == wx1:
                rel = f"{wx2}克{wx1}"
            else:
                rel = "无关"

            return json.dumps({
                "success": True,
                "五行1": wx1,
                "五行2": wx2,
                "关系": rel,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


class QiMenToolkit(Toolkit):
    def __init__(self, **kwargs):
        tools = [
            self.build_qimen_pan,
            self.analyze_qimen_geju,
            self.find_qimen_keji,
        ]
        super().__init__(name="qimen_tools", tools=tools, **kwargs)

    def build_qimen_pan(self, year: int, month: int, day: int, hour: int) -> str:
        """
        排奇门遁甲盘：根据公历时间排出奇门遁甲九宫格局（简化版时家奇门）。

        Args:
            year: 公历年份
            month: 月份
            day: 日期
            hour: 时辰 (0-23)
        """
        return json.dumps({
            "success": False,
            "capability_status": "experimental_disabled",
            "error": "奇门排盘尚未实现完整的节气定局、三元局数、值符值使与天地人神盘转布规则，已停止输出伪精确盘。",
            "allowed_use": "仅可查询传统术语资料，不可用于正式判断。",
        }, ensure_ascii=False)

    def analyze_qimen_geju(self, geju_name: str) -> str:
        """
        分析奇门格局：查询常见奇门格局的含义。

        Args:
            geju_name: 格局名称 (如 "吉格", "凶格", "伏吟", "反吟", "马星")
        """
        try:
            geju_info = {
                "吉格": ["天遁", "地遁", "人遁", "神遁", "龙遁", "虎遁", "风遁", "云遁"],
                "凶格": ["大格", "小格", "刑格", "悖格", "飞宫格", "时格"],
                "伏吟": "星门不动，主停滞、等待",
                "反吟": "星门对冲，主反复、变动",
                "马星": "主动态、奔波、变化",
                "空亡": "主虚、不成、待填实",
                "击刑": "主灾祸、意外",
                "入墓": "主暗昧、困顿",
            }
            info = geju_info.get(geju_name, "未收录此格局")
            return json.dumps({
                "success": True,
                "格局": geju_name,
                "含义": info if isinstance(info, str) else info,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def find_qimen_keji(self, question_type: str) -> str:
        """
        奇门用神取法：根据所问事项确定奇门遁甲中的用神宫位。

        Args:
            question_type: 问题类型 ("事业", "婚姻", "求财", "出行", "官司", "考试", "失物", "疾病")
        """
        return json.dumps({
            "success": False,
            "capability_status": "experimental_disabled",
            "问题类型": question_type,
            "error": "奇门完整排盘未实现，不能脱离盘面提供用神判断。",
            "allowed_use": "仅可查询传统术语资料。",
        }, ensure_ascii=False)

class LiuRenToolkit(Toolkit):
    def __init__(self, **kwargs):
        tools = [
            self.build_liuren_pan,
            self.analyze_sike,
            self.analyze_sanchuan,
        ]
        super().__init__(name="liuren_tools", tools=tools, **kwargs)

    def build_liuren_pan(self, year: int, month: int, day: int, hour: int) -> str:
        """
        排大六壬四课三传：根据公历时间排出大六壬天地盘、四课和三传。

        Args:
            year: 公历年份
            month: 月份
            day: 日期
            hour: 时辰 (0-23)
        """
        return json.dumps({
            "success": False,
            "capability_status": "experimental_disabled",
            "error": "大六壬排盘尚未实现月将加时、贵人、四课取法与九宗门完整发传规则，已停止输出伪精确三传。",
            "allowed_use": "仅可查询传统术语资料，不可用于正式判断。",
        }, ensure_ascii=False)

    def analyze_sike(self, sike_json: str) -> str:
        """
        分析四课：解读大六壬四课的含义。

        Args:
            sike_json: 四课数据的 JSON 字符串
        """
        try:
            sike = json.loads(sike_json)
            analysis = []
            for ke in sike:
                analysis.append({
                    "课名": ke.get("name", ""),
                    "上神": ke.get("upper", ""),
                    "下神": ke.get("lower", ""),
                    "关系": "上克下" if ke.get("relation") == "ke_down" else
                             "下克上" if ke.get("relation") == "ke_up" else
                             "上生下" if ke.get("relation") == "sheng_down" else
                             "下生上" if ke.get("relation") == "sheng_up" else "比和",
                })
            return json.dumps({"success": True, "四课分析": analysis}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def analyze_sanchuan(self, sanchuan_json: str) -> str:
        """
        分析三传：解读大六壬三传（初传、中传、末传）的含义。

        Args:
            sanchuan_json: 三传数据的 JSON 字符串
        """
        try:
            sc = json.loads(sanchuan_json)
            return json.dumps({
                "success": True,
                "初传": sc.get("first", ""),
                "中传": sc.get("second", ""),
                "末传": sc.get("third", ""),
                "说明": "初传主事始，中传主事中，末传主事终",
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
