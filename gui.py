from flask import (
    Flask,
    Response,
    jsonify,
    send_file,
    render_template,
    request,
    make_response,
)
import cv2, os
import threading
import logging
import subprocess
import time
import atexit
import sqlite3
from datetime import datetime
import json
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
paused = False
out = None  # -- it is used to store video file
filename = None
ffmpeg_process = None
total_frames = 0
frame_count = 0


def gstreamer_pipeline(
    sensor_id=0,
    capture_width=640,
    capture_height=480,
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
        f"video/x-raw, format=(string)BGR ! "
        f"queue ! "
        f"appsink"
    )


output_dir = "videos/"
os.makedirs(output_dir, exist_ok=True)


class VideoDurationFetcher:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.video_durations = {}
        os.makedirs(self.output_dir, exist_ok=True)
        self.fetch_all_video_durations()
        self.start_periodic_refresh()

    def fetch_all_video_durations(self):
        self.video_durations = {}
        for filename in os.listdir(self.output_dir):
            if filename.endswith(".mp4"):
                video_path = os.path.join(self.output_dir, filename)
                duration = self.get_video_duration_from_file(video_path)
                if duration is not None:
                    self.video_durations[filename] = duration

    def get_video_duration_from_file(self, video_path):
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            video_path,
        ]
        try:
            result = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            if result.returncode == 0:
                duration_info = json.loads(result.stdout)
                duration = float(duration_info["format"]["duration"])
                return duration
            else:
                error_message = result.stderr.decode("utf-8").strip()
                print(f"Failed to get duration for {video_path}: {error_message}")
                return None
        except Exception as e:
            print(
                f"Exception occurred while getting duration for {video_path}: {str(e)}"
            )
            return None

    def start_periodic_refresh(self):
        def periodic_refresh():
            while True:
                self.fetch_all_video_durations()
                time.sleep(60)

        thread = threading.Thread(target=periodic_refresh, daemon=True)
        # daemon = True: class run independtly and does not block main program
        thread.start()


# -- end of class VideoDurationFetcher
# Create instance of VideoDurationFetcher
video_duration_fetcher = VideoDurationFetcher(output_dir)


# this function is used for writing video into file with h265 codec
def start_ffmpeg_process(output_path, width, height, fps=20):
    command = [
        "ffmpeg",
        "-y",  # Overwrite output file if it exists
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",  # Input comes from stdin
        "-c:v",
        "libx265",  # Use libx265 for H.265 encoding
        "-pix_fmt",
        "yuv420p",
        output_path,
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE)


def capture_frames():
    global camera, frame, lock, stop_event, face_recognition, out, filename, ffmpeg_process

    # Set capture properties
    capture_width = 1280
    capture_height = 720
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, capture_width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, capture_height)

    # out = None
    # filename = None

    try:
        while not stop_event.is_set():
            if camera.isOpened():
                ret, new_frame = camera.read()
                if ret:
                    with lock:
                        processed_frame = face_recognition.process(new_frame.copy())
                        frame = processed_frame

                    """if out is None:
                        filename = get_next_filename(output_dir)
                        out = cv2.VideoWriter(
                            filename,
                            cv2.VideoWriter_fourcc(*"hevc"),
                            20,
                            (capture_width, capture_height),
                        )

                    # Write processed frame to the video file
                    out.write(new_frame)
                    """
                    if ffmpeg_process is None:
                        filename = get_next_filename(output_dir)
                        ffmpeg_process = start_ffmpeg_process(
                            filename, capture_width, capture_height
                        )

                    # Write raw frame to ffmpeg stdin
                    if ffmpeg_process is not None:
                        ffmpeg_process.stdin.write(new_frame.tobytes())

                else:
                    logging.error("Failed to capture frame.")
                    break
            else:
                logging.error("Camera not opened.")
                break
            time.sleep(0.03)
    except Exception as e:
        logging.error(f"Error capturing frame: {e}")


def get_next_filename(directory):
    """Generate the next available filename in the given directory."""
    existing_files = os.listdir(directory)
    if not existing_files:
        return os.path.join(directory, "output1.mp4")
    else:
        # Find the highest numbered outputX.mp4 file and increment
        max_number = max(
            [
                int(file.split("output")[1].split(".")[0])
                for file in existing_files
                if file.startswith("output")
            ]
        )
        next_number = max_number + 1
        return os.path.join(directory, f"output{next_number}.mp4")


@app.route("/")
def index():
    return render_template("gui.html")


@app.route("/index")
def second_page():
    return render_template("index.html", selected_date="", no_data=False)


# -----------------------------------------------------------------------------------------
# this function is used for index.html
@app.route("/attendance", methods=["POST"])
def attendance():
    selected_date = request.form.get("selected_date")
    selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d")
    formatted_date = selected_date_obj.strftime("%Y-%m-%d")

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name, time FROM attendance WHERE date = ?", (formatted_date,)
    )
    attendance_data = cursor.fetchall()

    conn.close()

    if not attendance_data:
        return render_template("index.html", selected_date=selected_date, no_data=True)

    return render_template(
        "index.html", selected_date=selected_date, attendance_data=attendance_data
    )


# ---------------------------------------------------------------------------------------


def generate_frames():
    global frame, lock, stop_event
    while not stop_event.is_set():
        with lock:
            if frame is not None:
                ret, jpeg = cv2.imencode(
                    ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                )
                if ret:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
                    )
                else:
                    logging.error("Failed to encode frame.")
            else:
                logging.debug("No frame available.")
        time.sleep(0.03)


@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/start", methods=["POST"])
def start_camera():
    print("START BUTTON IS CLICKED")
    global camera, capture_thread, stop_event, face_recognition, frame, lock

    try:
        with lock:
            if camera is None or not capture_thread.is_alive():
                if camera:
                    stop_camera_internal()  # Ensure camera is stopped and resources released
                    time.sleep(1)  # Give time for threads to release resources properly

                camera = cv2.VideoCapture(0)
                if not camera.isOpened():
                    logging.error("Failed to open camera.")
                    return jsonify(status="Failed to open camera"), 500

                face_recognition = Face_Recognizer()
                stop_event.clear()

                capture_thread = threading.Thread(target=capture_frames)
                capture_thread.start()

                return jsonify(status="Camera started")
            else:
                return jsonify(status="Camera already started")

    except Exception as e:
        logging.error(f"Error starting camera: {e}")
        return jsonify(status="Error starting camera", error=str(e)), 500


# clear all before staring new camera instance
def stop_camera_internal():
    global camera, capture_thread, face_recognition, frame, stop_event, ffmpeg_process

    if camera is not None:
        camera.release()
        camera = None
        frame = None

    if ffmpeg_process is not None:
        ffmpeg_process.stdin.close()
        ffmpeg_process.wait()
        ffmpeg_process = None


@app.route("/stop", methods=["POST"])
def stop_camera():
    print("STOP BUTTON IS CLICKED")
    global camera, frame, stop_event, capture_thread, face_recognition, out, ffmpeg_process
    try:
        with lock:
            if camera is not None:
                stop_event.set()
                if capture_thread:
                    capture_thread.join()  # Wait for thread to stop
                camera.release()
                camera = None
                face_recognition = None
                capture_thread = None
                frame = None

                """if out is not None:
                    out.release()
                    logging.info(f"Video saved as {filename}")
                """

                if ffmpeg_process is not None:
                    ffmpeg_process.stdin.close()
                    ffmpeg_process.wait()
                    ffmpeg_process = None

        return jsonify(status="Camera stopped")
    except Exception as e:
        logging.error(f"Error stopping camera: {e}")
        return jsonify(status="Error stopping camera", error=str(e)), 500


@app.route("/register", methods=["POST"])
def register():
    print("REGISTER BUTTON IS CLICKED")


# ---------------------------------------------------------------------------
# code below is used for displaying video from file (additional camera view of GUI)
# ---------------------------------------------------------------------------


@app.route("/view_saved", methods=["GET"])
def view_saved():
    print("VIEW BUTTON IS CLICKED")
    global frame_count
    frame_count = 0
    try:
        saved_videos = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
        return jsonify(status="Success", saved_videos=saved_videos)
    except Exception as e:
        logging.error(f"Error retrieving saved videos: {e}")
        return jsonify(status="Error", error=str(e)), 500


# display video onto gui from video file
def generate_frames_from_file(filename):
    global total_frames, frame_count
    try:
        frame_count = 0
        cap = cv2.VideoCapture(os.path.join(output_dir, filename))
        if not cap.isOpened():
            logging.error("Failed to open video file.")
            return
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        while cap.isOpened():
            global paused
            # Check if either paused or current_pause is True
            while paused:
                # Sleep to reduce CPU usage when paused
                time.sleep(1)
            ret, frame = cap.read()
            if not ret:
                break

            # Resize frame to 480x360
            resized_frame = cv2.resize(frame, (480, 360))

            ret, jpeg = cv2.imencode(
                ".jpg", resized_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            )
            if ret:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
                )
                frame_count += 1
            else:
                logging.error("Failed to encode frame.")

            time.sleep(0.03)

        cap.release()
    except Exception as e:
        logging.error(f"Error generating frames from file: {e}")


@app.route("/play_video/<filename>")
def play_video(filename):
    global paused, frame_count, total_frames
    total_frames = 0
    frame_count = 0
    if paused:
        paused = False  # Resume playback

    return Response(
        generate_frames_from_file(filename),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/slider_update", methods=["GET"])
def slider_update():
    global frame_count, total_frames
    print("frame_total: ", total_frames)
    print("frame count: ", frame_count)
    # Calculate the progress as a percentage
    if total_frames > 0 and frame_count != 0:
        progress = frame_count / total_frames
    else:
        progress = 0

    # Create the JSON response with the correct Content-Type header
    response = make_response(jsonify({"status": "success", "progress": progress}))
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


@app.route("/toggle_pause", methods=["POST"])
def toggle_pause():
    global paused
    paused = not paused  # Toggle pause state
    return "▶️" if paused else "||"


@app.route("/get_video_duration", methods=["GET"])
def get_video_duration():
    filename = request.args.get("filename")  # Get filename from query parameters

    if filename in video_duration_fetcher.video_durations:
        return jsonify(
            {
                "filename": filename,
                "duration": video_duration_fetcher.video_durations[filename],
            }
        )
    else:
        video_path = os.path.join(output_dir, filename)
        if not os.path.isfile(video_path):
            return jsonify({"error": f"Video file not found: {video_path}"}), 404

        duration = video_duration_fetcher.get_video_duration_from_file(video_path)
        if duration is not None:
            video_duration_fetcher.video_durations[filename] = duration
            return jsonify({"filename": filename, "duration": duration})
        else:
            return jsonify({"error": f"Failed to get duration for {filename}"}), 500


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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
