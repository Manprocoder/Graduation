from threading import Thread
import cv2
import logging
from tkinter import *
from PIL import Image, ImageTk
import numpy as np
from attendance_taker import Face_Recognizer, gstreamer_pipeline

def process(self, stream):
    if self.get_face_database():
        while stream.isOpened():
            self.frame_cnt += 1
            flag, img_rd = stream.read()
            if not flag:
                break
            
            img_rd = cv2.cvtColor(img_rd, cv2.COLOR_BGR2RGB)
            img_rd = Image.fromarray(img_rd)
            img_rd.thumbnail((640, 480), Image.ANTIALIAS)
            img_rd = ImageTk.PhotoImage(img_rd)

            # Update the UI
            panel.configure(image=img_rd)
            panel.image = img_rd

            root.update_idletasks()
            root.update()

            kk = cv2.waitKey(1)
            if kk == ord('q'):
                break

            self.update_fps()

        stream.release()
        cv2.destroyAllWindows()

def create_ui():
    global root, panel, start_button

    root = Tk()
    root.title("Face Recognition Application")

    # Buttons frame on the right
    button_frame = Frame(root)
    button_frame.pack(side="right", padx=10, pady=10)

    # Start Application button
    start_button = Button(button_frame, text="Start Application", command=start_application)
    start_button.pack(side="top", padx=10, pady=10)

    # Quit button
    quit_button = Button(button_frame, text="Quit", command=root.quit)
    quit_button.pack(side="top", padx=10, pady=10)

    root.mainloop()

def start_application():
    cap = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)
    Face_Recognizer_con = Face_Recognizer()
    Face_Recognizer_con.process(cap)
    cap.release()
    cv2.destroyAllWindows()


def main():
    logging.basicConfig(level=logging.INFO)

    # Create UI in a separate thread
    ui_thread = Thread(target=create_ui)
    ui_thread.start()

if __name__ == '__main__':
    main()

