# 📁 src/front/calendar_ui.py
import os
import json
import requests
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QListWidget, QPushButton, QInputDialog, QMessageBox, QFrame, QLineEdit, QLayout,
                               QDialog, QDateEdit, QTimeEdit, QCheckBox, QTextEdit, QCalendarWidget, QAbstractSpinBox)
from PySide6.QtCore import Qt, QDate, Signal, QTime, QThread
from PySide6.QtGui import QColor, QFont, QCursor, QPalette, QTextCharFormat

import weather
from back.calendar_service import calendar_service

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "data", "config.json")


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
# 🌟 网络请求子线程 (防止保存事件时 UI 卡死白屏)
# ==============================================================================
class NetworkWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, api_url, event_data):
        super().__init__()
        self.api_url = api_url
        self.event_data = event_data

    def run(self):
        try:
            res = requests.post(self.api_url, json=self.event_data, timeout=5)
            if res.status_code == 200:
                self.finished.emit(True, "同步成功")
            else:
                self.finished.emit(False, f"服务器返回异常代码: {res.status_code}")
        except Exception as e:
            self.finished.emit(False, f"无法连接到大脑: {str(e)}")


# ==============================================================================
# 🌟 事件添加对话框
# ==============================================================================
class NextcloudEventDialog(QDialog):
    """1:1 还原 Nextcloud 的事件添加表单 (现代化无边框扁平版)"""

    def __init__(self, selected_date, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 520)

        self._is_dragging = False
        self.drag_pos = None

        # 根布局
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)

        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("DialogBg")

        # 🌟 终极安全版 CSS：使用纯 URL 编码的 SVG，任何系统 100% 完美加载
        self.bg_frame.setStyleSheet("""
            #DialogBg {
                background-color: #FFF0F5;
                border: 3px solid #FFB7C5;
                border-radius: 15px;
            }

            QLineEdit, QTextEdit, QDateEdit, QTimeEdit { 
                background-color: white;
                border: 1px solid #FFD1DC; 
                border-radius: 6px; 
                padding: 5px 8px; 
                color: #333; 
                font-weight: bold;
                font-size: 13px;
                min-height: 24px;
            }
            QDateEdit { padding-right: 28px; }
            QTimeEdit { padding-right: 28px; }

            QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QTimeEdit:focus {
                border: 2px solid #FF1493;
            }

            /* 🌟 日期下拉按钮及粉色下箭头 */
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                background-color: #FFF0F5;
                border-left: 1px solid #FFD1DC;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }
            QDateEdit::drop-down:hover { background-color: #FFB7C5; }
            QDateEdit::down-arrow {
                /* 经过严格 URL 编码的纯粉色 SVG */
                image: url("data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20width%3D%2716%27%20height%3D%2716%27%3E%3Cpath%20d%3D%27M3%206%20l5%205%20l5%20-5%20Z%27%20fill%3D%27%23FF1493%27%2F%3E%3C%2Fsvg%3E");
                width: 16px; height: 16px;
            }

            /* 🌟 时间微调按钮及粉色上下箭头 */
            QTimeEdit::up-button, QTimeEdit::down-button {
                subcontrol-origin: padding;
                width: 24px;
                background-color: #FFF0F5;
                border-left: 1px solid #FFD1DC;
            }
            QTimeEdit::up-button {
                subcontrol-position: top right;
                border-bottom: 1px solid #FFD1DC;
                border-top-right-radius: 5px;
            }
            QTimeEdit::down-button {
                subcontrol-position: bottom right;
                border-bottom-right-radius: 5px;
            }
            QTimeEdit::up-button:hover, QTimeEdit::down-button:hover { background-color: #FFB7C5; }

            QTimeEdit::up-arrow {
                image: url("data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20width%3D%2716%27%20height%3D%2716%27%3E%3Cpath%20d%3D%27M3%2010%20l5%20-5%20l5%205%20Z%27%20fill%3D%27%23FF1493%27%2F%3E%3C%2Fsvg%3E");
                width: 16px; height: 16px;
            }
            QTimeEdit::down-arrow {
                image: url("data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20width%3D%2716%27%20height%3D%2716%27%3E%3Cpath%20d%3D%27M3%206%20l5%205%20l5%20-5%20Z%27%20fill%3D%27%23FF1493%27%2F%3E%3C%2Fsvg%3E");
                width: 16px; height: 16px;
            }

            QLabel { color: #C71585; font-weight: bold; font-size: 13px; border: none; background: transparent; }
            QCheckBox { color: #555; font-weight: bold; font-size: 13px; }
            QCheckBox::indicator { width: 18px; height: 18px; background: white; border-radius: 4px; border: 1px solid #FFD1DC; }
            QCheckBox::indicator:checked { background: #FF1493; image: none; border: 1px solid #FF1493; }
        """)
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(20, 20, 20, 20)
        bg_layout.setSpacing(12)

        title_layout = QHBoxLayout()
        title_lbl = QLabel("📅 添加云端日程")
        title_lbl.setStyleSheet("color: #FF1493; font-size: 16px; font-weight: bold;")

        self.btn_close = QPushButton("✖")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_close.setStyleSheet(
            "QPushButton { background-color: #FFB7C5; color: white; font-weight: bold; border-radius: 14px; border: none; } QPushButton:hover { background-color: #FF1493; }")
        self.btn_close.clicked.connect(self.reject)

        title_layout.addWidget(title_lbl)
        title_layout.addStretch()
        title_layout.addWidget(self.btn_close)
        bg_layout.addLayout(title_layout)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("📝 事件标题 (Testing creation)")
        self.title_input.setStyleSheet("font-size: 14px;")
        bg_layout.addWidget(self.title_input)

        time_panel = QFrame()
        time_panel.setStyleSheet("QFrame { background-color: transparent; }")
        form_layout = QGridLayout(time_panel)
        form_layout.setContentsMargins(0, 5, 0, 5)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(10)

        # ======================================================================
        # 🚀🚀🚀 终极杀手锏：在 Python 物理层面彻底销毁日期的“幽灵按钮”！
        # ======================================================================
        self.from_date = QDateEdit(selected_date)
        self.from_date.setCalendarPopup(True)
        self.from_date.setButtonSymbols(QAbstractSpinBox.NoButtons)  # 👈 销毁 from_date 幽灵按钮

        self.from_time = QTimeEdit(QTime.currentTime())
        self.from_time.setButtonSymbols(QAbstractSpinBox.UpDownArrows)  # 👈 保留时间按钮

        self.to_date = QDateEdit(selected_date)
        self.to_date.setCalendarPopup(True)
        self.to_date.setButtonSymbols(QAbstractSpinBox.NoButtons)  # 👈 销毁 to_date 幽灵按钮

        self.to_time = QTimeEdit(QTime.currentTime().addSecs(3600))
        self.to_time.setButtonSymbols(QAbstractSpinBox.UpDownArrows)  # 👈 保留时间按钮

        # 屏蔽滚轮
        for widget in [self.from_date, self.to_date, self.from_time, self.to_time]:
            widget.wheelEvent = lambda event: event.ignore()

        for date_edit in [self.from_date, self.to_date]:
            cal = date_edit.calendarWidget()
            cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
            cal.setStyleSheet("""
                QCalendarWidget QWidget { background-color: white; }
                QCalendarWidget QTableView { selection-background-color: #FF1493; selection-color: white; outline: none; }
                QCalendarWidget QToolButton { color: #FF1493; font-weight: bold; background: transparent; border: none; }
                QCalendarWidget QToolButton:hover { background-color: #FFB7C5; color: white; border-radius: 4px; }
            """)
            fmt_weekday = QTextCharFormat()
            fmt_weekday.setForeground(QColor("#333333"))
            fmt_weekend = QTextCharFormat()
            fmt_weekend.setForeground(QColor("#FF1493"))
            for day in [Qt.Monday, Qt.Tuesday, Qt.Wednesday, Qt.Thursday, Qt.Friday]:
                cal.setWeekdayTextFormat(day, fmt_weekday)
            for day in [Qt.Saturday, Qt.Sunday]:
                cal.setWeekdayTextFormat(day, fmt_weekend)

        form_layout.addWidget(QLabel("从 (From):"), 0, 0)
        form_layout.addWidget(self.from_date, 0, 1)
        form_layout.addWidget(self.from_time, 0, 2)

        form_layout.addWidget(QLabel("到 (To):"), 1, 0)
        form_layout.addWidget(self.to_date, 1, 1)
        form_layout.addWidget(self.to_time, 1, 2)
        bg_layout.addWidget(time_panel)

        self.all_day_cb = QCheckBox(" 全天事件 (All day)")
        self.all_day_cb.stateChanged.connect(self.toggle_all_day)
        bg_layout.addWidget(self.all_day_cb)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("📍 详细位置 (Add a location)")
        bg_layout.addWidget(self.location_input)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("✏️ 添加描述信息...")
        bg_layout.addWidget(self.desc_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("✔️ 保存并同步到 Nextcloud")
        self.btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save.setStyleSheet(
            "QPushButton { background-color: #87CEFA; color: white; border-radius: 8px; padding: 10px 20px; font-weight: bold; font-size: 13px; border: none; } QPushButton:hover { background-color: #00BFFF; }")
        self.btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_save)
        bg_layout.addLayout(btn_layout)

        root_layout.addWidget(self.bg_frame)
    def toggle_all_day(self, state):
        is_checked = (state == Qt.Checked or state == 2 or state == Qt.CheckState.Checked.value)
        self.from_time.setDisabled(is_checked)
        self.to_time.setDisabled(is_checked)

    def get_data(self):
        return {
            "title": self.title_input.text().strip() or "无标题",
            "is_all_day": self.all_day_cb.isChecked(),
            "start_date": self.from_date.date().toString("yyyy-MM-dd"),
            "start_time": self.from_time.time().toString("HH:mm"),
            "end_date": self.to_date.date().toString("yyyy-MM-dd"),
            "end_time": self.to_time.time().toString("HH:mm"),
            "location": self.location_input.text().strip(),
            "desc": self.desc_input.toPlainText().strip()
        }

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and getattr(self, '_is_dragging', False) and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        self.drag_pos = None


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

        # 持有子线程对象，防止被垃圾回收
        self.network_worker = None

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

    def update_info_panel(self):
        self.lbl_selected_date.setText(self.selected_date.toString("yyyy年 M月 d日"))

        weather_data = None
        days_diff = QDate.currentDate().daysTo(self.selected_date)
        if 0 <= days_diff <= 6:
            try:
                weather_data = weather.get_detailed_weather(self.selected_date)
            except Exception as e:
                print(f"⚠️ 天气请求被中断或异常: {e}")
                weather_data = None

        is_fake_data = False
        if not weather_data or "历史平均" in weather_data.get("location", "") or "连接大脑失败" in weather_data.get(
                "location", ""):
            is_fake_data = True

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
                for e in evs:
                    time_str = e.get('time_str', '未知时间')
                    title = e.get('title', '无标题')
                    desc = e.get('desc', '')

                    item_text = f"[{time_str}] {title}"
                    if desc:
                        item_text += f"\n 📝 {desc}"
                    self.event_list.addItem(item_text)
        except Exception as e:
            print(f"渲染日历列表失败: {e}")
            self.event_list.addItem("暂无安排~☕")

    def add_event(self):
        dialog = NextcloudEventDialog(self.selected_date, self)

        if dialog.exec():
            event_data = dialog.get_data()
            api_url = f"{get_api_base()}/api/calendar"

            # 更新 UI 状态，防止重复点击
            self.btn_add.setText("⏳ 正在同步...")
            self.btn_add.setEnabled(False)

            # 启动子线程执行网络请求
            self.network_worker = NetworkWorker(api_url, event_data)
            self.network_worker.finished.connect(self.on_event_added)
            self.network_worker.start()

    def on_event_added(self, success, message):
        # 恢复按钮状态
        self.btn_add.setText("➕ 添加事件")
        self.btn_add.setEnabled(True)

        if success:
            self.populate_grid()
            self.update_info_panel()
        else:
            QMessageBox.warning(self, "同步失败", f"无法同步到云端！\n详情: {message}")

    def delete_event(self):
        row = self.event_list.currentRow()
        if row >= 0 and "暂无安排" not in self.event_list.item(row).text():
            if QMessageBox.question(self, '确认', '确定删除？', QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                calendar_service.delete_event(self.selected_date.toString("yyyy-MM-dd"), row)
                self.populate_grid()
                self.update_info_panel()

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