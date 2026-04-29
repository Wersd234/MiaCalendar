# brain/llm.py
import ollama
from colorama import Fore
from config import MODEL_NAME, APP_MAP
# ✅ 从 prompts 导入构建函数，而不是导入死板的字符串
from brain.prompts import construct_system_prompt


class Brain:
    def __init__(self):
        # 1. 调用 prompts 模块生成完整的设定
        # 我们把 APP_MAP 传过去，让 prompts.py 去处理怎么拼接字符串
        self.full_system_prompt = construct_system_prompt(APP_MAP)

        # 2. 初始化历史
        self.history = [{'role': 'system', 'content': self.full_system_prompt}]

    def think(self, user_input):
        """发送输入，获取流式输出，并返回完整文本"""
        self.history.append({'role': 'user', 'content': user_input})

        print(Fore.GREEN + "[Jarvis]: ", end="")

        full_response = ""
        try:
            stream = ollama.chat(model=MODEL_NAME, messages=self.history, stream=True)

            for chunk in stream:
                content = chunk['message']['content']
                print(content, end="", flush=True)
                full_response += content

            self.history.append({'role': 'assistant', 'content': full_response})
            print("")  # 换行

            return full_response

        except Exception as e:
            print(Fore.RED + f"\n[Brain Error]: 大脑思考时短路了 -> {e}")
            return "抱歉，我的思维网络连接中断了。"