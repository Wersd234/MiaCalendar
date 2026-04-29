# 📁 src/front/front_main.py
import sys
import os
import json
import re
# 用于前端控制器请求 HTTP 接口
import requests
from PySide6.QtWidgets import QApplication
from PySide6.QtWebSockets import QWebSocket
# 导入 QTimer
from PySide6.QtCore import QUrl, QObject, QTimer

from pet_ui import DesktopPetUI
from forecast_ui import ForecastWindow

# 🌟 路径修正：向上跳2级回到 src 目录才能摸到 config.json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


class PetAppController(QObject):
    def __init__(self):
        super().__init__()
        # 1. 加载配置
        self.config = self.load_config()
        # 2. 实例化纯净的视觉层
        self.ui = DesktopPetUI()
        # 3. 🌟 核心新增：实例化 7 天天气独立窗口
        self.forecast_window = ForecastWindow()
        # 4. 实例化 WebSocket 网络层
        self.ws = QWebSocket()

        # 重连机制相关变量
        self.reconnect_timer = QTimer()
        self.reconnect_timer.setInterval(5000)  # 5秒自动重连一次
        self.reconnect_timer.timeout.connect(self.auto_reconnect_task)
        self.reconnect_attempts = 0

        self.is_first_chunk = True
        self.in_tag = False
        self.tag_buffer = ""

        # 5. 绑定信号与槽
        self.connect_signals()

    def load_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 控制器加载配置失败: {e}")
            return None

    def connect_signals(self):
        # UI 发送消息与重连信号连接
        self.ui.message_sent.connect(self.send_to_backend)
        self.ui.reconnect_requested.connect(self.manual_reconnect)

        # === 🌟 新增核心信号连接 ===
        # 当在桌宠视觉层点击“🌤️ 显示近七天天气”时
        self.ui.weather_7d_requested.connect(self.open_forecast_window)

        # WebSocket 事件连接
        self.ws.connected.connect(self.on_ws_connected)
        self.ws.disconnected.connect(self.on_ws_disconnected)
        self.ws.textMessageReceived.connect(self.on_ws_message_received)

    def start(self):
        """启动整个前端程序"""
        self.ui.show()
        if not self.config:
            self.ui.show_system_message("❌ 配置加载失败，无法启动网络。")
            return
        self.connect_ws()

    # ================= 🌟 连接与重连逻辑 =================

    def connect_ws(self):
        ws_url = self.config["backend"]["ws_url"]
        # 使用文字气泡显示正在连接
        self.ui.show_system_message("📡 正在呼叫大脑...")
        self.ws.open(QUrl(ws_url))

    def on_ws_connected(self):
        # 使用文字气泡显示连接成功
        self.ui.show_system_message("✅ 成功连接到大脑！")
        self.reconnect_timer.stop()
        self.reconnect_attempts = 0

    def on_ws_disconnected(self):
        # 使用文字气泡显示断开
        self.ui.show_system_message("❌ 与大脑断开连接...")
        if not self.reconnect_timer.isActive():
            self.reconnect_timer.start()

    def auto_reconnect_task(self):
        self.reconnect_attempts += 1
        # 使用文字气泡显示重连状态
        self.ui.show_system_message(f"🔄 正在进行第 {self.reconnect_attempts} 次自动重连...")
        self.connect_ws()

    def manual_reconnect(self):
        # 使用文字气泡显示手动重连
        self.ui.show_system_message("👉 用户发起手动重连...")
        self.reconnect_timer.stop()
        self.reconnect_attempts = 0
        self.connect_ws()

    # ================= 🌟 消息处理与拦截拦截器 (RAG拦截已删除) =================

    def send_to_backend(self, text):
        self.is_first_chunk = True
        self.in_tag = False
        self.tag_buffer = ""
        # ❌ 核心重构：删除关键词拦截 RAG 逻辑。前端只管“发”和“收”！
        # 直接通过 WebSocket 发送文字给后端
        self.ws.sendTextMessage(text)

    def on_ws_message_received(self, message):
        """接收 WebSocket 后端推过来的消息"""
        if message == "[DONE]":
            self.ui.finish_ai_reply()
            return

        if message.startswith("[ERROR]"):
            # AI报错也改用气泡显示，停留 5 秒
            self.ui.show_system_message(message, 5000)
            self.is_first_chunk = True
            return

        # 第一次收到有效字符时，让桌宠开始跳动
        if self.is_first_chunk:
            self.ui.start_ai_reply()
            self.is_first_chunk = False

        self.process_streaming_chunk(message)

    def process_streaming_chunk(self, chunk):
        """流式消息拦截器逻辑：拼括号[ACTION:smile]"""
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
        """解析并拦截标签，触发 UI 动作"""
        match = re.search(r'\[ACTION:([a-zA-Z0-9_]+)\]', tag_string)
        if match:
            action_name = match.group(1)
            # 通知 UI 切换表情
            self.ui.set_emotion(action_name)
            print(f"🎯 触发动作: {action_name}")

    # ================= 🌟 核心新增：打开天气窗口的逻辑 =================

    def open_forecast_window(self):
        """当用户在视觉层点击按钮发出信号时调用此方法"""
        self.ui.start_ai_reply()  # 让身体先跳起来
        self.ui.show_system_message("🌤️ 正在向气象站获取预报...")

        try:
            # 1. 获取并格式化后端 IP 和端口 (兼容config文件)
            host = self.config["backend"]["host"]
            port = self.config["backend"]["port"]
            # 兼容 0.0.0.0
            if host == "0.0.0.0": host = "127.0.0.1"
            url = f"http://{host}:{port}/api/weather/7days"

            # 2. 向自己本地后端发请求 (前端不涉及复杂网络，用 http 即可)
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                data = res.json().get("data", [])

                # 3. 🌟 核心操作：调用 ForecastWindow 的更新方法来弹出窗口
                # 传入数据列表，窗口会自动渲染 7 天项目
                self.forecast_window.update_forecast(data)

                self.ui.show_system_message("✅ 气报已送达！")
                # AI回复结束 (身体停止跳动)
                self.ui.finish_ai_reply()

            else:
                self.ui.show_system_message(f"❌ 服务器报错 ({res.status_code})")
                self.ui.finish_ai_reply()
        except Exception as e:
            print(f"获取 7 天天气出错: {e}")
            self.ui.show_system_message("❌ 连接环境大脑失败")
            self.ui.finish_ai_reply()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 实例化控制器并启动
    controller = PetAppController()
    controller.start()

    sys.exit(app.exec())