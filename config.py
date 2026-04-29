# config.py

# 🧠 大脑设置
MODEL_NAME = "llama3"
# ...

# ✅ 改造：直接用中文做“唯一ID”，简单粗暴，永不出错
APP_MAP = {
    # 格式: "中文名": ["进程名", r"路径", "窗口标题"]

    "微信": [
        "FORCE_WX",
        r'C:\Program Files\Tencent\Weixin\Weixin.exe',
    ],

    "谷歌浏览器": [
        "chrome.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "Chrome"
    ],


    "计算器": [
        "CalculatorApp.exe",
        "calc",
        "计算器"
    ],

    "记事本": [
        "notepad.exe",
        "notepad.exe",
        "记事本"
    ],

    # 对于英文本身就更通用的词，可以保留英文，或者中英都加
    "cmd": ["cmd.exe", "start cmd", "命令提示符"],
    "命令提示符": ["cmd.exe", "start cmd", "命令提示符"],

    "steam": [
        "FORCE_STEAM_POPUP",
        r'F:\Steam\steam.exe',
    ]
}

# === 视觉安全系统 ===
CAMERA_INDEX = 0           # 摄像头索引 (通常是0，如果有多个摄像头可能是1)
LOCK_TIMEOUT = 60          # 几秒钟没看到人脸就锁屏？(测试建议 10秒，实际使用建议 60秒)
FACE_TOLERANCE = 0.50      # 视觉识别容差 (越低越严格)
PC_PASSWORD = 0  # ⚠️ 必填，否则无法解锁
STARTUP_GRACE_PERIOD = 10 # 启动缓冲期 (秒)


# 2. Discord 机器人令牌 (来自 Developer Portal)
DISCORD_BOT_TOKEN = "YOUR_TOKEN_HERE"


# 3. Discord 用户 ID (用于鉴权，防止他人控制)
# 必须是整数 (Integer)
DISCORD_MASTER_ID =  463981448433631232


# 4. Discord 服务器 ID (用于斜杠指令秒级同步)
# 必须是整数 (Integer)
DISCORD_SERVER_ID = 730335238311378974