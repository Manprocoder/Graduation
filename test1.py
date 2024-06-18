import tkinter as tk
import cv2
from tkinter import messagebox
from get_faces_from_camera_tkinter import main as function1
from features_extraction_to_csv import main as img_to_csv
from test2 import Face_Recognizer
from PIL import Image, ImageTk

def run_function1():
    function1()
    messagebox.showinfo("Information", "Function 1 has been run")

def run_img_to_csv():
    img_to_csv()
    messagebox.showinfo("Information", "Image has been converted to CSV files")

def run_attendance_taker():
    face_recognizer = Face_Recognizer()
    face_recognizer.run_with_label(label_camera)  # Pass the label to the attendance taker
    messagebox.showinfo("Information", "Attendance taker has been run")

# Initialize main window
root = tk.Tk()
root.title("Face Register and Attendance System")
root.geometry("1000x500")

# Left frame for camera
frame_left_camera = tk.Frame(root, width=640, height=480)
frame_left_camera.pack(side=tk.LEFT, padx=10, pady=10)

# Right frame for buttons
frame_right_buttons = tk.Frame(root)
frame_right_buttons.pack(side=tk.RIGHT, padx=10, pady=10)

# Create and pack buttons in the right frame
button1 = tk.Button(frame_right_buttons, text="Run function 1", command=run_function1)
button1.pack(pady=5)

button2 = tk.Button(frame_right_buttons, text="Run function 2", command=run_img_to_csv)
button2.pack(pady=5)

button3 = tk.Button(frame_right_buttons, text="Run Attendance Taker", command=run_attendance_taker)
button3.pack(pady=5)

# Camera frame label
label_camera = tk.Label(frame_left_camera)
label_camera.pack()


# Start main loop
root.mainloop()

