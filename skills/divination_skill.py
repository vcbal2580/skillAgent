"""
命理卜算技能（娱乐向） - 基于天干地支、五行、八卦做简要解读。
"""

from datetime import datetime
from skills.base import BaseSkill


class DivinationSkill(BaseSkill):
    name = "fortune_divination"
    description = "根据用户问题做命理卜算（天干地支、五行、八卦）并给出简要建议，适合娱乐参考。"
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "想占问的问题，如事业、感情、财运等。",
            },
            "year": {
                "type": "integer",
                "description": "可选，年份（用于辅助参考），如 1996。",
            },
        },
        "required": ["question"],
    }

    STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    ELEMENT_BY_STEM = {
        "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
        "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
    }
    GUA = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]

    def _ganzhi_year(self, year: int) -> str:
        offset = year - 1984
        stem = self.STEMS[offset % 10]
        branch = self.BRANCHES[offset % 12]
        return f"{stem}{branch}"

    def _seed(self, question: str, year: int | None) -> int:
        base = sum(ord(ch) for ch in question)
        now = datetime.now()
        date_factor = now.year * 10000 + now.month * 100 + now.day
        year_factor = year if year else 0
        return base + date_factor + year_factor

    def execute(self, question: str, year: int | None = None) -> str:
        if not question.strip():
            return "错误: question 不能为空"

        now = datetime.now()
        current_gz = self._ganzhi_year(now.year)
        seed = self._seed(question, year)

        upper = self.GUA[seed % 8]
        lower = self.GUA[(seed // 8) % 8]
        changing_line = seed % 6 + 1

        stem = current_gz[0]
        element = self.ELEMENT_BY_STEM.get(stem, "土")

        element_advice = {
            "木": "宜主动拓展、人脉经营，先布局后发力。",
            "火": "宜提升曝光与表达，把握窗口期。",
            "土": "宜稳中求进，重视执行和复盘。",
            "金": "宜聚焦规则与效率，适合做减法。",
            "水": "宜学习沉淀，借势而行，避免硬碰硬。",
        }

        year_text = f"\n参考年份干支: {self._ganzhi_year(year)}" if year else ""

        return (
            "【命理卜算（娱乐参考）】\n"
            f"占问: {question}\n"
            f"今日年干支: {current_gz}{year_text}\n"
            f"五行主气: {element}\n"
            f"卦象: 上卦{upper} / 下卦{lower}\n"
            f"动爻: 第{changing_line}爻\n"
            f"解读: {element_advice[element]}\n"
            "提示: 结果仅供文化娱乐与自我反思，不作为专业决策依据。"
        )
