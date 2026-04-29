# system/calendar_service.py
import json
import os
from datetime import datetime, timedelta

DATA_FILE = "calendar.json"


class CalendarService:
    def __init__(self):
        self.events = self.load_events()

    def load_events(self):
        if not os.path.exists(DATA_FILE):
            return {}
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def save_events(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.events, f, ensure_ascii=False, indent=4)

    def get_events(self, date_str):
        """获取指定日期的事件列表"""
        return self.events.get(date_str, [])

    def add_event(self, date_str, time_str, title, desc=""):
        """添加事件"""
        if date_str not in self.events:
            self.events[date_str] = []

        self.events[date_str].append({
            "time": time_str,
            "title": title,
            "description": desc
        })
        # 按时间排序
        self.events[date_str].sort(key=lambda x: x["time"])
        self.save_events()

    def delete_event(self, date_str, index):
        """✅ 核心修复：增加删除功能"""
        if date_str in self.events:
            events_list = self.events[date_str]
            # 确保索引有效
            if 0 <= index < len(events_list):
                del events_list[index]
                # 如果该日期没事件了，清理掉 Key，保持 JSON 整洁
                if not events_list:
                    del self.events[date_str]
                self.save_events()

    def get_upcoming_events_str(self, days=3):
        """获取未来几天的日程 (供 AI 读取)"""
        upcoming = []
        today = datetime.now().date()
        for i in range(days + 1):
            d = today + timedelta(days=i)
            d_str = d.strftime("%Y-%m-%d")
            if d_str in self.events:
                for e in self.events[d_str]:
                    upcoming.append(f"[{d_str} {e['time']}] {e['title']}")
        return "\n".join(upcoming) if upcoming else "无近期安排"


# 单例实例
calendar_service = CalendarService()