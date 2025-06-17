# student_SIS.py
# FINAL VERSION v2: Includes a comprehensive dashboard AND full Nextcloud integration.

import streamlit as st
import pandas as pd
import os
import plotly.express as px
from nextcloud_sync import upload_file_to_nextcloud, download_file_from_nextcloud

st.set_page_config(page_title="ERP - SIS", page_icon="🧑‍🎓", layout="wide")

# --- File Paths & Columns ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENTS_CSV_PATH = os.path.join(BASE_DIR, 'students.csv')
FEES_CSV_PATH = os.path.join(BASE_DIR, 'fees.csv')
GRADES_CSV_PATH = os.path.join(BASE_DIR, 'grades.csv')
ATTENDANCE_CSV_PATH = os.path.join(BASE_DIR, 'Attendance', 'attendance.csv')

STUDENT_COLS = ['StudentID', 'FullName', 'DateOfBirth', 'Email', 'Major', 'Status']
FEE_COLS = ['StudentID', 'TotalFees', 'AmountPaid', 'DueDate']
GRADE_COLS = ['GradeID', 'StudentID', 'Subject', 'ExamType', 'Score', 'Grade', 'Date']
ATTENDANCE_COLS = ['StudentID', 'FullName']

# --- Helper Functions ---
@st.cache_data
def load_data(file_path, columns):
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df = pd.DataFrame(columns=columns)
        df.to_csv(file_path, index=False)
        return df
    return pd.read_csv(file_path)

def save_data(df, file_path, upload=True):
    """Saves data locally and automatically uploads to Nextcloud by default."""
    df.to_csv(file_path, index=False)
    st.cache_data.clear()
    if upload:
        with st.spinner(f"Syncing {os.path.basename(file_path)} to cloud..."):
            success, message = upload_file_to_nextcloud(file_path)
            if success: st.toast("☁️ Synced to cloud!")
            else: st.toast(f"☁️ Cloud sync failed: {message}", icon="❌")

# --- AUTOMATION FUNCTIONS ---
def sync_all_modules_for_new_student(student_id, full_name):
    # This function now leverages the enhanced save_data to auto-upload
    df = load_data(FEES_CSV_PATH, FEE_COLS)
    if student_id not in df['StudentID'].values:
        new_record = pd.DataFrame([{'StudentID': student_id, 'TotalFees': 0.0, 'AmountPaid': 0.0, 'DueDate': None}])
        df = pd.concat([df, new_record], ignore_index=True)
        save_data(df, FEES_CSV_PATH)

    df = load_data(ATTENDANCE_CSV_PATH, ATTENDANCE_COLS)
    if student_id not in df['StudentID'].values:
        new_record = pd.DataFrame([{'StudentID': student_id, 'FullName': full_name}])
        df = pd.concat([df, new_record], ignore_index=True)
        save_data(df, ATTENDANCE_CSV_PATH, upload=False) # No need to upload this one, it's derived
        upload_file_to_nextcloud(ATTENDANCE_CSV_PATH, remote_folder='Attendance')


def sync_name_change(student_id, new_full_name):
    df = load_data(ATTENDANCE_CSV_PATH, ATTENDANCE_COLS)
    if student_id in df['StudentID'].values:
        df.loc[df['StudentID'] == student_id, 'FullName'] = new_full_name
        save_data(df, ATTENDANCE_CSV_PATH, upload=False)
        upload_file_to_nextcloud(ATTENDANCE_CSV_PATH, remote_folder='Attendance')

# --- Main App ---
st.title("🧑‍🎓 Student Information System (SIS)")

# --- CLOUD SYNC IN SIDEBAR ---
st.sidebar.header("☁️ Cloud Sync")
if st.sidebar.button("Pull Latest Data from Cloud", key="sis_pull"):
    with st.spinner("Downloading all relevant ERP data..."):
        # This module is central, so it pulls all key data.
        s1, m1 = download_file_from_nextcloud(STUDENTS_CSV_PATH)
        s2, m2 = download_file_from_nextcloud(FEES_CSV_PATH)
        s3, m3 = download_file_from_nextcloud(GRADES_CSV_PATH)
        s4, m4 = download_file_from_nextcloud(ATTENDANCE_CSV_PATH, remote_folder='Attendance')
        st.sidebar.success("All data refreshed!")
        st.rerun()

# Load main student data
students_df = load_data(STUDENTS_CSV_PATH, STUDENT_COLS)

if 'Status' not in students_df.columns:
    students_df['Status'] = 'Active'
    save_data(students_df, STUDENTS_CSV_PATH)

tab_dash, tab_view, tab_add, tab_edit = st.tabs(["📊 Dashboard", "View Roster", "Add Student", "Edit/Deactivate Student"])

# ... (All dashboard, add, edit, and view logic remains exactly the same as before) ...