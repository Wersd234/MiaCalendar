import win32gui


def list_all_windows():
    print("正在扫描所有可见窗口...")
    print("-" * 30)

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                print(f"Handle: {hwnd} | Title: [{title}]")

    win32gui.EnumWindows(callback, None)
    print("-" * 30)


if __name__ == "__main__":
    list_all_windows()