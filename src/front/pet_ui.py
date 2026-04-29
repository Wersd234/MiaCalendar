# 📁 src/front/pet_ui.py
import os
import psutil
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLineEdit, QTextBrowser, QPushButton, QGraphicsDropShadowEffect,
                               QMenu, QLayout, QScrollArea, QFrame)
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, Slot
from PySide6.QtGui import QPixmap, QColor, QCursor, QTextCursor, QAction, QFont


try:
    from system.calendar_ui import AdvancedCalendar
except ImportError:
    AdvancedCalendar = None

# === 🌟 绝对路径与配置 ===
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMAGE_FOLDER = os.path.join(PROJECT_ROOT, "asset", "pet_states")
IDLE_THRESHOLD = 60000

EMOTION_FILES = {
    'closed': 'closed.png', 'open': 'open.png', 'happy': 'happy.png',
    'angry': 'angry.png', 'shock': 'shock.png', 'shy': 'shy.png', 'sleep': 'sleep.png'
}


# ==============================================================================
# 纯净版视觉展现层 ( DesktopPetUI )
# ==============================================================================
class DesktopPetUI(QWidget):
    # 暴露信号给控制器
    message_sent = Signal(str)
    reconnect_requested = Signal()
    # 🌟 核心新增信号：请求显示 7 天天气
    weather_7d_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 🌟 状态变量必须最先定义
        self.is_speaking = False
        self.is_sleeping = False
        self.jump_offset = 0
        self.jump_direction = 1
        self.drag_pos = QPoint()
        self.calendar_win = None

        # 加载素材
        self.emotion_pixmaps = {}
        self.load_emotions()
        self.current_open_pixmap = self.emotion_pixmaps['open']

        self.init_ui()
        self.init_timers()

    def init_ui(self):
        # 主布局：垂直
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)
        self.main_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(self.main_layout)

        # 气泡
        self.bubble = QLabel(self)
        self.bubble.setStyleSheet("""
            background-color: white; border: 2px solid #FFB7C5; border-radius: 15px; 
            padding: 8px; color: #555; font-family: 'Microsoft YaHei'; 
            font-size: 12px; font-weight: bold;
        """)
        self.bubble.setWordWrap(True)
        self.bubble.setAlignment(Qt.AlignCenter)
        self.bubble.hide()
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15);
        shadow.setColor(QColor(0, 0, 0, 80));
        shadow.setOffset(0, 4)
        self.bubble.setGraphicsEffect(shadow)

        # ================= 🌟 布局核心修理：人物左，按钮右 =================
        # 使用水平布局：中身体 | 右工具栏
        middle_container = QWidget()
        middle_layout = QHBoxLayout(middle_container)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)

        # 1. 身体 (靠左对齐，占据左侧空间)
        self.lbl_body = QLabel(self)
        self.lbl_body.setPixmap(self.emotion_pixmaps['closed'])
        self.lbl_body.setAlignment(Qt.AlignCenter)
        self.lbl_body.setCursor(QCursor(Qt.OpenHandCursor))
        middle_layout.addWidget(self.lbl_body, 1, Qt.AlignLeft | Qt.AlignVCenter)

        # 2. 右侧工具栏容器 (垂直布局，靠上对齐)
        # 所有的按钮都在这里参考 image_2.png！
        self.toolbar_container = QWidget()
        self.toolbar_layout = QVBoxLayout(self.toolbar_container)
        self.toolbar_layout.setAlignment(Qt.AlignTop)  # 按钮组整体靠上
        self.toolbar_layout.setContentsMargins(10, 30, 0, 0)  # 稍微往下一点
        self.toolbar_layout.setSpacing(10)  # 按钮间隔

        # 统一的按钮风格，Emoji字体参考日历窗口风格
        btn_style = """
            QPushButton { 
                background-color: #FFF0F5; border: 2px solid #FFB7C5; border-radius: 17px; 
                font-size: 16px; color: #FF69B4; font-family: 'Emoji'; 
            } 
            QPushButton:hover { 
                background-color: #FF69B4; color: white; border: 2px solid white; 
            }
        """

        # 日历按钮
        self.btn_calendar = QPushButton("📅")
        self.btn_calendar.setFixedSize(35, 35)
        self.btn_calendar.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_calendar.setStyleSheet(btn_style)
        self.btn_calendar.clicked.connect(self.toggle_calendar)
        self.toolbar_layout.addWidget(self.btn_calendar)

        # 🌟 新增：七天天气预报按钮 (🌤️ 参考图片按钮)
        self.btn_weather = QPushButton("🌤️")
        self.btn_weather.setFixedSize(35, 35)
        self.btn_weather.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_weather.setStyleSheet(btn_style)
        # 点击后发射信号通知外部控制器
        self.btn_weather.clicked.connect(self.weather_7d_requested.emit)
        self.toolbar_layout.addWidget(self.btn_weather)

        middle_layout.addWidget(self.toolbar_container, 0, Qt.AlignRight | Qt.AlignTop)

        self.main_layout.addWidget(middle_container)
        self.main_layout.addSpacing(10)

        # 输入区
        self.input_container = QWidget()
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(5, 0, 5, 0)
        self.input_container.setLayout(input_layout)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("和 Mia 聊天...")
        self.input_box.setFixedHeight(35)
        self.input_box.setStyleSheet(
            "QLineEdit { background-color: #FFF0F5; border: 2px solid #FF69B4; border-radius: 17px; padding: 0 15px; color: #C71585; font-family: 'Microsoft YaHei'; font-weight: bold; } QLineEdit:focus { border: 2px solid #FF1493; background-color: white; }")
        self.input_box.returnPressed.connect(self.trigger_send_message)

        self.btn_history = QPushButton("📜")
        self.btn_history.setFixedSize(35, 35)
        self.btn_history.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_history.setStyleSheet(
            "QPushButton { background-color: #FFB7C5; border: 2px solid white; border-radius: 17px; font-size: 16px; color: white; } QPushButton:hover { background-color: #FF69B4; }")
        self.btn_history.clicked.connect(self.toggle_history)

        input_layout.addWidget(self.input_box)
        input_layout.addWidget(self.btn_history)
        self.main_layout.addWidget(self.input_container)

        # 历史记录
        self.history_box = QTextBrowser()
        self.history_box.setMaximumHeight(200)
        self.history_box.setStyleSheet(
            "QTextBrowser { background-color: rgba(255, 255, 255, 230); border: 2px solid #FFB7C5; border-radius: 10px; padding: 10px; font-size: 13px; color: #555; font-family: 'Microsoft YaHei'; }")
        self.history_box.hide()
        self.main_layout.addWidget(self.history_box)
        self.is_history_open = False

        self.main_layout.addWidget(self.bubble)

    def init_timers(self):
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(30)

        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self.go_to_sleep)
        self.reset_idle_timer()

        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.update_system_stats)
        self.monitor_timer.start(2000)

        self.close_bubble_timer = QTimer(self)
        self.close_bubble_timer.setSingleShot(True)
        self.close_bubble_timer.timeout.connect(self.hide_bubble)

    def load_emotions(self):
        for emo_name, filename in EMOTION_FILES.items():
            path = os.path.join(IMAGE_FOLDER, filename)
            if os.path.exists(path):
                pix = QPixmap(path).scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.emotion_pixmaps[emo_name] = pix
            else:
                if 'open' in self.emotion_pixmaps: self.emotion_pixmaps[emo_name] = self.emotion_pixmaps['open']
        if 'closed' not in self.emotion_pixmaps: self.emotion_pixmaps['closed'] = QPixmap(280, 280)

    # ================= 暴露给外部的 API 接口 =================

    def set_emotion(self, emotion_name):
        if emotion_name in self.emotion_pixmaps:
            self.current_open_pixmap = self.emotion_pixmaps[emotion_name]
        else:
            self.current_open_pixmap = self.emotion_pixmaps['open']

    def start_ai_reply(self):
        self.reset_idle_timer()
        self.is_speaking = True
        self.bubble.setText("")
        self.bubble.show()
        self.input_container.hide()
        self.history_box.hide()
        self.is_history_open = False

    def append_ai_text(self, text_chunk):
        self.reset_idle_timer()
        current_text = self.bubble.text()
        self.bubble.setText(current_text + text_chunk)

    def finish_ai_reply(self):
        self.is_speaking = False
        self.input_container.show()

        final_text = self.bubble.text()

        # 说完后一次性存入历史记录
        if final_text:
            self.append_history(f"<font color='#FF1493'><b>Mia:</b></font> {final_text}", newline=True)

        # 动态计算气泡保留时间
        text_length = len(final_text)
        display_time = max(5000, 3000 + text_length * 300)

        self.close_bubble_timer.start(display_time)
        self.set_emotion('open')

    def show_system_message(self, text, duration=3000):
        self.bubble.setText(text)
        self.bubble.show()
        # 系统提示也偷偷留存一份在历史记录里
        self.append_history(f"<font color='#808080'><i>{text}</i></font>", newline=True)
        self.close_bubble_timer.start(duration)

    def trigger_send_message(self):
        text = self.input_box.text().strip()
        if not text: return
        self.reset_idle_timer()
        self.append_history(f"<b>You:</b> {text}", newline=True)
        self.input_box.clear()
        self.message_sent.emit(text)

    # ================= 内部 UI 逻辑 =================

    def append_history(self, html_text, newline=False):
        if newline:
            self.history_box.append(html_text)
        else:
            cursor = self.history_box.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertHtml(html_text)
        self.history_box.ensureCursorVisible()

    def hide_bubble(self):
        self.update_system_stats()

    def reset_idle_timer(self):
        if self.is_sleeping: self.wake_up()
        self.idle_timer.start(IDLE_THRESHOLD)

    def go_to_sleep(self):
        if not self.is_speaking:
            self.is_sleeping = True
            msg = "💤 呼...呼..."
            self.bubble.setText(msg)
            self.bubble.show()
            self.append_history(f"<font color='#808080'><i>{msg}</i></font>", newline=True)
            self.input_container.hide()
            self.history_box.hide()
            self.is_history_open = False
            self.toolbar_container.hide()  # 睡觉藏起右侧按钮
            QTimer.singleShot(3000, self.bubble.hide)

    def wake_up(self):
        self.is_sleeping = False
        self.bubble.hide()
        self.input_container.show()
        self.toolbar_container.show()  # 唤醒显示右侧按钮
        self.idle_timer.start(IDLE_THRESHOLD)
        QTimer.singleShot(500, self.update_system_stats)

    def update_system_stats(self):
        # 修复冲突核心修复：如果气泡倒计时 isActive = True，绝不能刷新状态覆盖文字
        if self.is_speaking or self.is_sleeping or self.close_bubble_timer.isActive(): return
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            self.bubble.setText(f"💻 CPU: {cpu}%  |  🧠 RAM: {mem}%")
            if not self.bubble.isVisible(): self.bubble.show()
        except:
            pass

    def update_animation(self):
        if self.is_speaking:
            self.lbl_body.setPixmap(self.current_open_pixmap)
            self.jump_offset += 2 * self.jump_direction
            if self.jump_offset > 8: self.jump_direction = -1
            if self.jump_offset < 0: self.jump_direction = 1
            self.lbl_body.setContentsMargins(0, 0, 0, self.jump_offset)
            return
        if self.is_sleeping:
            self.lbl_body.setPixmap(self.emotion_pixmaps['sleep'])
            self.lbl_body.setContentsMargins(0, 20, 0, 0)
        else:
            self.lbl_body.setPixmap(self.emotion_pixmaps['closed'])
            self.lbl_body.setContentsMargins(0, 0, 0, 0)
            self.jump_offset = 0

    def toggle_calendar(self):
        if self.calendar_win and self.calendar_win.isVisible():
            self.calendar_win.close()
        else:
            if not AdvancedCalendar:
                self.show_system_message("⚠️ 未找到日历模块")
                return
            if self.calendar_win is None:
                self.calendar_win = AdvancedCalendar()
            self.calendar_win.show()
            self.calendar_win.raise_()
            self.calendar_win.activateWindow()

    def toggle_history(self):
        self.reset_idle_timer()
        if self.is_history_open:
            self.history_box.hide()
        else:
            self.history_box.show()
        self.is_history_open = not self.is_history_open

    def mousePressEvent(self, event):
        self.reset_idle_timer()
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.pos())
            if child not in [self.input_box, self.btn_history, self.history_box, self.btn_calendar, self.btn_weather]:
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
        elif event.button() == Qt.RightButton:
            menu = QMenu(self)

            # --- 👇 新增天气动作 👇 ---
            weather_act = QAction("🌤️ 显示近七天天气 (7-Day Forecast)", self)
            weather_act.triggered.connect(self.weather_7d_requested.emit)
            menu.addAction(weather_act)
            menu.addSeparator()

            recon_act = QAction("🔄 重新连接大脑 (Reconnect)", self)
            recon_act.triggered.connect(self.reconnect_requested.emit)
            menu.addAction(recon_act)
            menu.addSeparator()

            cal_act = QAction("📅 切换日程 (Toggle Calendar)", self)
            cal_act.triggered.connect(self.toggle_calendar)
            menu.addAction(cal_act)
            menu.addSeparator()

            quit_act = QAction("❌ 退出 (Exit)", self)
            quit_act.triggered.connect(self.window().close)  # QApplication.quit -> window().close
            menu.addAction(quit_act)

            menu.exec(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()