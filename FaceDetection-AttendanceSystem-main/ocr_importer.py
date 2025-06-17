# ocr_importer.py
# ENHANCED v4: Now displays all recognized text from the 'text' column of the raw OCR data.

import streamlit as st
import pandas as pd
import os
import pytesseract
from PIL import Image
import re
import cv2
import numpy as np

# --- OCR ENGINE CONFIGURATION ---
try:
    if os.name == 'nt':
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except FileNotFoundError:
    st.error("Tesseract OCR engine not found. Please ensure it's installed and the path in the script is correct.")
    st.stop()

# --- Page Configuration ---
st.set_page_config(page_title="ERP - Document Scanner", page_icon="🖨️", layout="wide")
st.title("🖨️ Document Scanner (OCR)")
st.info("Upload an image of a structured document like a roster or attendance sheet to extract its data into a table.")

# --- ADVANCED IMAGE PREPROCESSING ---
def preprocess_for_ocr(image):
    open_cv_image = np.array(image.convert('RGB'))
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

# --- THE TABLE RECONSTRUCTION ENGINE ---
def extract_and_reconstruct_table(image):
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DATAFRAME, config='--psm 6')
    data = data[data.conf > 40]
    
    lines = {}
    for index, word_data in data.iterrows():
        key = (word_data['block_num'], word_data['par_num'], word_data['line_num'])
        if key not in lines:
            lines[key] = []
        lines[key].append(word_data)

    reconstructed_rows = []
    for key in sorted(lines.keys()):
        line_words = sorted(lines[key], key=lambda x: x['left'])
        line_text = ' '.join([str(w['text']) for w in line_words]).strip()
        
        match = re.search(r'(\d+)?\s*([A-Z\s]{5,})\s*([A-Z0-9-]{10,})\s*([A-Z0-9]{8,})?', line_text, re.IGNORECASE)
        
        if match:
            s_no, name, id_1, id_2 = (match.group(1) or ''), match.group(2).strip(), match.group(3).strip(), (match.group(4) or '')
            reconstructed_rows.append({'S.No.': s_no, 'Extracted Name': name, 'Enrollment ID': id_1, 'Seat No.': id_2})

    if not reconstructed_rows:
        st.warning("Could not reconstruct a table from the document. The format may be highly unusual or OCR quality was too low. Check the 'Raw Data Output' below.")
        return pd.DataFrame(), data
        
    return pd.DataFrame(reconstructed_rows), data

# --- Main Application ---
st.sidebar.header("Instructions")
st.sidebar.markdown("""
1.  **Upload a clear image.** A scanner app on your phone (like Adobe Scan) is highly recommended.
2.  **Process** the image. The system will now use an advanced engine to find and reconstruct table data.
3.  **Review and Correct** the output. OCR is an aid, not magic. Use the editable table to fix any errors.
4.  **Save** the cleaned data to the ERP.
""")

uploaded_file = st.file_uploader("1. Upload Document Image", type=['png', 'jpg', 'jpeg', 'bmp'])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    col1, col2 = st.columns(2)
    with col1:
        st.image(image, caption='Original Uploaded Image', use_column_width=True)

    # Use session state to avoid reprocessing the image on every interaction
    if 'processed_image' not in st.session_state or st.session_state.get('uploaded_filename') != uploaded_file.name:
        with st.spinner("Applying advanced image processing..."):
            processed_image = preprocess_for_ocr(image)
            st.session_state['processed_image'] = processed_image
            st.session_state['uploaded_filename'] = uploaded_file.name # Track the filename
    
    with col2:
        st.image(st.session_state['processed_image'], caption='Image Processed for OCR', use_column_width=True)

    if st.button("2. Extract Table Data", type="primary"):
        with st.spinner("Performing deep OCR and reconstructing table... This may take a moment."):
            reconstructed_df, raw_ocr_data = extract_and_reconstruct_table(st.session_state['processed_image'])
            st.session_state['ocr_df'] = reconstructed_df
            st.session_state['raw_ocr_data'] = raw_ocr_data
        st.rerun()

# Display results if they exist in the session state
if 'ocr_df' in st.session_state:
    st.subheader("3. Review and Correct Extracted Data")
    st.info("This table was algorithmically reconstructed from the OCR data. Please verify and edit any errors.")
    
    edited_df = st.data_editor(st.session_state['ocr_df'], num_rows="dynamic", use_container_width=True)
    
    st.markdown("---")
    st.subheader("4. Save Data to System")
    st.warning("This feature will append new students to your main student list. It will not import attendance marks yet.")

    if st.button("Append New Students to SIS"):
        if not edited_df.empty:
            with st.spinner("Saving new students..."):
                students_df = pd.read_csv(STUDENTS_CSV_PATH)
                new_records = []
                for _, row in edited_df.iterrows():
                    if row['Extracted Name'] not in students_df['FullName'].values:
                        new_id = (students_df['StudentID'].max() + 1) if not students_df.empty else 101
                        new_records.append({'StudentID': new_id, 'FullName': row['Extracted Name'], 'Email': f"student.{new_id}@example.com", 'Major': 'To be assigned', 'Status': 'Active', 'DateOfBirth': None})
                        students_df = pd.concat([students_df, pd.DataFrame([new_records[-1]])], ignore_index=True)
                
                if new_records:
                    final_df = pd.DataFrame(new_records)
                    updated_students_df = pd.concat([pd.read_csv(STUDENTS_CSV_PATH), final_df], ignore_index=True)
                    updated_students_df.to_csv(STUDENTS_CSV_PATH, index=False)
                    st.success(f"✅ Successfully added {len(new_records)} new students to the system!")
                else:
                    st.info("No new students found to add (they may already exist in the system).")
        else:
            st.error("No data to save.")

# --- THIS IS THE CHANGE ---
if 'raw_ocr_data' in st.session_state:
    with st.expander("Show Raw OCR Data (for debugging)"):
        
        # 1. Get the raw DataFrame from Tesseract
        raw_data_df = st.session_state['raw_ocr_data']
        
        # 2. Filter out empty/whitespace text entries and join them with spaces
        all_text = ' '.join(raw_data_df['text'].dropna().astype(str).tolist())
        
        # 3. Display the joined text in a text area
        st.text_area("All Extracted Text (Concatenated)", all_text, height=200)
        
        # 4. Display the raw DataFrame as before for detailed inspection
        st.dataframe(raw_data_df)
# --- END OF CHANGE ---