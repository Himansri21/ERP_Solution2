# run_erp.py
# This is the main entry point for your ERP System.
# Run this file from your terminal: python run_erp.py

import subprocess
import sys
import os

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def launch_script(script_name, use_streamlit=False):
    """Launches a given Python script."""
    try:
        command = []
        if use_streamlit:
            command = ['streamlit', 'run', script_name]
        else:
            # Use sys.executable to ensure the script runs with the same Python interpreter
            # that is running this launcher script (important for virtual environments).
            command = [sys.executable, script_name]
        
        print(f"\n🚀 Launching {script_name}...")
        print("   (Close the application window or press CTRL+C in the new terminal to return here)")
        
        # Popen runs the command in a new process, allowing the menu to continue
        process = subprocess.Popen(command)
        process.wait() # Wait for the user to close the app before showing the menu again

    except FileNotFoundError:
        print(f"\n❌ Error: '{script_name}' not found.")
        if use_streamlit:
            print("   Is Streamlit installed? Try: pip install streamlit")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

def main_menu():
    """Displays the main menu and handles user input."""
    while True:
        clear_screen()
        print("="*40)
        print("    🎓 Welcome to Your College ERP 🎓")
        print("="*40)
        print("\nSelect a module to launch:")
        print("  [1] 🧑‍🎓 Student Information System (SIS)")
        print("  [2] 📸 Face Recognition Attendance")
        print("  [3] 📊 Data Analytics Portal")
        print("  [4] 🚪 Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == '1':
            launch_script('student_SIS.py', use_streamlit=True)
        elif choice == '2':
            launch_script('main_final.py')
        elif choice == '3':
            launch_script('app3.py', use_streamlit=True)
        elif choice == '4':
            print("\n👋 Goodbye!\n")
            break
        else:
            print("\nInvalid choice. Please try again.")
        
        input("\nPress Enter to return to the menu...")

if __name__ == "__main__":
    main_menu()