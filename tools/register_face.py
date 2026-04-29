# tools/register_face.py
import cv2
import os


def capture_my_face():
    # 自动创建 data 文件夹
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    save_path = os.path.join(base_dir, "data")
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    cap = cv2.VideoCapture(0)
    print("=== 面部录入模式 ===")
    print("请正对摄像头，调整好光线。")
    print("按 'S' 键保存，按 'Q' 退出")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法调用摄像头，请检查连接！")
            break

        cv2.imshow('Jarvis Vision Register', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            # 保存照片到 data/me.jpg
            file_name = os.path.join(save_path, "me.jpg")
            cv2.imwrite(file_name, frame)
            print(f"✅ 面部数据已采集: {file_name}")
            break
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    capture_my_face()