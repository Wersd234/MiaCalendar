# system/memory.py
import json
import os
from datetime import datetime

# =================配置区=================
MEMORY_FILE = "memory.json"  # 记忆文件路径
MAX_HISTORY = 100  # ✅ 修改：现在可以保存最近 100 条对话


# ========================================

class MemorySystem:
    def __init__(self):
        self.history = []
        self.load_memory()

    def load_memory(self):
        """加载记忆，如果不存在则创建空的"""
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"⚠️ 记忆文件损坏，重置记忆: {e}")
                self.history = []
        else:
            self.history = []

    def save_memory(self):
        """保存记忆到 JSON"""
        try:
            with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 记忆保存失败: {e}")

    def remember(self, user_input, ai_response):
        """
        核心逻辑：写入新记忆 + 限制大小
        """
        entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": user_input,
            "ai": ai_response
        }

        self.history.append(entry)

        # 🔥【FIFO清理】如果超过 100 条，删除最旧的一条
        while len(self.history) > MAX_HISTORY:
            self.history.pop(0)

        self.save_memory()

    def get_context_string(self):
        """
        将最近的记忆打包成字符串，发给 AI 大脑
        """
        context_str = ""

        # ✅ 策略调整：
        # 虽然我们硬盘里存了 100 条，但为了防止 Token 爆炸，
        # 我们只提取最近的 30 条发给 AI 思考。
        # 如果你的模型 Context Window 很大，可以把这个 [-30:] 改成 [-100:]
        recent_logs = self.history[-30:]

        for log in recent_logs:
            context_str += f"User: {log['user']}\nJarvis: {log['ai']}\n"

        return context_str

    def clear_memory(self):
        """清空所有记忆"""
        self.history = []
        if os.path.exists(MEMORY_FILE):
            os.remove(MEMORY_FILE)
        print("🧹 大脑已格式化。")