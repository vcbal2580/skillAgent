"""
Date/time utility skill - returns current date, time, and weekday info.
"""

import time
from datetime import datetime, timezone, timedelta
from skills.base import BaseSkill


class DateTimeSkill(BaseSkill):
    name = "get_datetime"
    description = "Get the current date, time, weekday, and related info. Supports different UTC offsets."
    parameters = {
        "type": "object",
        "properties": {
            "timezone_offset": {
                "type": "integer",
                "description": "UTC offset in hours, e.g. 8 for China (CST), -5 for US Eastern. Default: 8.",
                "default": 8,
            },
        },
        "required": [],
    }

    # Weekday names indexed Monday=0 .. Sunday=6 (translated at runtime)
    WEEKDAY_KEYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def execute(self, timezone_offset: int = 8) -> str:
        from core.i18n import _
        tz = timezone(timedelta(hours=timezone_offset))
        now = datetime.now(tz)
        weekday = _(self.WEEKDAY_KEYS[now.weekday()])

        tz_name = f"UTC{'+' if timezone_offset >= 0 else ''}{timezone_offset}"

        return (
            f"Current time ({tz_name}):\n"
            f"Date: {now.strftime('%Y-%m-%d')}\n"
            f"Time: {now.strftime('%H:%M:%S')}\n"
            f"Weekday: {weekday}\n"
            f"Timestamp: {int(now.timestamp())}"
        )
