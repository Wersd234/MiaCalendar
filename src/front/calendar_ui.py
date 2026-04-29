# 📁 src/front/calendar_ui.py
import os
import json
import requests
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QListWidget, QPushButton, QInputDialog, QMessageBox, QFrame, QLineEdit, QLayout)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QFont, QCursor

import weather
from back.calendar_service import calendar_service

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "data/config.json")


def get_api_base():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            host = config["backend"]["host"]
            port = config["backend"]["port"]
            if host == "0.0.0.0": host = "127.0.0.1"
            return f"http://{host}:{port}"
    except:
        return "http://127.0.0.1:8000"


# ==============================================================================
# 🌟 自定义日期格子
# ==============================================================================
class DayCell(QFrame):
    clicked = Signal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DayCellFrame")
        self.setFixedSize(65, 65)

        self.date = QDate()
        self.is_selected = False
        self.is_today = False
        self.is_current_month = True

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(0)

        top_layout = QHBoxLayout()
        self.lbl_day = QLabel()
        self.lbl_day.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.lbl_day.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.lbl_weather = QLabel()
        self.lbl_weather.setFont(QFont("Emoji", 10))
        self.lbl_weather.setAttribute(Qt.WA_TransparentForMouseEvents)

        top_layout.addWidget(self.lbl_day, alignment=Qt.AlignLeft)
        top_layout.addWidget(self.lbl_weather, alignment=Qt.AlignRight)

        self.lbl_event = QLabel()
        self.lbl_event.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
        self.lbl_event.setAlignment(Qt.AlignCenter)
        self.lbl_event.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.main_layout.addLayout(top_layout)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.lbl_event)

    def set_data(self, date, is_current_month, weather_icon, has_event):
        self.date = date
        self.is_current_month = is_current_month
        self.is_today = (date == QDate.currentDate())
        self.lbl_day.setText(str(date.day()))
        self.lbl_weather.setText(weather_icon)
        self.lbl_event.setText("📍有安排" if has_event else "")
        self.update_style()

    def set_selected(self, selected):
        self.is_selected = selected
        self.update_style()

    def update_style(self):
        style = "background: transparent; border: none; "
        if self.is_selected:
            self.setStyleSheet("#DayCellFrame { background-color: #FFB7C5; border-radius: 10px; }")
            self.lbl_day.setStyleSheet(style + "color: white;")
            self.lbl_event.setStyleSheet(style + "color: white;")
        elif self.is_today:
            self.setStyleSheet(
                "#DayCellFrame { background-color: white; border: 2px solid #FF1493; border-radius: 10px; }")
            self.lbl_day.setStyleSheet(style + "color: #FF1493;")
            self.lbl_event.setStyleSheet(style + "color: #FF1493;")
        elif self.is_current_month:
            self.setStyleSheet(
                "#DayCellFrame { background-color: white; border: 2px solid #FFE4E1; border-radius: 10px; }")
            self.lbl_day.setStyleSheet(style + "color: #555;")
            self.lbl_event.setStyleSheet(style + "color: #FF1493;")
        else:
            self.setStyleSheet(
                "#DayCellFrame { background-color: transparent; border: 1px solid #F0F0F0; border-radius: 10px; }")
            self.lbl_day.setStyleSheet(style + "color: #CCC;")
            self.lbl_event.setStyleSheet(style + "color: #FFC0CB;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.date)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


# ==============================================================================
# 🌟 主日历窗口
# ==============================================================================
class AdvancedCalendar(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setFixedSize(850, 520)

        # 拖拽状态锁
        self.drag_pos = None
        self._is_dragging = False

        self.current_date = QDate.currentDate()
        self.selected_date = QDate.currentDate()

        self.forecast_dict = self.fetch_7d_forecast_icons()

        self.init_ui()
        self.populate_grid()
        self.update_info_panel()

    def fetch_7d_forecast_icons(self):
        try:
            url = f"{get_api_base()}/api/weather/7days"
            res = requests.get(url, timeout=2)
            if res.status_code == 200:
                data = res.json().get("data", [])
                return {day['date']: day['icon'] for day in data}
        except:
            pass
        return {}

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSizeConstraint(QLayout.SetFixedSize)

        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("MainBgFrame")
        self.bg_frame.setStyleSheet(
            "#MainBgFrame { background-color: #FFF0F5; border: 3px solid #FFB7C5; border-radius: 15px; }")

        bg_layout = QHBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(15, 15, 15, 15)
        bg_layout.setSpacing(20)

        left_panel = QVBoxLayout()
        header_layout = QHBoxLayout()
        btn_style = "QPushButton { background-color: #FFB7C5; color: white; font-weight: bold; border-radius: 5px; padding: 5px 15px; border: none; } QPushButton:hover { background-color: #FF69B4; }"

        self.btn_prev = QPushButton("◀ 上个月")
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_prev.clicked.connect(self.prev_month)

        self.lbl_month_year = QLabel()
        self.lbl_month_year.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        self.lbl_month_year.setStyleSheet("color: #555; background: transparent; border: none;")
        self.lbl_month_year.setAlignment(Qt.AlignCenter)

        self.btn_next = QPushButton("下个月 ▶")
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_next.clicked.connect(self.next_month)

        header_layout.addWidget(self.btn_prev)
        header_layout.addWidget(self.lbl_month_year, 1)
        header_layout.addWidget(self.btn_next)
        left_panel.addLayout(header_layout)

        week_layout = QHBoxLayout()
        for w in ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]:
            lbl = QLabel(w)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "color: #FF1493; font-weight: bold; background: transparent; border: none; border-bottom: 2px solid #FFD1DC; padding-bottom: 5px;")
            week_layout.addWidget(lbl)
        left_panel.addLayout(week_layout)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(8)
        self.cells = []
        for row in range(6):
            for col in range(7):
                cell = DayCell()
                cell.clicked.connect(self.on_date_selected)
                self.grid_layout.addWidget(cell, row, col)
                self.cells.append(cell)

        left_panel.addLayout(self.grid_layout)
        left_panel.addStretch()
        bg_layout.addLayout(left_panel, 6)

        right_panel = QFrame()
        right_panel.setObjectName("RightSidePanel")
        right_panel.setStyleSheet(
            "#RightSidePanel { background-color: white; border-radius: 10px; border: 2px solid #FFD1DC; }")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 10, 15, 15)

        top_right_layout = QHBoxLayout()
        top_right_layout.addStretch()
        self.btn_close = QPushButton("✖")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_close.setStyleSheet(
            "QPushButton { color: white; background-color: #FFB7C5; font-weight: bold; font-size: 14px; border-radius: 15px; border: none;} QPushButton:hover { background-color: #FF1493; }")
        self.btn_close.clicked.connect(self.close)
        top_right_layout.addWidget(self.btn_close)
        right_layout.addLayout(top_right_layout)

        self.lbl_selected_date = QLabel()
        self.lbl_selected_date.setFont(QFont("Microsoft YaHei", 15, QFont.Bold))
        self.lbl_selected_date.setStyleSheet("color: #FF1493; background: transparent; border: none;")
        self.lbl_selected_date.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.lbl_selected_date)

        self.weather_info = QLabel()
        self.weather_info.setWordWrap(True)
        right_layout.addWidget(self.weather_info)

        right_layout.addWidget(QLabel("📌 今日安排：",
                                      styleSheet="color: #C71585; font-weight: bold; background: transparent; border: none; margin-top: 10px;"))
        self.event_list = QListWidget()
        self.event_list.setStyleSheet(
            "QListWidget { border: none; background-color: white; font-size: 13px; color: #555; outline: none;} QListWidget::item { border-bottom: 1px dashed #FFE4E1; padding: 5px; } QListWidget::item:selected { background-color: #FFB7C5; color: white; border-radius: 5px; }")
        right_layout.addWidget(self.event_list)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("➕ 添加事件")
        self.btn_add.setStyleSheet(btn_style)
        self.btn_add.clicked.connect(self.add_event)

        self.btn_del = QPushButton("🗑️ 删除选中")
        self.btn_del.setStyleSheet(
            "QPushButton { background-color: #FFDAB9; color: white; font-weight: bold; border-radius: 5px; padding: 8px; border: none;} QPushButton:hover { background-color: #F4A460; }")
        self.btn_del.clicked.connect(self.delete_event)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_del)
        right_layout.addLayout(btn_layout)

        bg_layout.addWidget(right_panel, 4)
        self.main_layout.addWidget(self.bg_frame)

    def populate_grid(self):
        year, month = self.current_date.year(), self.current_date.month()
        self.lbl_month_year.setText(f"{year}年 {month}月")
        first_day = QDate(year, month, 1)
        offset = first_day.dayOfWeek() if first_day.dayOfWeek() != 7 else 0
        start_date = first_day.addDays(-offset)

        for i in range(42):
            curr = start_date.addDays(i)
            w_icon = self.forecast_dict.get(curr.toString("yyyy-MM-dd"), "")
            self.cells[i].set_data(curr, curr.month() == month, w_icon,
                                   len(calendar_service.get_events(curr.toString("yyyy-MM-dd"))) > 0)
            self.cells[i].set_selected(curr == self.selected_date)

    def on_date_selected(self, date):
        self.selected_date = date
        self.populate_grid()
        self.update_info_panel()

    def prev_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.populate_grid()

    def next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.populate_grid()

    # ================= 🌟 核心防崩补丁 =================
    def update_info_panel(self):
        self.lbl_selected_date.setText(self.selected_date.toString("yyyy年 M月 d日"))

        weather_data = None
        # 1. 严格计算日期差，只有点到“从今天算起的未来 7 天内”，才允许请求天气！
        days_diff = QDate.currentDate().daysTo(self.selected_date)
        if 0 <= days_diff <= 6:
            try:
                # 给底层的模块加上安全保护套
                weather_data = weather.get_detailed_weather(self.selected_date)
            except Exception as e:
                print(f"⚠️ 天气请求被中断或异常: {e}")
                weather_data = None

        # 2. 判断是否没有有效数据
        is_fake_data = False
        if not weather_data or "历史平均" in weather_data.get("location", "") or "连接大脑失败" in weather_data.get(
                "location", ""):
            is_fake_data = True

        # 3. 安全更新面板
        if not is_fake_data and "temp_range" in weather_data:
            self.weather_info.setStyleSheet(
                "color: #555; font-size: 13px; border: none; padding: 10px; background-color: #FFF0F5; border-radius: 8px;")
            w_text = f"{weather_data['icon']} 温度: <b>{weather_data['temp_range']}</b><br>🌧️ 降雨概率: {weather_data['rain_txt']}<br>💨 风速: {weather_data['wind']}"
            self.weather_info.setText(w_text)
        else:
            self.weather_info.setStyleSheet(
                "color: #CCC; font-size: 12px; border: none; padding: 5px; background: transparent;")
            self.weather_info.setText("☁️ 未知天气 (仅支持近7天预报)")

        self.event_list.clear()
        try:
            evs = calendar_service.get_events(self.selected_date.toString("yyyy-MM-dd"))
            if not evs:
                self.event_list.addItem("暂无安排~☕")
            else:
                for e in evs: self.event_list.addItem(f"[{e['time']}] {e['title']}\n {e['description']}")
        except Exception:
            self.event_list.addItem("暂无安排~☕")

    def add_event(self):
        t, ok1 = QInputDialog.getText(self, "时间", "时间 (如 09:00):", text="09:00")
        if not ok1 or not t.strip(): return
        tl, ok2 = QInputDialog.getText(self, "标题", "内容:")
        if not ok2 or not tl.strip(): return
        d, ok3 = QInputDialog.getText(self, "详情", "备注:")
        if ok3:
            calendar_service.add_event(self.selected_date.toString("yyyy-MM-dd"), t.strip(), tl.strip(), d.strip())
            self.populate_grid()
            self.update_info_panel()

    def delete_event(self):
        row = self.event_list.currentRow()
        if row >= 0 and "暂无安排" not in self.event_list.item(row).text():
            if QMessageBox.question(self, '确认', '确定删除？', QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                calendar_service.delete_event(self.selected_date.toString("yyyy-MM-dd"), row)
                self.populate_grid()
                self.update_info_panel()

    # ================= 🌟 手动拖拽防锁死逻辑 =================
    def mousePressEvent(self, event):
        self._is_dragging = False
        if event.button() == Qt.LeftButton:
            if event.position().y() < 70:
                child = self.childAt(event.position().toPoint())
                if isinstance(child, QPushButton):
                    super().mousePressEvent(event)
                    return
                self._is_dragging = True
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and getattr(self, '_is_dragging', False) and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        self.drag_pos = None
        super().mouseReleaseEvent(event)