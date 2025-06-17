# main_attendance_module.py
# FINAL VERSION: Perfectly synced with the corrected CSV data structure.

import threading
import multiprocessing
import queue
import os
import sys
import subprocess
from datetime import datetime
from functools import partial
import pandas as pd
import cv2
import numpy as np
from PIL import Image
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.factory import Factory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _perform_training_work(msg_queue, dataset_path, trainer_path, cascade_path):
    # This worker function is robust and needs no changes.
    # ... (code is identical to the last version)
    try:
        def get_image_labels(path):
            images_path = [os.path.join(path, f) for f in os.listdir(path)]
            face_cascade = cv2.CascadeClassifier(cascade_path)
            face_samples, ids = [], []
            for image_path in images_path:
                try:
                    PIL_img = Image.open(image_path).convert('L'); img_numpy = np.array(PIL_img, 'uint8')
                    face_id = int(os.path.split(image_path)[-1].split("_")[1])
                    faces = face_cascade.detectMultiScale(img_numpy)
                    for (x, y, w, h) in faces:
                        face_samples.append(img_numpy[y:y + h, x:x + w]); ids.append(face_id)
                except Exception: continue
            return face_samples, ids
        if not os.path.isdir(dataset_path) or not os.listdir(dataset_path): msg_queue.put(("message", "Dataset is empty.")); return
        msg_queue.put(("update_status", "Training faces... Please wait."))
        recog = cv2.face.LBPHFaceRecognizer_create(); faces, ids = get_image_labels(dataset_path)
        if not faces: msg_queue.put(("message", "No faces found in dataset.")); return
        recog.train(faces, np.array(ids)); os.makedirs(trainer_path, exist_ok=True)
        recog.write(os.path.join(trainer_path, 'trainer.yml'))
        message = f"Training complete. {len(np.unique(ids))} face(s) trained."
        msg_queue.put(("message", message))
    except Exception as e: msg_queue.put(("message", f"Error in training: {e}"))
    finally: msg_queue.put(("done", None))

if __name__ == "__main__":
    multiprocessing.freeze_support()
    class AttendenceWindow(Screen): pass
    class DatasetWindow(Screen): pass
    class WindowManager(ScreenManager): pass

    class AttendanceModuleApp(App):
        # ... (most of the app class is identical)
        CONFIDENCE_THRESHOLD = 50; REQUIRED_BLINKS = 10; CAM_WIDTH = 1280; CAM_HEIGHT = 720; MSG_DURATION = 5
        running = False; att_thread = None; train_process = None; training_queue = None; queue_check_event = None
        capture_event = None; capture = None; snap_count = 0; snap_target = 0; capture_name = ""; capture_face_id = 0
        STUDENTS_CSV_PATH = os.path.join(BASE_DIR, 'students.csv')
        ATTENDANCE_CSV_PATH = os.path.join(BASE_DIR, 'Attendance', 'attendance.csv') # CORRECTED PATH
        DATASET_PATH = os.path.join(BASE_DIR, 'dataset'); TRAINER_PATH = os.path.join(BASE_DIR, 'trainer')
        CASCADE_FACE_PATH = os.path.join(BASE_DIR, 'haarcascade_frontalface_default.xml')
        CASCADE_EYE_PATH = os.path.join(BASE_DIR, 'haarcascade_eye.xml')

        def build(self):
            Window.clearcolor = (.8, .8, .8, 1); Factory.register('AttendenceWindow', cls=AttendenceWindow); Factory.register('DatasetWindow', cls=DatasetWindow)
            try: root_widget = Builder.load_file("my.kv")
            except Exception as e: print(f"Error: {e}"); sys.exit(1)
            self.title = 'Attendance Module'; self.training_queue = multiprocessing.Queue()
            os.makedirs(self.DATASET_PATH, exist_ok=True); os.makedirs(self.TRAINER_PATH, exist_ok=True); os.makedirs(os.path.dirname(self.ATTENDANCE_CSV_PATH), exist_ok=True)
            return root_widget

        def on_start(self): self.root.get_screen('second').bind(on_enter=self.load_students_for_spinner)
        def on_stop(self):
            self.running = False
            if self.att_thread and self.att_thread.is_alive(): self.att_thread.join(timeout=1)
            if self.train_process and self.train_process.is_alive(): self.train_process.terminate(); self.train_process.join()

        def show_message(self, message, screen="both", duration=None):
            if self.root:
                if screen in ("both", "main"): self.root.get_screen('main').ids.info.text = message
                if screen in ("both", "second"): self.root.get_screen('second').ids.info.text = message
                Clock.schedule_once(self.clear_message, duration or self.MSG_DURATION)
        def clear_message(self, dt):
            if self.root: self.root.get_screen('main').ids.info.text = ""; self.root.get_screen('second').ids.info.text = ""
        def break_loop(self): self.running = False; self.show_message("Process stopped.", "main")
        def startTrain(self):
            if self.train_process and self.train_process.is_alive(): self.show_message("Training already in progress."); return
            self.train_process = multiprocessing.Process(target=_perform_training_work, args=(self.training_queue, self.DATASET_PATH, self.TRAINER_PATH, self.CASCADE_FACE_PATH), daemon=True)
            self.train_process.start()
            if not self.queue_check_event: self.queue_check_event = Clock.schedule_interval(self._check_training_queue, 0.1)
        def _check_training_queue(self, dt):
            try:
                message_type, data = self.training_queue.get_nowait()
                if message_type == "update_status": self.show_message(data, "both", duration=999)
                elif message_type == "message": self.show_message(data, "both")
                elif message_type == "done":
                    if self.queue_check_event: self.queue_check_event.cancel(); self.queue_check_event = None
            except queue.Empty:
                if self.train_process and not self.train_process.is_alive():
                    if self.queue_check_event: self.queue_check_event.cancel(); self.queue_check_event = None
        def startAttendance(self):
            if self.att_thread is None or not self.att_thread.is_alive():
                self.running = True; self.att_thread = threading.Thread(target=self.Attendance, daemon=True); self.att_thread.start()
        def UserList(self): self._open_file(self.STUDENTS_CSV_PATH, "students.csv not found.")
        def AttendanceList(self): self._open_file(self.ATTENDANCE_CSV_PATH, "Attendance file not found.")
        def _open_file(self, file_path, msg):
            if not os.path.exists(file_path): self.show_message(msg); return
            try:
                if sys.platform == "win32": os.startfile(file_path)
                else: subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", file_path])
            except Exception as e: self.show_message(f"Error opening file: {e}")

        def load_students_for_spinner(self, *args):
            try:
                df = pd.read_csv(self.STUDENTS_CSV_PATH)
                active_students = df[df['Status'] != 'Inactive'] # Only show active students
                student_list = [f"{row.FullName} (ID: {row.StudentID})" for _, row in active_students.iterrows()]
                spinner = self.root.get_screen('second').ids.student_spinner; spinner.values = student_list
                spinner.text = "Click to select a student"
            except Exception as e: self.show_message(f"Error loading students: {e}", "second")
        def startDataset(self):
            if self.capture_event: self.show_message("Capture already running."); return
            selected_student_str = self.root.get_screen('second').ids.student_spinner.text
            snap_text = self.root.get_screen('second').ids.snap.text.strip()
            if selected_student_str in ["Click to select a student", ""]: self.show_message("Please select a student."); return
            try: self.snap_target = int(snap_text)
            except ValueError: self.show_message("Snap Amount must be a number."); return
            self.capture_name, self.capture_face_id = self._parse_student_str(selected_student_str)
            if not self.capture_name: return
            self.face_cascade = cv2.CascadeClassifier(self.CASCADE_FACE_PATH)
            if self.face_cascade.empty(): self.show_message("Error: Failed to load face cascade."); return
            self.capture = cv2.VideoCapture(0); self.capture.set(3, self.CAM_WIDTH); self.capture.set(4, self.CAM_HEIGHT)
            self.snap_count = 0; self.capture_event = Clock.schedule_interval(self.update_capture_frame, 1.0 / 30.0)
        def stopDataset(self):
            if self.capture_event: self.capture_event.cancel(); self.capture_event = None
            if self.capture: self.capture.release(); self.capture = None
            if self.root: self.root.get_screen('second').ids.capture_vid.texture = None
            self.show_message("Capture stopped.", "second")
        def _parse_student_str(self, student_str):
            try: name_part, id_part = student_str.rsplit(' (ID: ', 1); return name_part, int(id_part[:-1])
            except ValueError: self.show_message("Invalid student format."); return None, None
        def update_capture_frame(self, dt):
            if not self.capture or not self.capture.isOpened(): return
            ret, frame = self.capture.read()
            if not ret: return
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY); faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                if self.snap_count < self.snap_target:
                    self.snap_count += 1; simple_name = self.capture_name.split(" ")[0]
                    image_path = os.path.join(self.DATASET_PATH, f"{simple_name}_{self.capture_face_id}_{self.snap_count}.jpg")
                    cv2.imwrite(image_path, gray[y:y + h, x:x + w]); self.show_message(f"Captured {self.snap_count}/{self.snap_target}", "second", duration=2)
            if self.snap_count >= self.snap_target: self.show_message(f"Capture complete for {self.capture_name}."); self.stopDataset()
            buf = cv2.flip(frame, 0).tobytes(); texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte'); self.root.get_screen('second').ids.capture_vid.texture = texture
        def Attendance(self):
            try: user_id = int(self.root.get_screen('main').ids.user_id.text)
            except ValueError: Clock.schedule_once(lambda dt: self.show_message("Invalid User ID.", "main")); return
            trainer_file = os.path.join(self.TRAINER_PATH, 'trainer.yml')
            if not os.path.exists(trainer_file): Clock.schedule_once(lambda dt: self.show_message("Training file not found.")); return
            face_cascade = cv2.CascadeClassifier(self.CASCADE_FACE_PATH); eye_cascade = cv2.CascadeClassifier(self.CASCADE_EYE_PATH)
            if face_cascade.empty() or eye_cascade.empty(): Clock.schedule_once(lambda dt: self.show_message("Cascade files not found.")); return
            recog = cv2.face.LBPHFaceRecognizer_create(); recog.read(trainer_file)
            blink = 0; attendance_marked = False; camera = cv2.VideoCapture(0)
            camera.set(3, self.CAM_WIDTH); camera.set(4, self.CAM_HEIGHT)
            while self.running:
                ret, frame = camera.read()
                if not ret: continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY); faces = face_cascade.detectMultiScale(gray, 1.2, 5)
                current_face_recognized = False
                for (x, y, w, h) in faces:
                    label, confidence = recog.predict(gray[y:y+h, x:x+w])
                    if label == user_id and confidence < self.CONFIDENCE_THRESHOLD:
                        current_face_recognized = True
                        try:
                            df = pd.read_csv(self.STUDENTS_CSV_PATH); name = df.loc[df['StudentID'] == user_id, 'FullName'].iloc[0]
                        except Exception: name = "Known User"
                        roi_gray = gray[y:y + h, x:x + w]; eyes = eye_cascade.detectMultiScale(roi_gray, 1.1, 5)
                        if len(eyes) < 2: blink += 1
                        if blink > self.REQUIRED_BLINKS:
                            Clock.schedule_once(lambda dt, n=name: self.show_message(f"Attendance marked for {n}!", "main"))
                            Clock.schedule_once(lambda dt: self._record_attendance(user_id, name))
                            attendance_marked = True; self.running = False; break
                if not current_face_recognized: blink = 0
                if self.root: self.display_frame(frame)
                if attendance_marked: break
            camera.release(); cv2.destroyAllWindows()
            if self.root: self.display_frame(np.zeros((1, 1, 3), dtype=np.uint8))
        def _record_attendance(self, user_id, name):
            now = datetime.now(); date_str = now.strftime("%Y-%m-%d")
            try:
                try: df_att = pd.read_csv(self.ATTENDANCE_CSV_PATH)
                except FileNotFoundError: df_att = pd.DataFrame(columns=['StudentID', 'FullName'])
                if 'FullName' not in df_att.columns: df_att.insert(1, 'FullName', '')
                if date_str not in df_att.columns: df_att[date_str] = 'Absent'
                if user_id not in df_att['StudentID'].values:
                    new_row = pd.DataFrame([{'StudentID': user_id, 'FullName': name}])
                    df_att = pd.concat([df_att, new_row], ignore_index=True).fillna('Absent')
                df_att.loc[df_att['StudentID'] == user_id, 'FullName'] = name
                df_att.loc[df_att['StudentID'] == user_id, date_str] = 'Present'
                df_att.to_csv(self.ATTENDANCE_CSV_PATH, index=False)
            except Exception as e: self.show_message(f"Error writing attendance: {e}", "main")
        def display_frame(self, frame, dt=None):
            if self.root:
                buf = cv2.flip(frame, 0).tobytes(); texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
                texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte'); self.root.get_screen('main').ids.vid.texture = texture
    AttendanceModuleApp().run()