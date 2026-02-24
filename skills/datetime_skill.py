"""
Date/time utility skill - demonstrates how to add simple skills.
"""

import time
from datetime import datetime, timezone, timedelta
from skills.base import BaseSkill


class DateTimeSkill(BaseSkill):
    name = "get_datetime"
    description = "获取当前日期、时间、星期等信息，支持不同时区。"
    parameters = {
        "type": "object",
        "properties": {
            "timezone_offset": {
                "type": "integer",
                "description": "时区偏移(小时)，如中国为8，美国东部为-5。默认为8(北京时间)。",
                "default": 8,
            },
        },
        "required": [],
    }

    WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

    def execute(self, timezone_offset: int = 8) -> str:
        tz = timezone(timedelta(hours=timezone_offset))
        now = datetime.now(tz)
        weekday = self.WEEKDAY_CN[now.weekday()]

        tz_name = f"UTC{'+' if timezone_offset >= 0 else ''}{timezone_offset}"

        return (
            f"当前时间 ({tz_name}):\n"
            f"日期: {now.strftime('%Y年%m月%d日')}\n"
            f"时间: {now.strftime('%H:%M:%S')}\n"
            f"星期: {weekday}\n"
            f"时间戳: {int(now.timestamp())}"
        )
