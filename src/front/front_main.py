# 📁 src/front/front_main.py
import sys
import os
import datetime
import json
import re
import requests
from PySide6.QtWidgets import QApplication
from PySide6.QtWebSockets import QWebSocket
from PySide6.QtCore import QUrl, QObject, QTimer

from pet_ui import DesktopPetUI
from forecast_ui import ForecastWindow
from calendar_ui import AdvancedCalendar
from anime_ui import AnimeWindow  # 🌟 导入新写的追番模块

from PySide6.QtGui import QColor, QFont, QCursor, QPalette, QTextCharFormat

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


class PetAppController(QObject):
    def __init__(self):
        super().__init__()
        self.config = self.load_config()
        self.ui = DesktopPetUI()
        self.forecast_window = ForecastWindow()
        self.calendar_win = None
        self.anime_win = None  # 🌟 存放追番窗口的实例
        self.ws = QWebSocket()

        self.reconnect_timer = QTimer()
        self.reconnect_timer.setInterval(5000)
        self.reconnect_timer.timeout.connect(self.auto_reconnect_task)
        self.reconnect_attempts = 0

        # 🌟 新增：追番提醒引擎 (每 30 秒检查一次当前时间)
        self.anime_monitor_timer = QTimer()
        self.anime_monitor_timer.setInterval(30000)
        self.anime_monitor_timer.timeout.connect(self.check_anime_broadcast)

        self.is_first_chunk = True
        self.in_tag = False
        self.tag_buffer = ""

        self.connect_signals()

    def load_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 控制器加载配置失败: {e}")
            return None

    def connect_signals(self):
        self.ui.message_sent.connect(self.send_to_backend)
        self.ui.reconnect_requested.connect(self.manual_reconnect)

        self.ui.weather_7d_requested.connect(self.open_forecast_window)
        self.ui.calendar_requested.connect(self.toggle_calendar)
        self.ui.anime_requested.connect(self.toggle_anime)  # 🌟 绑定追番点击事件

        self.ws.connected.connect(self.on_ws_connected)
        self.ws.disconnected.connect(self.on_ws_disconnected)
        self.ws.textMessageReceived.connect(self.on_ws_message_received)

    def start(self):
        self.ui.show()
        if not self.config:
            self.ui.show_system_message("❌ 配置加载失败，无法启动网络。")
            return
        self.connect_ws()
        self.anime_monitor_timer.start() # 🌟 启动追番监控引擎

    # ================= 🌟 连接与重连逻辑 =================

    def connect_ws(self):
        ws_url = self.config["backend"]["ws_url"]
        self.ui.show_system_message("📡 正在呼叫大脑...")
        self.ws.open(QUrl(ws_url))

    def on_ws_connected(self):
        self.ui.show_system_message("✅ 成功连接到大脑！")
        self.reconnect_timer.stop()
        self.reconnect_attempts = 0

    def on_ws_disconnected(self):
        self.ui.show_system_message("❌ 与大脑断开连接...")
        if not self.reconnect_timer.isActive():
            self.reconnect_timer.start()

    def auto_reconnect_task(self):
        self.reconnect_attempts += 1
        self.ui.show_system_message(f"🔄 正在进行第 {self.reconnect_attempts} 次自动重连...")
        self.connect_ws()

    def manual_reconnect(self):
        self.ui.show_system_message("👉 用户发起手动重连...")
        self.reconnect_timer.stop()
        self.reconnect_attempts = 0
        self.connect_ws()

    # ================= 🌟 追番到点提醒引擎 (后端请求版) =================
    def check_anime_broadcast(self):
        """向后端请求最新数据，检查是否到了追番时间"""
        try:
            # 🌟 统一通过 API 获取数据
            host = self.config["backend"]["host"]
            port = self.config["backend"]["port"]
            api_url = f"http://{host}:{port}/api/anime/watchlist"
            res = requests.get(api_url, timeout=5)

            if res.status_code != 200:
                return
            watchlist = res.json().get("data", [])
        except:
            return

        now = datetime.datetime.now()
        week_map = {"0": "周日", "1": "周一", "2": "周二", "3": "周三", "4": "周四", "5": "周五", "6": "周六"}
        current_day = week_map[now.strftime('%w')]
        current_time = now.strftime("%H:%M")
        today_date_str = now.strftime("%Y-%m-%d")

        data_changed = False

        for anime in watchlist:
            if anime.get("status") == "正在追":
                if anime.get("day") == current_day and anime.get("time") == current_time:
                    if anime.get("last_remind") != today_date_str:
                        anime["last_remind"] = today_date_str
                        data_changed = True

                        anime_name = anime.get("name")
                        current_ep = anime.get("ep", 1)

                        trigger_prompt = (
                            f"【系统最高指令：主人关注的番剧《{anime_name}》第{current_ep}集就在刚才更新了！"
                            f"请立刻用极其兴奋的语气提醒主人！"
                            f"务必在回复最开头带上 [ACTION:happy]！】"
                        )
                        print(f"⏰ 触发追番提醒: {anime_name}")
                        self.send_to_backend(trigger_prompt)

        if data_changed:
            try:
                # 🌟 有更新时，再通过 API 发回给后端保存
                requests.post(api_url, json=watchlist, timeout=5)
                if self.anime_win and self.anime_win.isVisible():
                    self.anime_win.anime_data = watchlist
                    self.anime_win.refresh_watchlist()
            except:
                pass

    # ================= 🌟 消息处理与拦截拦截器 =================

    def send_to_backend(self, text):
        self.is_first_chunk = True
        self.in_tag = False
        self.tag_buffer = ""
        self.ws.sendTextMessage(text)

    def on_ws_message_received(self, message):
        if message == "[DONE]":
            self.ui.finish_ai_reply()
            return

        if message.startswith("[ERROR]"):
            self.ui.show_system_message(message, 5000)
            self.is_first_chunk = True
            return

        if self.is_first_chunk:
            self.ui.start_ai_reply()
            self.is_first_chunk = False

        self.process_streaming_chunk(message)

    def process_streaming_chunk(self, chunk):
        for char in chunk:
            if char == '[':
                self.in_tag = True
                self.tag_buffer = "["
            elif char == ']' and self.in_tag:
                self.tag_buffer += "]"
                self.in_tag = False
                self.execute_tag(self.tag_buffer)
                self.tag_buffer = ""
            elif self.in_tag:
                self.tag_buffer += char
            else:
                self.ui.append_ai_text(char)

    def execute_tag(self, tag_string):
        match = re.search(r'\[ACTION:([a-zA-Z0-9_]+)\]', tag_string)
        if match:
            action_name = match.group(1)
            self.ui.set_emotion(action_name)
            print(f"🎯 触发动作: {action_name}")

    # ================= 🌟 调度天气、日历、追番窗口 =================

    def open_forecast_window(self):
        self.ui.start_ai_reply()
        self.ui.show_system_message("🌤️ 正在向气象站获取预报...")

        try:
            host = self.config["backend"]["host"]
            port = self.config["backend"]["port"]
            if host == "0.0.0.0": host = "127.0.0.1"
            url = f"http://{host}:{port}/api/weather/7days"

            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                data = res.json().get("data", [])
                self.forecast_window.update_forecast(data)
                self.ui.show_system_message("✅ 气报已送达！")
                self.ui.finish_ai_reply()
            else:
                self.ui.show_system_message(f"❌ 服务器报错 ({res.status_code})")
                self.ui.finish_ai_reply()
        except Exception as e:
            print(f"获取 7 天天气出错: {e}")
            self.ui.show_system_message("❌ 连接环境大脑失败")
            self.ui.finish_ai_reply()

    def toggle_calendar(self):
        """🌟 控制器负责调度日历窗口的开关"""
        if self.calendar_win and self.calendar_win.isVisible():
            self.calendar_win.close()
        else:
            if not AdvancedCalendar:
                self.ui.show_system_message("⚠️ 未找到日历模块")
                return
            if self.calendar_win is None:
                self.calendar_win = AdvancedCalendar()
            self.calendar_win.show()
            self.calendar_win.raise_()
            self.calendar_win.activateWindow()

    def toggle_anime(self):
        """🌟 控制器负责调度追番窗口的开关"""
        if self.anime_win and self.anime_win.isVisible():
            self.anime_win.hide()
        else:
            if self.anime_win is None:
                self.anime_win = AnimeWindow()
            self.anime_win.show()
            self.anime_win.raise_()
            self.anime_win.activateWindow()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = PetAppController()
    controller.start()
    sys.exit(app.exec())