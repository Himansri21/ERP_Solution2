# courses_system.py
# CORRECTED: Fixes the 'merge on object and int64' error by standardizing data types.

import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="ERP - Courses", page_icon="🗓️", layout="wide")

# --- File Paths & Columns ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COURSES_CSV_PATH = os.path.join(BASE_DIR, 'courses.csv')
TEACHERS_CSV_PATH = os.path.join(BASE_DIR, 'teachers.csv')
GRADES_CSV_PATH = os.path.join(BASE_DIR, 'grades.csv')
STUDENTS_CSV_PATH = os.path.join(BASE_DIR, 'students.csv')

COURSE_COLS = ['CourseID', 'CourseName', 'Department', 'Credits', 'TeacherID']
TEACHER_COLS = ['TeacherID', 'TeacherName', 'Department', 'Email']

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
st.title("🗓️ Course & Timetable Management")

courses_df = load_data(COURSES_CSV_PATH, COURSE_COLS)
teachers_df = load_data(TEACHERS_CSV_PATH, TEACHER_COLS)

tab1, tab2, tab3 = st.tabs(["View Courses", "Add/Edit Course", "Manage Teachers"])

with tab1:
    st.header("Course Catalog & Details")
    if courses_df.empty:
        st.info("No courses created yet. Please add a course in the 'Add/Edit Course' tab.")
    else:
        # --- THIS IS THE FIX ---
        # Ensure 'TeacherID' columns are the same data type (string) before merging.
        # This prevents the 'object and int64' error.
        courses_df['TeacherID'] = courses_df['TeacherID'].astype(str)
        teachers_df['TeacherID'] = teachers_df['TeacherID'].astype(str)
        # --- END OF FIX ---
        
        display_courses_df = pd.merge(courses_df, teachers_df, on='TeacherID', how='left', suffixes=('', '_teacher')).fillna('Unassigned')
        st.dataframe(display_courses_df[['CourseID', 'CourseName', 'Department', 'Credits', 'TeacherName']], use_container_width=True)
        
        st.markdown("---")
        st.subheader("Detailed Course View")
        course_list = [f"{row.CourseName} ({row.CourseID})" for _, row in courses_df.iterrows()]
        selected_course_str = st.selectbox("Select a course to see details", course_list)

        if selected_course_str:
            course_id = selected_course_str.split('(')[-1][:-1]
            grades_df = load_data(GRADES_CSV_PATH, ['StudentID', 'Subject', 'Score'])
            students_df = load_data(STUDENTS_CSV_PATH, ['StudentID', 'FullName', 'Status'])
            
            course_name_to_match = courses_df[courses_df['CourseID'] == course_id]['CourseName'].iloc[0]
            enrolled_students_ids = grades_df[grades_df['Subject'].str.lower() == course_name_to_match.lower()]['StudentID'].unique()
            
            if len(enrolled_students_ids) > 0:
                enrolled_students_df = students_df[students_df['StudentID'].isin(enrolled_students_ids) & (students_df['Status'] == 'Active')]
                course_grades = grades_df[grades_df['StudentID'].isin(enrolled_students_ids) & (grades_df['Subject'].str.lower() == course_name_to_match.lower())]
                
                if not course_grades.empty:
                    avg_score = course_grades['Score'].mean()
                    st.metric("Average Score for this Course", f"{avg_score:.2f}/100")
                
                st.write(f"**Enrolled Students ({len(enrolled_students_df)}):**")
                st.dataframe(enrolled_students_df[['FullName', 'StudentID', 'Email']], use_container_width=True)
            else:
                st.info("No students have recorded grades for this course yet.")


with tab2:
    st.header("Add or Edit a Course")
    action = st.radio("Select Action", ["Add New Course", "Edit Existing Course"], horizontal=True, key="course_action")

    if action == "Add New Course":
        with st.form("add_course_form"):
            if courses_df.empty or courses_df['CourseID'].isnull().all(): new_course_id = 201
            else: numeric_ids = pd.to_numeric(courses_df['CourseID'].astype(str).str.lstrip('C'), errors='coerce'); new_course_id = int(numeric_ids.max() + 1) if not numeric_ids.isnull().all() else 201
            
            course_id = st.text_input("Course ID", value=f"C{new_course_id}", disabled=True)
            course_name = st.text_input("Course Name")
            department = st.selectbox("Department", ["Computer Science", "Business Administration", "Engineering", "Arts & Humanities"])
            credits = st.number_input("Credits", min_value=1, max_value=6, step=1)
            teacher_list = ["Unassigned"] + [f"{row.TeacherName} (ID: {row.TeacherID})" for _, row in teachers_df.iterrows()]
            assigned_teacher_str = st.selectbox("Assign Teacher", teacher_list)
            
            submitted = st.form_submit_button("Add Course")
            if submitted and course_name:
                teacher_id = "Unassigned" if assigned_teacher_str == "Unassigned" else str(assigned_teacher_str.split('(ID: ')[1][:-1])
                new_course = pd.DataFrame([{'CourseID': course_id, 'CourseName': course_name, 'Department': department, 'Credits': credits, 'TeacherID': teacher_id}])
                courses_df = pd.concat([courses_df, new_course], ignore_index=True)
                save_data(courses_df, COURSES_CSV_PATH)
                st.success(f"Course '{course_name}' added successfully!")
                st.rerun()

    else: # Edit Existing Course
        if not courses_df.empty:
            course_list = [f"{row.CourseName} ({row.CourseID})" for _, row in courses_df.iterrows()]
            selected_course_str = st.selectbox("Select Course to Edit", course_list)
            course_id = selected_course_str.split('(')[-1][:-1]
            course_data = courses_df[courses_df['CourseID'] == course_id].iloc[0]
            
            with st.form("edit_course_form"):
                st.write(f"**Editing: {course_data['CourseName']}**")
                new_course_name = st.text_input("Course Name", value=course_data['CourseName'])
                
                teacher_list = ["Unassigned"] + [f"{row.TeacherName} (ID: {row.TeacherID})" for _, row in teachers_df.iterrows()]
                current_teacher_id = str(course_data['TeacherID'])
                
                try:
                    # Find the full string representation of the current teacher for the default index
                    current_teacher_obj = next((t for t in teacher_list if f"(ID: {current_teacher_id})" in t), None)
                    default_index = teacher_list.index(current_teacher_obj) if current_teacher_obj else 0
                except (ValueError, StopIteration):
                    default_index = 0 # Default to 'Unassigned'
                
                new_assigned_teacher_str = st.selectbox("Assign Teacher", teacher_list, index=default_index)

                updated = st.form_submit_button("Save Changes")
                if updated:
                    new_teacher_id = "Unassigned" if new_assigned_teacher_str == "Unassigned" else str(new_assigned_teacher_str.split('(ID: ')[1][:-1])
                    courses_df.loc[courses_df['CourseID'] == course_id, 'CourseName'] = new_course_name
                    courses_df.loc[courses_df['CourseID'] == course_id, 'TeacherID'] = new_teacher_id
                    save_data(courses_df, COURSES_CSV_PATH)
                    st.success("Course updated!")
                    st.rerun()
        else:
            st.info("No courses to edit.")

with tab3:
    st.header("Manage Teachers")
    with st.form("add_teacher_form", clear_on_submit=True):
        new_teacher_id = (teachers_df['TeacherID'].astype(int).max() + 1) if not teachers_df.empty else 501
        
        teacher_id = st.number_input("Teacher ID", value=int(new_teacher_id), disabled=True)
        teacher_name = st.text_input("Teacher's Full Name")
        teacher_dept = st.selectbox("Department", ["Computer Science", "Business Administration", "Engineering", "Arts & Humanities"], key="teacher_dept")
        email = st.text_input("Email Address")
        submitted = st.form_submit_button("Add Teacher")
        if submitted and teacher_name and email:
            new_teacher = pd.DataFrame([{'TeacherID': str(teacher_id), 'TeacherName': teacher_name, 'Department': teacher_dept, 'Email': email}])
            teachers_df = pd.concat([teachers_df, new_teacher], ignore_index=True)
            save_data(teachers_df, TEACHERS_CSV_PATH)
            st.success(f"Teacher '{teacher_name}' added successfully!")
            st.rerun()

    st.subheader("Current Faculty List")
    st.dataframe(teachers_df, use_container_width=True)