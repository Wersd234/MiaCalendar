import sys
import time
import threading
import queue
import ctypes
from colorama import init, Fore

# --- GUI 库 ---
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, Signal

# --- 功能模块 ---
from pet import DesktopPet
from system.app_control import WindowsController
from system.weather import get_weather_report
from system.vision import vision_system
from system.remote import run_discord_bot
# ✅ 记忆系统
from system.memory import MemorySystem
# ✅ 日历服务
from system.calendar_service import calendar_service

# 延迟加载大脑
from brain.llm import Brain


# 注意：mouth 和 ears 在下面动态加载，防止静默模式报错

# ==============================================================================
# 1. 权限自检
# ==============================================================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if not is_admin():
    # print("正在申请管理员权限...")
    # ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    # sys.exit()
    pass  # 调试期间如果嫌烦可以先把强制提权关掉，或者保留上面代码

init(autoreset=True)


# ==============================================================================
# 2. 启动菜单
# ==============================================================================
def ask_for_mode():
    print(Fore.CYAN + "==========================================")
    print(Fore.CYAN + "       JARVIS SYSTEM STARTUP MENU")
    print(Fore.CYAN + "==========================================")
    print(Fore.WHITE + "请选择运行模式：")
    print(Fore.GREEN + "  [1] 全功能语音模式 (有声音 + 有气泡 + 听筒)")
    print(Fore.YELLOW + "  [2] 静默文字模式   (无声音 + 仅气泡 + 仅打字)")
    print(Fore.RED + "  [3] 仅安保模式     (视觉 + Discord)")
    print(Fore.CYAN + "------------------------------------------")

    return False, True  # 强制返回：Voice=Off, Brain=On (静默模式)


# 获取全局配置
VOICE_MODE, BRAIN_MODE = ask_for_mode()

# 按需导入语音模块
Mouth = None
Ears = None
if VOICE_MODE:
    from system.mouth import Mouth
    from system.ears import Ears


# ==============================================================================
# 3. 后台工作线程
# ==============================================================================
class JarvisWorker(QThread):
    speaking_signal = Signal(bool)  # 控制嘴巴/动作状态
    bubble_signal = Signal(str)  # 控制气泡内容
    calendar_signal = Signal()  # ✅ 新增：日历控制信号

    def __init__(self):
        super().__init__()
        self.running = True
        self.msg_queue = queue.Queue()

        self.brain = None
        self.mouth = None
        self.ears = None
        self.memory = None

    def put_message(self, text):
        """GUI 线程把文字传给后台线程的入口"""
        self.msg_queue.put(text)

    def run(self):
        # --- 初始化 ---
        threading.Thread(target=run_discord_bot, daemon=True).start()
        vision_system.start_monitoring()

        if BRAIN_MODE:
            print(Fore.CYAN + "   [System]: 初始化大脑...")
            self.brain = Brain()

            # ✅ 初始化记忆系统
            print(Fore.CYAN + "   [System]: 读取长期记忆库...")
            self.memory = MemorySystem()

            if VOICE_MODE:
                print(Fore.CYAN + "   [System]: 初始化语音模块...")
                self.mouth = Mouth()
                self.ears = Ears()
            else:
                print(Fore.YELLOW + "   [System]: 静默模式 - 语音模块已跳过。")

        # 开场白
        start_msg = "Mia V8.1 (日历整合版) 已上线。"
        if not VOICE_MODE: start_msg += " (静默模式)"
        self.speak_and_animate(start_msg)

        # --- 核心循环 ---
        while self.running:
            try:
                user_input = ""

                # === A. 优先处理 GUI 输入 ===
                if not self.msg_queue.empty():
                    user_input = self.msg_queue.get()
                    print(Fore.MAGENTA + f"   [GUI Input]: {user_input}")

                # === B. 处理语音输入 ===
                elif VOICE_MODE and self.ears:
                    vision_system.pause()
                    try:
                        user_input = self.ears.listen()
                    except:
                        pass
                    vision_system.resume()

                else:
                    time.sleep(0.1)
                    continue

                if not user_input: continue

                # === ✅ 特殊指令：清空记忆 ===
                if user_input == "/forget":
                    if self.memory:
                        self.memory.clear_memory()
                        self.speak_and_animate("记忆已格式化，你是谁？")
                    continue

                # === 逻辑处理 ===
                if any(word in user_input for word in ["退出", "关闭", "再见"]):
                    self.speak_and_animate("正在下线。")
                    QApplication.quit()
                    break

                # 思考
                if self.brain:
                    # 1. 获取历史记忆
                    history_context = ""
                    if self.memory:
                        history_context = self.memory.get_context_string()

                    # ✅ 2. 获取未来3天的日程 (供AI参考)
                    upcoming_events = calendar_service.get_upcoming_events_str(days=3)

                    # 3. 构造超级 Prompt
                    full_prompt = f"""
【历史对话摘要】
{history_context}

【用户日程 (未来3天)】
{upcoming_events}

【当前用户输入】
{user_input}
"""
                    # 4. 发送给 AI 思考
                    response = self.brain.think(full_prompt)
                    print(Fore.CYAN + f"Jarvis: {response}")

                    # 5. 记住这次对话
                    if self.memory:
                        self.memory.remember(user_input, response)

                    # === 执行指令判断 ===

                    if "[[CMD:" in response:
                        cmd = response.split("[[CMD:")[1].split("]]")[0]
                        success, name = WindowsController.execute(cmd)
                        msg = f"正在打开 {name}" if success else "打开失败"
                        self.speak_and_animate(msg)

                    elif "[[WEATHER:" in response:
                        city = response.split("[[WEATHER:")[1].split("]]")[0]
                        report = get_weather_report(city if city != "local" else "")
                        self.speak_and_animate(report)

                    # ✅✅✅ 日历触发逻辑 ✅✅✅
                    elif "[[CALENDAR]]" in response:
                        # 触发信号，通知 UI 打开日历
                        self.calendar_signal.emit()
                        # 去掉标签，朗读剩下的文字
                        clean_text = response.replace("[[CALENDAR]]", "").strip()
                        self.speak_and_animate(clean_text)

                    else:
                        self.speak_and_animate(response)

            except Exception as e:
                print(Fore.RED + f"Error: {e}")
                time.sleep(1)

    def speak_and_animate(self, text):
        """
        核心修改：确保无论什么模式，信号都能发出去
        """
        # 1. 发送气泡信号 (这会触发 Pet 的 show_bubble -> 从而触发跳动)
        if text:
            self.bubble_signal.emit(text)

        # 2. 如果是语音模式，还要负责朗读
        if VOICE_MODE and self.mouth:
            self.speaking_signal.emit(True)  # 强制张嘴
            self.mouth.say(text)  # 阻塞朗读
            self.speaking_signal.emit(False)  # 朗读完毕闭嘴

        # 3. 静默模式
        elif not VOICE_MODE:
            # 不需要做任何事，因为 bubble_signal 发出去后，
            # Pet 端会自动显示气泡 -> set_speaking(True) -> 开始跳动 -> 5秒后自动停止
            pass


# ==============================================================================
# 4. 程序主入口
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 1. 创建桌宠
    pet_window = DesktopPet()
    pet_window.show()

    # 2. 创建后台
    worker = JarvisWorker()

    # --- 关键信号连接 ---

    # 气泡与动画连接
    worker.bubble_signal.connect(pet_window.show_bubble)

    # ✅ 日历信号连接 (后台发信号 -> 界面弹日历)
    worker.calendar_signal.connect(pet_window.open_calendar)

    # 输入信号连接
    pet_window.input_signal.connect(worker.put_message)

    # 语音模式下的精准口型控制 (可选)
    if VOICE_MODE:
        worker.speaking_signal.connect(pet_window.set_speaking)

    worker.start()
    sys.exit(app.exec())