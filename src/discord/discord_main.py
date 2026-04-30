# 📁 src/discord/discord_main.py
import discord
import httpx
import os
import json
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {}


config = load_config()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or config.get("discord", {}).get("bot_token", "")

host = config.get("backend", {}).get("host", "127.0.0.1")
port = config.get("backend", {}).get("port", 8000)
if host == "0.0.0.0": host = "127.0.0.1"
API_URL = f"http://{host}:{port}/api/discord_chat"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"✅ Discord 桥接端已启动！登录身份: {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if client.user in message.mentions or isinstance(message.channel, discord.DMChannel):
        clean_msg = message.content.replace(f'<@{client.user.id}>', '').strip()

        # 🌟 日常语气
        if not clean_msg:
            await message.reply("我在听哦，怎么啦？")
            return

        async with message.channel.typing():
            try:
                # 🌟 1. 读取 Discord 频道的历史消息
                history_list = []
                async for past_msg in message.channel.history(limit=30, before=message):
                    if not past_msg.content: continue

                    role = "assistant" if past_msg.author == client.user else "user"
                    clean_past_content = past_msg.content.replace(f'<@{client.user.id}>', '').strip()

                    # 👈 核心修复：如果是机器人自己以前说的话，绝对不要加名字前缀！
                    if role == "assistant":
                        final_content = clean_past_content
                    else:
                        # 如果是群友说的话，带上名字，让 AI 知道它在和谁聊天
                        final_content = f"{past_msg.author.name}说: {clean_past_content}"

                    history_list.append({
                        "role": role,
                        "content": final_content
                    })

                history_list.reverse()
                # 发送给大脑
                async with httpx.AsyncClient() as http_client:
                    payload = {
                        "user_id": str(message.author.id),
                        "message": clean_msg,
                        "history": history_list
                    }
                    res = await http_client.post(API_URL, json=payload, timeout=300.0)

                    if res.status_code == 200:
                        reply = res.json().get("reply", "哎呀，我大脑一片空白，什么也没想出来...")
                        await message.reply(reply)
                    else:
                        await message.reply(f"❌ 呼叫本地大脑失败啦 (状态码: {res.status_code})，是不是你电脑关机了？")

            except Exception as e:
                await message.reply(f"❌ 发生了奇怪的错误：{e}")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("⚠️ 启动失败：请先在 config.json 中填入你的 Discord Token！")
    else:
        client.run(DISCORD_TOKEN)