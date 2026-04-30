# 📁 src/front/anime_ui.py
import os
import json
import requests
import threading
import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QMessageBox, QTabWidget,
                               QMenu, QScrollArea, QInputDialog, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor

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


class AnimeWindow(QWidget):
    api_fetch_done = Signal(list)
    watchlist_loaded = Signal(list)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(980, 550)

        self.drag_pos = None
        self.anime_data = []
        self.season_data = []
        self.api_base = get_api_base()

        self.init_ui()

        self.api_fetch_done.connect(self.on_api_fetch_done)
        self.watchlist_loaded.connect(self.on_watchlist_loaded)

        # 🌟 核心修改：初始化时，同时在后台静默拉取本地追番和网络新番库
        threading.Thread(target=self.fetch_watchlist_from_backend, daemon=True).start()
        self.fetch_season_from_backend()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.bg_frame = QFrame()
        self.bg_frame.setStyleSheet(
            "QFrame { background-color: #FFF0F5; border: 3px solid #FFB7C5; border-radius: 15px; }")
        bg_layout = QVBoxLayout(self.bg_frame)

        # === 顶部标题栏 ===
        top_layout = QHBoxLayout()
        title_lbl = QLabel("📺 Mia 的追番看板")
        title_lbl.setFont(QFont("Microsoft YaHei", 15, QFont.Bold))
        title_lbl.setStyleSheet("color: #FF1493; border: none; background: transparent;")

        # 按钮降级为手动刷新功能
        self.btn_sync = QPushButton("🔄 刷新数据")
        self.btn_sync.setStyleSheet(
            "QPushButton { background-color: #87CEFA; color: white; font-weight: bold; border-radius: 15px; padding: 5px 15px; border:none;} QPushButton:hover { background-color: #00BFFF; }")
        self.btn_sync.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_sync.clicked.connect(self.fetch_season_from_backend)

        btn_close = QPushButton("✖")
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        btn_close.setStyleSheet(
            "QPushButton { color: white; background-color: #FFB7C5; font-weight: bold; border-radius: 15px; border: none;} QPushButton:hover { background-color: #FF1493; }")
        btn_close.clicked.connect(self.hide)

        top_layout.addWidget(title_lbl)
        top_layout.addWidget(self.btn_sync)
        top_layout.addStretch()
        top_layout.addWidget(btn_close)
        bg_layout.addLayout(top_layout)

        # === 选项卡 ===
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 2px solid #FFD1DC; border-radius: 8px; background: transparent; }
            QTabBar::tab { background: #FFE4E1; color: #C71585; padding: 8px 25px; margin-right: 2px; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: bold; font-size: 13px;}
            QTabBar::tab:selected { background: #FFB7C5; color: white; }
        """)

        self.watch_board, self.watch_layouts = self.create_week_board(is_watchlist=True)
        self.season_board, self.season_layouts = self.create_week_board(is_watchlist=False)

        self.tabs.addTab(self.watch_board, "⭐ 我的追番时间表")
        self.tabs.addTab(self.season_board, "📅 本季放送全库")

        bg_layout.addWidget(self.tabs)
        bg_layout.addWidget(QLabel("💡 提示：在【我的追番】中右键卡片可修改提醒时间；在【本季放送】中右键可一键追番！",
                                   styleSheet="color:#888; border:none; font-size: 11px;"))
        self.main_layout.addWidget(self.bg_frame)

    # ================= 🌟 七天横向看板生成器 =================
    def create_week_board(self, is_watchlist=True):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(5, 5, 5, 5)

        day_layouts = {}
        days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        today_idx = datetime.datetime.now().weekday()

        for i, day in enumerate(days):
            panel = QFrame()
            if i == today_idx:
                panel.setStyleSheet(
                    "QFrame { background-color: #FFD1DC; border: 2px solid #FF1493; border-radius: 8px; }")
            else:
                panel.setStyleSheet(
                    "QFrame { background-color: rgba(255, 255, 255, 0.6); border: 1px solid #FFD1DC; border-radius: 8px; }")

            p_layout = QVBoxLayout(panel)
            p_layout.setContentsMargins(5, 5, 5, 5)

            lbl_day = QLabel()
            lbl_day.setAlignment(Qt.AlignCenter)
            if i == today_idx:
                lbl_day.setText(f"🌟 {day}")
                lbl_day.setStyleSheet(
                    "font-weight: bold; color: #FF1493; border: none; background: transparent; font-size: 15px;")
            else:
                lbl_day.setText(day)
                lbl_day.setStyleSheet(
                    "font-weight: bold; color: #C71585; border: none; background: transparent; font-size: 13px;")
            p_layout.addWidget(lbl_day)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

            content_widget = QWidget()
            content_widget.setStyleSheet("background: transparent;")
            content_layout = QVBoxLayout(content_widget)
            content_layout.setAlignment(Qt.AlignTop)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(6)

            scroll.setWidget(content_widget)
            p_layout.addWidget(scroll)

            day_layouts[day] = content_layout
            layout.addWidget(panel)

        return container, day_layouts

    # ================= 🌟 HTTP 数据交互 =================
    def fetch_watchlist_from_backend(self):
        try:
            res = requests.get(f"{self.api_base}/api/anime/watchlist", timeout=5)
            if res.status_code == 200:
                self.watchlist_loaded.emit(res.json().get("data", []))
        except:
            pass

    def on_watchlist_loaded(self, data):
        self.anime_data = data
        self.refresh_watchlist()

    def sync_watchlist_to_backend(self):
        try:
            requests.post(f"{self.api_base}/api/anime/watchlist", json=self.anime_data, timeout=5)
        except Exception as e:
            print(f"同步数据失败: {e}")

    def fetch_season_from_backend(self):
        self.btn_sync.setText("⏳ 同步中...")
        self.btn_sync.setEnabled(False)
        threading.Thread(target=self._fetch_task, daemon=True).start()

    def _fetch_task(self):
        try:
            res = requests.get(f"{self.api_base}/api/anime/bangumi", timeout=15)
            if res.status_code == 200:
                self.api_fetch_done.emit(res.json().get("data", []))
            else:
                self.api_fetch_done.emit([])
        except:
            self.api_fetch_done.emit([])

    def on_api_fetch_done(self, new_data):
        self.btn_sync.setEnabled(True)
        self.btn_sync.setText("🔄 刷新数据")
        # 🌟 修复：去除烦人的弹窗，实现无感静默更新
        if new_data:
            self.season_data = new_data
            self.refresh_seasonlist()

    # ================= 🌟 UI 卡片渲染逻辑 =================
    def clear_layouts(self, layouts_dict):
        for layout in layouts_dict.values():
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

    def refresh_watchlist(self):
        self.clear_layouts(self.watch_layouts)

        for i, anime in enumerate(self.anime_data):
            day = anime.get("day", "周一")
            if day not in self.watch_layouts: continue

            card = QFrame()
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            card.setStyleSheet("""
                QFrame { background-color: white; border: 1px solid #FFB7C5; border-radius: 6px; }
                QFrame:hover { background-color: #FFF0F5; border: 1px solid #FF1493; }
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(6, 6, 6, 6)
            c_layout.setSpacing(4)

            t_layout = QHBoxLayout()
            t_lbl = QLabel(f"⏰ {anime.get('time', '22:00')}")
            t_lbl.setStyleSheet(
                "color: #FF1493; font-size: 11px; font-weight: bold; border: none; background: transparent;")
            t_layout.addWidget(t_lbl)
            t_layout.addStretch()
            c_layout.addLayout(t_layout)

            n_lbl = QLabel(anime.get("name", ""))
            n_lbl.setWordWrap(True)
            n_lbl.setMinimumHeight(35)
            n_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            n_lbl.setStyleSheet(
                "color: #333; font-size: 12px; font-weight: bold; border: none; background: transparent;")
            c_layout.addWidget(n_lbl)

            bot_layout = QHBoxLayout()
            ep_lbl = QLabel(f"第 {anime.get('ep', 1)} 集")
            ep_lbl.setStyleSheet("color: #888; font-size: 11px; border: none; background: transparent;")

            btn_add = QPushButton("+1")
            btn_add.setFixedSize(26, 20)
            btn_add.setCursor(QCursor(Qt.PointingHandCursor))
            btn_add.setStyleSheet(
                "background-color: #FFB7C5; color: white; border-radius: 4px; font-weight: bold; font-size: 10px; border:none;")
            btn_add.clicked.connect(lambda _, idx=i: self.add_progress(idx))

            bot_layout.addWidget(ep_lbl)
            bot_layout.addStretch()
            bot_layout.addWidget(btn_add)
            c_layout.addLayout(bot_layout)

            card.setContextMenuPolicy(Qt.CustomContextMenu)
            card.customContextMenuRequested.connect(lambda pos, idx=i, c=card: self.show_watch_menu(pos, idx, c))

            self.watch_layouts[day].addWidget(card)

    def refresh_seasonlist(self):
        self.clear_layouts(self.season_layouts)

        for i, anime in enumerate(self.season_data):
            day = anime.get("day", "周一")
            if day not in self.season_layouts: continue

            card = QFrame()
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            card.setStyleSheet("""
                QFrame { background-color: #F8F8FF; border: 1px dashed #B0C4DE; border-radius: 6px; }
                QFrame:hover { background-color: #E6E6FA; border: 1px solid #87CEFA; }
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(6, 6, 6, 6)
            c_layout.setSpacing(4)

            t_layout = QHBoxLayout()
            t_lbl = QLabel(f"⏰ {anime.get('time', '未知')}")
            t_lbl.setStyleSheet(
                "color: #4682B4; font-size: 11px; font-weight: bold; border: none; background: transparent;")
            t_layout.addWidget(t_lbl)
            t_layout.addStretch()
            c_layout.addLayout(t_layout)

            n_lbl = QLabel(anime.get("name", ""))
            n_lbl.setWordWrap(True)
            n_lbl.setMinimumHeight(35)
            n_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            n_lbl.setStyleSheet(
                "color: #555; font-size: 11px; font-weight: bold; border: none; background: transparent;")
            c_layout.addWidget(n_lbl)

            card.setContextMenuPolicy(Qt.CustomContextMenu)
            card.customContextMenuRequested.connect(lambda pos, idx=i, c=card: self.show_season_menu(pos, idx, c))

            self.season_layouts[day].addWidget(card)

    # ================= 🌟 右键交互菜单 =================
    def show_watch_menu(self, pos, index, card):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: white; border: 1px solid #FFB7C5; } 
            QMenu::item { color: #555; padding: 5px 20px; }
            QMenu::item:selected { background: #FFB7C5; color: white; }
        """)
        act_time = menu.addAction("⏰ 修改提醒时间")
        act_day = menu.addAction("📅 移动到其他星期")
        menu.addSeparator()
        act_del = menu.addAction("🗑️ 删除追番")

        action = menu.exec(card.mapToGlobal(pos))
        if action == act_time:
            new_time, ok = QInputDialog.getText(self, "修改时间", "请输入新时间 (如 22:30):",
                                                text=self.anime_data[index].get("time", "22:00"))
            if ok and new_time:
                self.anime_data[index]["time"] = new_time
                self.sync_watchlist_to_backend()
                self.refresh_watchlist()
        elif action == act_day:
            days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            current_day = self.anime_data[index].get("day", "周一")
            start_idx = days.index(current_day) if current_day in days else 0
            new_day, ok = QInputDialog.getItem(self, "修改星期", "选择新的放送星期:", days, start_idx, False)
            if ok and new_day:
                self.anime_data[index]["day"] = new_day
                self.sync_watchlist_to_backend()
                self.refresh_watchlist()
        elif action == act_del:
            if QMessageBox.question(self, '确认', '确定不再追这部番了吗？',
                                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self.anime_data.pop(index)
                self.sync_watchlist_to_backend()
                self.refresh_watchlist()

    def show_season_menu(self, pos, index, card):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: white; border: 1px solid #87CEFA; } 
            QMenu::item { color: #555; padding: 5px 20px; }
            QMenu::item:selected { background: #87CEFA; color: white; }
        """)

        anime_name = self.season_data[index].get("name", "")
        anime_day = self.season_data[index].get("day", "周一")
        anime_time = self.season_data[index].get("time", "22:00")

        act_add = menu.addAction(f"➕ 将《{anime_name}》加入追番")
        if menu.exec(card.mapToGlobal(pos)) == act_add:
            for a in self.anime_data:
                if a["name"] == anime_name:
                    QMessageBox.information(self, "提示", "这部番已经在你的列表里啦！")
                    return

            self.anime_data.append({
                "name": anime_name, "day": anime_day, "time": anime_time,
                "ep": 1, "status": "正在追", "last_remind": ""
            })
            self.sync_watchlist_to_backend()
            self.refresh_watchlist()
            self.tabs.setCurrentIndex(0)

    def add_progress(self, index):
        self.anime_data[index]["ep"] = self.anime_data[index].get("ep", 1) + 1
        self.sync_watchlist_to_backend()
        self.refresh_watchlist()

    # ================= 🌟 防锁死拖动 =================
    def mousePressEvent(self, event):
        self._is_dragging = False
        if event.button() == Qt.LeftButton and event.position().y() < 60:
            child = self.childAt(event.position().toPoint())
            if isinstance(child, QPushButton) or isinstance(child, QTabWidget):
                super().mousePressEvent(event)
                return
            self._is_dragging = True
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
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