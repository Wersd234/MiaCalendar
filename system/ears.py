# system/ears.py
import os
import sys  # 引入 sys
from colorama import Fore
import speech_recognition as sr

# ==========================================
# 🚨 暴力引导：双重保险模式
# ==========================================
current_root = os.getcwd()
libs_path = os.path.join(current_root, "libs")

if os.path.exists(libs_path):
    # 1. 方法 A: Python 3.8+ 推荐方式
    try:
        os.add_dll_directory(libs_path)
    except Exception:
        pass

    # 2. 方法 B: 传统 PATH 环境变量 (最稳)
    # 把 libs 目录直接塞到环境变量的最前面
    os.environ["PATH"] = libs_path + os.pathsep + os.environ["PATH"]

    print(Fore.GREEN + f"   [System]: 已强制注入驱动路径到 PATH: libs/")
else:
    print(Fore.RED + f"   [Fatal]: 找不到 libs 文件夹！请确认 cublas64_12.dll 在里面！")

# ==========================================
from faster_whisper import WhisperModel
# 配置
MODEL_SIZE = "large-v3"
# 确保音频文件进入 temp 文件夹
TEMP_AUDIO_FILE = os.path.join("temp", "input.wav")

# 唤醒词列表
WAKE_WORDS = ["jarvis", "贾维斯", "老贾", "系统"]


class Ears:
    def __init__(self):
        print(Fore.CYAN + f"   [System]: 正在加载听觉神经 ({MODEL_SIZE})...")

        # 自动创建 temp 文件夹
        if not os.path.exists("temp"):
            os.makedirs("temp")

        # 加载 Whisper
        self.model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16")

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 2000
        self.recognizer.dynamic_energy_threshold = False

        print(Fore.CYAN + "   [System]: 听觉系统上线 (已启用唤醒词过滤)。")

    def listen(self):
        """监听麦克风"""
        with sr.Microphone() as source:
            print(Fore.MAGENTA + "\n   (👂 正在聆听... 请说话)")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.2)

            try:
                audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=10)
                print(Fore.MAGENTA + "   (⚡ 正在分析声波...)")

                with open(TEMP_AUDIO_FILE, "wb") as f:
                    f.write(audio.get_wav_data())

                # 转录
                segments, info = self.model.transcribe(
                    TEMP_AUDIO_FILE,
                    beam_size=5,
                    language="zh",
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                    condition_on_previous_text=False
                )

                full_text = ""
                for segment in segments:
                    full_text += segment.text

                # 清理文件
                if os.path.exists(TEMP_AUDIO_FILE):
                    os.remove(TEMP_AUDIO_FILE)

                clean_text = full_text.strip()
                if not clean_text:
                    return None

                # 唤醒词检测
                lower_text = clean_text.lower()
                triggered_word = None
                for w in WAKE_WORDS:
                    if lower_text.startswith(w.lower()):
                        triggered_word = w
                        break

                if triggered_word:
                    command = clean_text[len(triggered_word):].strip()
                    command = command.lstrip(",.，。!！ ")

                    if not command:
                        return None

                    print(Fore.GREEN + f"   [唤醒成功]: {command}")
                    return command
                else:
                    print(Fore.LIGHTBLACK_EX + f"   [忽略闲聊]: {clean_text}")
                    return None

            except sr.WaitTimeoutError:
                return None
            except Exception as e:
                print(Fore.RED + f"   [Ears Error]: {e}")
                if os.path.exists(TEMP_AUDIO_FILE):
                    os.remove(TEMP_AUDIO_FILE)
                return None