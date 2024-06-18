from PyQt5.QtWidgets import QApplication, QDialog, QGraphicsView, QGraphicsScene, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap
from camera_ui import Ui_Dialog
import sys
import cv2

def gstreamer_pipeline(
    sensor_id=0,
    capture_width=320,
    capture_height=240,
    display_width=640,
    display_height=480,
    framerate=60,
    flip_method=0,
):
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, framerate=(fraction){framerate}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! "
        f"videoconvert ! "
        f"video/x-raw, format=(string)BGR ! appsink"
    )

class CameraThread(QThread):
    signal = pyqtSignal(QImage)

    def __init__(self):
        super(CameraThread, self).__init__()
        self.running = True
        
    def run(self):
        cap = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)
        while self.running:
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, (640, 480))
                height, width, channel = frame.shape
                bytesPerLine = 3 * width
                image = QImage(frame.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
                self.signal.emit(image)
            else:
                break
        cap.release()
    
    def stop(self):
        self.running = False
        self.wait()  # Ensure the thread stops completely

class Dialog(QDialog):
    def __init__(self, parent=None):
        super(Dialog, self).__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        
        self.cameraThread = CameraThread()
        self.cameraThread.signal.connect(self.update_frame)

        self.ui.startButton.clicked.connect(self.start_camera)
        self.ui.stopButton.clicked.connect(self.stop_camera)
        self.ui.savedButton.clicked.connect(self.saved_button_clicked)

    def start_camera(self):
        if not self.cameraThread.isRunning():
            self.cameraThread.running = True
            self.cameraThread.start()

    def stop_camera(self):
        print("Stop button clicked")
        if self.cameraThread.isRunning():
            self.cameraThread.signal.disconnect(self.update_frame) #stop update frame onto graphics view
            self.cameraThread.stop()        #stop camera thread
            self.clear_graphics_view()      #clear graphics view
            self.cameraThread.signal.connect(self.update_frame)  # Reconnect the signal for future use

    def saved_button_clicked(self):
        print("Saved button clicked")

    def update_frame(self, image):
        scene = QGraphicsScene()
        pixmap = QPixmap.fromImage(image)
        pixmap = pixmap.scaled(self.ui.graphicsView.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scene.addPixmap(pixmap)
        self.ui.graphicsView.setScene(scene)
    
    def clear_graphics_view(self):
        self.ui.graphicsView.setScene(QGraphicsScene())  # Clear the QGraphicsView

def main():
    app = QApplication(sys.argv)
    window = Dialog()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
