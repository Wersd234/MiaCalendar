# pet.py (V8.4 - 完美居中 + 开关优化版)
import sys
import os
import psutil
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QApplication,
                               QLineEdit, QTextBrowser, QPushButton, QGraphicsDropShadowEffect,
                               QMenu, QLayout, QCalendarWidget, QDialog, QToolTip)
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, Slot
from PySide6.QtGui import QPixmap, QColor, QCursor, QFont, QAction

# 引入日历 UI
from system.calendar_ui import AdvancedCalendar

# =================配置区=================
IMAGE_FOLDER = "petData"
IDLE_THRESHOLD = 60000  # 60秒无操作睡觉

EMOTION_FILES = {
    'closed': 'closed.png',
    'open': 'open.png',
    'happy': 'happy.png',
    'angry': 'angry.png',
    'shock': 'shock.png',
    'shy': 'shy.png',
    'sleep': 'sleep.png'
}

EMOTION_KEYWORDS = {
    'happy': ['哈哈', '嘿嘿', '开心', '高兴', '好耶', '喜欢', '棒', 'nice', 'lol'],
    'angry': ['生气', '可恶', '讨厌', '哼', '烦人', '滚', '怒', '不理你'],
    'shock': ['什么', '惊讶', '吓', '真的假的', '不会吧', '哇', 'wow', '?'],
    'shy': ['害羞', '脸红', '不好意思', '那个...', '哎呀']
}


class DesktopPet(QWidget):
    input_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 加载素材
        self.emotion_pixmaps = {}
        self.load_emotions()
        self.current_open_pixmap = self.emotion_pixmaps['open']

        # === 1. 主布局 (垂直) ===
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)
        self.main_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(self.main_layout)

        # 预创建气泡 (放在最下面显示)
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

        # === 2. 中间区域 (网格布局：左按钮 | 中身体 | 右占位) ===
        # 使用 Grid 布局来实现完美居中
        middle_container = QWidget()
        middle_layout = QGridLayout(middle_container)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        # middle_layout.setSpacing(0)

        # [左侧 Column 0] 工具栏 (日历按钮)
        self.toolbar_layout = QVBoxLayout()
        self.toolbar_layout.setAlignment(Qt.AlignTop)

        self.btn_calendar = QPushButton("📅")
        self.btn_calendar.setFixedSize(35, 35)
        self.btn_calendar.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_calendar.setToolTip("打开/关闭 日程表")
        self.btn_calendar.setStyleSheet("""
            QPushButton {
                background-color: #FFF0F5; border: 2px solid #FFB7C5; 
                border-radius: 17px; font-size: 16px; color: #FF69B4;
            }
            QPushButton:hover {
                background-color: #FF69B4; color: white; border: 2px solid white;
            }
        """)
        # ✅ 修改：连接到 toggle_calendar 而不是 open_calendar
        self.btn_calendar.clicked.connect(self.toggle_calendar)

        self.toolbar_layout.addWidget(self.btn_calendar)
        self.toolbar_layout.addSpacing(20)  # 稍微往下一点

        # 将工具栏放入 Grid 的 (0, 0)
        middle_layout.addLayout(self.toolbar_layout, 0, 0, Qt.AlignTop)

        # [中间 Column 1] 身体
        self.lbl_body = QLabel(self)
        self.lbl_body.setPixmap(self.emotion_pixmaps['closed'])
        self.lbl_body.setAlignment(Qt.AlignCenter)
        self.lbl_body.setCursor(QCursor(Qt.OpenHandCursor))

        # 将身体放入 Grid 的 (0, 1)，并居中
        middle_layout.addWidget(self.lbl_body, 0, 1, Qt.AlignCenter)

        # [右侧 Column 2] 空气占位符 (为了平衡左边的按钮)
        # 这是一个看不见的 Widget，宽度和按钮一样，强行把身体挤到正中间
        dummy_spacer = QWidget()
        dummy_spacer.setFixedSize(35, 35)
        # 将占位符放入 Grid 的 (0, 2)
        middle_layout.addWidget(dummy_spacer, 0, 2)

        self.main_layout.addWidget(middle_container)
        self.main_layout.addSpacing(10)

        # === 3. 底部输入区 ===
        self.input_container = QWidget()
        input_layout = QHBoxLayout();
        input_layout.setContentsMargins(5, 0, 5, 0)
        self.input_container.setLayout(input_layout)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("指令...")
        self.input_box.setFixedHeight(35)
        self.input_box.setStyleSheet(
            "QLineEdit { background-color: #FFF0F5; border: 2px solid #FF69B4; border-radius: 17px; padding: 0 15px; color: #C71585; font-family: 'Microsoft YaHei'; font-weight: bold; } QLineEdit:focus { border: 2px solid #FF1493; background-color: white; }")
        self.input_box.returnPressed.connect(self.send_message)

        self.btn_history = QPushButton("📜")
        self.btn_history.setFixedSize(35, 35);
        self.btn_history.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_history.setStyleSheet(
            "QPushButton { background-color: #FFB7C5; border: 2px solid white; border-radius: 17px; font-size: 16px; color: white; } QPushButton:hover { background-color: #FF69B4; }")
        self.btn_history.clicked.connect(self.toggle_history)

        input_layout.addWidget(self.input_box);
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

        # === 4. 气泡放到最下面 (监控) ===
        self.main_layout.addWidget(self.bubble)

        # === 状态与变量 ===
        self.is_speaking = False
        self.is_sleeping = False
        self.jump_offset = 0
        self.jump_direction = 1
        self.drag_pos = QPoint()

        self.calendar_win = None

        # 计时器
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(30)

        self.bubble_timer = QTimer(self)
        self.bubble_timer.setSingleShot(True)
        self.bubble_timer.timeout.connect(self.end_speaking)

        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self.go_to_sleep)
        self.reset_idle_timer()

        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.update_system_stats)
        self.monitor_timer.start(2000)

    # ================= 辅助逻辑 =================
    def load_emotions(self):
        for emo_name, filename in EMOTION_FILES.items():
            path = os.path.join(IMAGE_FOLDER, filename)
            if os.path.exists(path):
                pix = QPixmap(path).scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.emotion_pixmaps[emo_name] = pix
            else:
                if 'open' in self.emotion_pixmaps:
                    self.emotion_pixmaps[emo_name] = self.emotion_pixmaps['open']
        if 'closed' not in self.emotion_pixmaps: self.emotion_pixmaps['closed'] = QPixmap(280, 280)

    def detect_emotion(self, text):
        for emotion, keywords in EMOTION_KEYWORDS.items():
            for kw in keywords:
                if kw in text: return emotion
        return None

    def reset_idle_timer(self):
        if self.is_sleeping: self.wake_up()
        self.idle_timer.start(IDLE_THRESHOLD)

    def update_system_stats(self):
        if self.is_speaking or self.is_sleeping: return
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            msg = f"💻 CPU: {cpu}%  |  🧠 RAM: {mem}%"
            self.bubble.setText(msg)
            if not self.bubble.isVisible(): self.bubble.show()
        except:
            pass

    def go_to_sleep(self):
        if not self.is_speaking:
            self.is_sleeping = True
            msg = "💤 呼...呼..."
            self.bubble.setText(msg);
            self.bubble.show()
            self.append_history(msg)
            self.input_container.hide();
            self.history_box.hide();
            self.is_history_open = False
            self.btn_calendar.hide()
            QTimer.singleShot(3000, self.bubble.hide)

    def wake_up(self):
        self.is_sleeping = False
        self.bubble.hide()
        self.input_container.show()
        self.btn_calendar.show()
        self.idle_timer.start(IDLE_THRESHOLD)
        QTimer.singleShot(500, self.update_system_stats)

    def send_message(self):
        text = self.input_box.text().strip()
        if not text: return
        self.reset_idle_timer()
        if self.is_history_open: self.toggle_history()
        self.input_signal.emit(text)
        self.input_box.clear()

    def toggle_history(self):
        self.reset_idle_timer()
        if self.is_history_open:
            self.history_box.hide()
        else:
            self.history_box.show()
            sb = self.history_box.verticalScrollBar();
            sb.setValue(sb.maximum())
        self.is_history_open = not self.is_history_open

    @Slot(str)
    def append_history(self, text):
        if not text.startswith("<b>You:</b>"):
            text = f"<font color='#FF1493'><b>Mia:</b></font> {text}"
        self.history_box.append(text)
        sb = self.history_box.verticalScrollBar();
        sb.setValue(sb.maximum())

    @Slot(str)
    def show_bubble(self, text):
        self.reset_idle_timer()
        self.bubble.setText(text);
        self.bubble.show()
        self.append_history(text)
        emo = self.detect_emotion(text)
        if emo and emo in self.emotion_pixmaps:
            self.current_open_pixmap = self.emotion_pixmaps[emo]
        else:
            self.current_open_pixmap = self.emotion_pixmaps['open']
        self.set_speaking(True)
        self.bubble_timer.start(5000)

    def end_speaking(self):
        self.set_speaking(False)
        QTimer.singleShot(1000, self.update_system_stats)

    @Slot(bool)
    def set_speaking(self, status):
        self.is_speaking = status
        if status:
            self.input_container.hide();
            self.history_box.hide();
            self.is_history_open = False
        else:
            self.input_container.show()

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

    # ✅ 新增：切换日历状态 (开 <-> 关)
    def toggle_calendar(self):
        if self.calendar_win and self.calendar_win.isVisible():
            self.calendar_win.close()  # 如果开着，就关掉
        else:
            self.open_calendar()  # 如果关着，就打开

    def open_calendar(self):
        if self.calendar_win is None:
            self.calendar_win = AdvancedCalendar()
        self.calendar_win.show()
        self.calendar_win.raise_()
        self.calendar_win.activateWindow()

    # --- 鼠标事件 ---
    def mousePressEvent(self, event):
        self.reset_idle_timer()
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.pos())
            if child not in [self.input_box, self.btn_history, self.history_box, self.btn_calendar]:
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
        elif event.button() == Qt.RightButton:
            menu = QMenu(self)

            cal_act = QAction("📅 切换日程 (Toggle Calendar)", self)
            cal_act.triggered.connect(self.toggle_calendar)  # 更新为 toggle
            menu.addAction(cal_act)

            menu.addSeparator()

            quit_act = QAction("❌ 退出 (Exit)", self)
            quit_act.triggered.connect(QApplication.quit)
            menu.addAction(quit_act)

            menu.exec(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if not self.drag_pos.isNull():
                self.move(event.globalPosition().toPoint() - self.drag_pos)
                event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec())