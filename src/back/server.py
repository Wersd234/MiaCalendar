# 📁 src/back/server.py
import os
import json
import httpx
import re
from dotenv import load_dotenv
from typing import List, Dict, Any
from anime_service import anime_service
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from calendar_service import calendar_service
from weather_service import (
    fetch_weather_from_api,
    fetch_7_days_forecast,
    get_ai_weather_report,
    get_ai_7_days_report
)

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ENV_PATH = os.path.join(BASE_DIR, ".env")

# 🌟 新增：强制加载根目录下的 .env 文件
load_dotenv(ENV_PATH)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


config = load_config()
history_db = {}


def get_active_model():
    try:
        import requests
        models_url = config["ai_server"]["url"].replace("/chat/completions", "/models")
        resp = requests.get(models_url, timeout=5)
        if resp.status_code == 200:
            models_data = resp.json()
            if "data" in models_data and len(models_data["data"]) > 0:
                return models_data["data"][0]["id"]
    except:
        pass
    return "local-model"


# ================= 🌟 HTTP 路由区域 =================
@app.get("/api/weather")
async def get_daily_weather_endpoint(date: str):
    data = fetch_weather_from_api(date)
    return {"status": "success", "data": data}


@app.get("/api/weather/7days")
async def get_weather_7days_endpoint():
    data = fetch_7_days_forecast()
    return {"status": "success", "data": data}


class EventItem(BaseModel):
    title: str
    is_all_day: bool
    start_date: str
    start_time: str
    end_date: str
    end_time: str
    location: str = ""
    desc: str = ""


@app.get("/api/calendar")
async def get_calendar_events(date: str):
    data = calendar_service.get_events(date)
    return {"status": "success", "data": data}


@app.post("/api/calendar")
async def add_calendar_event(item: EventItem):
    calendar_service.add_event(item.model_dump())
    return {"status": "success"}


@app.delete("/api/calendar")
async def delete_calendar_event(date: str, index: int):
    calendar_service.delete_event(date, index)
    return {"status": "success"}


# ================= 🌟 追番 HTTP 路由区域 =================
@app.get("/api/anime/bangumi")
async def get_bangumi_calendar():
    data = anime_service.fetch_bangumi_season()
    return {"status": "success", "data": data}


@app.get("/api/anime/watchlist")
async def get_watchlist():
    data = anime_service.get_watchlist()
    return {"status": "success", "data": data}


@app.post("/api/anime/watchlist")
async def update_watchlist(watchlist: List[Dict[str, Any]]):
    anime_service.save_watchlist(watchlist)
    return {"status": "success"}


# ================= 🌟 Discord 专用 HTTP 路由区域 =================
class DiscordChatRequest(BaseModel):
    user_id: str
    message: str
    history: list = []


@app.post("/api/discord_chat")
async def discord_chat_endpoint(req: DiscordChatRequest):
    user_id = req.user_id
    user_message = req.message
    owner_id = os.getenv("DISCORD_OWNER_ID") or config.get("discord", {}).get("owner_id", "")

    # 1. 🌟 修改人设提示：强调你们是好朋友，不是主仆
    if f"discord_{user_id}" not in history_db:
        base_prompt = config["ai_server"]["system_prompt"]
        history_db[f"discord_{user_id}"] = [{
            "role": "system",
            "content": base_prompt + "\n注意：你现在正在通过 Discord 聊天。你和对话的人是无话不谈的平等挚友/好搭档，绝对不要叫对方“主人”，要像普通朋友一样自然地交流。只使用文字回复，不要使用 [ACTION:xxx] 标签。"
        }]

    # 2. 🌟 隐私鉴权：判断是不是你的好朋友 (也就是你自己)
    is_best_friend = (user_id == owner_id)

    now = datetime.now()
    week_map = {"0": "日", "1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六"}
    current_time_str = now.strftime("%Y年%m月%d日") + f" 星期{week_map[now.strftime('%w')]} " + now.strftime("%H:%M")

    forecast_txt = get_ai_7_days_report()

    # 如果是挚友，开心分享行程；如果是普通群友，傲娇保密
    if is_best_friend:
        fresh_events = calendar_service.get_upcoming_events_str(days=7) or "暂无日程安排"
        auth_status = "✅ 身份确认：你是她最好的朋友兼搭档！已获取 Nextcloud 专属日历权限。"
        speaker = "好朋友"
    else:
        fresh_events = "【隐私警告】对方是 Discord 上的普通群友，不是你最好的朋友！为了保护朋友的隐私，你绝对不可以透露任何 Nextcloud 里的日程安排，请用调皮或委婉的语气拒绝查询日历的要求。"
        auth_status = f"❌ 身份：普通群友 (ID: {user_id})。不可透露私人隐私。"
        speaker = "群里的朋友"

    # 3. 组装环境快照
    dynamic_context = (
        f"【系统实时快照】\n"
        f"当前时间：{current_time_str}\n"
        f"天气实况：\n{forecast_txt}\n"
        f"安全验证：{auth_status}\n"
        f"日历状态：\n{fresh_events}\n"
        f"--------------------------------\n"
    )

    msg_to_ai = f"{dynamic_context}\n{speaker}在Discord上说：{user_message}"

    # 4. 组装对话流
    system_msg = history_db[f"discord_{user_id}"][0]
    current_messages = [system_msg] + req.history + [{"role": "user", "content": msg_to_ai}]

    payload = {
        "model": get_active_model(),
        "messages": current_messages,
        "temperature": 0.8,
        "stream": False
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(config["ai_server"]["url"], json=payload, timeout=300.0)
            data = resp.json()
            reply = data['choices'][0]['message']['content']

            clean_reply = re.sub(r'\[ACTION:[a-zA-Z0-9_]+\]', '', reply).strip()
            return {"reply": clean_reply}
    except Exception as e:
        return {"reply": f"🧠 哎呀，我的大脑好像短路了，稍等我一下哦：{str(e)}"}


# ================= 🌟 WebSocket 区域 (桌宠大脑核心) =================
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user_id = "default_user"

    # 1. 初始化桌宠人设
    if user_id not in history_db:
        base_prompt = config["ai_server"]["system_prompt"]
        emotion_guide = (
            "\n\n【视觉动作及人设规范】\n"
            "你和眼前的人是无话不谈的平等挚友/好搭档，不要使用“主人”这种称呼，语气要自然、亲切，可以适当互相开玩笑。\n"
            "你可以通过在回复的最开头加入 [ACTION:表情名] 来控制你的表情。可选表情：\n"
            "- [ACTION:shy] : 害羞、被夸奖时使用。\n"
            "- [ACTION:happy] : 心情愉快、开心时使用。\n"
            "- [ACTION:angry] : 傲娇、吐槽对方或假装生气时使用。\n"
            "- [ACTION:shock] : 惊讶时使用。\n"
            "- [ACTION:open] : 平常聊天时使用。\n"
            "注意：每条回复仅限在开头使用一个标签。"
        )
        history_db[user_id] = [{"role": "system", "content": f"{base_prompt} {emotion_guide}"}]
        print(f"🧠 桌宠大脑已初始化，『挚友』人设与情绪规范加载完毕！")

    try:
        while True:
            user_message = await websocket.receive_text()

            now = datetime.now()
            week_map = {"0": "日", "1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六"}
            current_time_str = now.strftime("%Y年%m月%d日") + f" 星期{week_map[now.strftime('%w')]} " + now.strftime(
                "%H:%M")

            fresh_events = calendar_service.get_upcoming_events_str(days=7) or "暂无日程安排"
            forecast_txt = get_ai_7_days_report()

            emotion_hint = ""
            if any(keyword in user_message for keyword in ["可爱", "萌", "漂亮", "喜欢你", "真棒", "好乖"]):
                emotion_hint = "【特别提示：你的好朋友正在夸你，请表现得有些害羞，务必在回复最开头加上 [ACTION:shy]】\n"

            dynamic_context = (
                f"【系统实时快照 (如果朋友问天气、日程才回答)】\n"
                f"当前时间：{current_time_str}\n"
                f"最新日程表：\n{fresh_events}\n"
                f"天气实况：\n{forecast_txt}\n"
                f"{emotion_hint}"
                f"--------------------------------\n"
            )

            # 🌟 替换掉“主人说”
            msg_to_ai = f"{dynamic_context}\n好朋友说：{user_message}"

            history_db[user_id].append({"role": "user", "content": user_message})
            current_messages = history_db[user_id][:-1] + [{"role": "user", "content": msg_to_ai}]

            payload = {
                "model": get_active_model(),
                "messages": current_messages,
                "temperature": 0.8,
                "stream": True
            }

            full_response = ""
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream("POST", config["ai_server"]["url"], json=payload,
                                             timeout=60.0) as response:
                        if response.status_code != 200:
                            await websocket.send_text(f"[ERROR] AI报错: {response.status_code}")
                            continue

                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                decoded_line = line.replace('data: ', '').strip()
                                if decoded_line == '[DONE]': break
                                try:
                                    data = json.loads(decoded_line)
                                    content = data['choices'][0]['delta'].get('content', '')
                                    if content:
                                        full_response += content
                                        await websocket.send_text(content)
                                except json.JSONDecodeError:
                                    continue

                await websocket.send_text("[DONE]")
                history_db[user_id].append({"role": "assistant", "content": full_response})

            except Exception as e:
                await websocket.send_text(f"[ERROR] 连接 AI 失败: {str(e)}")
                await websocket.send_text("[DONE]")

    except WebSocketDisconnect:
        print("前端已断开连接")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config["backend"]["host"], port=config["backend"]["port"])