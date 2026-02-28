"""
黄历技能（娱乐向） - 提供简化版宜忌、方位与日签。
"""

import random
from datetime import datetime
from skills.base import BaseSkill


class AlmanacSkill(BaseSkill):
    name = "huangli_today"
    description = "提供简化版黄历信息（宜/忌、吉位、日签），支持指定日期。"
    parameters = {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "可选，日期，格式 YYYY-MM-DD；不传则默认今天。",
            },
        },
        "required": [],
    }

    STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    YI_ITEMS = [
        "会友", "签约", "学习", "整理", "出行", "开会", "求职", "复盘", "写作", "健身", "理财规划", "修整",
    ]
    JI_ITEMS = [
        "冲动消费", "争执", "拖延", "熬夜", "冒进决策", "情绪化回复", "临时改计划", "过度承诺", "分心多线", "久坐",
    ]
    DIRECTIONS = ["正东", "东南", "正南", "西南", "正西", "西北", "正北", "东北"]
    NOTES = [
        "先稳后快，利于积累信用。",
        "沟通胜于对抗，宜先听后说。",
        "适合做减法，聚焦最重要的事。",
        "贵在持续，小步也能见进展。",
        "今天适合收尾和清账，避免开太多新坑。",
    ]

    def _ganzhi_year(self, year: int) -> str:
        offset = year - 1984
        return f"{self.STEMS[offset % 10]}{self.BRANCHES[offset % 12]}"

    def _parse_date(self, date: str | None) -> datetime:
        if not date:
            return datetime.now()
        return datetime.strptime(date, "%Y-%m-%d")

    def execute(self, date: str = "") -> str:
        try:
            dt = self._parse_date(date.strip() if date else None)
        except ValueError:
            return "错误: date 格式应为 YYYY-MM-DD"

        seed = dt.year * 10000 + dt.month * 100 + dt.day
        rnd = random.Random(seed)

        yi = rnd.sample(self.YI_ITEMS, 3)
        ji = rnd.sample(self.JI_ITEMS, 3)
        cai_pos = rnd.choice(self.DIRECTIONS)
        xi_pos = rnd.choice(self.DIRECTIONS)
        note = rnd.choice(self.NOTES)

        return (
            "【今日黄历（娱乐参考）】\n"
            f"日期: {dt.strftime('%Y-%m-%d')}\n"
            f"年干支: {self._ganzhi_year(dt.year)}\n"
            f"宜: {'、'.join(yi)}\n"
            f"忌: {'、'.join(ji)}\n"
            f"财神方位: {cai_pos}\n"
            f"喜神方位: {xi_pos}\n"
            f"日签: {note}\n"
            "提示: 内容为简化文化娱乐版本，不替代专业历法。"
        )
