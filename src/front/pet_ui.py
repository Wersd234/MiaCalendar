# 📁 src/front/pet_ui.py
import os
import psutil
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLineEdit, QTextBrowser, QPushButton, QGraphicsDropShadowEffect,
                               QMenu, QLayout, QScrollArea, QFrame)
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, Slot
from PySide6.QtGui import QPixmap, QColor, QCursor, QTextCursor, QAction, QFont

# === 🌟 绝对路径与素材配置 ===
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMAGE_FOLDER = os.path.join(PROJECT_ROOT, "asset", "pet_states")
IDLE_THRESHOLD = 60000  # 1分钟无操作进入睡眠

EMOTION_FILES = {
    'closed': 'closed.png', 'open': 'open.png', 'happy': 'happy.png',
    'angry': 'angry.png', 'shock': 'shock.png', 'shy': 'shy.png', 'sleep': 'sleep.png'
}


class DesktopPetUI(QWidget):
    # 🌟 所有的信号暴露区
    message_sent = Signal(str)
    reconnect_requested = Signal()
    weather_7d_requested = Signal()
    calendar_requested = Signal()
    anime_requested = Signal()  # 🌟 追番信号

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.is_speaking = False
        self.is_sleeping = False
        self._is_dragging = False  # 物理锁，防止幽灵拖拽
        self.jump_offset = 0
        self.jump_direction = 1
        self.drag_pos = QPoint()

        # 🌟 预加载所有表情素材
        self.emotion_pixmaps = {}
        self.load_emotions()
        # 当前活跃表情 (默认为 open.png)
        self.current_active_pixmap = self.emotion_pixmaps.get('open')

        self.init_ui()
        self.init_timers()

    def load_emotions(self):
        for emo_name, filename in EMOTION_FILES.items():
            path = os.path.join(IMAGE_FOLDER, filename)
            if os.path.exists(path):
                pix = QPixmap(path).scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.emotion_pixmaps[emo_name] = pix
            else:
                print(f"⚠️ 丢失素材: {path}")

        if 'closed' not in self.emotion_pixmaps:
            self.emotion_pixmaps['closed'] = QPixmap(280, 280)
        if 'open' not in self.emotion_pixmaps:
            self.emotion_pixmaps['open'] = self.emotion_pixmaps['closed']

    def init_ui(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)
        self.main_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(self.main_layout)

        # 气泡
        self.bubble = QLabel(self)
        self.bubble.setStyleSheet("""
            background-color: white; border: 2px solid #FFB7C5; border-radius: 15px; 
            padding: 10px; color: #555; font-family: 'Microsoft YaHei'; 
            font-size: 13px; font-weight: bold;
        """)
        self.bubble.setWordWrap(True)
        self.bubble.setAlignment(Qt.AlignCenter)
        self.bubble.hide()

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.bubble.setGraphicsEffect(shadow)

        # 身体与工具栏
        middle_container = QWidget()
        middle_layout = QHBoxLayout(middle_container)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)

        self.lbl_body = QLabel(self)
        self.lbl_body.setPixmap(self.emotion_pixmaps['closed'])
        self.lbl_body.setAlignment(Qt.AlignCenter)
        self.lbl_body.setCursor(QCursor(Qt.OpenHandCursor))
        middle_layout.addWidget(self.lbl_body, 1, Qt.AlignLeft | Qt.AlignVCenter)

        self.toolbar_container = QWidget()
        toolbar_layout = QVBoxLayout(self.toolbar_container)
        toolbar_layout.setAlignment(Qt.AlignTop)
        toolbar_layout.setContentsMargins(10, 30, 0, 0)
        toolbar_layout.setSpacing(10)

        btn_style = """
            QPushButton { 
                background-color: #FFF0F5; border: 2px solid #FFB7C5; border-radius: 17px; 
                font-size: 16px; color: #FF69B4; font-family: 'Emoji'; 
            } 
            QPushButton:hover { background-color: #FF69B4; color: white; border: 2px solid white; }
        """

        self.btn_calendar = QPushButton("📅")
        self.btn_calendar.setFixedSize(35, 35)
        self.btn_calendar.setStyleSheet(btn_style)
        self.btn_calendar.clicked.connect(self.calendar_requested.emit)

        self.btn_weather = QPushButton("🌤️")
        self.btn_weather.setFixedSize(35, 35)
        self.btn_weather.setStyleSheet(btn_style)
        self.btn_weather.clicked.connect(self.weather_7d_requested.emit)

        # 🌟 追番按钮
        self.btn_anime = QPushButton("📺")
        self.btn_anime.setFixedSize(35, 35)
        self.btn_anime.setStyleSheet(btn_style)
        self.btn_anime.clicked.connect(self.anime_requested.emit)

        toolbar_layout.addWidget(self.btn_calendar)
        toolbar_layout.addWidget(self.btn_weather)
        toolbar_layout.addWidget(self.btn_anime)  # 加入右侧工具栏
        middle_layout.addWidget(self.toolbar_container, 0, Qt.AlignRight | Qt.AlignTop)

        self.main_layout.addWidget(middle_container)

        # 输入区
        self.input_container = QWidget()
        input_layout = QHBoxLayout(self.input_container)
        input_layout.setContentsMargins(5, 0, 5, 0)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("和 Mia 聊天...")
        self.input_box.setFixedHeight(35)
        self.input_box.setStyleSheet(
            "QLineEdit { background-color: #FFF0F5; border: 2px solid #FF69B4; border-radius: 17px; padding: 0 15px; color: #C71585; font-family: 'Microsoft YaHei'; font-weight: bold; }")
        self.input_box.returnPressed.connect(self.trigger_send_message)

        self.btn_history = QPushButton("📜")
        self.btn_history.setFixedSize(35, 35)
        self.btn_history.setStyleSheet(
            "QPushButton { background-color: #FFB7C5; border: 2px solid white; border-radius: 17px; color: white; }")
        self.btn_history.clicked.connect(self.toggle_history)

        input_layout.addWidget(self.input_box)
        input_layout.addWidget(self.btn_history)
        self.main_layout.addWidget(self.input_container)

        # 历史记录
        self.history_box = QTextBrowser()
        self.history_box.setMaximumHeight(180)
        self.history_box.setStyleSheet(
            "QTextBrowser { background-color: rgba(255, 255, 255, 230); border: 2px solid #FFB7C5; border-radius: 10px; padding: 10px; color: #555; }")
        self.history_box.hide()
        self.main_layout.addWidget(self.history_box)

        self.main_layout.addWidget(self.bubble)

    def init_timers(self):
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(30)

        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self.go_to_sleep)
        self.reset_idle_timer()

        self.close_bubble_timer = QTimer(self)
        self.close_bubble_timer.setSingleShot(True)
        self.close_bubble_timer.timeout.connect(self.hide_bubble)

        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.update_system_stats)
        self.monitor_timer.start(2000)

    # ================= 🌟 以下是你之前不小心漏掉的功能函数 =================

    def show_system_message(self, text, duration=3000):
        self.reset_idle_timer()
        self.bubble.setText(text)
        self.bubble.show()
        self.append_history(f"<font color='#808080'><i>{text}</i></font>", newline=True)
        self.close_bubble_timer.start(duration)

    def set_emotion(self, emotion_name):
        if emotion_name in self.emotion_pixmaps:
            self.current_active_pixmap = self.emotion_pixmaps[emotion_name]
            if not self.is_sleeping:
                self.lbl_body.setPixmap(self.current_active_pixmap)
        else:
            self.current_active_pixmap = self.emotion_pixmaps.get('open')

    def start_ai_reply(self):
        self.reset_idle_timer()
        self.is_speaking = True
        self.bubble.setText("")
        self.bubble.show()
        self.input_container.hide()
        self.history_box.hide()

    def append_ai_text(self, text_chunk):
        self.reset_idle_timer()
        self.bubble.setText(self.bubble.text() + text_chunk)

    def finish_ai_reply(self):
        self.is_speaking = False
        self.input_container.show()
        final_text = self.bubble.text()
        if final_text:
            self.append_history(f"<font color='#FF1493'><b>Mia:</b></font> {final_text}", newline=True)
        display_time = max(5000, 3000 + len(final_text) * 200)
        self.close_bubble_timer.start(display_time)

    def hide_bubble(self):
        self.bubble.hide()
        self.current_active_pixmap = self.emotion_pixmaps.get('open')
        self.update_system_stats()

    def update_animation(self):
        if self.is_speaking:
            self.lbl_body.setPixmap(self.current_active_pixmap)
            self.jump_offset += 2 * self.jump_direction
            if self.jump_offset > 8: self.jump_direction = -1
            if self.jump_offset < 0: self.jump_direction = 1
            self.lbl_body.setContentsMargins(0, 0, 0, self.jump_offset)
            return

        if self.is_sleeping:
            self.lbl_body.setPixmap(self.emotion_pixmaps.get('sleep'))
            self.lbl_body.setContentsMargins(0, 20, 0, 0)
            return

        # 保持说话后的表情
        if self.bubble.isVisible() and self.close_bubble_timer.isActive():
            self.lbl_body.setPixmap(self.current_active_pixmap)
            self.lbl_body.setContentsMargins(0, 0, 0, 0)
            return

        self.lbl_body.setPixmap(self.emotion_pixmaps.get('closed'))
        self.lbl_body.setContentsMargins(0, 0, 0, 0)
        self.jump_offset = 0

    def update_system_stats(self):
        if self.is_speaking or self.is_sleeping or self.close_bubble_timer.isActive(): return
        try:
            cpu, mem = psutil.cpu_percent(), psutil.virtual_memory().percent
            self.bubble.setText(f"💻 CPU: {cpu}%  |  🧠 RAM: {mem}%")
            self.bubble.show()
        except:
            pass

    # 👇 刚才报错就是因为缺了这个发送消息的函数
    def trigger_send_message(self):
        text = self.input_box.text().strip()
        if not text: return
        self.reset_idle_timer()
        self.append_history(f"<b>You:</b> {text}", newline=True)
        self.input_box.clear()
        self.message_sent.emit(text)

    def append_history(self, html, newline=False):
        if newline:
            self.history_box.append(html)
        else:
            cursor = self.history_box.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertHtml(html)
        self.history_box.ensureCursorVisible()

    def reset_idle_timer(self):
        if self.is_sleeping: self.wake_up()
        self.idle_timer.start(IDLE_THRESHOLD)

    def go_to_sleep(self):
        if self.is_speaking: return
        self.is_sleeping = True
        self.bubble.setText("💤 呼...呼...")
        self.bubble.show()
        self.input_container.hide()
        self.toolbar_container.hide()
        QTimer.singleShot(3000, self.bubble.hide)

    def wake_up(self):
        self.is_sleeping = False
        self.bubble.hide()
        self.input_container.show()
        self.toolbar_container.show()
        self.idle_timer.start(IDLE_THRESHOLD)

    def toggle_history(self):
        self.history_box.setVisible(not self.history_box.isVisible())

    def mousePressEvent(self, event):
        self.reset_idle_timer()
        self._is_dragging = False
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.pos())
            if child not in [self.input_box, self.btn_history, self.history_box, self.btn_calendar, self.btn_weather,
                             self.btn_anime]:
                self._is_dragging = True
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and getattr(self, '_is_dragging', False) and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        self.drag_pos = None

    def toggle_always_on_top(self):
        """切换窗口是否置于顶层"""
        flags = self.windowFlags()

        # 检查当前是否是置顶状态
        if flags & Qt.WindowStaysOnTopHint:
            # 如果是置顶，就取消置顶
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
            self.show_system_message("已取消置顶~", 2000)
        else:
            # 如果未置顶，就加上置顶标志
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
            self.show_system_message("已永远置于顶层！", 2000)

        # Qt 的特性：修改 flags 后窗口会隐藏，必须重新 show 一下
        self.show()

    def show_context_menu(self, pos):
        menu = QMenu(self)

        # 🌟 菜单美化 CSS
        menu.setStyleSheet("""
            QMenu { 
                background-color: white; 
                border: 2px solid #FFB7C5; 
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item { 
                color: #FF1493;
                font-family: 'Microsoft YaHei';
                font-weight: bold; 
                font-size: 13px;
                padding: 8px 25px 8px 20px; 
                border-radius: 5px;
            }
            QMenu::item:selected { 
                background-color: #FFF0F5;
                color: #FF1493;
            }
            QMenu::separator {
                height: 1px;
                background-color: #FFD1DC;
                margin: 4px 10px;
            }
        """)

        # 🌟 0. 动态判断当前的置顶状态，生成对应的按钮
        is_on_top = bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
        top_text = "📌 取消置顶" if is_on_top else "📌 置于顶层"
        act_top = QAction(top_text, self)
        act_top.triggered.connect(self.toggle_always_on_top)
        menu.addAction(act_top)

        menu.addSeparator()  # 加一条粉色分割线

        # 1. 天气
        act_weather = QAction("🌤️ 七天天气预报", self)
        act_weather.triggered.connect(self.weather_7d_requested.emit)
        menu.addAction(act_weather)

        # 2. 日历
        act_cal = QAction("📅 切换日历显示", self)
        act_cal.triggered.connect(self.calendar_requested.emit)
        menu.addAction(act_cal)

        # 3. 追番
        act_anime = QAction("📺 我的追番列表", self)
        act_anime.triggered.connect(self.anime_requested.emit)
        menu.addAction(act_anime)

        # 4. 重连
        act_reconnect = QAction("🔄 重新连接大脑", self)
        act_reconnect.triggered.connect(self.reconnect_requested.emit)
        menu.addAction(act_reconnect)

        menu.addSeparator()

        # 5. 退出
        act_exit = QAction("❌ 退出程序", self)
        act_exit.triggered.connect(self.window().close)
        menu.addAction(act_exit)

        menu.exec(pos)