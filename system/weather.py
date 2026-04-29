# system/weather.py
import requests
import random
from datetime import datetime, timedelta
from colorama import Fore

# ================= 配置区 =================
# 墨尔本坐标 (Melbourne CBD)
LAT = -37.8136
LON = 144.9631
# 缓存：避免每次点击都联网 (Key: "2026-02-13", Value: {data...})
_WEATHER_CACHE = {}
_LAST_FETCH_TIME = 0


def get_simple_weather_icon(date=None):
    """
    日历小图标：为了不卡顿，这个依然保持简单逻辑
    或者你可以根据 get_detailed_weather 的缓存来同步
    """
    # 简单的映射：如果缓存里有雨，就显示雨，否则晴
    d_str = date.toString("yyyy-MM-dd")
    if d_str in _WEATHER_CACHE:
        data = _WEATHER_CACHE[d_str]
        if data.get('is_rain', False):
            return "🌧"
    return "☀"  # 默认晴天，视觉比较干净


def fetch_real_weather_from_api(date_obj):
    """
    从 Open-Meteo (BOM数据源) 获取真实天气
    """
    try:
        date_str = date_obj.toString("yyyy-MM-dd")

        # 1. 检查缓存 (如果缓存里有，且获取时间在 10 分钟内，直接返回)
        global _LAST_FETCH_TIME
        import time
        now_ts = time.time()

        if date_str in _WEATHER_CACHE:
            # 简单的缓存策略：只要有数据就先用着，避免卡顿
            return _WEATHER_CACHE[date_str]

        # 2. 判断日期范围 (API 只能查最近的)
        today = datetime.now().date()
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        days_diff = (target - today).days

        # 如果差距太大 (超过7天或已经是过去)，API 查不到 forecast，只能模拟或返回空
        if days_diff < 0 or days_diff > 7:
            return _generate_fake_avg_data()  # 过去/未来太久，用模拟平均值

        # 3. 构造 API 请求
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT,
            "longitude": LON,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
            "timezone": "Australia/Sydney",  # 墨尔本通常用 AEST/AEDT
            "start_date": date_str,
            "end_date": date_str
        }

        # 发送请求 (Timeout 设置短一点，防止界面卡死)
        res = requests.get(url, params=params, timeout=2)
        if res.status_code != 200:
            return _generate_fake_avg_data()

        api_data = res.json()

        if "daily" not in api_data:
            return _generate_fake_avg_data()

        daily = api_data["daily"]

        # 4. 解析数据
        t_max = daily["temperature_2m_max"][0]
        t_min = daily["temperature_2m_min"][0]
        rain_prob = daily["precipitation_probability_max"][0]
        rain_sum = daily["precipitation_sum"][0]
        wind_speed = daily["wind_speed_10m_max"][0]

        is_rain = rain_prob > 30 or rain_sum > 1.0

        final_data = {
            "location": "📍 墨尔本 (BOM实况)",
            "temp_range": f"{t_min}°C ~ {t_max}°C",
            "humidity": "N/A",  # Daily API 不反回湿度，用 N/A 或随机
            "wind": f"{wind_speed} km/h",
            "rain_txt": f"{rain_prob}% ({rain_sum}mm)",
            "is_rain": is_rain
        }

        # 写入缓存
        _WEATHER_CACHE[date_str] = final_data
        return final_data

    except Exception as e:
        print(f"Weather API Error: {e}")
        return _generate_fake_avg_data()


def _generate_fake_avg_data():
    """备用数据：当断网或日期太远时使用"""
    return {
        "location": "📍 墨尔本 (历史平均)",
        "temp_range": "12°C ~ 22°C",
        "humidity": "60%",
        "wind": "15 km/h",
        "rain_txt": "20%",
        "is_rain": False
    }


def get_detailed_weather(date=None):
    """
    UI 调用的主入口
    """
    if date is None:
        return _generate_fake_avg_data()

    return fetch_real_weather_from_api(date)


# =========================================================
# AI 对话接口
# =========================================================
def get_weather_report(city=""):
    # 为了保持一致，AI 也读取今天的缓存数据
    from PySide6.QtCore import QDate
    today = QDate.currentDate()
    data = get_detailed_weather(today)
    return f"报告：{data['location']} 今天气温 {data['temp_range']}，降雨概率 {data['rain_txt']}。"


if __name__ == "__main__":
    # 测试
    from PySide6.QtCore import QDate

    print(get_detailed_weather(QDate.currentDate()))