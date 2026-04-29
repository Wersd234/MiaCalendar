# system/app_control.py
import subprocess
import psutil
import win32gui
import win32con
import win32process
import difflib  # <--- 新增：用于模糊匹配
from colorama import Fore
from config import APP_MAP  # 确保路径引用正确


class WindowsController:
    """Jarvis 的双手：V4.0 智能纠错与增强启动版"""

    @staticmethod
    def execute(target_key):
        """
        执行主入口
        Returns: (Success: bool, AppName: str)
        """
        raw_key = target_key.lower().strip()
        final_key = raw_key

        # === 1. 智能模糊匹配 (解决 wxchat/msedge 问题) ===
        if raw_key not in APP_MAP:
            # 在配置里找最像的一个 (相似度 > 0.6)
            matches = difflib.get_close_matches(raw_key, APP_MAP.keys(), n=1, cutoff=0.6)
            if matches:
                final_key = matches[0]
                print(Fore.YELLOW + f"   [System]: '{raw_key}' 不存在，自动识别为 -> '{final_key}'")
            else:
                print(Fore.RED + f"   [System]: 未知指令 '{raw_key}'，也猜不到您想开什么。")
                return False, raw_key

        # 读取配置
        config = APP_MAP[final_key]
        process_name = config[0]
        exe_path = config[1]
        # 获取标题关键字 (如果有第3个参数)
        title_keyword = config[2] if len(config) > 2 else None

        # 显示名称 (用于语音反馈)
        display_name = title_keyword if title_keyword else final_key

        print(Fore.CYAN + f"   [System]: 正在处理 {final_key} ...")

        # === 2. 尝试寻找现有窗口 ===
        hwnd = None

        # 策略 A: 优先匹配标题 (解决 UWP 计算器、记事本等)
        if title_keyword:
            hwnd = WindowsController._find_window_by_title_keyword(title_keyword)

        # 策略 B: 如果标题没找到，且配置了有效的进程名，则查进程
        # 注意：有些配置进程名是 "FORCE_NEW_WINDOW"，这种时候就跳过查找直接启动
        if not hwnd and process_name and "FORCE" not in process_name:
            hwnd = WindowsController._find_window_by_process(process_name)

        # === 3. 执行操作 (唤醒 或 启动) ===
        if hwnd:
            success = WindowsController.focus_window(hwnd)
            return success, display_name
        else:
            print(Fore.YELLOW + f"   [System]: 未找到运行实例，准备启动新进程...")
            success = WindowsController.launch_app(exe_path)
            return success, display_name

    @staticmethod
    def launch_app(app_path):
        try:
            # 1. 清理前后空格
            clean_path = app_path.strip()

            # 2. 智能加引号
            # 如果路径里有空格，且两头没有引号，才给它加上
            if " " in clean_path and not clean_path.startswith('"'):
                final_cmd = f'"{clean_path}"'
            else:
                final_cmd = clean_path

            print(Fore.CYAN + f"   [Debug]: 最终执行指令 -> {final_cmd}")

            # 3. 启动
            subprocess.Popen(final_cmd, shell=True)
            return True

        except Exception as e:
            print(Fore.RED + f"   [Error]: 启动失败 - {e}")
            return False

    # ================= 窗口查找底层逻辑 (保持不变) =================

    @staticmethod
    def _find_window_by_title_keyword(keyword):
        """通过标题关键字找窗口"""
        target_hwnd = None

        def callback(hwnd, _):
            nonlocal target_hwnd
            if target_hwnd: return
            if win32gui.IsWindowVisible(hwnd):
                text = win32gui.GetWindowText(hwnd)
                if text and keyword.lower() in text.lower():
                    target_hwnd = hwnd

        win32gui.EnumWindows(callback, None)
        return target_hwnd

    @staticmethod
    def _find_window_by_process(process_name_keyword):
        """通过进程名找窗口"""
        target_pids = []
        # 找到所有匹配的 PID
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if process_name_keyword.lower() in proc.info['name'].lower():
                    target_pids.append(proc.info['pid'])
            except:
                pass

        if not target_pids: return None

        target_hwnd = None

        def callback(hwnd, _):
            nonlocal target_hwnd
            if target_hwnd: return
            if win32gui.IsWindowVisible(hwnd):
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid in target_pids:
                    target_hwnd = hwnd

        win32gui.EnumWindows(callback, None)
        return target_hwnd

    @staticmethod
    def focus_window(hwnd):
        """唤醒并置顶窗口"""
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shell.SendKeys('%')
            except:
                pass
            win32gui.SetForegroundWindow(hwnd)
            print(Fore.GREEN + f"   [System]: 窗口已唤醒 (Handle: {hwnd})")
            return True
        except Exception as e:
            print(Fore.RED + f"   [Warning]: 唤醒窗口受阻: {e}")
            return False