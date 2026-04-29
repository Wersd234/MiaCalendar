# 📁 src/back/server.py
import os
import json
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# 🌟 修复1：补充导入所有的天气相关函数
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

# 🌟 修复2：补充单日天气接口（给前端的日历使用）
@app.get("/api/weather")
async def get_daily_weather_endpoint(date: str):
    """前端日历调用此接口获取指定日期的天气"""
    data = fetch_weather_from_api(date)
    return {"status": "success", "data": data}


# 7 天天气接口（给前端的 "显示近七天天气" 按钮使用）
@app.get("/api/weather/7days")
async def get_weather_7days_endpoint():
    """前端调用此接口获取 7 天天气预报"""
    data = fetch_7_days_forecast()
    return {"status": "success", "data": data}


# ================= 🌟 WebSocket 区域 =================
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user_id = "default_user"

    # 初始化时注入今天的天气感知
    if user_id not in history_db:
        base_prompt = config["ai_server"]["system_prompt"]
        current_weather_txt = get_ai_weather_report()
        smart_prompt = f"{base_prompt} \n\n【系统实时信息】：{current_weather_txt}"
        history_db[user_id] = [{"role": "system", "content": smart_prompt}]
        print(f"🧠 AI 大脑已注入环境感知: {current_weather_txt}")

    try:
        while True:
            user_message = await websocket.receive_text()
            print(f"收到前端消息: {user_message}")

            # 🌟 修复3：加入关键词拦截与 RAG 增强
            msg_to_ai = user_message
            # 只要用户提到这些词，就偷偷去拿 7 天数据给 AI 看
            if any(keyword in user_message for keyword in ["天气", "下雨", "气温", "冷", "热", "带伞", "出去玩"]):
                print("☁️ 检测到天气询问，正在提取实时气象数据注入大脑...")
                forecast_txt = get_ai_7_days_report()
                msg_to_ai = f"【系统提示：用户正在询问天气。请根据以下实时气象数据回答用户的问题，并给出贴心的建议。回答简短、傲娇、幽默：\n{forecast_txt}】\n\n主人说：{user_message}"

            # 把带有提示的消息（或者普通消息）存入记忆并发送给模型
            history_db[user_id].append({"role": "user", "content": msg_to_ai})

            payload = {
                "model": get_active_model(),
                "messages": history_db[user_id],
                "temperature": 0.7,
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
                                if decoded_line == '[DONE]':
                                    break
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

    print("--- 正在初始化后端 (带环境感知能力) ---")
    uvicorn.run(app, host=config["backend"]["host"], port=config["backend"]["port"])