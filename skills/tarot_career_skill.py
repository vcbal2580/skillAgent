"""
塔罗事业解读技能（娱乐向） - 抽牌并输出事业方向建议。
"""

import random
from datetime import datetime
from skills.base import BaseSkill


class TarotCareerSkill(BaseSkill):
    name = "tarot_career_reading"
    description = "抽取塔罗牌并提供事业方向解读（娱乐参考）。"
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "事业相关问题，例如：要不要换工作、如何升职、项目是否推进。",
            },
            "cards": {
                "type": "integer",
                "description": "抽牌数量，支持 1 或 3，默认 3。",
                "default": 3,
            },
        },
        "required": ["question"],
    }

    DECK = [
        "愚者", "魔术师", "女祭司", "女皇", "皇帝", "教皇", "恋人", "战车", "力量", "隐者", "命运之轮",
        "正义", "倒吊人", "死神", "节制", "恶魔", "高塔", "星星", "月亮", "太阳", "审判", "世界",
    ]

    CARD_MEANING_CAREER = {
        "愚者": "新机会在路上，适合尝试新方向，但要控制试错成本。",
        "魔术师": "你的资源可被整合，主动表达能力会带来机会。",
        "女祭司": "先观察信息再行动，避免被表面机会误导。",
        "女皇": "重视长期价值与可持续性，团队协作能放大成果。",
        "皇帝": "适合建立规则和权责边界，领导力是关键。",
        "教皇": "遵循流程与专业标准，适合考证或进修。",
        "恋人": "关键在选择，价值观一致比短期收益更重要。",
        "战车": "执行力强则突破快，避免多线分散。",
        "力量": "稳住情绪与节奏，软实力会成为胜负手。",
        "隐者": "需要深耕专业，先沉淀后爆发。",
        "命运之轮": "周期变化明显，抓住时机比硬拼更重要。",
        "正义": "强调公平与契约，注意合规与文档。",
        "倒吊人": "短期停滞是换视角的信号，不宜急躁。",
        "死神": "旧模式结束，新阶段开启，宜果断取舍。",
        "节制": "跨团队协同与节奏管理决定成败。",
        "恶魔": "警惕内耗和短期诱惑，守住底线。",
        "高塔": "结构性变化在即，提前准备预案。",
        "星星": "方向清晰，适合公开展示成果与愿景。",
        "月亮": "信息不完全，重要决定要二次验证。",
        "太阳": "成果可见度高，适合冲刺关键目标。",
        "审判": "复盘后再出发，过去经验会成为助力。",
        "世界": "阶段性圆满，适合升维或开启下一层级挑战。",
    }

    def _build_seed(self, question: str) -> int:
        now = datetime.now()
        daily = now.year * 10000 + now.month * 100 + now.day
        return sum(ord(c) for c in question) + daily

    def execute(self, question: str, cards: int = 3) -> str:
        if not question.strip():
            return "错误: question 不能为空"
        if cards not in (1, 3):
            cards = 3

        rnd = random.Random(self._build_seed(question))
        picked = rnd.sample(self.DECK, cards)
        orientations = [rnd.choice(["正位", "逆位"]) for _ in range(cards)]

        lines = ["【塔罗事业解读（娱乐参考）】", f"问题: {question}"]

        if cards == 1:
            card, ori = picked[0], orientations[0]
            meaning = self.CARD_MEANING_CAREER[card]
            if ori == "逆位":
                meaning = f"当前可能受阻。{meaning} 建议先解决关键阻碍后推进。"
            lines.extend([
                f"抽到: {card}（{ori}）",
                f"解读: {meaning}",
            ])
        else:
            positions = ["过去基础", "当前状态", "近期趋势"]
            for pos, card, ori in zip(positions, picked, orientations):
                meaning = self.CARD_MEANING_CAREER[card]
                if ori == "逆位":
                    meaning = f"该位置存在阻力。{meaning}"
                lines.append(f"- {pos}: {card}（{ori}）→ {meaning}")

        lines.append("建议: 优先做一件最能提升职业确定性的行动，并在一周内验证结果。")
        lines.append("提示: 结果仅供文化娱乐与自我启发，不作为专业决策依据。")
        return "\n".join(lines)
