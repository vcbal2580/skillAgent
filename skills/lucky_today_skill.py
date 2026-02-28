"""
Today's luck skill (entertainment) - generates a daily lucky index,
lucky colour, lucky number, and action suggestion.
"""

import random
from datetime import datetime
from skills.base import BaseSkill


class LuckyTodaySkill(BaseSkill):
    name = "today_luck"
    description = "Generate today's lucky index, lucky colour, lucky number, and action suggestion (entertainment)."
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Optional name or nickname for personalised results.",
            },
        },
        "required": [],
    }

    COLORS = ["青色", "金色", "红色", "蓝色", "绿色", "橙色", "紫色", "白色"]
    DIRECTIONS = ["正东", "东南", "正南", "西南", "正西", "西北", "正北", "东北"]
    ACTIONS = [
        "整理工位与文件，提升专注力",
        "主动沟通一个卡住的问题",
        "先完成最难的一件事",
        "复盘最近一次成功经验",
        "减少无效会议与打断",
        "学习一项新工具或技巧",
    ]

    def _seed(self, name: str) -> int:
        now = datetime.now()
        date_seed = now.year * 10000 + now.month * 100 + now.day
        return date_seed + sum(ord(ch) for ch in name)

    def execute(self, name: str = "") -> str:
        from core.i18n import _
        rnd = random.Random(self._seed(name))
        score = rnd.randint(60, 99)
        lucky_number = rnd.randint(1, 9)
        color = rnd.choice(self.COLORS)
        direction = rnd.choice(self.DIRECTIONS)
        action = rnd.choice(self.ACTIONS)

        if score >= 90:
            level = _("Great Fortune")
        elif score >= 75:
            level = _("Good Fortune")
        else:
            level = _("Mild Fortune")
        person = name if name.strip() else "you"

        return (
            _("【Today's Luck (entertainment only)】") + "\n"
            f"Subject: {person}\n"
            f"Lucky index: {score}/100 ({level})\n"
            f"Lucky number: {lucky_number}\n"
            f"Lucky colour: {color}\n"
            f"Lucky direction: {direction}\n"
            f"Today's suggestion: {action}\n"
            + _("Note: For cultural entertainment and self-motivation only.")
        )
