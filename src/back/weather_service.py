# 📁 src/back/weather_service.py
import requests
import time
from datetime import datetime

# ================= 配置区 =================
# 墨尔本坐标 (Melbourne CBD)
LAT = -37.8136
LON = 144.9631

# 缓存：Key: "yyyy-MM-dd", Value: {"data": {...}, "timestamp": 12345}
_WEATHER_CACHE = {}
CACHE_EXPIRE_SECONDS = 600  # 缓存有效期 10 分钟


def get_weather_icon_by_code(wmo_code):
    """根据 WMO 天气代码返回Emoji图标"""
    if wmo_code in [0]: return "☀️"  # 晴朗
    if wmo_code in [1, 2, 3]: return "⛅"  # 多云/阴天
    if wmo_code in [45, 48]: return "🌫️"  # 雾
    if wmo_code in [51, 53, 55, 56, 57]: return "🌧️"  # 毛毛雨
    if wmo_code in [61, 63, 65, 66, 67]: return "🌧️"  # 降雨
    if wmo_code in [71, 73, 75, 77]: return "❄️"  # 降雪
    if wmo_code in [80, 81, 82]: return "🌦️"  # 阵雨
    if wmo_code in [95, 96, 99]: return "⛈️"  # 雷暴
    return "🌡️"


def fetch_weather_from_api(date_str: str):
    """后端核心：向 BOM 获取数据并缓存"""
    try:
        now_ts = time.time()
        # 1. 检查缓存
        if date_str in _WEATHER_CACHE:
            cached_item = _WEATHER_CACHE[date_str]
            if now_ts - cached_item["timestamp"] < CACHE_EXPIRE_SECONDS:
                return cached_item["data"]

        # 2. 判断日期范围
        today = datetime.now().date()
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        days_diff = (target - today).days

        if days_diff < -1 or days_diff > 7:
            return _generate_fake_avg_data()  # 过去/未来太久用模拟数据

        # 3. 构造 API 请求
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT,
            "longitude": LON,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
            "timezone": "Australia/Melbourne",
            "start_date": date_str,
            "end_date": date_str
        }

        # 设置超时为 5 秒，后端不怕卡顿，Timeout 放宽
        res = requests.get(url, params=params, timeout=5)
        res.raise_for_status()

        api_data = res.json()
        if "daily" not in api_data:
            return _generate_fake_avg_data()

        daily = api_data["daily"]

        # 4. 解析数据
        wmo_code = daily["weather_code"][0]
        t_max = daily["temperature_2m_max"][0]
        t_min = daily["temperature_2m_min"][0]
        rain_prob = daily["precipitation_probability_max"][0]
        rain_sum = daily["precipitation_sum"][0]

        is_rain = rain_prob > 30 or rain_sum > 1.0
        icon = get_weather_icon_by_code(wmo_code)

        final_data = {
            "location": "📍 墨尔本 (BOM实况)",
            "temp_range": f"{t_min}°C ~ {t_max}°C",
            "humidity": "N/A",
            "wind": f"{daily['wind_speed_10m_max'][0]} km/h",
            "rain_txt": f"{rain_prob}% ({rain_sum}mm)",
            "is_rain": is_rain,
            "icon": icon,
            "weather_code": wmo_code
        }

        # 5. 写入缓存并记录当前时间戳
        _WEATHER_CACHE[date_str] = {
            "data": final_data,
            "timestamp": now_ts
        }
        return final_data

    except Exception as e:
        print(f"Backend Weather API Error: {e}")
        return _generate_fake_avg_data()


def _generate_fake_avg_data():
    """备用数据：当断网或日期太远时使用"""
    return {
        "location": "📍 墨尔本 (历史平均)",
        "temp_range": "12°C ~ 22°C",
        "humidity": "60%",
        "wind": "15 km/h",
        "rain_txt": "20% (0mm)",
        "is_rain": False,
        "icon": "⛅",
        "weather_code": 3
    }


def get_ai_weather_report(date_str=None):
    """便捷入口：返回一句实时的天气文字报告（供 AI 使用）"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    data = fetch_weather_from_api(date_str)
    return f"环境实况：{data['location']} 今天的气温是 {data['temp_range']}，降雨概率 {data['rain_txt']}。"


# ================= 这里才是放 7 天预报功能的地方 =================

def fetch_7_days_forecast():
    """获取未来 7 天的天气预报"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT,
            "longitude": LON,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
            "timezone": "Australia/Melbourne",
            "forecast_days": 7
        }
        res = requests.get(url, params=params, timeout=5)
        res.raise_for_status()
        daily = res.json().get("daily", {})

        forecast_list = []
        for i in range(7):
            date_str = daily["time"][i]
            wmo_code = daily["weather_code"][i]
            t_max = daily["temperature_2m_max"][i]
            t_min = daily["temperature_2m_min"][i]
            rain_prob = daily["precipitation_probability_max"][i]

            forecast_list.append({
                "date": date_str,
                "icon": get_weather_icon_by_code(wmo_code),
                "temp_range": f"{t_min}°C ~ {t_max}°C",
                "rain_prob": f"{rain_prob}%"
            })
        return forecast_list
    except Exception as e:
        print(f"Backend 7-Day API Error: {e}")
        return []


def get_ai_7_days_report():
    """为 AI 准备的 7 天天气文字报告"""
    forecasts = fetch_7_days_forecast()
    if not forecasts:
        return "暂时无法获取天气预报数据。"

    report = "以下是墨尔本未来7天天气预报：\n"
    for f in forecasts:
        report += f"- {f['date']}: {f['icon']} 气温 {f['temp_range']}, 降雨率 {f['rain_prob']}\n"
    return report