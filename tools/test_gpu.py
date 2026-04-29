try:
    import nvidia.cublas.lib
    import nvidia.cudnn.lib
    import os

    print("✅ NVIDIA 库 Python 包已安装！")
    print(f"   CuBLAS 路径: {os.path.dirname(nvidia.cublas.lib.__file__)}")
    print(f"   CuDNN  路径: {os.path.dirname(nvidia.cudnn.lib.__file__)}")

    # 顺便检查一下 faster-whisper 能不能找到它
    from faster_whisper import WhisperModel

    print("✅ Faster-Whisper 模块加载正常")

except ImportError as e:
    print(f"❌ 失败: 缺少库 -> {e}")
    print("请务必在终端运行: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12")
except Exception as e:
    print(f"❌ 其他错误: {e}")