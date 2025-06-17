# library_system.py
# ENHANCED: Now checks student's fee status before issuing a book.

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="ERP - Library Management",
    page_icon="📚",
    layout="wide"
)

# --- File Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIBRARY_CSV_PATH = os.path.join(BASE_DIR, 'library.csv')
STUDENTS_CSV_PATH = os.path.join(BASE_DIR, 'students.csv')
FEES_CSV_PATH = os.path.join(BASE_DIR, 'fees.csv')

# --- Helper Functions (assuming similar ones exist) ---
@st.cache_data
def load_data(file_path, columns):
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=columns)
        df.to_csv(file_path, index=False)
        return df
    return pd.read_csv(file_path)

def save_data(df, file_path):
    df.to_csv(file_path, index=False)
    st.cache_data.clear()

# --- Main Application ---
st.title("📚 Library Management System")
st.markdown("---")

# Load data
library_df = load_data(LIBRARY_CSV_PATH, ['StudentID', 'BookID', 'BookTitle', 'IssueDate', 'ReturnDate'])
students_df = load_data(STUDENTS_CSV_PATH, ['StudentID', 'FullName'])
fees_df = load_data(FEES_CSV_PATH, ['StudentID', 'Status'])

st.header("Issue a New Book")

# Create dropdowns for students and books
student_list = [f"{row.FullName} (ID: {row.StudentID})" for _, row in students_df.iterrows()]
# For simplicity, we'll use a hardcoded book list. In a real app, this would be from a books.csv
book_list = {"B1001: Introduction to Python": 1001, "B1002: Data Structures": 1002, "B1003: History of Art": 1003}

selected_student_str = st.selectbox("Select Student", student_list)
selected_book_title = st.selectbox("Select Book", book_list.keys())

if st.button("Issue Book"):
    if not selected_student_str:
        st.warning("Please select a student.")
    else:
        student_id = int(selected_student_str.split('(ID: ')[1][:-1])
        
        # --- AUTOMATION: FEE STATUS CHECK ---
        student_fee_status = "Paid" # Default to Paid if student not found in fees file
        if student_id in fees_df['StudentID'].values:
            student_fee_status = fees_df.loc[fees_df['StudentID'] == student_id, 'Status'].iloc[0]

        if student_fee_status == 'Overdue':
            st.error(f"❌ Transaction Blocked: Student ID {student_id} has overdue fees. Please clear dues before issuing new books.")
        else:
            # --- Proceed with issuing the book ---
            book_id = book_list[selected_book_title]
            issue_date = datetime.now().strftime("%Y-%m-%d")

            new_issue = pd.DataFrame([{
                'StudentID': student_id, 'BookID': book_id, 'BookTitle': selected_book_title.split(':')[1].strip(),
                'IssueDate': issue_date, 'ReturnDate': 'N/A'
            }])
            
            library_df = pd.concat([library_df, new_issue], ignore_index=True)
            save_data(library_df, LIBRARY_CSV_PATH)
            st.success(f"✅ Book '{selected_book_title}' issued to Student ID {student_id}.")
            st.rerun()

st.header("Issued Books Log")
st.dataframe(library_df, use_container_width=True)