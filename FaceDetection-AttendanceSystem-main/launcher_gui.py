# launcher_gui.py
# FINAL VERSION: Now includes the new OCR Document Scanner module.

import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import StringProperty, ListProperty
from functools import partial
import subprocess
import sys
import os

Window.size = (550, 850) # Slightly increased height for the new button
Window.clearcolor = (0.15, 0.15, 0.18, 1)

class ModuleCard(ButtonBehavior, BoxLayout):
    text = StringProperty('')
    description = StringProperty('')
    bg_color = ListProperty([1, 1, 1, 1])

    def __init__(self, **kwargs):
        super(ModuleCard, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = (15, 10)
        self.spacing = 5
        with self.canvas.before:
            self.color_instruction = Color(rgba=self.bg_color)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[8])
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        main_text = Label(text=f'[b]{self.text}[/b]', font_size='18sp', markup=True, halign='center', valign='bottom', size_hint_y=0.6)
        desc_text = Label(text=self.description, font_size='13sp', color=(0.95, 0.95, 0.95, 0.8), halign='center', valign='top', size_hint_y=0.4, text_size=(self.width-30, None))
        self.add_widget(main_text)
        self.add_widget(desc_text)

    def on_bg_color(self, instance, value):
        if hasattr(self, 'color_instruction'): self.color_instruction.rgba = value
    def update_canvas(self, instance, value):
        if hasattr(self, 'rect'):
            self.rect.pos = self.pos
            self.rect.size = self.size
            self.children[0].text_size = (self.width-30, None)
            
class ERPLauncherApp(App):
    def build(self):
        self.title = 'College ERP Dashboard'
        main_layout = BoxLayout(orientation='vertical', padding=25, spacing=12)
        title_label = Label(text='[b]College ERP Dashboard[/b]', font_size='32sp', markup=True, size_hint_y=None, height=50)
        subtitle_label = Label(text='Select a module to launch', font_size='18sp', color=(0.8, 0.8, 0.8, 1), size_hint_y=None, height=30)
        main_layout.add_widget(title_label)
        main_layout.add_widget(subtitle_label)

        card_height = 80
        
        modules = [
            {'name': 'Student Information System', 'desc': 'Manage student records (Add, Edit, Delete)', 'script': 'student_SIS.py', 'color': (0.1, 0.5, 0.8, 1), 'is_kivy': False},
            {'name': 'Course & Timetable', 'desc': 'Define courses and manage faculty', 'script': 'courses_system.py', 'color': (0.8, 0.4, 0.1, 1), 'is_kivy': False},
            {'name': 'Grade & Marking System', 'desc': 'Assign and track student grades', 'script': 'grades_system.py', 'color': (0.1, 0.7, 0.7, 1), 'is_kivy': False},
            {'name': 'Fees Management', 'desc': 'Track student fees, payments, and dues', 'script': 'fees_analysis.py', 'color': (0.9, 0.6, 0.2, 1), 'is_kivy': False},
            {'name': 'Library Management', 'desc': 'Manage book catalog, issue and return books', 'script': 'library_system.py', 'color': (0.6, 0.4, 0.8, 1), 'is_kivy': False},
            {'name': 'Announcements Board', 'desc': 'Post and view college-wide notices', 'script': 'announcements_board.py', 'color': (0.9, 0.2, 0.4, 1), 'is_kivy': False},
            
            # --- NEW MODULE ADDED ---
            {'name': 'Document Scanner (OCR)', 'desc': 'Import data from scanned documents or images', 'script': 'ocr_importer.py', 'color': (0.5, 0.2, 0.7, 1), 'is_kivy': False},
            
            {'name': 'Face Recognition Attendance', 'desc': 'Take attendance using facial recognition', 'script': 'main_attendance_module.py', 'color': (0.2, 0.7, 0.4, 1), 'is_kivy': True},
            {'name': 'Analytics & Reports', 'desc': 'View 360° profiles and analyze data', 'script': 'app3.py', 'color': (0.9, 0.8, 0.2, 1), 'is_kivy': False},
        ]

        for module in modules:
            card = ModuleCard(text=module['name'], description=module['desc'], bg_color=module['color'], size_hint_y=None, height=card_height)
            # Correctly use 'is_kivy' to decide if it's a streamlit app or a regular python script
            is_streamlit = not module['is_kivy'] 
            card.bind(on_press=partial(self.launch_module, script_name=module['script'], use_streamlit=is_streamlit))
            main_layout.add_widget(card)

        main_layout.add_widget(BoxLayout(size_hint_y=0.1))
        exit_button = Button(text='[b]🚪 Exit[/b]', font_size='20sp', markup=True, size_hint_y=None, height=60, background_color=(0.8, 0.2, 0.2, 1), background_normal='')
        exit_button.bind(on_press=self.stop)
        main_layout.add_widget(exit_button)
        return main_layout

    def launch_module(self, instance, script_name, use_streamlit=False):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(base_dir, script_name)
            if not os.path.exists(script_path):
                print(f"❌ Error: Script not found at '{script_path}'")
                return
            
            # The command logic is already perfect for handling both types of apps
            command = ['streamlit', 'run', script_path] if use_streamlit else [sys.executable, script_path]
            
            print(f"🚀 Launching module: {' '.join(command)}")
            subprocess.Popen(command)
        except Exception as e:
            print(f"❌ An error occurred while launching '{script_name}': {e}")

if __name__ == "__main__":
    ERPLauncherApp().run()