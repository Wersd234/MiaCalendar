import edge_tts
import pygame
import asyncio
import threading
import os
import time

# 语音配置
VOICE = "zh-CN-YunxiNeural"


class Mouth:
    def __init__(self):
        # 初始化 pygame 音频混合器
        pygame.mixer.init()

    def say(self, text):
        """外部调用的入口"""
        clean_text = text.split("[[")[0].strip()
        if not clean_text:
            return

        # 启动线程播放
        threading.Thread(target=self._run_speech, args=(clean_text,)).start()

    def _run_speech(self, text):
        """私有方法：运行异步的 TTS 生成"""
        try:
            asyncio.run(self._generate_and_play(text))
        except Exception as e:
            # 这里的 print 可以帮你定位问题，但不影响主程序运行
            print(f"   [Mouth Error]: {e}")

    async def _generate_and_play(self, text):
        """生成音频并播放 (保存到 temp 文件夹)"""
        # --- 修改开始 ---
        # 1. 确保 temp 文件夹存在
        temp_dir = "temp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # 2. 生成带路径的文件名: temp/speech_xxxx.mp3
        temp_filename = os.path.join(temp_dir, f"speech_{int(time.time() * 1000)}.mp3")
        # --- 修改结束 ---

        try:
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(temp_filename)

            # ... 下面的播放逻辑保持不变 ...
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            pygame.mixer.music.unload()

        except Exception as e:
            print(f"播放出错: {e}")
        finally:
            # 删除文件时也要带上路径
            if os.path.exists(temp_filename):
                try:
                    os.remove(temp_filename)
                except:
                    pass

    def cleanup(self):
        """退出时清理"""
        pygame.mixer.quit()