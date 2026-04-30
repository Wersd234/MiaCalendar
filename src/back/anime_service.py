# 📁 src/back/anime_service.py
import os
import json
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "data", "anime_list.json")


class AnimeService:
    def get_watchlist(self):
        """读取本地追番数据"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return []

    def save_watchlist(self, data):
        """保存追番数据到本地"""
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def fetch_bangumi_season(self):
        """爬取 Bangumi 当季新番"""
        try:
            headers = {'User-Agent': 'Mia-Desktop-Pet/1.0'}
            res = requests.get("https://api.bgm.tv/calendar", headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                new_season_data = []
                day_map = {"星期一": "周一", "星期二": "周二", "星期三": "周三",
                           "星期四": "周四", "星期五": "周五", "星期六": "周六", "星期日": "周日"}

                for day_info in data:
                    cn_day = day_info.get("weekday", {}).get("cn", "")
                    mapped_day = day_map.get(cn_day, "完结/不定期")
                    for item in day_info.get("items", []):
                        name = item.get("name_cn") or item.get("name")
                        if name:
                            new_season_data.append({
                                "name": name, "day": mapped_day, "time": "22:00"
                            })
                return new_season_data
        except Exception as e:
            print(f"Bangumi API 错误: {e}")
        return []


anime_service = AnimeService()