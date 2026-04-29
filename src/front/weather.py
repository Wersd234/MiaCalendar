# 📁 src/front/weather.py
import os
import json
import requests
from PySide6.QtCore import QDate

# === 读取配置，找到后端的地址 ===
# 当前文件在 src/front/weather.py，向上跳 2 级回到 src 目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def load_backend_url():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            host = config["backend"]["host"]
            port = config["backend"]["port"]
            if host == "0.0.0.0": host = "127.0.0.1"
            return f"http://{host}:{port}/api/weather"
    except Exception as e:
        print(f"前端天气模块加载配置失败: {e}")
        return "http://127.0.0.1:8000/api/weather"

WEATHER_API_URL = load_backend_url()

# 前端本地缓存
_LOCAL_FRONTEND_CACHE = {}

def get_detailed_weather(date_obj: QDate):
    """前端调用后端的接口获取单日天气"""
    if date_obj is None:
        date_obj = QDate.currentDate()

    date_str = date_obj.toString("yyyy-MM-dd")

    if date_str in _LOCAL_FRONTEND_CACHE:
        return _LOCAL_FRONTEND_CACHE[date_str]

    try:
        res = requests.get(WEATHER_API_URL, params={"date": date_str}, timeout=2)
        if res.status_code == 200:
            result = res.json()
            if result.get("status") == "success":
                data = result["data"]
                _LOCAL_FRONTEND_CACHE[date_str] = data
                return data
    except Exception as e:
        print(f"无法连接到大脑获取天气: {e}")

    return {
        "location": "⚠️ 连接大脑失败",
        "temp_range": "N/A", "humidity": "N/A", "wind": "N/A",
        "rain_txt": "N/A", "is_rain": False, "icon": "❓", "weather_code": 0
    }

def get_simple_weather_icon(date_obj: QDate):
    """日历界面调用，只查本地缓存"""
    date_str = date_obj.toString("yyyy-MM-dd")
    if date_str in _LOCAL_FRONTEND_CACHE:
        return _LOCAL_FRONTEND_CACHE[date_str].get("icon", "☀️")
    return "☀️"

if __name__ == "__main__":
    print("测试向后端请求天气:", get_detailed_weather(QDate.currentDate()))