"""
Weather skill - fetches real-time weather and short-range forecast.

Data sources (all free, no API key required):
  - IP geolocation : ip-api.com/json       (fallback when no city given)
  - City geocoding : nominatim.openstreetmap.org
  - Weather        : api.open-meteo.com    (WMO-standard codes, metric units)
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime

from skills.base import BaseSkill

# WMO Weather interpretation codes → Chinese description
_WMO: dict[int, str] = {
    0: "晴",
    1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "冰雾",
    51: "毛毛雨", 53: "小雨", 55: "中雨",
    56: "冻毛毛雨", 57: "冻雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻小雨", 67: "冻大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    77: "雪粒",
    80: "阵雨", 81: "中阵雨", 82: "强阵雨",
    85: "阵雪", 86: "强阵雪",
    95: "雷阵雨",
    96: "雷阵雨伴冰雹", 99: "强雷阵雨伴冰雹",
}

def _wmo(code: int | str) -> str:
    return _WMO.get(int(code), f"未知({code})")

def _get_json(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "VcbalAgent/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


class WeatherSkill(BaseSkill):
    name = "get_weather"
    description = (
        "Get current weather conditions and a multi-day forecast for any city. "
        "Use this skill for ALL weather-related questions instead of web_search."
    )
    parameters = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": (
                    "City name, e.g. 'Shenzhen', '深圳', 'Beijing', '北京'. "
                    "Omit (or pass null) to auto-detect from the user's current IP address."
                ),
            },
            "days": {
                "type": "integer",
                "description": "Number of forecast days to include (1-7). Default: 3.",
                "default": 3,
            },
        },
        "required": [],
    }

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _geolocate_by_ip() -> tuple[float, float, str]:
        """
        Return (lat, lon, display_name) inferred from the outbound IP address.
        Uses ip-api.com (free, no key, max 45 req/min).
        """
        data = _get_json("http://ip-api.com/json/?fields=status,message,lat,lon,city,regionName,country")
        if data.get("status") != "success":
            raise ValueError(f"IP geolocation failed: {data.get('message', 'unknown error')}")
        city    = data.get("city", "")
        region  = data.get("regionName", "")
        country = data.get("country", "")
        display = ", ".join(p for p in [city, region, country] if p)
        return float(data["lat"]), float(data["lon"]), display or "Unknown"

    @staticmethod
    def _geocode(city: str) -> tuple[float, float, str]:
        """Return (lat, lon, display_name) for a city string."""
        params = urllib.parse.urlencode({
            "q": city,
            "format": "json",
            "limit": 1,
            "addressdetails": 0,
        })
        url = f"https://nominatim.openstreetmap.org/search?{params}"
        data = _get_json(url)
        if not data:
            raise ValueError(f"City not found: {city!r}")
        r = data[0]
        return float(r["lat"]), float(r["lon"]), r.get("display_name", city)

    @staticmethod
    def _fetch_weather(lat: float, lon: float, days: int) -> dict:
        """Fetch weather from open-meteo."""
        params = urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "current": ",".join([
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "precipitation",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
            ]),
            "daily": ",".join([
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "wind_speed_10m_max",
            ]),
            "timezone": "auto",
            "forecast_days": min(max(days, 1), 7),
            "wind_speed_unit": "kmh",
        })
        url = f"https://api.open-meteo.com/v1/forecast?{params}"
        return _get_json(url)

    # ------------------------------------------------------------------ #
    #  Execute                                                             #
    # ------------------------------------------------------------------ #

    def execute(self, city: str | None = None, days: int = 3) -> str:  # type: ignore[override]
        try:
            # 1. Resolve location: city name → nominatim, or IP → ip-api.com
            if city:
                lat, lon, display_name = self._geocode(city)
                location_note = ""
            else:
                lat, lon, display_name = self._geolocate_by_ip()
                location_note = "  (根据 IP 推断)"

            # 2. Fetch weather
            w = self._fetch_weather(lat, lon, days)

            # 3. Format current conditions
            cur = w["current"]
            cur_time = cur.get("time", "")[:16].replace("T", " ")
            timezone = w.get("timezone", "")

            lines = [
                f"📍 {display_name.split(',')[0]}  ({lat:.2f}°N, {lon:.2f}°E){location_note}",
                f"🕐 观测时间：{cur_time}  ({timezone})",
                "",
                "━━━ 当前天气 ━━━",
                f"天气状况：{_wmo(cur['weather_code'])}",
                f"温度：{cur['temperature_2m']} °C"
                f"  体感：{cur['apparent_temperature']} °C",
                f"湿度：{cur['relative_humidity_2m']} %",
                f"风速：{cur['wind_speed_10m']} km/h",
                f"小时降水：{cur['precipitation']} mm",
                "",
                f"━━━ 未来 {days} 天预报 ━━━",
            ]

            # 4. Format daily forecast
            daily = w["daily"]
            for i in range(min(days, len(daily["time"]))):
                date_str = daily["time"][i]
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                    label = ["今天", "明天", "后天"].get(i, date_str) if i < 3 \
                            else dt.strftime("%m/%d")
                    # Quick labelfix using list indexing
                    if i == 0:
                        label = "今天"
                    elif i == 1:
                        label = "明天"
                    elif i == 2:
                        label = "后天"
                    else:
                        label = dt.strftime("%m/%d")
                except ValueError:
                    label = date_str

                desc = _wmo(daily["weather_code"][i])
                hi   = daily["temperature_2m_max"][i]
                lo   = daily["temperature_2m_min"][i]
                rain = daily["precipitation_sum"][i]
                wind = daily["wind_speed_10m_max"][i]

                lines.append(
                    f"{label}({date_str})  {desc}  "
                    f"{lo}~{hi} °C  "
                    f"雨量:{rain} mm  "
                    f"最大风速:{wind} km/h"
                )

            return "\n".join(lines)

        except Exception as e:
            return f"天气查询失败：{e}"
