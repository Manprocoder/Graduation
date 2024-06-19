from flask import Flask, Response, jsonify, send_file, request
import cv2
import threading
import logging
import time
from attendance_taker import Face_Recognizer

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

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
        f"queue ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"queue ! "
        f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! "
        f"videoconvert ! "
        f"queue ! "
        f"video/x-raw, format=(string)BGR ! appsink"
    )

camera = None
frame = None
lock = threading.Lock()
capture_thread = None
stop_event = threading.Event()

# Instantiate your FaceRecognizer class
face_recognizer = None
frame_skip = 5  # Process every 5th frame
frame_count = 0


def capture_frames():
    global camera, frame, lock, stop_event, frame_count
    while not stop_event.is_set():
        with lock:
            if camera is not None:
                ret, new_frame = camera.read()
                if ret:
                    frame_count += 1
                    if frame_count % frame_skip == 0:
                        if face_recognizer is not None:
                            frame = face_recognizer.process_frame(new_frame)  # Process the frame
                        else:
                            frame = new_frame
                    else:
                        frame = new_frame
                else:
                    logging.error("Failed to read frame from camera.")
        time.sleep(0.03)  # Add delay to reduce CPU usage


@app.route('/')
def index():
    return send_file('gui.html')

@app.route('/start', methods=['POST'])
def start_camera():
    global camera, capture_thread, stop_event, face_recognizer
    if camera is None:
        try:
            camera = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)
            if not camera.isOpened():
                raise RuntimeError("Could not open camera.")
            stop_event.clear()
            face_recognizer = Face_Recognizer()
            capture_thread = threading.Thread(target=capture_frames)
            capture_thread.start()
            return jsonify(status='Camera started')
        except Exception as e:
            logging.error(f"Error starting camera: {e}")
            return jsonify(status='Error starting camera', error=str(e)), 500
    return jsonify(status='Camera already started')

@app.route('/stop', methods=['POST'])
def stop_camera():
    global camera, frame, stop_event, capture_thread, face_recognizer
    with lock:
        if camera is not None:
            stop_event.set()
            capture_thread.join()
            camera.release()
            camera = None
            frame = None
            face_recognizer = None
    return jsonify(status='Camera stopped')

def generate_frames():
    global frame, lock
    while True:
        with lock:
            if frame is not None:
                ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    logging.debug("Frame encoded successfully.")
                    yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                else:
                    logging.error("Failed to encode frame.")
            else:
                logging.debug("No frame available.")
        time.sleep(0.03)        #add delay to reduce CPU usage    

@app.route('/video_feed')
def video_feed():
    try:
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        logging.error(f"Error generating video feed: {e}")
        return jsonify(status='Error generating video feed', error=str(e)), 500

@app.route('/view_saved', methods=['POST'])
def view_saved():
    # Placeholder for the /view_saved functionality
    return jsonify(status='Not implemented'), 501

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)