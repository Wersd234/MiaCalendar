# 📁 src/back/server.py
import os
import json
import httpx
import re  # 🌟 增加正则支持
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
    date_str: str
    time_str: str
    title: str
    desc: str = ""


@app.get("/api/calendar")
async def get_calendar_events(date: str):
    data = calendar_service.get_events(date)
    return {"status": "success", "data": data}


@app.post("/api/calendar")
async def add_calendar_event(item: EventItem):
    calendar_service.add_event(item.date_str, item.time_str, item.title, item.desc)
    return {"status": "success"}


@app.delete("/api/calendar")
async def delete_calendar_event(date: str, index: int):
    calendar_service.delete_event(date, index)
    return {"status": "success"}


# ================= 🌟 WebSocket 区域 (大脑核心) =================
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user_id = "default_user"

    # 1. 🌟 初始化注入：增加 [ACTION] 协议说明
    if user_id not in history_db:
        base_prompt = config["ai_server"]["system_prompt"]
        current_weather_txt = get_ai_weather_report()
        upcoming_events_txt = calendar_service.get_upcoming_events_str(days=3)

        # 🌟 核心改进：在 System Prompt 中加入视觉动作规范
        emotion_guide = (
            "\n\n【视觉动作规范】\n"
            "你可以通过在回复的最开头加入 [ACTION:表情名] 来控制你的桌宠形象。可选表情：\n"
            "- [ACTION:shy] : 当朋友夸奖你、调戏你或感到不好意思时使用。\n"
            "- [ACTION:happy] : 当心情愉快或欢迎朋友时使用。\n"
            "- [ACTION:angry] : 当朋友欺负你或你说教时使用。\n"
            "- [ACTION:shock] : 当感到惊讶或听到意外消息时使用。\n"
            "注意：每条回复仅限在开头使用一个标签。请保持一个友善的形象。"
        )

        smart_prompt = f"{base_prompt} {emotion_guide} \n\n【系统实时信息】\n天气实况：{current_weather_txt}\n未来三天日程：\n{upcoming_events_txt}"
        history_db[user_id] = [{"role": "system", "content": smart_prompt}]
        print(f"🧠 大脑已初始化，成功注入环境感知与情绪系统！")

    try:
        while True:
            user_message = await websocket.receive_text()
            msg_to_ai = user_message

            # ================= 🌟 关键词拦截与情绪诱导 (Emotion RAG) =================

            # 1. 检测夸奖/可爱相关 (触发 shy)
            if any(keyword in user_message for keyword in ["可爱", "萌", "漂亮", "喜欢你", "真棒", "好乖"]):
                print("💖 检测到夸奖，正在诱导害羞情绪...")
                msg_to_ai = f"【系统提示：你的朋友正在夸奖你，请表现得非常害羞，务必在回复最开头加上 [ACTION:shy]】\n\n主人说：{user_message}"

            # 2. 检测天气相关
            elif any(keyword in user_message for keyword in ["天气", "下雨", "气温", "冷", "热", "带伞"]):
                forecast_txt = get_ai_7_days_report()
                msg_to_ai = f"【系统提示：用户询问天气，请参考以下气象数据回答。回答要简短、傲娇，并根据天气决定表情（如阴雨用 [ACTION:angry]，晴天用 [ACTION:happy]）：\n{forecast_txt}】\n\n主人说：{user_message}"

            # 3. 检测日程相关
            elif any(keyword in user_message for keyword in ["日程", "安排", "打算", "计划", "明天干嘛"]):
                fresh_events = calendar_service.get_upcoming_events_str(days=7)
                msg_to_ai = f"【系统提示：用户正在询问日程，请作为秘书如实回答。开头可以加上 [ACTION:shock] 如果日程很满：\n{fresh_events}】\n\n主人说：{user_message}"
            # ===================================================================

            history_db[user_id].append({"role": "user", "content": msg_to_ai})

            payload = {
                "model": get_active_model(),
                "messages": history_db[user_id],
                "temperature": 0.8,  # 🌟 略微调高温度，让表情更多变
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