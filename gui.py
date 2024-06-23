from flask import Flask, Response, jsonify, send_file
import cv2, os
import threading
import logging
import time
import atexit
from attendance_taker import Face_Recognizer

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

camera = None
frame = None
lock = threading.Lock()
capture_thread = None
stop_event = threading.Event()
face_recognition = None

def gstreamer_pipeline(
    sensor_id=0,
    capture_width=640,
    capture_height=480,
    display_width=1280,
    display_height=720,
    framerate=24,
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
        f"video/x-raw, format=(string)BGR ! "
        f"queue ! "
        f"appsink"
    )
    
output_dir = 'videos/'
os.makedirs(output_dir, exist_ok=True)

paused = False 
 
def capture_frames():
    global camera, frame, lock, stop_event, face_recognition
    out = None
    try:
        while not stop_event.is_set():
            if camera.isOpened():
                ret, new_frame = camera.read()
                if ret:
                    with lock:
                        processed_frame = face_recognition.process(new_frame.copy())
                        frame = processed_frame
                    if out is None:
                        output_path = get_next_filename(output_dir)
                        fourcc = cv2.VideoWriter_fourcc(*'hvc1')  # Use mp4v for H.264, hvc1: h265
                        out = cv2.VideoWriter(output_path, fourcc, 20, (1280, 720))
                        if not out.isOpened():
                            logging.error("Failed to open VideoWriter.")
                            break
                    out.write(new_frame)
                else:
                    logging.error("Failed to capture frame.")
                    break
            else:
                logging.error("Camera not opened.")
                break
            time.sleep(0.03)
    except Exception as e:
        logging.error(f"Error capturing frame: {e}")
    finally:
        if out is not None:
            out.release()
            logging.info("VideoWriter released.")
 
def get_next_filename(directory):
    """Generate the next available filename in the given directory."""
    existing_files = os.listdir(directory)
    if not existing_files:
        return os.path.join(directory, 'output1.mp4')
    else:
        # Find the highest numbered outputX.mp4 file and increment
        max_number = max([int(file.split('output')[1].split('.')[0]) for file in existing_files if file.startswith('output')])
        next_number = max_number + 1
        return os.path.join(directory, f'output{next_number}.mp4')       
    
@app.route('/')
def index():
    return send_file('gui.html')

def generate_frames():
    global frame, lock, stop_event
    while not stop_event.is_set():
        with lock:
            if frame is not None:
                ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                else:
                    logging.error("Failed to encode frame.")
            else:
                logging.debug("No frame available.")
        time.sleep(0.03)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start', methods=['POST'])
def start_camera():
    print("START BUTTON IS CLICKED")
    global camera, capture_thread, stop_event, face_recognition
    
    if camera is None or not capture_thread.is_alive():
        if camera:
            camera.release()
            camera = None
            
        camera = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)
        if not camera.isOpened():
            logging.error("Failed to open camera.")
            return jsonify(status='Failed to open camera'), 500
        
        face_recognition = Face_Recognizer()
        stop_event.clear()
        capture_thread = threading.Thread(target=capture_frames)
        capture_thread.start()
        
        return jsonify(status='Camera started')
    else:
        return jsonify(status='Camera already started')

@app.route('/stop', methods=['POST'])
def stop_camera():
    print("STOP BUTTON IS CLICKED")
    global camera, stop_event, capture_thread, face_recognition
    try:
        stop_event.set()  # Signal capture thread to stop
        if capture_thread and capture_thread.is_alive():
            capture_thread.join(timeout=1)  # Wait for thread to terminate with timeout
            
        if face_recognition:
            face_recognition = None
            
        if camera:
            camera.release()  # Release camera resource
            camera = None
        return jsonify(status='Camera stopped')
    except Exception as e:
        logging.error(f"Error stopping camera: {e}")
        return jsonify(status='Error stopping camera', error=str(e)), 500
    
@app.route('/view_saved', methods=['GET'])
def view_saved():
    print("VIEW BUTTON IS CLICKED")
    try:
        saved_videos = [f for f in os.listdir(output_dir) if f.endswith('.mp4')]
        return jsonify(status='Success', saved_videos=saved_videos)
    except Exception as e:
        logging.error(f"Error retrieving saved videos: {e}")
        return jsonify(status='Error', error=str(e)), 500
    
def generate_frames_from_file(filename):
    try:
        cap = cv2.VideoCapture(os.path.join(output_dir, filename))
        if not cap.isOpened():
            logging.error("Failed to open video file.")
            return

        global paused

        while cap.isOpened():
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    break

                # Resize frame to 480x360
                resized_frame = cv2.resize(frame, (480, 360))

                ret, jpeg = cv2.imencode('.jpg', resized_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                else:
                    logging.error("Failed to encode frame.")
                time.sleep(0.03)
            else:
                time.sleep(1)  # Sleep to reduce CPU usage when paused

        cap.release()
    except Exception as e:
        logging.error(f"Error generating frames from file: {e}")


@app.route('/videos/<filename>')
def get_video(filename):
    return send_file(os.path.join(output_dir, filename))

@app.route('/play_video/<filename>')
def play_video(filename):
    global paused
    if paused:
        paused = False  # Resume playback
    return Response(generate_frames_from_file(filename), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_pause', methods=['POST'])
def toggle_pause():
    global paused
    paused = not paused  # Toggle pause state
    return "Paused" if paused else "Resumed"

# Graceful shutdown function to release resources
def graceful_shutdown():
    global camera, capture_thread, face_recognition
    logging.info("Performing graceful shutdown...")
    try:
        stop_event.set()  # Signal capture thread to stop
        if capture_thread and capture_thread.is_alive():
            capture_thread.join(timeout=1)  # Wait for thread to terminate
        
        if face_recognition:
            face_recognition = None
            
        if camera:
            camera.release()  # Release camera resource
            camera = None
        logging.info("Shutdown completed.")
    except Exception as e:
        logging.error(f"Error during shutdown: {e}")

# Register graceful_shutdown function to be called when Python interpreter exits
atexit.register(graceful_shutdown)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
