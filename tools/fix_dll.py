import os
import shutil
import site


def copy_nvidia_dlls():
    # 1. 获取当前虚拟环境的 site-packages 目录
    site_packages = site.getsitepackages()[0]  # 通常是 .venv/Lib/site-packages
    project_root = os.getcwd()  # 当前项目目录

    print(f"🔍 正在搜索库目录: {site_packages}")
    print(f"📂 目标目录: {project_root}")
    print("-" * 30)

    # 我们需要找的关键文件
    target_dlls = [
        "cublas64_12.dll",
        "cublasLt64_12.dll",
        "cudnn_cnn_infer64_8.dll",
        "cudnn_ops_infer64_8.dll"
    ]

    found_count = 0

    # 2. 暴力遍历 site-packages 寻找这些 DLL
    for root, dirs, files in os.walk(site_packages):
        for file in files:
            if file in target_dlls:
                source_path = os.path.join(root, file)
                dest_path = os.path.join(project_root, file)

                # 如果当前目录下还没有，就复制过来
                if not os.path.exists(dest_path):
                    try:
                        shutil.copy2(source_path, dest_path)
                        print(f"✅ 已复制: {file}")
                        found_count += 1
                    except Exception as e:
                        print(f"❌ 复制失败 {file}: {e}")
                else:
                    print(f"⚡ 已存在 (跳过): {file}")
                    found_count += 1

    print("-" * 30)
    if found_count >= 2:
        print("🎉 修复完成！关键驱动文件已就位。")
        print("🚀 现在请直接运行 main.py")
    else:
        print("⚠️ 未找到所有文件。请确认你确实运行了 pip install nvidia-cublas-cu12 nvidia-cudnn-cu12")


if __name__ == "__main__":
    copy_nvidia_dlls()