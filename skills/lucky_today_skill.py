"""
今日好运技能（娱乐向） - 生成今日幸运指数与建议。
"""

import random
from datetime import datetime
from skills.base import BaseSkill


class LuckyTodaySkill(BaseSkill):
    name = "today_luck"
    description = "生成今日好运指数、幸运色、幸运数字和行动建议（娱乐参考）。"
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "可选，姓名或昵称，用于个性化幸运结果。",
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
        rnd = random.Random(self._seed(name))
        score = rnd.randint(60, 99)
        lucky_number = rnd.randint(1, 9)
        color = rnd.choice(self.COLORS)
        direction = rnd.choice(self.DIRECTIONS)
        action = rnd.choice(self.ACTIONS)

        level = "大吉" if score >= 90 else "中吉" if score >= 75 else "小吉"
        person = name if name.strip() else "你"

        return (
            "【今日好运（娱乐参考）】\n"
            f"对象: {person}\n"
            f"好运指数: {score}/100（{level}）\n"
            f"幸运数字: {lucky_number}\n"
            f"幸运色: {color}\n"
            f"幸运方位: {direction}\n"
            f"今日建议: {action}\n"
            "提示: 结果仅供文化娱乐与自我激励。"
        )
