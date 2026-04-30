# 📁 src/back/calendar_service.py
import os
import json
import caldav
from datetime import datetime, timedelta
from dotenv import load_dotenv

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)


class NextcloudCalendarService:
    def __init__(self):
        self.config = self.load_config()
        self.calendar = self._connect_nextcloud()

    def load_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            return {}

    def _connect_nextcloud(self):
        nc_config = self.config.get("nextcloud", {})
        url = nc_config.get("caldav_url")
        username = nc_config.get("username")
        password = os.getenv("NEXTCLOUD_PASSWORD") or nc_config.get("password", "")


        if not (url and username and password):
            print("⚠️ 未配置 Nextcloud 日历，请检查 config.json")
            return None

        try:
            # 🌟 终极修复：彻底关闭 SSL 验证
            client = caldav.DAVClient(
                url=url,
                username=username,
                password=password,
                ssl_verify_cert=False
            )

            # 强制覆盖底层请求库的验证机制 (对抗最新版 requests 的严苛限制)
            if hasattr(client, 'session'):
                client.session.verify = False

            principal = client.principal()
            calendars = principal.calendars()

            # 如果配置了特定的日历名称，就找那个，否则用获取到的第一个日历
            target_cal_name = nc_config.get("calendar_name", "Personal")

            for cal in calendars:
                if target_cal_name in cal.name:
                    print(f"✅ 成功连接到 Nextcloud 日历: {cal.name}")
                    return cal

            if calendars:
                print(f"✅ 默认连接到 Nextcloud 日历: {calendars[0].name}")
                return calendars[0]

        except Exception as e:
            print(f"❌ Nextcloud 日历连接失败，请检查网络或凭证: {e}")

        return None

    def get_events(self, date_str):
        """提供给前端日历 UI：获取指定日期的日程"""
        if not self.calendar:
            return []

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            # 搜索这一天 00:00 到第二天 00:00 的所有事件
            start = target_date
            end = target_date + timedelta(days=1)

            # expand=True 会自动展开循环/重复的日程
            events = self.calendar.search(start=start, end=end, event=True, expand=True)

            result = []
            for e in events:
                # 获取底层的 iCalendar 数据对象
                ical = e.icalendar_instance.walk("VEVENT")[0]
                title = str(ical.get('SUMMARY', '无标题'))
                desc = str(ical.get('DESCRIPTION', ''))
                uid = str(ical.get('UID', ''))

                dtstart = ical.get('DTSTART').dt

                # 判断是全天事件还是具体时间点事件
                if isinstance(dtstart, datetime):
                    time_str = dtstart.strftime("%H:%M")
                else:
                    time_str = "全天"

                result.append({
                    "title": title,
                    "time_str": time_str,
                    "desc": desc,
                    "uid": uid  # 保存 UID 以便后续精准删除
                })

            # 按照时间排序
            result.sort(key=lambda x: x["time_str"])
            return result

        except Exception as e:
            print(f"获取日程失败: {e}")
            return []

    def add_event(self, event_data: dict):
        """提供给前端：向 Nextcloud 添加包含完整字段的新日程"""
        if not self.calendar:
            return

        title = event_data.get("title", "无标题")
        is_all_day = event_data.get("is_all_day", False)
        location = event_data.get("location", "")
        desc = event_data.get("desc", "")

        start_date = event_data.get("start_date")
        start_time = event_data.get("start_time")
        end_date = event_data.get("end_date")
        end_time = event_data.get("end_time")

        try:
            if is_all_day:
                # 全天事件：不需要具体时间，只需日期。NC 规定结束日期必须是第二天。
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
                if start_dt == end_dt:
                    end_dt += timedelta(days=1)
            else:
                # 具体时间事件：拼接日期和时间
                start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
                end_dt = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")

            self.calendar.save_event(
                dtstart=start_dt,
                dtend=end_dt,
                summary=title,
                description=desc,
                location=location
            )
            print(f"✅ 成功同步完整事件到 Nextcloud: {title}")
        except Exception as e:
            print(f"❌ 添加日程失败: {e}")

    def delete_event(self, date_str, index):
        """提供给前端：删除指定日程"""
        if not self.calendar:
            return

        # 先获取这一天的事件列表，找到对应的 UID，然后通过 UID 在云端删除
        events = self.get_events(date_str)
        if 0 <= index < len(events):
            uid_to_delete = events[index].get("uid")
            if uid_to_delete:
                try:
                    event = self.calendar.event_by_uid(uid_to_delete)
                    event.delete()
                    print("✅ 成功从 Nextcloud 彻底删除日程")
                except Exception as e:
                    print(f"❌ 删除失败: {e}")

    def get_upcoming_events_str(self, days=7):
        """提供给 AI 大脑的后台轮询：提取未来日程快照"""
        if not self.calendar:
            return "未连接 Nextcloud 日历，暂无数据"

        try:
            start = datetime.now()
            end = start + timedelta(days=days)
            events = self.calendar.search(start=start, end=end, event=True, expand=True)

            if not events:
                return "未来几天没有日程安排"

            lines = []
            for e in events:
                ical = e.icalendar_instance.walk("VEVENT")[0]
                title = str(ical.get('SUMMARY', '无标题'))

                dtstart = ical.get('DTSTART').dt
                if isinstance(dtstart, datetime):
                    date_str = dtstart.strftime("%Y-%m-%d %H:%M")
                else:
                    date_str = dtstart.strftime("%Y-%m-%d") + " (全天)"

                lines.append(f"- {date_str}: {title}")

            lines.sort()
            return "\n".join(lines)

        except Exception as e:
            return f"获取云端日程失败: {e}"


# 实例化并导出，保持和以前的 import 兼容
calendar_service = NextcloudCalendarService()