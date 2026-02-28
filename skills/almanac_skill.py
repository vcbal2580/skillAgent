"""
Almanac skill (entertainment) - provides a simplified daily almanac with
auspicious/inauspicious activities, lucky directions, and a daily note.
"""

import random
from datetime import datetime
from skills.base import BaseSkill


class AlmanacSkill(BaseSkill):
    name = "huangli_today"
    description = "Provide a simplified daily almanac (auspicious/inauspicious activities, directions, daily note). Supports a specific date."
    parameters = {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Optional date in YYYY-MM-DD format; defaults to today.",
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
        from core.i18n import _
        try:
            dt = self._parse_date(date.strip() if date else None)
        except ValueError:
            return _("Error: date format must be YYYY-MM-DD")

        seed = dt.year * 10000 + dt.month * 100 + dt.day
        rnd = random.Random(seed)

        yi = rnd.sample(self.YI_ITEMS, 3)
        ji = rnd.sample(self.JI_ITEMS, 3)
        cai_pos = rnd.choice(self.DIRECTIONS)
        xi_pos = rnd.choice(self.DIRECTIONS)
        note = rnd.choice(self.NOTES)

        return (
            _("【Today's Almanac (entertainment only)】") + "\n"
            f"Date: {dt.strftime('%Y-%m-%d')}\n"
            f"Year stem-branch: {self._ganzhi_year(dt.year)}\n"
            f"Auspicious: {'\u3001'.join(yi)}\n"
            f"Inauspicious: {'\u3001'.join(ji)}\n"
            f"Wealth direction: {cai_pos}\n"
            f"Joy direction: {xi_pos}\n"
            f"Daily note: {note}\n"
            + _("Note: Simplified cultural almanac for entertainment; does not replace a professional calendar.")
        )
