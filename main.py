from PyQt5.QtWidgets import QApplication, QDialog, QGraphicsScene, QGraphicsPixmapItem, QListWidget, QListWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from camera_ui import Ui_Dialog
from attendance_taker import Face_Recognizer
import sys
import cv2

def gstreamer_pipeline(
    sensor_id=0,
    capture_width=1280,
    capture_height=720,
    display_width=1280,
    display_height=720,
    framerate=30,
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

    def __init__(self, face_recognizer):
        super(CameraThread, self).__init__()
        self.running = True
        self.face_recognizer = face_recognizer
        
        
    def run(self):
        cap = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)
        while self.running:
            ret, frame = cap.read()
            if ret:
                process_frame = self.face_recognizer.process_frame(frame)
                    
                height, width, channel = process_frame.shape
                bytesPerLine = 3 * width
                image = QImage(process_frame.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
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
        
        self.face_recognizer = Face_Recognizer()
        self.cameraThread = CameraThread(self.face_recognizer)
        self.cameraThread.signal.connect(self.update_frame)

        self.ui.startButton.clicked.connect(self.start_camera)
        self.ui.stopButton.clicked.connect(self.stop_camera)
        self.ui.savedButton.clicked.connect(self.saved_button_clicked)
        '''self.timer = QTimer()
        self.timer.timeout.connect(self.update_view)
        self.frame_rate = 30
        self.timer_interval = int(1000/self.frame_rate)
        '''
        #self.current_image = None
        self.scene = QGraphicsScene()
        self.pixmap_item = QGraphicsPixmapItem()   
        self.scene.addItem(self.pixmap_item)
        self.ui.graphicsView.setScene(self.scene) 
        

    def start_camera(self):
        print("Start button clicked")
        if not self.cameraThread.isRunning():
            self.cameraThread.running = True
            self.cameraThread.start()
            #self.timer.start(self.timer_interval)
            
    def stop_camera(self):
        print("Stop button clicked")
        if self.cameraThread.isRunning():
            self.cameraThread.signal.disconnect(self.update_frame) #stop update frame onto graphics view
            self.cameraThread.stop()        #stop camera thread
            self.clear_graphics_view()      #clear graphics view
            self.cameraThread.signal.connect(self.update_frame)  # Reconnect the signal for future use
            #self.timer.stop()               #stop timer

    def saved_button_clicked(self):
        print("Saved button clicked")
    
    '''def update_frame(self, frame):
        self.current_image = frame
    '''
    def update_frame(self, frame):
        if frame is not None:
            pixmap = QPixmap.fromImage(frame)
            pixmap = pixmap.scaled(self.ui.graphicsView.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            '''scene = QGraphicsScene()
            scene.addPixmap(pixmap)
            self.ui.graphicsView.setScene(scene)
            '''
            self.pixmap_item.setPixmap(pixmap)
        else:
            print("No frame to display")
    
    def clear_graphics_view(self):
        #self.ui.graphicsView.setScene(QGraphicsScene())  # Clear the QGraphicsView
        self.pixmap_item.setPixmap(QPixmap())  # Clear the current frame

def main():
    app = QApplication(sys.argv)
    window = Dialog()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
