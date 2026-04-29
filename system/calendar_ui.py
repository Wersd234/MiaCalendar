# system/calendar_ui.py
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                               QPushButton, QGridLayout, QFrame, QScrollArea,
                               QDialog, QListWidget, QListWidgetItem, QGraphicsDropShadowEffect,
                               QLineEdit, QTextEdit, QTimeEdit, QMenu)
from PySide6.QtCore import Qt, QDate, Signal, QTime
from PySide6.QtGui import QColor, QFont, QAction
import calendar
from datetime import datetime

# 引入业务模块
from system.calendar_service import calendar_service
from system.weather import get_simple_weather_icon, get_detailed_weather

# ================= 样式配置 =================
STYLE_PINK = """
    QWidget { font-family: 'Microsoft YaHei'; color: #333; }
    QScrollBar:vertical {
        border: none; background: #FFF0F5; width: 6px; margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #FFB7C5; min-height: 20px; border-radius: 3px;
    }
    QPushButton {
        background-color: #FFB7C5; color: white; border-radius: 5px; padding: 5px; border: none;
    }
    QPushButton:hover { background-color: #FF69B4; }

    QLabel#DateNum { font-size: 14px; font-weight: bold; border: none; background: transparent; }
    QLabel#WeatherIcon { font-size: 16px; border: none; background: transparent; }
"""


# ✅ 事件录入对话框
class EventInputDialog(QDialog):
    def __init__(self, date_str, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 380)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QDialog { background-color: white; border: 2px solid #FFB7C5; border-radius: 20px; }
            QLineEdit, QTextEdit, QTimeEdit { 
                border: 1px solid #FFB7C5; border-radius: 10px; padding: 8px; background: #FFF0F5; color: #555;
            }
            QLabel { color: #FF69B4; font-weight: bold; font-size: 13px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(QLabel(f"📅 录入日期: {date_str}"))
        layout.addWidget(QLabel("⏰ 时间:"))
        self.time_input = QTimeEdit()
        self.time_input.setTime(QTime.currentTime())
        layout.addWidget(self.time_input)
        layout.addWidget(QLabel("📝 标题:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("要做什么？")
        layout.addWidget(self.title_input)
        layout.addWidget(QLabel("📖 描述:"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("详情备忘...")
        layout.addWidget(self.desc_input)

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("确认保存")
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setStyleSheet("background-color: #DDD; color: #777;")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "time": self.time_input.time().toString("HH:mm"),
            "title": self.title_input.text().strip(),
            "desc": self.desc_input.toPlainText().strip()
        }


# ================= 单个日期格子 =================
class DayCell(QFrame):
    clicked = Signal(QDate)

    def __init__(self, date, parent=None):
        super().__init__(parent)
        self.date = date
        self.date_str = date.toString("yyyy-MM-dd")
        self.is_today = (self.date == QDate.currentDate())
        self.is_selected = False

        self.setFixedSize(100, 100)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        top_layout = QHBoxLayout()
        self.lbl_date = QLabel(str(date.day()))
        self.lbl_date.setObjectName("DateNum")
        self.lbl_date.setAlignment(Qt.AlignCenter)
        self.lbl_weather = QLabel(get_simple_weather_icon(self.date))
        self.lbl_weather.setObjectName("WeatherIcon")
        top_layout.addWidget(self.lbl_date)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_weather)
        layout.addLayout(top_layout)

        self.event_container = QVBoxLayout()
        self.event_container.setSpacing(1)
        layout.addLayout(self.event_container)
        layout.addStretch()

        self.refresh_events()
        self.update_style()

    def refresh_events(self):
        for i in reversed(range(self.event_container.count())):
            self.event_container.itemAt(i).widget().setParent(None)
        events = calendar_service.get_events(self.date_str)
        for i, e in enumerate(events):
            if i >= 2:
                lbl = QLabel("...")
                lbl.setStyleSheet("color: #999; font-size: 9px; border: none;")
                self.event_container.addWidget(lbl)
                break
            lbl = QLabel(f"• {e['title']}")
            lbl.setStyleSheet("color: #555; font-size: 10px; border: none;")
            self.event_container.addWidget(lbl)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_style()

    def update_style(self):
        inner = "border: none; background: transparent;"
        if self.is_selected:
            self.setStyleSheet("DayCell { border: 2px solid #FF69B4; background-color: #FFB7C5; border-radius: 12px; }")
            self.lbl_date.setStyleSheet(f"{inner} color: #C71585; font-weight: 900;")
        elif self.is_today:
            self.setStyleSheet("DayCell { border: 2px dashed #FF1493; background-color: #FFFFFF; border-radius: 12px; }")
            self.lbl_date.setStyleSheet(f"{inner} color: #FF1493; font-weight: bold;")
        else:
            self.setStyleSheet("DayCell { border: 2px solid #FFB7C5; background-color: #FFF0F5; border-radius: 12px; } DayCell:hover { background-color: #FFC0CB; }")
            self.lbl_date.setStyleSheet(f"{inner} color: #555;")
        self.lbl_weather.setStyleSheet(inner)

    def mousePressEvent(self, event):
        self.clicked.emit(self.date)
        super().mousePressEvent(event)


# ================= 右侧详情面板 =================
class RightDetailPanel(QWidget):
    data_changed_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedWidth(280)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.weather_box = QFrame()
        self.weather_box.setStyleSheet("QFrame { background-color: #FFF0F5; border: 2px solid #FFB7C5; border-radius: 15px; }")
        self.weather_box.setFixedHeight(210)
        wb_layout = QVBoxLayout(self.weather_box)
        self.lbl_location = QLabel("📍 --")
        self.lbl_location.setStyleSheet("color: #FF69B4; font-weight: bold;")
        self.lbl_sel_date = QLabel("---")
        self.lbl_sel_date.setAlignment(Qt.AlignCenter)
        self.lbl_sel_date.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.lbl_temp = QLabel("🌡 温度: --")
        self.lbl_rain = QLabel("🌧 降雨: --")
        self.lbl_wind = QLabel("🍃 风速: --")
        for lbl in [self.lbl_temp, self.lbl_rain, self.lbl_wind]:
            lbl.setStyleSheet("border: none; color: #555;")
        wb_layout.addWidget(self.lbl_location)
        wb_layout.addWidget(self.lbl_sel_date)
        wb_layout.addWidget(self.lbl_temp)
        wb_layout.addWidget(self.lbl_rain)
        wb_layout.addWidget(self.lbl_wind)
        wb_layout.addStretch()
        self.layout.addWidget(self.weather_box)

        self.lbl_event_title = QLabel("📅 今日安排")
        self.lbl_event_title.setStyleSheet("font-weight: bold; margin-top: 10px; color: #FF69B4; border: none;")
        self.layout.addWidget(self.lbl_event_title)

        self.event_list = QListWidget()
        self.event_list.setStyleSheet("QListWidget { background-color: #FFF0F5; border-radius: 10px; border: 2px solid #FFB7C5; padding: 5px; } QListWidget::item { border-bottom: 1px dashed #FFB7C5; padding: 5px; color: #555; }")
        # 右键菜单
        self.event_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.event_list.customContextMenuRequested.connect(self.show_context_menu)
        self.layout.addWidget(self.event_list)

        self.btn_add = QPushButton("➕ 添加事件")
        self.btn_add.clicked.connect(self.add_real_event)
        self.layout.addWidget(self.btn_add)
        self.current_date = QDate.currentDate()

    def update_info(self, date: QDate):
        self.current_date = date
        d_str = date.toString("yyyy-MM-dd")
        self.lbl_sel_date.setText(date.toString("yyyy年M月d日"))
        w_data = get_detailed_weather(date)
        self.lbl_location.setText(w_data["location"])
        self.lbl_temp.setText(f"🌡 温度: {w_data['temp_range']}")
        self.lbl_rain.setText(f"🌧 降雨: {w_data['rain_txt']}")
        self.lbl_wind.setText(f"🍃 风速: {w_data['wind']}")
        self.event_list.clear()
        events = calendar_service.get_events(d_str)
        if not events:
            self.event_list.addItem("暂无安排")
        else:
            for e in events:
                item = QListWidgetItem(f"⏰ {e['time']} - {e['title']}")
                item.setToolTip(e.get('description', ''))
                self.event_list.addItem(item)

    def show_context_menu(self, pos):
        item = self.event_list.itemAt(pos)
        if not item or item.text() == "暂无安排": return
        menu = QMenu(self)
        del_act = QAction("❌ 删除此日程", self)
        del_act.triggered.connect(lambda: self.delete_event(self.event_list.row(item)))
        menu.addAction(del_act)
        menu.exec(self.event_list.mapToGlobal(pos))

    def delete_event(self, index):
        calendar_service.delete_event(self.current_date.toString("yyyy-MM-dd"), index)
        self.update_info(self.current_date)
        self.data_changed_signal.emit()

    def add_real_event(self):
        d_str = self.current_date.toString("yyyy-MM-dd")
        dialog = EventInputDialog(d_str, self)
        if dialog.exec():
            data = dialog.get_data()
            if data["title"]:
                calendar_service.add_event(d_str, data["time"], data["title"], data["desc"])
                self.update_info(self.current_date)
                self.data_changed_signal.emit()


# ================= 主窗口类 =================
class AdvancedCalendar(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mia's Schedule")

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # ✅ 修复1：窗口加宽到 1250，保证能放下 1200 的框
        self.resize(1250, 650)

        self.bg_frame = QFrame(self)
        # ✅ 修复2：背景框加宽到 1200 (原 1100 导致内容放不下被切)
        self.bg_frame.setGeometry(0, 0, 1200, 650)
        self.bg_frame.setStyleSheet("""
            QFrame {
                background-color: #FFF0F5; 
                border-radius: 20px;
                border: 2px solid #FFB7C5;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20);
        shadow.setColor(QColor(0, 0, 0, 60));
        shadow.setOffset(0, 5)
        self.bg_frame.setGraphicsEffect(shadow)

        main_layout = QHBoxLayout(self.bg_frame)
        # ✅ 修复3：右边距 60，给关闭按钮留出绝对安全区，防止重叠
        main_layout.setContentsMargins(20, 20, 60, 20)

        # 左侧
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀ 上个月")
        self.btn_next = QPushButton("下个月 ▶")
        self.lbl_month_title = QLabel()
        self.lbl_month_title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        self.lbl_month_title.setStyleSheet("color: #333; border: none; background: transparent;")
        self.lbl_month_title.setAlignment(Qt.AlignCenter)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.lbl_month_title)
        nav_layout.addWidget(self.btn_next)
        left_layout.addLayout(nav_layout)

        # 表头
        week_layout = QHBoxLayout()
        week_layout.setSpacing(5)
        weeks = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
        for w in weeks:
            lbl = QLabel(w)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedHeight(40)
            lbl.setStyleSheet("""
                QLabel {
                    font-family: 'Microsoft YaHei';
                    font-weight: bold; color: #FF69B4;
                    border: 2px solid #FFB7C5;
                    border-radius: 12px;
                    background-color: #FFF0F5;
                }
            """)
            week_layout.addWidget(lbl)
        left_layout.addLayout(week_layout)

        # 网格
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(18)
        left_layout.addLayout(self.grid_layout)

        main_layout.addWidget(left_panel, stretch=2)

        # 右侧
        self.right_panel = RightDetailPanel()
        self.right_panel.data_changed_signal.connect(self.render_calendar)
        main_layout.addWidget(self.right_panel, stretch=1)

        # 关闭
        self.btn_close = QPushButton("×", self)
        # ✅ 修复4：按钮移动到 1155，位于右侧留白区域，不遮挡内容
        self.btn_close.setGeometry(1155, 10, 30, 30)
        self.btn_close.clicked.connect(self.hide)
        self.btn_close.setStyleSheet(
            "background-color: #FF69B4; border-radius: 15px; font-size: 18px; font-weight: bold; color: white;")

        self.current_date = QDate.currentDate()
        self.cells = []

        self.btn_prev.clicked.connect(self.prev_month)
        self.btn_next.clicked.connect(self.next_month)

        self.render_calendar()
        self.setStyleSheet(STYLE_PINK)

    def render_calendar(self):
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)
        self.cells.clear()

        self.lbl_month_title.setText(self.current_date.toString("yyyy年 M月"))

        first_day = QDate(self.current_date.year(), self.current_date.month(), 1)
        start_day_of_week = first_day.dayOfWeek()
        if start_day_of_week == 7: start_day_of_week = 0
        days_in_month = first_day.daysInMonth()

        row = 0;
        col = start_day_of_week
        for day in range(1, days_in_month + 1):
            date = QDate(self.current_date.year(), self.current_date.month(), day)
            cell = DayCell(date)
            cell.clicked.connect(self.on_date_clicked)
            self.grid_layout.addWidget(cell, row, col)
            self.cells.append(cell)
            col += 1
            if col > 6: col = 0; row += 1

        today = QDate.currentDate()
        if today.year() == self.current_date.year() and today.month() == self.current_date.month():
            self.on_date_clicked(today)
        else:
            if self.cells: self.on_date_clicked(self.cells[0].date)

    def on_date_clicked(self, date):
        self.current_date = date
        for c in self.cells:
            c.set_selected(c.date == date)
        self.right_panel.update_info(date)

    def prev_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.render_calendar()

    def next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.render_calendar()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()