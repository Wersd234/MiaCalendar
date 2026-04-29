import cv2
import threading
import time

# OpenCV 自带的人脸识别模型
CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'


class VisionSystem:
    def __init__(self):
        self.running = False
        self.paused = False
        self.cap = None
        self.thread = None
        self.face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

        # ✅ 新增：用于存储最新的一帧画面，供 Discord 使用
        self.latest_frame = None
        self.lock = threading.Lock()  # 线程锁，防止读取冲突

    def start_monitoring(self):
        if self.running: return
        self.running = True
        self.paused = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def get_snapshot(self):
        """
        ✅ 新增：外部获取当前画面的接口
        """
        # 如果摄像头没开，尝试临时开一下（防止纯文字模式下无法拍照）
        if not self.running or self.latest_frame is None:
            return self._force_snapshot()

        with self.lock:
            if self.latest_frame is not None:
                # 复制一份图像，防止多线程操作干扰
                return self.latest_frame.copy()
        return None

    def _force_snapshot(self):
        """备用方案：如果视觉系统没开，临时拍一张"""
        temp_cap = cv2.VideoCapture(0)
        if not temp_cap.isOpened(): return None
        ret, frame = temp_cap.read()
        temp_cap.release()
        return frame if ret else None

    def _run(self):
        self.cap = cv2.VideoCapture(0)

        while self.running:
            if self.paused:
                time.sleep(0.5)
                continue

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(1)
                continue

            # ✅ 存储当前帧 (加锁保护)
            with self.lock:
                self.latest_frame = frame

            # --- 视觉处理逻辑 (人脸识别) ---
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))

            # (可选) 如果你想让 Discord 看到的照片里带绿框，就把画框代码放在这里
            # for (x, y, w, h) in faces:
            #    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            time.sleep(0.03)

        if self.cap:
            self.cap.release()


vision_system = VisionSystem()