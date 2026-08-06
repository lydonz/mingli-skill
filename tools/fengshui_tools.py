from __future__ import annotations

import json

from .toolkit_base import Toolkit
from .calendar_engine import BAGUA


FANGWEI_BAGUA = {
    "北": "坎", "东北": "艮", "东": "震", "东南": "巽",
    "南": "离", "西南": "坤", "西": "兑", "西北": "乾",
}

STAR_MEANING = {
    1: {"名": "一白", "五行": "水", "吉凶": "吉", "主": "官贵、桃花、智慧"},
    2: {"名": "二黑", "五行": "土", "吉凶": "凶", "主": "病符、小人"},
    3: {"名": "三碧", "五行": "木", "吉凶": "凶", "主": "是非、官灾"},
    4: {"名": "四绿", "五行": "木", "吉凶": "吉", "主": "文昌、学业"},
    5: {"名": "五黄", "五行": "土", "吉凶": "大凶", "主": "灾厄、疾病"},
    6: {"名": "六白", "五行": "金", "吉凶": "吉", "主": "武贵、权力"},
    7: {"名": "七赤", "五行": "金", "吉凶": "凶", "主": "口舌、盗贼"},
    8: {"名": "八白", "五行": "土", "吉凶": "吉", "主": "财帛、置业"},
    9: {"名": "九紫", "五行": "火", "吉凶": "吉", "主": "喜庆、姻缘"},
}


class FengShuiToolkit(Toolkit):
    def __init__(self, **kwargs):
        tools = [
            self.bazhai_minggua,
            self.bazhai_fangwei,
            self.xuankong_period,
            self.xuankong_feixing,
            self.star_meaning,
            self.direction_analysis,
            self.wuxing_shape,
            self.suggest_layout,
        ]
        super().__init__(name="fengshui_tools", tools=tools, **kwargs)

    def bazhai_minggua(self, year: int, gender: str = "男") -> str:
        """
        八宅命卦：根据出生年份和性别计算命卦（东四命或西四命）。

        Args:
            year: 出生年份 (公历)
            gender: 性别 ("男" 或 "女")
        """
        return json.dumps({
            "success": False,
            "capability_status": "disabled_pending_table_verification",
            "error": "八宅命卦与游年方位表尚未完成逐宫校勘，已停止输出吉凶方位。",
            "allowed_use": "不得据此进行住宅、医疗、财务或人生决策。",
        }, ensure_ascii=False)

    def bazhai_fangwei(self, ming_gua: str, direction: str) -> str:
        """
        八宅方位吉凶：查询命卦在某一方位的吉凶属性。

        Args:
            ming_gua: 命卦 (如 "坎", "离", "震", "乾")
            direction: 方位 (如 "北", "南", "东", "西", "东北", "东南", "西北", "西南")
        """
        return json.dumps({
            "success": False,
            "capability_status": "disabled_pending_table_verification",
            "error": "八宅游年方位表尚未完成逐宫校勘，当前不提供吉凶判断。",
            "allowed_use": "仅可查询方位与八卦的基础对应关系。",
        }, ensure_ascii=False)

    def xuankong_period(self, year: int) -> str:
        """
        玄空元运：根据年份确定当前所处的三元九运。

        Args:
            year: 年份
        """
        try:
            period_7_end = 2003
            base_period = 7
            base_year = 1864

            total_periods = (year - base_year) // 20
            current_period = (base_period + total_periods - 6) % 9
            if current_period == 0:
                current_period = 9

            period_start = base_year + (total_periods) * 20
            period_end = period_start + 19

            yuan = {1: "上元", 2: "上元", 3: "上元",
                    4: "中元", 5: "中元", 6: "中元",
                    7: "下元", 8: "下元", 9: "下元"}

            return json.dumps({
                "success": True,
                "年份": year,
                "当前运": f"第{current_period}运",
                "三元": yuan.get(current_period, "未知"),
                "运期": f"{period_start}-{period_end}",
                "当运星": current_period,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def xuankong_feixing(self, period: int, facing_direction: str) -> str:
        """
        玄空飞星排盘：根据运数和朝向排出九宫飞星盘。

        Args:
            period: 运数 (1-9)
            facing_direction: 房屋朝向 ("子"=北, "午"=南, "卯"=东, "酉"=西, 
                             "丑"=东北偏北, "寅"=东北偏东, "辰"=东南偏东, "巳"=东南偏南,
                             "未"=西南偏南, "申"=西南偏西, "戌"=西北偏西, "亥"=西北偏北)
        """
        return json.dumps({
            "success": False,
            "capability_status": "experimental_disabled",
            "error": "玄空宅盘需要建造/换运时间、坐向兼向、二十四山阴阳与山向飞布等完整输入和算法；当前简化公式已停用。",
            "allowed_use": "玄空元运和星名可作文化资料查询，不可生成正式宅盘。",
        }, ensure_ascii=False)

    def star_meaning(self, star_num: int) -> str:
        """
        飞星含义：查询玄空飞星中某一星曜的含义。

        Args:
            star_num: 星数 (1-9)
        """
        try:
            info = STAR_MEANING.get(star_num)
            if not info:
                return json.dumps({"success": False, "error": f"星数范围1-9"}, ensure_ascii=False)
            return json.dumps({
                "success": True,
                "capability_status": "cultural_reference_only",
                "星数": star_num,
                "传统象意": info,
                "使用边界": "星名吉凶仅作传统文化资料，不用于医疗、财务或安全决策。",
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def direction_analysis(self, direction: str) -> str:
        """
        方位分析：查询某一方位对应的后天八卦、五行及风水属性。

        Args:
            direction: 方位 ("北", "南", "东", "西", "东北", "东南", "西北", "西南")
        """
        try:
            gua = FANGWEI_BAGUA.get(direction)
            if not gua:
                return json.dumps({"success": False, "error": f"未知方位 '{direction}'"}, ensure_ascii=False)

            gua_info = BAGUA[gua]
            family_map = {"乾": "父亲", "坤": "母亲", "震": "长男", "巽": "长女",
                          "坎": "中男", "离": "中女", "艮": "少男", "兑": "少女"}

            return json.dumps({
                "success": True,
                "capability_status": "cultural_reference_only",
                "方位": direction,
                "对应卦": gua,
                "象": gua_info["象"],
                "五行": gua_info["五行"],
                "洛书数": gua_info["数"],
                "家庭成员": family_map.get(gua, "未知"),
                "使用边界": "方位与家庭象仅为传统八卦对应，不代表现实家庭成员状态。",
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def wuxing_shape(self, shape: str) -> str:
        """
        五行形煞：根据建筑或地形形状判断五行属性。

        Args:
            shape: 形状 ("方形", "圆形", "长形", "尖形", "波浪形")
        """
        try:
            shape_wx = {
                "方形": {"五行": "土", "特征": "稳重厚实", "影响": "主稳定"},
                "圆形": {"五行": "金", "特征": "圆润流畅", "影响": "主圆满"},
                "长形": {"五行": "木", "特征": "高耸挺拔", "影响": "主生长"},
                "尖形": {"五行": "火", "特征": "尖锐突出", "影响": "主冲动"},
                "波浪形": {"五行": "水", "特征": "流动弯曲", "影响": "主动态"},
            }
            info = shape_wx.get(shape)
            if not info:
                return json.dumps({"success": False, "error": f"未收录 '{shape}'"}, ensure_ascii=False)
            return json.dumps({
                "success": True,
                "capability_status": "cultural_reference_only",
                "形状": shape,
                "传统象意": info,
                "使用边界": "形状五行仅作文化分类，不构成建筑安全或投资判断。",
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def suggest_layout(self, room_type: str, gua_position: str) -> str:
        """
        风水布局建议：根据房间类型和所在宫位给出基本风水布局建议。

        Args:
            room_type: 房间类型 ("大门", "卧室", "厨房", "卫生间", "书房", "客厅", "财位")
            gua_position: 所在宫位/方位 ("北", "南", "东", "西", "东北", "东南", "西北", "西南")
        """
        try:
            suggestions = {
                "大门": {"宜": "方正明亮、开在吉方", "忌": "正对楼梯、电梯、直路冲射"},
                "卧室": {"宜": "安静、方正、床头靠实墙", "忌": "横梁压顶、镜子对床、门冲床"},
                "厨房": {"宜": "通风明亮、水火不相对", "忌": "灶对大门、灶背靠窗"},
                "卫生间": {"宜": "通风干燥、保持清洁", "忌": "正对大门、在房屋中心"},
                "书房": {"宜": "文昌位、背靠实墙、光线充足", "忌": "背门而坐、横梁压顶"},
                "客厅": {"宜": "宽敞明亮、沙发靠实墙", "忌": "穿堂风、开门见阳台"},
                "财位": {"宜": "明亮整洁、放吉祥物或绿植", "忌": "堆放杂物、昏暗污秽"},
            }

            info = suggestions.get(room_type)
            if not info:
                return json.dumps({"success": False, "error": f"未收录 '{room_type}'"}, ensure_ascii=False)

            gua = FANGWEI_BAGUA.get(gua_position, "")
            return json.dumps({
                "success": True,
                "capability_status": "general_environment_advice",
                "房间": room_type,
                "方位": gua_position,
                "对应卦": gua,
                "宜": info["宜"],
                "忌": info["忌"],
                "使用边界": "建议仅涉及通风、照明、整洁和动线等一般环境原则，不宣称吉凶效果。",
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
