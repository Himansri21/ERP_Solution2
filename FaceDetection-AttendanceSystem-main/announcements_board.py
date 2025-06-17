# announcements_board.py

import streamlit as st
import pandas as pd
import os
from datetime import date, datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="ERP - Notice Board",
    page_icon="📢",
    layout="centered" # Centered layout is better for a notice board
)

# --- File Path ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTICES_CSV_PATH = os.path.join(BASE_DIR, 'notices.csv')

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

# --- Main Application ---
st.title("📢 College Notice Board")
st.markdown("---")

# Load data
notices_df = load_data(NOTICES_CSV_PATH, ['NoticeID', 'Title', 'Content', 'PostDate', 'Audience'])

# --- Sidebar for Admin Actions ---
st.sidebar.header("Admin Actions")
with st.sidebar.expander("Post a New Announcement"):
    with st.form("new_notice_form", clear_on_submit=True):
        title = st.text_input("Notice Title")
        content = st.text_area("Notice Content (supports Markdown)")
        audience = st.selectbox("Audience", ["All", "Students Only", "Faculty Only"])
        
        submitted = st.form_submit_button("Post Notice")
        if submitted:
            if not all([title, content]):
                st.warning("Title and content cannot be empty.")
            else:
                new_id = (notices_df['NoticeID'].max() + 1) if not notices_df.empty else 1
                post_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                new_notice = pd.DataFrame([{
                    'NoticeID': new_id, 'Title': title, 'Content': content,
                    'PostDate': post_date, 'Audience': audience
                }])
                
                notices_df = pd.concat([notices_df, new_notice], ignore_index=True)
                save_data(notices_df, NOTICES_CSV_PATH)
                st.sidebar.success("Notice posted successfully!")
                st.rerun()

# --- Display Notices ---
st.header("Current Announcements")

if notices_df.empty:
    st.info("There are no announcements at this time.")
else:
    # Sort by most recent first
    sorted_df = notices_df.sort_values(by='PostDate', ascending=False)
    
    for _, notice in sorted_df.iterrows():
        with st.container():
            st.subheader(notice['Title'])
            
            # Use columns for metadata
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"Posted on: {notice['PostDate']}")
            with col2:
                st.caption(f"For: {notice['Audience']}")
            
            st.markdown(notice['Content'])
            st.markdown("---")