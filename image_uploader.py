import sys
import os
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt5.QtCore import QThread, pyqtSignal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image

API_URL = "https://visitorsgallery-api.divine-wave-35ee.workers.dev/image"
DEFAULT_PROJECT_ID = "noset"
SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']
MIME_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.bmp': 'image/bmp',
    '.gif': 'image/gif',
    '.webp': 'image/webp'
}

class UploadWorker(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.observer = Observer()

    def run(self):
        event_handler = ImageHandler(self.log_signal)
        self.observer.schedule(event_handler, self.folder_path, recursive=False)
        self.observer.start()
        self.log_signal.emit(f"🔍 開始監控資料夾：{self.folder_path}")
        self.exec_()

    def stop(self):
        self.observer.stop()
        self.observer.join()

class ImageHandler(FileSystemEventHandler):
    def __init__(self, log_signal):
        self.log_signal = log_signal

    def on_created(self, event):
        if not event.is_directory and self.is_supported_image(event.src_path):
            self.log_signal.emit(f"📷 偵測到新圖片：{event.src_path}")
            self.upload_image(event.src_path)

    def is_supported_image(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        # 只支援已列出的圖片格式
        return ext in SUPPORTED_EXTENSIONS and self.is_image(file_path)

    def is_image(self, file_path):
        try:
            with Image.open(file_path) as img:
                img.verify()  # 驗證圖片是否損壞
            return True
        except (IOError, SyntaxError):
            return False

    def upload_image(self, file_path):
        try:
            ext = os.path.splitext(file_path)[1].lower()
            mime_type = MIME_TYPES.get(ext)
            if mime_type is None:
                self.log_signal.emit(f"❌ 不支援的圖片格式：{ext}")
                return

            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, mime_type)}
                data = {'projectid': DEFAULT_PROJECT_ID}  # 確保有傳 projectid

                # 發送 POST 請求，requests 自動處理 multipart/form-data 的 boundary
                response = requests.post(API_URL, files=files, data=data)
                
                if response.status_code == 200:
                    res_json = response.json()
                    if res_json.get("success"):
                        self.log_signal.emit(f"✅ 上傳成功：{res_json['filename']}\n🌐 URL: {res_json['url']}")
                    else:
                        self.log_signal.emit(f"❌ 上傳失敗：{res_json}")
                else:
                    self.log_signal.emit(f"❌ 上傳失敗 HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_signal.emit(f"⚠️ 錯誤：{e}")

class UploaderApp(QWidget):
    def __init__(self, folder_path):
        super().__init__()
        self.setWindowTitle("📤 圖片即時上傳器")
        self.setGeometry(200, 200, 600, 400)

        self.layout = QVBoxLayout()
        self.label = QLabel(f"監控資料夾：{folder_path}")
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.log)
        self.setLayout(self.layout)

        self.worker = UploadWorker(folder_path)
        self.worker.log_signal.connect(self.log_message)
        self.worker.start()

    def log_message(self, message):
        self.log.append(message)

    def closeEvent(self, event):
        self.worker.stop()
        super().closeEvent(event)

def main():
    if len(sys.argv) < 2:
        print("❗ 請輸入要監控的資料夾路徑作為參數")
        sys.exit(1)

    folder_path = sys.argv[1]
    if not os.path.isdir(folder_path):
        print("❗ 指定的資料夾不存在")
        sys.exit(1)

    app = QApplication(sys.argv)
    uploader_app = UploaderApp(folder_path)
    uploader_app.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
