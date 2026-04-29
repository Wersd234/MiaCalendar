# 📁 src/front/forecast_ui.py
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                               QFrame, QGraphicsDropShadowEffect, QPushButton)
from PySide6.QtCore import Qt, QDate, QPoint
from PySide6.QtGui import QFont, QColor, QCursor


class DayForecastWidget(QFrame):
    """单日天气的小部件"""

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setObjectName("DayCard")
        self.setStyleSheet("""
            #DayCard {
                background-color: white; 
                border-radius: 12px; 
                border: 2px solid #FFD1DC; 
            }
        """)
        self.setFixedHeight(75)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 5, 15, 5)
        self.main_layout.setSpacing(15)

        self.lbl_date = QLabel(self)
        self.lbl_date.setFixedWidth(80)
        self.lbl_date.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.lbl_date.setStyleSheet("color: #FF1493; background: transparent; border: none;")
        self.lbl_date.setAlignment(Qt.AlignCenter)

        self.lbl_icon = QLabel(self)
        self.lbl_icon.setFixedWidth(50)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setFont(QFont("Emoji", 26))
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")

        self.lbl_info = QLabel(self)
        self.lbl_info.setStyleSheet("color: #555; font-size: 13px; background: transparent; border: none;")
        self.lbl_info.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self.main_layout.addWidget(self.lbl_date)
        self.main_layout.addWidget(self.lbl_icon)
        self.main_layout.addWidget(self.lbl_info)

        self.set_data(data)

    def set_data(self, data):
        date_obj = QDate.fromString(data['date'], "yyyy-MM-dd")
        self.lbl_date.setText(date_obj.toString("M月d日"))
        self.lbl_icon.setText(data['icon'])
        self.lbl_info.setText(f"🌡️ 温度: <b>{data['temp_range']}</b><br>🌧️ 降雨: {data['rain_prob']}")


class ForecastWindow(QWidget):
    """七天天气预报独立窗口 (无边框版)"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌤️ 未来七天墨尔本天气预报")

        # 🌟 魔法 1：去掉边框，开启背景透明
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setFixedSize(420, 680)

        # 记录鼠标拖拽位置
        self.drag_pos = QPoint()

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        self.window_content = QWidget()
        self.window_content.setObjectName("MainContent")
        self.window_content.setStyleSheet("""
            #MainContent {
                background-color: #FFF0F5; 
                border: 3px solid #FFB7C5; 
                border-radius: 20px; 
            }
        """)
        self.content_layout = QVBoxLayout(self.window_content)
        self.content_layout.setContentsMargins(15, 15, 15, 15)

        # 🌟 魔法 2：自定义带有关闭按钮的标题栏
        title_hbox = QHBoxLayout()
        title_hbox.setContentsMargins(0, 0, 0, 0)

        # 左侧占位（为了让标题绝对居中）
        spacer_left = QLabel()
        spacer_left.setFixedWidth(30)
        title_hbox.addWidget(spacer_left)

        # 中间标题
        title_style = "color: #C71585; font-size: 18px; font-weight: bold; border: none; background: transparent;"
        self.lbl_title = QLabel("📡 墨尔本气象站预报")
        self.lbl_title.setStyleSheet(title_style)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        title_hbox.addWidget(self.lbl_title)

        # 右侧关闭按钮
        self.btn_close = QPushButton("✖")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_close.setStyleSheet("""
            QPushButton { color: #FFB7C5; font-weight: bold; font-size: 18px; border: none; background: transparent; }
            QPushButton:hover { color: #FF1493; }
        """)
        self.btn_close.clicked.connect(self.hide)  # 点击隐藏窗口
        title_hbox.addWidget(self.btn_close, 0, Qt.AlignRight)

        self.content_layout.addLayout(title_hbox)
        self.content_layout.addSpacing(10)

        self.forecast_list_layout = QVBoxLayout()
        self.forecast_list_layout.setContentsMargins(0, 0, 0, 0)
        self.forecast_list_layout.setSpacing(12)

        self.content_layout.addLayout(self.forecast_list_layout)
        self.content_layout.addStretch()
        self.main_layout.addWidget(self.window_content)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20);
        shadow.setColor(QColor(0, 0, 0, 100));
        shadow.setOffset(0, 5)
        self.window_content.setGraphicsEffect(shadow)

    def update_forecast(self, data_list):
        while self.forecast_list_layout.count():
            item = self.forecast_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for i, data in enumerate(data_list):
            day_widget = DayForecastWidget(data, self)
            self.forecast_list_layout.addWidget(day_widget)
            if i == 0:
                day_widget.lbl_date.setText(f"{day_widget.lbl_date.text()}\n(今天)")
                day_widget.lbl_date.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))

        self.show()
        self.raise_()
        self.activateWindow()

    # 🌟 魔法 3：让无边框窗口可以被鼠标拖动
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()