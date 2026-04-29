# system/remote.py
import discord
from discord import app_commands
from discord.ext import commands
import os
import cv2
import asyncio
import subprocess
import ctypes
import mss
import mss.tools
import sys
import psutil
import pyperclip
import datetime
import pyautogui
import random  # ✅ 新增：用于随机抽取
import io
from system.vision import vision_system

# === 1. 配置加载 ===
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DISCORD_BOT_TOKEN, DISCORD_MASTER_ID, DISCORD_SERVER_ID
    from system.weather import get_weather_report
except ImportError:
    DISCORD_BOT_TOKEN = None
    DISCORD_MASTER_ID = 0
    DISCORD_SERVER_ID = 0


    def get_weather_report(city):
        return "❌ 模块缺失"

# ==============================================================================
# ⛔ [配置] 拒绝访问素材库 (文件夹路径)
# ==============================================================================
# 请在这里填入一个文件夹的路径，里面放满嘲讽的 GIF 或图片
# 比如: r"C:\Users\Jason\Pictures\Jarvis_Deny_Gifs"
ACCESS_DENIED_FOLDER = r"asset"

# ==============================================================================

TEMP_SCREENSHOT = "temp_screen.png"
TEMP_CAM = "temp_cam.jpg"
is_live_running = False


class JarvisBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        if DISCORD_SERVER_ID:
            guild = discord.Object(id=DISCORD_SERVER_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"   [Discord]: 指令已同步到服务器 ID: {DISCORD_SERVER_ID}")


bot = JarvisBot()


# === 权限检查 ===
def is_master_interaction():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id == DISCORD_MASTER_ID

    return app_commands.check(predicate)


@bot.event
async def on_ready():
    print(f"   [Discord]: 卫星连接成功 (User: {bot.user})")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="System Integrity"))


# ==============================================================================
# 🔥 [核心修改] 随机抽取 GIF 进行拒绝
# ==============================================================================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # 捕获权限不足错误
    if isinstance(error, app_commands.CheckFailure):
        msg_content = "⛔ **你不是我的主人。**"

        selected_file = None

        # 1. 检查文件夹是否存在
        if os.path.exists(ACCESS_DENIED_FOLDER) and os.path.isdir(ACCESS_DENIED_FOLDER):
            # 2. 获取所有图片/GIF 文件
            files_list = [
                f for f in os.listdir(ACCESS_DENIED_FOLDER)
                if f.lower().endswith(('.gif', '.jpg', '.png', '.jpeg', '.webp'))
            ]

            # 3. 如果文件夹里有东西，随机抽一个
            if files_list:
                random_filename = random.choice(files_list)
                selected_file = os.path.join(ACCESS_DENIED_FOLDER, random_filename)

        # 4. 发送消息
        if selected_file:
            try:
                await interaction.response.send_message(
                    content=msg_content,
                    file=discord.File(selected_file),
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(f"{msg_content} (GIF 发送失败: {e})", ephemeral=True)
        else:
            # 如果没找到文件夹或文件夹是空的，只发文字
            await interaction.response.send_message(f"{msg_content}\n(提示: 拒绝素材库为空或路径配置错误)",
                                                    ephemeral=True)

    else:
        # 其他系统错误
        await interaction.response.send_message(f"❌ System Error: {error}", ephemeral=True)


# ==============================================================================
# 🎮 指令集 (保持不变)
# ==============================================================================

@bot.tree.command(name="status", description="系统仪表盘")
@is_master_interaction()
async def status(interaction: discord.Interaction):
    await interaction.response.defer()
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('C:/')
    boot = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")

    embed = discord.Embed(title="🖥️ System Status", color=0x00ffcc)
    embed.add_field(name="CPU", value=f"{cpu}%", inline=True)
    embed.add_field(name="RAM", value=f"{mem.percent}%", inline=True)
    embed.add_field(name="Disk (C:)", value=f"{disk.percent}% Used", inline=True)
    embed.add_field(name="Boot Time", value=boot, inline=False)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="screen", description="多屏截图")
@is_master_interaction()
async def screen(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        with mss.mss() as sct:
            sct.shot(mon=-1, output=TEMP_SCREENSHOT)
            await interaction.followup.send(file=discord.File(TEMP_SCREENSHOT))
            os.remove(TEMP_SCREENSHOT)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")


@bot.tree.command(name="cam", description="获取实时监控画面")
@is_master_interaction()
async def cam(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        # 1. 直接从 Jarvis 的眼睛里拿数据，不自己开摄像头
        frame = vision_system.get_snapshot()

        if frame is None:
            await interaction.followup.send("❌ 无法获取画面 (摄像头被占用或未连接)。")
            return

        # 2. 内存转码：把 OpenCV 图片转成 Discord 能发的 JPG
        # 这样就不需要保存到硬盘上的 TEMP_CAM 文件了，速度更快，也不伤硬盘
        success, buffer = cv2.imencode('.jpg', frame)

        if not success:
            await interaction.followup.send("❌ 图片编码失败。")
            return

        # 3. 创建二进制文件流
        io_buf = io.BytesIO(buffer)
        io_buf.seek(0)

        # 4. 发送
        await interaction.followup.send(file=discord.File(fp=io_buf, filename="snapshot.jpg"))

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")


@bot.tree.command(name="live", description="开启实时监控")
@app_commands.describe(mode="screen/cam")
@app_commands.choices(
    mode=[app_commands.Choice(name="Screen", value="screen"), app_commands.Choice(name="Camera", value="cam")])
@is_master_interaction()
async def live(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    global is_live_running
    if is_live_running: return await interaction.response.send_message("⚠️ Stream already running.")
    await interaction.response.send_message(f"🔴 LIVE: {mode.name} (Auto-stop in 5m)")
    msg = await interaction.original_response()
    is_live_running = True
    target = mode.value
    count = 0
    try:
        while is_live_running:
            path = None
            if target == "screen":
                path = TEMP_SCREENSHOT
                with mss.mss() as sct:
                    try:
                        sct.shot(mon=-1, output=path)
                    except:
                        break
            elif target == "cam":
                path = TEMP_CAM
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not cap.isOpened(): break
                ret, frame = cap.read()
                cap.release()
                if ret: cv2.imwrite(path, cv2.resize(frame, (640, 360)), [cv2.IMWRITE_JPEG_QUALITY, 60])

            if path and os.path.exists(path):
                await msg.edit(attachments=[discord.File(path)])
                count += 1
                await asyncio.sleep(1.5)
            else:
                break
            if count > 200: break
    finally:
        is_live_running = False
        if os.path.exists(TEMP_SCREENSHOT): os.remove(TEMP_SCREENSHOT)
        if os.path.exists(TEMP_CAM): os.remove(TEMP_CAM)
        try:
            await msg.edit(content=f"🏁 Stream ended.")
        except:
            pass


@bot.tree.command(name="stop", description="停止监控")
@is_master_interaction()
async def stop(interaction: discord.Interaction):
    global is_live_running
    is_live_running = False
    await interaction.response.send_message("🛑 Stopping stream...")


@bot.tree.command(name="cmd", description="执行CMD")
@is_master_interaction()
async def cmd(interaction: discord.Interaction, command: str):
    await interaction.response.defer()
    try:
        output = subprocess.check_output(command, shell=True, encoding='gbk', stderr=subprocess.STDOUT)
        res = output if output else "✅ Executed."
        if len(res) > 1900: res = res[:1900] + "..."
        await interaction.followup.send(f"```\n{res}\n```")
    except Exception as e:
        await interaction.followup.send(f"❌: {e}")


@bot.tree.command(name="lock", description="锁屏")
@is_master_interaction()
async def lock(interaction: discord.Interaction):
    ctypes.windll.user32.LockWorkStation()
    await interaction.response.send_message("🔒 Workstation Locked.")


@bot.tree.command(name="say", description="TTS朗读")
@is_master_interaction()
async def say(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(f"🗣️ Broadcasting: {text}")
    subprocess.Popen(
        f'PowerShell -Command "Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text}\');"',
        shell=True)


@bot.tree.command(name="weather", description="天气查询")
@is_master_interaction()
async def weather(interaction: discord.Interaction, city: str = ""):
    await interaction.response.defer()
    target = city if city else "local"
    report = get_weather_report(target)
    await interaction.followup.send(embed=discord.Embed(title="Weather Report", description=report, color=0x3498db))


# === 启动 ===
def run_discord_bot():
    if not DISCORD_BOT_TOKEN: print("   [Discord Error]: No Token found."); return
    try:
        asyncio.set_event_loop(asyncio.new_event_loop())
        bot.run(DISCORD_BOT_TOKEN)
    except Exception as e:
        print(f"   [Discord Error]: {e}")


if __name__ == "__main__": run_discord_bot()