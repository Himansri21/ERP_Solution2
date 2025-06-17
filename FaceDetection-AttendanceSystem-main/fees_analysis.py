# fees_analysis.py
# ENHANCED: Includes payment history, fee reminders, and a better dashboard.

import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

st.set_page_config(page_title="ERP - Fees", page_icon="💰", layout="wide")

# --- File Paths & Columns ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENTS_CSV_PATH = os.path.join(BASE_DIR, 'students.csv')
FEES_CSV_PATH = os.path.join(BASE_DIR, 'fees.csv')
PAYMENT_HISTORY_CSV_PATH = os.path.join(BASE_DIR, 'payment_history.csv') # NEW

FEE_COLS = ['StudentID', 'TotalFees', 'AmountPaid', 'DueDate']
STUDENT_COLS = ['StudentID', 'FullName', 'Status']
HISTORY_COLS = ['PaymentID', 'StudentID', 'Amount', 'PaymentDate']

# --- Helper Functions ---
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

# --- Main App ---
st.title("💰 Fees Analysis & Payments")

# Load data
students_df = load_data(STUDENTS_CSV_PATH, STUDENT_COLS)
fees_df = load_data(FEES_CSV_PATH, FEE_COLS)
payment_history_df = load_data(PAYMENT_HISTORY_CSV_PATH, HISTORY_COLS)

active_students_df = students_df[students_df['Status'] != 'Inactive']
if active_students_df.empty:
    st.error("No active students found. Add students in the SIS module first.")
    st.stop()

# Merge data for a full view
full_fees_df = pd.merge(active_students_df, fees_df, on='StudentID', how='left').fillna(0)
full_fees_df['Balance'] = full_fees_df['TotalFees'] - full_fees_df['AmountPaid']
full_fees_df['Status'] = full_fees_df.apply(lambda row: "Paid" if row['Balance'] <= 0 else "Overdue" if pd.notna(row['DueDate']) and pd.to_datetime(row['DueDate']).date() < date.today() else "Partial" if row['AmountPaid'] > 0 else "Unpaid", axis=1)

# --- Sidebar for Actions ---
st.sidebar.header("Actions")
action = st.sidebar.radio("Choose an action", ["Fees Dashboard", "Record a Payment", "Setup Student Fees", "View Payment History"])

if action == "Fees Dashboard":
    st.header("Fees Dashboard")
    total_due = full_fees_df['TotalFees'].sum()
    total_collected = full_fees_df['AmountPaid'].sum()
    outstanding = total_due - total_collected
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Fees Due", f"₹{total_due:,.2f}")
    col2.metric("Total Fees Collected", f"₹{total_collected:,.2f}")
    col3.metric("Total Outstanding", f"₹{outstanding:,.2f}", delta_color="inverse")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        status_counts = full_fees_df['Status'].value_counts()
        st.subheader("Fee Status Distribution")
        st.bar_chart(status_counts)
    with col2:
        st.subheader("Overdue Fees by Major")
        overdue_df = full_fees_df[full_fees_df['Status'] == 'Overdue']
        overdue_by_major = overdue_df.groupby('Major')['Balance'].sum()
        st.bar_chart(overdue_by_major)

    st.header("Detailed Fee Status")
    def style_status(status):
        colors = {'Paid': 'green', 'Overdue': 'red', 'Partial': 'orange', 'Unpaid': 'gray'}
        return f'background-color: {colors.get(status, "white")}; color: white'
    st.dataframe(full_fees_df[['FullName', 'StudentID', 'TotalFees', 'AmountPaid', 'Balance', 'DueDate', 'Status']].style.applymap(style_status, subset=['Status']), use_container_width=True)

elif action == "Record a Payment":
    st.header("Record a New Payment")
    with st.form("record_payment_form"):
        student_list = [f"{row.FullName} (ID: {row.StudentID})" for _, row in active_students_df.iterrows()]
        selected_student_str = st.selectbox("Select Student", student_list)
        payment_amount = st.number_input("Payment Amount", min_value=0.01)

        submitted = st.form_submit_button("Record Payment")
        if submitted:
            student_id = int(selected_student_str.split('(ID: ')[1][:-1])
            fees_df.loc[fees_df['StudentID'] == student_id, 'AmountPaid'] += payment_amount
            save_data(fees_df, FEES_CSV_PATH)
            
            # AUTOMATION: Log the payment to the history
            new_payment_id = (payment_history_df['PaymentID'].max() + 1) if not payment_history_df.empty else 1001
            history_record = pd.DataFrame([{'PaymentID': new_payment_id, 'StudentID': student_id, 'Amount': payment_amount, 'PaymentDate': date.today()}])
            payment_history_df = pd.concat([payment_history_df, history_record], ignore_index=True)
            save_data(payment_history_df, PAYMENT_HISTORY_CSV_PATH)
            
            st.success(f"Payment of ₹{payment_amount} recorded for {selected_student_str}.")

elif action == "Setup Student Fees":
    st.header("Setup or Edit Student Fee Structures")
    student_list = [f"{row.FullName} (ID: {row.StudentID})" for _, row in active_students_df.iterrows()]
    selected_student_str = st.selectbox("Select Student to Edit", student_list)
    student_id = int(selected_student_str.split('(ID: ')[1][:-1])
    student_record = fees_df[fees_df['StudentID'] == student_id].iloc[0]
    
    with st.form("edit_fee_form"):
        total_fees = st.number_input("Total Fees for Course/Semester", value=float(student_record['TotalFees']), min_value=0.0)
        due_date_val = pd.to_datetime(student_record['DueDate']).date() if pd.notna(student_record['DueDate']) else date.today()
        due_date = st.date_input("Fee Due Date", value=due_date_val)
        updated = st.form_submit_button("Save Fee Structure")
        if updated:
            fees_df.loc[fees_df['StudentID'] == student_id, 'TotalFees'] = total_fees
            fees_df.loc[fees_df['StudentID'] == student_id, 'DueDate'] = due_date.strftime("%Y-%m-%d")
            save_data(fees_df, FEES_CSV_PATH)
            st.success(f"Fee structure updated for {selected_student_str}.")

elif action == "View Payment History":
    st.header("Full Payment History")
    if payment_history_df.empty:
        st.info("No payments have been recorded yet.")
    else:
        history_display = pd.merge(payment_history_df, students_df[['StudentID', 'FullName']], on='StudentID', how='left')
        st.dataframe(history_display[['PaymentID', 'FullName', 'Amount', 'PaymentDate']], use_container_width=True)