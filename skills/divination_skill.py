"""
Fortune divination skill (entertainment) - interprets questions using
Heavenly Stems (Tian Gan), Earthly Branches (Di Zhi), Five Elements,
and Eight Trigrams (Ba Gua).
"""

from datetime import datetime
from skills.base import BaseSkill


class DivinationSkill(BaseSkill):
    name = "fortune_divination"
    description = "Fortune divination (entertainment) - interprets a question using Heavenly Stems, Earthly Branches, Five Elements, and Eight Trigrams."
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to divine, e.g. career, relationships, finances.",
            },
            "year": {
                "type": "integer",
                "description": "Optional birth year for reference, e.g. 1996.",
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
        from core.i18n import _
        if not question.strip():
            return _("Error: question cannot be empty")

        now = datetime.now()
        current_gz = self._ganzhi_year(now.year)
        seed = self._seed(question, year)

        upper = self.GUA[seed % 8]
        lower = self.GUA[(seed // 8) % 8]
        changing_line = seed % 6 + 1

        stem = current_gz[0]
        element = self.ELEMENT_BY_STEM.get(stem, "土")

        # Element advice - Chinese cultural content; English translations available in .po
        element_advice = {
            "木": _("Expand proactively, focus on networking; plan before acting."),
            "火": _("Boost visibility and communication; seize the window of opportunity."),
            "土": _("Steady progress with execution; review and iterate."),
            "金": _("Focus on rules and efficiency; simplify."),
            "水": _("Learn and accumulate; ride the current, avoid head-on clashes."),
        }

        year_text = f"\nReference year stem-branch: {self._ganzhi_year(year)}" if year else ""

        return (
            _("【Fortune Divination (entertainment only)】") + "\n"
            f"Question: {question}\n"
            f"Current year stem-branch: {current_gz}{year_text}\n"
            f"Five-Element qi: {element}\n"
            f"Trigrams: upper {upper} / lower {lower}\n"
            f"Changing line: {changing_line}\n"
            f"Reading: {element_advice[element]}\n"
            + _("Note: For cultural entertainment and self-reflection only, not professional advice.")
        )
