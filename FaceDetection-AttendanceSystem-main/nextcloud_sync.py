# nextcloud_sync.py
# A dedicated module for synchronizing ERP data with a Nextcloud server.

import os
from nextcloud import NextCloud
from datetime import datetime

# --- CONFIGURATION ---
# IMPORTANT: For security, it's best to load these from environment variables
# or a secure config file, not hardcoded directly in the script.
# For now, we'll put them here for simplicity.
#
# Replace these with your actual EC2 and Nextcloud App Password details.
NEXTCLOUD_URL = 'http://YOUR_EC2_PUBLIC_IP'  # Or your domain if you have one
NEXTCLOUD_USER = 'YOUR_GENERATED_APP_USERNAME' # The username you just copied
NEXTCLOUD_PASS = 'YOUR_GENERATED_APP_PASSWORD' # The password you just copied

# This is the directory on your Nextcloud server where the files will be stored.
REMOTE_ERP_DIR = 'ERP_DATA'

def get_nextcloud_client():
    """Initializes and returns a Nextcloud client instance."""
    try:
        nc = NextCloud(endpoint=NEXTCLOUD_URL, user=NEXTCLOUD_USER, password=NEXTCLOUD_PASS)
        # Check if the base directory exists, create it if not.
        nc.create_folder(REMOTE_ERP_DIR)
        return nc
    except Exception as e:
        print(f"❌ Could not connect to Nextcloud server at {NEXTCLOUD_URL}. Error: {e}")
        return None

def upload_file_to_nextcloud(local_file_path, remote_folder=''):
    """Uploads a single file from the local path to a folder on Nextcloud."""
    nc = get_nextcloud_client()
    if not nc:
        return False, "Nextcloud connection failed."

    if not os.path.exists(local_file_path):
        return False, f"Local file not found: {local_file_path}"

    local_filename = os.path.basename(local_file_path)
    
    # Construct the full remote path
    if remote_folder:
        # Ensure the sub-folder exists
        full_remote_folder_path = os.path.join(REMOTE_ERP_DIR, remote_folder)
        nc.create_folder(full_remote_folder_path)
        remote_path = os.path.join(full_remote_folder_path, local_filename)
    else:
        remote_path = os.path.join(REMOTE_ERP_DIR, local_filename)

    try:
        print(f"☁️ Uploading '{local_filename}' to Nextcloud at '{remote_path}'...")
        nc.upload_file(local_path=local_file_path, remote_path=remote_path)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return True, f"Successfully uploaded at {timestamp}"
    except Exception as e:
        return False, f"Upload failed. Error: {e}"

def download_file_from_nextcloud(local_file_path, remote_folder=''):
    """Downloads a single file from Nextcloud to the local path, overwriting it."""
    nc = get_nextcloud_client()
    if not nc:
        return False, "Nextcloud connection failed."

    local_filename = os.path.basename(local_file_path)
    
    if remote_folder:
        remote_path = os.path.join(REMOTE_ERP_DIR, remote_folder, local_filename)
    else:
        remote_path = os.path.join(REMOTE_ERP_DIR, local_filename)
    
    try:
        print(f"☁️ Downloading '{local_filename}' from Nextcloud at '{remote_path}'...")
        nc.download_file(remote_path=remote_path, local_path=local_file_path)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return True, f"Successfully downloaded at {timestamp}"
    except Exception as e:
        # This often happens if the file doesn't exist on the server yet.
        return False, f"Download failed. File might not exist on server. Error: {e}"

# Example of how you would sync all files
def sync_all_data(direction='upload'):
    """A master function to upload or download all ERP data files."""
    print(f"--- Starting Full Data Sync (Direction: {direction}) ---")
    
    # Define all the files and their remote subfolders
    files_to_sync = {
        'students.csv': '',
        'teachers.csv': '',
        'courses.csv': '',
        'grades.csv': '',
        'fees.csv': '',
        'payment_history.csv': '',
        'books.csv': '',
        'book_issuances.csv': '',
        'notices.csv': '',
        'attendance.csv': 'Attendance' # This file goes into a subfolder
    }
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for filename, remote_subfolder in files_to_sync.items():
        # Handle the special case for the attendance file's local path
        if remote_subfolder == 'Attendance':
            local_path = os.path.join(base_dir, remote_subfolder, filename)
        else:
            local_path = os.path.join(base_dir, filename)

        if direction == 'upload':
            success, message = upload_file_to_nextcloud(local_path, remote_subfolder)
        else: # download
            success, message = download_file_from_nextcloud(local_path, remote_subfolder)

        if not success:
            print(f"⚠️  Warning for {filename}: {message}")

    print("--- Sync Complete ---")

# This allows you to run this script directly to perform a sync
if __name__ == '__main__':
    # Default action is to upload. You can change it to 'download'.
    sync_all_data(direction='upload')