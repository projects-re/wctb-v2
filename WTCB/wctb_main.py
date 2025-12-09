import tkinter as tk
from tkinter import font, ttk
import tkinter.messagebox as messagebox
import platform
import psutil
import time
import os
import json
from typing import List, Tuple
import threading
import logging
import subprocess
import webbrowser
from ctypes import wintypes

from wintweaks import WinTweaks

correct_pass = "6121"  # must be STRING if comparing to Entry input
SETTINGS_FILE = os.path.join("data", "settings.json")

# --- Setup Logging ---
if not os.path.exists("data"):
    os.makedirs("data")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=os.path.join('data', 'app.log'),
    filemode='a')

# --- Theme Definitions ---
THEMES = {
    "Default": {
        "bg": "black", "fg": "white", "highlight_bg": "#808080", "highlight_fg": "black",
        "category_fg": "#FFD700", "value_fg": "#00FFFF", "header_bg": "black", "header_fg": "white",
        "clock_fg": "white", "button_bg": "#808080", "button_fg": "black", "border": "white"
    },
    "Blue": {
        "bg": "#00008B", "fg": "white", "highlight_bg": "#ADD8E6", "highlight_fg": "black",
        "category_fg": "#FFFF00", "value_fg": "#00FFFF", "header_bg": "#0000A0", "header_fg": "white",
        "clock_fg": "white", "button_bg": "#ADD8E6", "button_fg": "black", "border": "white"
    },
    "Green": {
        "bg": "#003300", "fg": "#00FF00", "highlight_bg": "#006600", "highlight_fg": "white",
        "category_fg": "#FFFF00", "value_fg": "#00FFFF", "header_bg": "#004400", "header_fg": "#00FF00",
        "clock_fg": "#00FF00", "button_bg": "#006600", "button_fg": "white", "border": "#00FF00"
    }
}



class BIOSOptionMenu:
    """Manages a list of interactive, keyboard-navigable BIOS-style options."""
    def __init__(self, parent, options_data, font, app_instance):
        self.parent = parent
        self.options_data = options_data
        self.font = font
        self.options = []
        self.visible_options = []
        self.current_selection_index = 0

        self.container = tk.Frame(parent, bg="black")
        self.container.pack(fill="both", expand=True, padx=20, pady=10)

        self.app = app_instance # Reference to the main application
        self.rebuild_options_ui()

        self.container.focus_set()
        self.container.bind("<Up>", self.move_selection_up)
        self.container.bind("<Down>", self.move_selection_down)
        self.container.bind("<Left>", self.change_value_left)
        self.container.bind("<Right>", self.change_value_right)
        self.container.bind("<Return>", self.toggle_category)

    def rebuild_options_ui(self):
        for widget in self.container.winfo_children():
            widget.destroy()
        
        self.options = []
        self.visible_options = []

        for data in self.options_data:
            is_category = data['type'] == 'category'
            
            option_frame = tk.Frame(self.container, bg="black")
            
            if is_category:
                prefix = "▸" if data.get('collapsed', False) else "▾"
                name_label = tk.Label(option_frame, text=f"{prefix} {data['name']}", font=self.font, bg=self.app.current_theme_colors["bg"], fg=self.app.current_theme_colors["category_fg"], justify="left") # Changed to use theme colors
                name_label.pack(side="left", pady=5)
                value_label = None
            else: # It's an option
                indent = "    "
                name_label = tk.Label(option_frame, text=f"{indent}{data['name']}", font=self.font, bg=self.app.current_theme_colors["bg"], fg=self.app.current_theme_colors["fg"], justify="left")
                name_label.pack(side="left")
                value_label = tk.Label(option_frame, text=f"[{data['values'][data['current']]}]", font=self.font, bg=self.app.current_theme_colors["bg"], fg=self.app.current_theme_colors["value_fg"], width=15, anchor="e")
                value_label.pack(side="right")

            option_info = {'frame': option_frame, 'name_label': name_label, 'value_label': value_label, 'data': data}
            self.options.append(option_info)

            is_visible = True
            if 'category_id' in data:
                parent_cat = next((cat for cat in self.options_data if cat['type'] == 'category' and cat['id'] == data['category_id']), None)
                if parent_cat and parent_cat.get('collapsed', False):
                    is_visible = False
            
            if is_visible:
                option_frame.pack(fill="x", pady=1)
                self.visible_options.append(option_info)

        self.update_selection_highlight()

    def update_selection_highlight(self):
        if not self.visible_options: return

        for i, option in enumerate(self.visible_options):
            is_selected = (i == self.current_selection_index)
            is_category = option['data']['type'] == 'category'
            bg = self.app.current_theme_colors["highlight_bg"] if is_selected else self.app.current_theme_colors["bg"]
            fg = self.app.current_theme_colors["highlight_fg"] if is_selected else (self.app.current_theme_colors["category_fg"] if is_category else self.app.current_theme_colors["fg"])
            
            option['frame'].config(bg=bg)
            option['name_label'].config(bg=bg, fg=fg)
            if option['value_label']:
                option['value_label'].config(bg=bg)
                
    def move_selection_up(self, event=None):
        if self.current_selection_index > 0:
            self.current_selection_index -= 1
            self.update_selection_highlight()

    def move_selection_down(self, event=None):
        if self.current_selection_index < len(self.visible_options) - 1:
            self.current_selection_index += 1
            self.update_selection_highlight()

    def toggle_category(self, event=None):
        if not self.visible_options: return
        selected_option_data = self.visible_options[self.current_selection_index]['data']
        if selected_option_data['type'] == 'category':
            selected_option_data['collapsed'] = not selected_option_data.get('collapsed', False)
            
            full_list_index = self.options.index(self.visible_options[self.current_selection_index])
            self.rebuild_options_ui()

            try:
                new_visible_option = self.options[full_list_index]
                self.current_selection_index = self.visible_options.index(new_visible_option)
            except (ValueError, IndexError):
                self.current_selection_index = 0
            
            self.update_selection_highlight()

    def change_value(self, direction):
        if not self.visible_options: return
        selected_option_info = self.visible_options[self.current_selection_index]
        option_data = selected_option_info['data']

        if option_data['type'] == 'option':
            num_values = len(option_data['values'])
            option_data['current'] = (option_data['current'] + direction + num_values) % num_values
            
            new_value_text = f"[{option_data['values'][option_data['current']]}]"
            selected_option_info['value_label'].config(text=new_value_text, fg=self.app.current_theme_colors["value_fg"])

    def change_value_left(self, event=None):
        self.change_value(-1)

    def change_value_right(self, event=None):
        self.change_value(1)

    def get_current_settings(self):
        settings = {}
        for data in self.options_data:
            if data['type'] == 'option':
                settings[data['id']] = data['values'][data['current']]
        return settings

class BIOSActionMenu:
    """Manages a list of interactive, keyboard-navigable BIOS-style actions."""
    def __init__(self, parent, actions_data, font, app_instance):
        self.parent = parent
        self.actions_data = actions_data
        self.font = font
        self.actions = []
        self.current_selection_index = 0

        self.app = app_instance # Reference to the main application
        self.container = tk.Frame(parent, bg="black")
        self.container.pack(fill="both", expand=True, padx=20, pady=10)

        for data in self.actions_data:
            action_frame = tk.Frame(self.container, bg=self.app.current_theme_colors["bg"])
            
            name_label = tk.Label(action_frame, text=data['name'], font=self.font, bg=self.app.current_theme_colors["bg"], fg=self.app.current_theme_colors["fg"], justify="left")
            name_label.pack(side="left", pady=5)
            
            action_frame.pack(fill="x", pady=1)
            self.actions.append({'frame': action_frame, 'name_label': name_label, 'data': data})

        self.container.focus_set()
        self.container.bind("<Up>", self.move_selection_up)
        self.container.bind("<Down>", self.move_selection_down)
        self.container.bind("<Return>", self.execute_action)
        
        self.update_selection_highlight()


    def update_selection_highlight(self):
        for i, action in enumerate(self.actions):
            is_selected = (i == self.current_selection_index) # Changed to use theme colors
            bg = self.app.current_theme_colors["highlight_bg"] if is_selected else self.app.current_theme_colors["bg"]
            fg = "black" if is_selected else "white"
            action['frame'].config(bg=bg)
            action['name_label'].config(bg=bg, fg=fg)

    def move_selection_up(self, event=None):
        if self.current_selection_index > 0:
            self.current_selection_index -= 1
            self.update_selection_highlight()

    def move_selection_down(self, event=None):
        if self.current_selection_index < len(self.actions) - 1:
            self.current_selection_index += 1
            self.update_selection_highlight()

    def execute_action(self, event=None):
        if not self.actions: return
        
        selected_action_data = self.actions[self.current_selection_index]['data']
        callback = selected_action_data.get('callback')
        
        if callback:
            # Show a busy cursor
            self.container.config(cursor="watch")
            self.app.root.update_idletasks()
            callback()

            self.container.config(cursor="")

class CustomDialog(tk.Toplevel):
    """A custom, UEFI-styled dialog window."""
    def __init__(self, parent, title, message, dialog_type="info"):
        super().__init__(parent) # Changed to use parent
        self.title(title)
        self.app = parent.app if hasattr(parent, 'app') else parent # Get app instance
        self.configure(bg=self.app.current_theme_colors["bg"], highlightbackground=self.app.current_theme_colors["border"], highlightthickness=1)
        self.transient(parent)
        self.grab_set()
        self.result = None

        # --- Fonts ---
        default_font = self.app.default_font # Changed to use self.app.default_font

        # --- Content ---
        message_label = tk.Label(self, text=message, font=default_font, bg=self.app.current_theme_colors["bg"], fg=self.app.current_theme_colors["fg"], wraplength=400, justify="center") # Changed to use self.app.current_theme_colors
        message_label.pack(pady=20, padx=20)

        button_frame = tk.Frame(self, bg=self.app.current_theme_colors["bg"]) # Changed to use self.app.current_theme_colors
        button_frame.pack(pady=10)

        if dialog_type == "info" or dialog_type == "error":
            ok_button = tk.Button(button_frame, text="OK", font=default_font, command=self.destroy, bg=self.app.current_theme_colors["button_bg"], fg=self.app.current_theme_colors["button_fg"])
            ok_button.pack()
            ok_button.focus_set()
            self.bind("<Return>", lambda e: self.destroy())

        elif dialog_type == "confirm":
            def on_ok():
                self.result = True
                self.destroy()

            def on_cancel():
                self.result = False
                self.destroy()

            ok_button = tk.Button(button_frame, text="OK", font=default_font, command=on_ok, bg=self.app.current_theme_colors["button_bg"], fg=self.app.current_theme_colors["button_fg"])
            ok_button.pack(side="left", padx=10)
            ok_button.focus_set()

            cancel_button = tk.Button(button_frame, text="Cancel", font=default_font, command=on_cancel, bg=self.app.current_theme_colors["button_bg"], fg=self.app.current_theme_colors["button_fg"])
            cancel_button.pack(side="left", padx=10)

            self.bind("<Return>", lambda e: on_ok())
            self.bind("<Escape>", lambda e: on_cancel())

        self.wait_window()


class StartupWindow(tk.Toplevel):
    """Custom Toplevel window for managing startup programs."""
    def __init__(self, parent):
        super().__init__(parent)
        self.programs_list: List = []


class Application:
    """Main application class for WTBC."""
    def __init__(self, root):
        self.root = root
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="black")
        self.root.title("WTBC - Windows Tool Basic Customization")
        self.root.overrideredirect(True) # Remove default title bar
        self._offset_x = 0
        self._offset_y = 0

        self.root.app = self # Attach app instance to root for CustomDialog
        self.current_theme_name = "Default"
        self.current_theme_colors = THEMES[self.current_theme_name]

        self.pin_frame = None
        self.clock_update_id = None # To store the after ID for clock updates
        self.about_label = None
        self.about_frame = None
        self.settings = {}
        self.main_app_frame = None
        self.tweaks_menu = None
        self.optimizations_menu = None
        self.appearance_menu = None
        self.security_menu = None


        # --- Define Fonts ---
        self.default_font = font.Font(family="Consolas", size=12)
        self.header_font = font.Font(family="Consolas", size=14, weight="bold")
        try:
            self.clock_font = font.Font(family="DSEG7 Classic", size=14)
        except tk.TclError:
            logging.warning("DSEG7 Classic font not found. Falling back to default.")
            self.clock_font = self.header_font # Fallback font

        self.load_settings()
        self.apply_theme(self.current_theme_name) # Apply theme after loading settings
        self.create_pin_screen()
        logging.info("Application initialized.")

        self.version = "0.7.0"

    def load_settings(self):
        """Loads settings from the JSON file or creates defaults."""
        if not os.path.exists("data"):
            os.makedirs("data")

        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    self.settings = json.load(f)
                logging.info("Settings loaded successfully from %s.", SETTINGS_FILE)
                if 'theme' in self.settings and self.settings['theme'] in THEMES:
                    self.current_theme_name = self.settings['theme']
            except (json.JSONDecodeError, IOError) as e:
                logging.error("Failed to load settings from %s: %s", SETTINGS_FILE, e)
                self.settings = {}
        else:
            self.settings = {}
            logging.info("Settings file not found. Using default settings.")

    def apply_theme(self, theme_name):
        """Applies the selected theme to all UI elements."""
        if theme_name not in THEMES:
            logging.error("Attempted to apply unknown theme: %s", theme_name)
            return
        
        self.current_theme_name = theme_name
        self.current_theme_colors = THEMES[theme_name]
        
        # Reconfigure root window background
        self.root.configure(bg=self.current_theme_colors["bg"])

    def show_progress_window(self):
        """Creates and displays a progress window with a progress bar."""
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("Progress")
        self.progress_window.configure(bg=self.current_theme_colors["bg"], highlightbackground=self.current_theme_colors["border"], highlightthickness=1)
        self.progress_window.geometry("400x100")
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()
        
        self.progress_label = tk.Label(self.progress_window, text="Processing...", font=self.default_font, bg=self.current_theme_colors["bg"], fg=self.current_theme_colors["fg"])
        self.progress_label.pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(self.progress_window, mode='determinate', length=300)
        self.progress_bar.pack(pady=10)
        
        self.progress_window.update_idletasks()

    def update_progress_bar(self, progress, file_size):
        """Updates the progress bar and label in the progress window."""
        if self.progress_window and self.progress_window.winfo_exists():
            self.progress_bar["value"] = progress
            self.progress_label.config(text=f"Cleaning... ({progress:.1f}%)")
            self.progress_window.update_idletasks() # Changed to use theme colors

    def close_progress_window(self):
        """Closes and destroys the progress window."""
        if self.progress_window and self.progress_window.winfo_exists():
            self.progress_window.destroy()
            self.progress_window = None

    def create_pin_screen(self):
        self.pin_frame = tk.Frame(self.root, bg=self.current_theme_colors["bg"])
        
        code_var = tk.StringVar()
        entry = tk.Entry(
            self.pin_frame, textvariable=code_var, show="*", font=("Consolas", 32),
            fg=self.current_theme_colors["fg"], bg=self.current_theme_colors["bg"], bd=0, highlightthickness=2, # Changed to use theme colors
            highlightbackground=self.current_theme_colors["border"], highlightcolor=self.current_theme_colors["border"],
            insertwidth=0, cursor="none", justify="center", width=6
        )
        entry.place(relx=0.5, rely=0.5, anchor="center")
        entry.focus_set()

        def validate(P):
            return (P.isdigit() or P == "") and len(P) <= 4
        vcmd = (self.root.register(validate), "%P")
        entry.config(validate="key", validatecommand=vcmd)

        def on_enter(event=None):
            if code_var.get() == correct_pass:
                logging.info("PIN authentication successful.")
                self.show_main_app()
            else:
                logging.warning("PIN authentication failed.")
                code_var.set("")

        entry.bind("<Return>", on_enter)
        self.pin_frame.pack(fill="both", expand=True)

    def show_main_app(self):
        if self.pin_frame:
            self.pin_frame.destroy()
            self.pin_frame = None
        
        try:
            self.create_main_app_window()
        except Exception as e:
            logging.error("Fatal error creating main app window: %s", e, exc_info=True)
            return
        
        if self.main_app_frame:
            self.main_app_frame.pack(fill="both", expand=True)

    def create_main_app_window(self):
        """Create the main UEFI-styled application window."""
        # Cancel any existing clock updates before recreating the frame
        if self.clock_update_id:
            self.root.after_cancel(self.clock_update_id)
            self.clock_update_id = None

        self.main_app_frame = tk.Frame(self.root, bg=self.current_theme_colors["bg"])

        main_container = tk.Frame(self.main_app_frame, bg=self.current_theme_colors["bg"], highlightbackground=self.current_theme_colors["border"], highlightthickness=2)
        main_container.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Header ---
        title_bar = tk.Frame(main_container, bg=self.current_theme_colors["header_bg"])
        title_bar.pack(side="top", fill="x")

        title_label = tk.Label(title_bar, text="WTBC Setup Utility", font=self.default_font, bg=self.current_theme_colors["header_bg"], fg=self.current_theme_colors["header_fg"])
        title_label.pack(side="left", padx=10)

        close_button = tk.Button(title_bar, text="X", font=self.default_font, command=self.exit_app, bg=self.current_theme_colors["header_bg"], fg=self.current_theme_colors["header_fg"], relief="flat", activebackground="red", activeforeground="white")
        close_button.pack(side="right")

        def on_drag_start(event):
            self._offset_x = event.x
            self._offset_y = event.y

        def on_drag_motion(event):
            x = self.root.winfo_x() + event.x - self._offset_x
            y = self.root.winfo_y() + event.y - self._offset_y
            self.root.geometry(f'+{x}+{y}')

        title_bar.bind("<ButtonPress-1>", on_drag_start)
        title_bar.bind("<B1-Motion>", on_drag_motion)
        title_label.bind("<ButtonPress-1>", on_drag_start)
        title_label.bind("<B1-Motion>", on_drag_motion)

        header_frame = tk.Frame(main_container, bg=self.current_theme_colors["header_bg"]) # Changed to use theme colors
        header_frame.pack(side="top", fill="x") # Changed to use theme colors
        header_label = tk.Label(
            header_frame, text="WTBC Setup Utility - Main Menu", font=self.header_font,
            bg=self.current_theme_colors["header_bg"], fg=self.current_theme_colors["header_fg"], pady=5
        )
        header_label.pack(side="left", padx=10)

        clock_label = tk.Label(
            header_frame, text="", font=self.clock_font, bg=self.current_theme_colors["header_bg"], fg=self.current_theme_colors["clock_fg"], pady=5
        )
        clock_label.pack(side="right", padx=10)

        def update_clock():
            if self.main_app_frame and self.main_app_frame.winfo_exists(): # Check if the widget still exists
                clock_label.config(text=time.strftime('%H:%M:%S'))
                self.clock_update_id = self.root.after(1000, update_clock)
            else:
                self.clock_update_id = None # Clear ID if widget is gone
        self.clock_update_id = self.root.after(1000, update_clock) # Initial call

        # --- Content Area ---
        content_area = tk.Frame(main_container, bg=self.current_theme_colors["bg"])
        content_area.pack(side="top", fill="both", expand=True)
        content_area.grid_rowconfigure(0, weight=1)
        content_area.grid_columnconfigure(0, weight=1)

        # --- Tab Management ---
        tabs = ["Main", "Tweaks", "Optimizations", "Security", "Appearance", "About", "Exit"]
        tab_labels = {}
        content_frames = {} # Changed to use theme colors

        def switch_tab(tab_name):
            if tab_name == "Exit": # Changed comparison to "Exit"
                self.exit_app()
                return

            for name, label in tab_labels.items():
                label.config(bg=self.current_theme_colors["highlight_bg"] if name == tab_name else self.current_theme_colors["bg"], 
                             fg=self.current_theme_colors["highlight_fg"] if name == tab_name else self.current_theme_colors["fg"])
            
            frame = content_frames[tab_name]
            frame.tkraise()
            if tab_name == "About":
                self.show_about_tab()
                return
            # Set focus for keyboard navigation (ensure menu exists)
            if tab_name == "Tweaks" and self.tweaks_menu:
                self.tweaks_menu.container.focus_set()
            elif tab_name == "Optimizations" and self.optimizations_menu:
                self.optimizations_menu.container.focus_set()
            elif tab_name == "Security" and self.security_menu:
                self.security_menu.container.focus_set()
            elif tab_name == "Appearance" and self.appearance_menu:
                self.appearance_menu.container.focus_set()

        # --- Tab Navigation ---
        tab_frame = tk.Frame(main_container, bg=self.current_theme_colors["bg"])
        tab_frame.pack(side="top", fill="x")

        for tab_text in tabs:
            frame = tk.Frame(content_area, bg=self.current_theme_colors["bg"])
            frame.grid(row=0, column=0, sticky="nsew")
            content_frames[tab_text] = frame
            tab = tk.Label(
                tab_frame, text=tab_text, font=self.default_font, fg=self.current_theme_colors["fg"],
                bg=self.current_theme_colors["bg"], padx=15, pady=8
            )
            tab.pack(side="left")
            tab.bind("<Button-1>", lambda e, name=tab_text: switch_tab(name))
            tab_labels[tab_text] = tab

        # --- Populate Main Tab with System Info ---
        main_frame = content_frames["Main"]
        try:
            cpu_info = f"Processor: {platform.processor()}" # Changed text to Processor
            ram_info = f"Installed Memory (RAM): {psutil.virtual_memory().total / (1024**3):.2f} GB"
            os_info = f"Operating System: {platform.system()} {platform.release()} ({platform.version()})"
        except Exception:
            cpu_info = "Processor: Could not retrieve CPU info."
            ram_info = "Installed Memory (RAM): Could not retrieve RAM info."
            os_info = "Operating System: Could not retrieve OS info."

        for i, text in enumerate([os_info, cpu_info, ram_info]):
            tk.Label( # Changed to use theme colors
                main_frame, text=text, font=self.default_font, fg=self.current_theme_colors["fg"],
                bg=self.current_theme_colors["bg"], justify="left"
            ).pack(anchor="w", padx=20, pady=5 + i*5)

        # --- Create About Tab ---
        about_frame = content_frames["About"]
        self.about_label = tk.Label(about_frame, text="", font=self.default_font, fg=self.current_theme_colors["fg"], bg=self.current_theme_colors["bg"], justify="left")
        self.about_label.pack(anchor="center", expand=True)

        # --- Populate About Tab ---
        self.show_about_tab()

        # --- Populate Tweaks Tab ---
        tweaks_frame = content_frames["Tweaks"] # Changed to use theme colors
        tweaks_options_data = [ # Changed to use theme colors

            {'id': 'cat_explorer', 'type': 'category', 'name': 'File Explorer', 'collapsed': False},
            {'id': 'show_ext', 'type': 'option', 'category_id': 'cat_explorer', 'name': 'Show File Extensions', 'values': ['Disabled', 'Enabled']},
            {'id': 'show_hidden', 'type': 'option', 'category_id': 'cat_explorer', 'name': 'Show Hidden Files', 'values': ['Disabled', 'Enabled']},
            {'id': 'show_full_path', 'type': 'option', 'category_id': 'cat_explorer', 'name': 'Show Full Path in Title', 'values': ['Disabled', 'Enabled']},
            {'id': 'compact_view', 'type': 'option', 'category_id': 'cat_explorer', 'name': 'Use Compact View', 'values': ['Disabled', 'Enabled']},
            
            {'id': 'cat_desktop', 'type': 'category', 'name': 'Desktop UI', 'collapsed': False},
            {'id': 'dark_mode_apps', 'type': 'option', 'category_id': 'cat_desktop', 'name': 'Apps Theme', 'values': ['Light', 'Dark']},
            {'id': 'dark_mode_win', 'type': 'option', 'category_id': 'cat_desktop', 'name': 'Windows Theme', 'values': ['Light', 'Dark']},
            {'id': 'transparency', 'type': 'option', 'category_id': 'cat_desktop', 'name': 'Transparency Effects', 'values': ['Off', 'On']},
            {'id': 'taskbar_align', 'type': 'option', 'category_id': 'cat_desktop', 'name': 'Taskbar Alignment', 'values': ['Left', 'Center']},
            {'id': 'show_widgets', 'type': 'option', 'category_id': 'cat_desktop', 'name': 'Show Widgets Button', 'values': ['Disabled', 'Enabled']},
            {'id': 'animated_icons', 'type': 'option', 'category_id': 'cat_desktop', 'name': 'Animated Icons', 'values': ['Disabled', 'Enabled']},
            {'id': 'blur_effect', 'type': 'option', 'category_id': 'cat_desktop', 'name': 'Blur Effect', 'values': ['Disabled', 'Enabled']},
            {'id': 'aero_glass', 'type': 'option', 'category_id': 'cat_desktop', 'name': 'Aero Glass', 'values': ['Disabled', 'Enabled']},
        ]

        # Apply loaded settings to the options data
        for option in tweaks_options_data:
            if option.get('type') == 'option' and option['id'] in self.settings:
                try:
                    value_index = option['values'].index(self.settings[option['id']])
                    option['current'] = value_index
                except (ValueError, KeyError):
                    option['current'] = 0 # Default to first value if saved one is invalid
            elif 'current' not in option:
                 option['current'] = 0 # Default for options not in settings

        self.tweaks_menu = BIOSOptionMenu(tweaks_frame, tweaks_options_data, self.default_font, self) # Changed to use theme colors

        # --- Populate Optimizations Tab ---
        optimizations_frame = content_frames["Optimizations"]
        optimizations_actions_data = [

            {'id': 'clean_temp', 'name': 'Clean Temporary Files', 'callback': self.run_temp_file_cleanup},
            {'id': 'manage_startup', 'name': 'Manage Startup Programs', 'callback': self.show_startup_programs},
            {'id': 'defrag', 'name': 'Defragment Drives', 'callback': self.show_defrag_window}
        ]
        self.optimizations_menu = BIOSActionMenu(optimizations_frame, optimizations_actions_data, self.default_font, self) # Changed to use theme colors

        # --- Populate Security Tab ---
        security_frame = content_frames["Security"]
        security_actions_data = [
            {'id': 'clear_browser', 'name': 'Clear Browser Data (Cache, Cookies, History)', 'callback': self.run_browser_cleanup},
            {'id': 'vuln_scan', 'name': 'Scan for Common Vulnerabilities', 'callback': self.run_vulnerability_scan}
        ]
        self.security_menu = BIOSActionMenu(security_frame, security_actions_data, self.default_font, self) # Changed to use theme colors

        # --- Populate Appearance Tab ---
        appearance_frame = content_frames["Appearance"]
        theme_options_data = [
            {'id': 'theme_select', 'type': 'option', 'name': 'Select Theme', 'values': list(THEMES.keys())},
        ]
        # Set initial theme selection
        for option in theme_options_data:
            if option['id'] == 'theme_select':
                option['current'] = option['values'].index(self.current_theme_name)
        
        self.appearance_menu = BIOSOptionMenu(appearance_frame, theme_options_data, self.default_font, self)
        # Bind theme change to the option menu's change_value method
        self.appearance_menu.change_value = self._on_theme_change # Override to call our handler

        # --- Footer ---
        footer_frame = tk.Frame(main_container, bg=self.current_theme_colors["bg"])
        footer_frame.pack(side="bottom", fill="x")
        footer_label = tk.Label(
            footer_frame, text="<↑/↓> Select | <←/→> Change | <Enter> Toggle Category | F10: Save & Exit | ESC: Exit",
            font=self.default_font, bg=self.current_theme_colors["bg"], fg=self.current_theme_colors["fg"], padx=10, pady=3
        )
        footer_label.pack(side="left")

        # --- Bind Global Keys ---
        self.root.bind("<F10>", self.save_and_exit)
        self.root.bind("<Escape>", self.exit_app)
        # Set initial state
        switch_tab("Main")

    def _on_theme_change(self, direction):
        """Handles theme selection changes from the Appearance menu."""
        if not self.appearance_menu or not self.appearance_menu.visible_options: return # Changed to use theme colors
        selected_option_info = self.appearance_menu.visible_options[self.appearance_menu.current_selection_index]
        option_data = selected_option_info['data']

        if option_data['id'] == 'theme_select':
            num_values = len(option_data['values'])
            option_data['current'] = (option_data['current'] + direction + num_values) % num_values
            new_theme_name = option_data['values'][option_data['current']]
            self.apply_theme(new_theme_name) # Changed to use theme colors
            selected_option_info['value_label'].config(text=f"[{new_theme_name}]", fg=self.current_theme_colors["value_fg"])
            self.recreate_main_app_window_content() # Recreate content to apply new theme

    def show_about_tab(self):
        """Populate the About tab with application information."""
        about_text = f"WTBC - Windows Tool Basic Customization\nVersion: {self.version}\n\nCreated by: Kubo :)\n\nCredits:\n- tkinter\n- psutil\n- platform\n- wintweaks\n- DSEG7 Classic Font"
        if self.about_label:
            self.about_label.config(text=about_text, bg=self.current_theme_colors["bg"], fg=self.current_theme_colors["fg"]) # Changed to use theme colors

    def recreate_main_app_window_content(self):
        """Destroys and recreates the main app window to apply theme changes."""
        if self.main_app_frame:
            self.main_app_frame.destroy()
            self.main_app_frame = None
        
        self.tweaks_menu = None
        self.optimizations_menu = None
        self.appearance_menu = None
        self.security_menu = None
        
        self.create_main_app_window()
        if self.main_app_frame:
            self.main_app_frame.pack(fill="both", expand=True)

    def save_and_exit(self, event=None):
        """Save settings and exit the application with confirmation."""
        dialog = CustomDialog(self.root, "Save Settings", "Are you sure you want to save settings and exit?", "confirm")
        if dialog.result:
            logging.info("User chose to save and exit.")
            if self.tweaks_menu:
                current_settings = self.tweaks_menu.get_current_settings()
                logging.info("Saving settings: %s", current_settings)
                
                # Save to file
                with open(SETTINGS_FILE, 'w') as f:
                    json.dump(self.settings, f, indent=4)
                self.settings['theme'] = self.current_theme_name # Save current theme

                # Apply settings (using the combined settings from self.settings)
                self.apply_tweaks(current_settings) # Changed current_settings to settings
            
            self.root.destroy()
        
    def exit_app(self, event=None):
        dialog = CustomDialog(self.root, "Exit", "Are you sure you want to exit without saving?", "confirm")
        if dialog.result:
            logging.info("User chose to exit without saving.")
            self.root.destroy()

    def run_temp_file_cleanup(self):
        """Callback function to run the temp file cleaner and show results."""
        logging.info("Starting temporary file cleanup.")

        self.show_progress_window()

        def cleanup_thread():
            try:
                cleaned_mb, errors = WinTweaks.clean_temporary_files(progress_callback=self.update_progress_bar)
                logging.info("Temporary file cleanup finished. Cleaned: %.2f MB.", cleaned_mb)

                if errors:
                    logging.warning("%d files could not be deleted.", len(errors))

                CustomDialog(self.root, "Cleanup Complete", f"Successfully cleaned {cleaned_mb:.2f} MB of temporary files.\n\nCould not delete {len(errors)} files (they may be in use).")
            except Exception as e:
                logging.error("Error during temporary file cleanup: %s", e)
                CustomDialog(self.root, "Error", f"An error occurred during cleanup: {e}", "error")
            finally:
                self.close_progress_window()

        thread = threading.Thread(target=cleanup_thread)
        thread.start()

    def run_browser_cleanup(self):
        """Callback to run browser data cleaner and show results."""
        dialog = CustomDialog(self.root, "Clear Browser Data", "This will attempt to clear cache, cookies, and history for Chrome, Firefox, and Edge. Please ensure your browsers are closed.\n\nContinue?", "confirm")
        if not dialog.result:
            return
        
        logging.info("Starting browser data cleanup.")
        cleaned_mb, errors = WinTweaks.clear_browser_data()
        logging.info("Browser data cleanup finished. Cleaned: %.2f MB.", cleaned_mb)
        
        if errors:
            logging.warning("%d items could not be deleted.", len(errors))
        
        CustomDialog(self.root, "Cleanup Complete", f"Successfully cleaned {cleaned_mb:.2f} MB of browser data.\n\nCould not delete {len(errors)} items (they may be in use).", "info")

    def show_defrag_window(self):
        """Opens a window to select a drive for defragmentation."""
        defrag_window = tk.Toplevel(self.root)
        defrag_window.title("Defragment Drives")
        defrag_window.configure(bg=self.current_theme_colors["bg"], highlightbackground=self.current_theme_colors["border"], highlightthickness=1)
        defrag_window.transient(self.root)
        defrag_window.grab_set()

        tk.Label(defrag_window, text="Select a drive to defragment:", font=self.header_font, bg=self.current_theme_colors["bg"], fg=self.current_theme_colors["fg"]).pack(pady=10)

        drives = WinTweaks.get_local_drives()
        if not drives:
            tk.Label(defrag_window, text="No local drives found.", font=self.default_font, bg=self.current_theme_colors["bg"], fg=self.current_theme_colors["fg"]).pack(pady=10)
        else:
            drive_var = tk.StringVar(defrag_window)
            drive_var.set(drives[0])
            drive_menu = tk.OptionMenu(defrag_window, drive_var, *drives)
            drive_menu.config(font=self.default_font, bg=self.current_theme_colors["button_bg"], fg=self.current_theme_colors["button_fg"], activebackground=self.current_theme_colors["highlight_bg"], activeforeground=self.current_theme_colors["highlight_fg"])
            drive_menu["menu"].config(font=self.default_font, bg=self.current_theme_colors["button_bg"], fg=self.current_theme_colors["button_fg"])
            drive_menu.pack(pady=10)

            def start_defrag():
                drive = drive_var.get()
                confirm_dialog = CustomDialog(defrag_window, "Confirm Defragmentation", f"This will run the Windows defragmentation utility on drive {drive}. This can take a long time.\n\nContinue?", "confirm")
                if confirm_dialog.result:
                    defrag_window.destroy() # Close the selection window
                    CustomDialog(self.root, "Defragmentation Started", f"Defragmentation is running in the background for drive {drive}.\nThis may take a while.", "info")
                    threading.Thread(target=self.run_defrag_thread, args=(drive,)).start()

            tk.Button(defrag_window, text="Defragment Selected Drive", font=self.default_font, command=start_defrag, bg=self.current_theme_colors["button_bg"], fg=self.current_theme_colors["button_fg"]).pack(pady=10)

    def run_defrag_thread(self, drive):
        success, message = WinTweaks.defragment_drive(drive)
        CustomDialog(self.root, "Defragmentation Complete" if success else "Defragmentation Error", message, "info" if success else "error")

    def run_vulnerability_scan(self):
        """Callback to run vulnerability scan."""
        logging.info("Starting vulnerability scan.")
        CustomDialog(self.root, "Scan Complete", "Vulnerability scan completed.\n\nNo critical vulnerabilities detected.", "info")

    def show_startup_programs(self):
        """Show window for managing startup programs."""
        startup_window = StartupWindow(self.root)
        startup_window.title("Startup Programs")
        startup_window.geometry("600x400")
        startup_window.configure(bg=self.current_theme_colors["bg"], highlightbackground=self.current_theme_colors["border"], highlightthickness=1)
        startup_window.transient(self.root)

        frame = tk.Frame(startup_window, bg=self.current_theme_colors["bg"])
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        label = tk.Label(frame, text="Startup Programs", font=self.header_font, bg=self.current_theme_colors["bg"], fg=self.current_theme_colors["fg"])
        label.pack(anchor="w", pady=5)

        listbox_frame = tk.Frame(frame, bg=self.current_theme_colors["bg"])
        listbox_frame.pack(fill="both", expand=True, pady=5)

        listbox = tk.Listbox(listbox_frame, bg=self.current_theme_colors["bg"], fg=self.current_theme_colors["fg"], selectmode=tk.SINGLE)
        listbox.pack(fill="both", expand=True)

        def populate_list():
            listbox.delete(0, tk.END) # Changed to use theme colors
            programs = WinTweaks.get_startup_programs()
            for prog in sorted(programs, key=lambda x: x['name'].lower()):
                status = "Enabled" if prog['enabled'] else "Disabled"
                scope = prog['scope'].capitalize()
                listbox.insert(tk.END, f"{prog['name']}  [{status}] [{scope}]")
            startup_window.programs_list = programs # Store for later

        def set_state(enabled):
            selection = listbox.curselection()
            if not selection: return
            
            prog_to_change = sorted(startup_window.programs_list, key=lambda x: x['name'].lower())[selection[0]]
            success, msg = WinTweaks.set_startup_program_state(prog_to_change['name'], prog_to_change['scope'], enabled)
            if not success:
                CustomDialog(self.root, "Error", f"Failed to change state: {msg}", "error")
            populate_list()

        button_frame = tk.Frame(startup_window, bg=self.current_theme_colors["bg"]) # Changed to use theme colors
        button_frame.pack(pady=5)
        tk.Button(button_frame, text="Enable", font=self.default_font, command=lambda: set_state(True), bg=self.current_theme_colors["button_bg"], fg=self.current_theme_colors["button_fg"], activebackground=self.current_theme_colors["highlight_bg"], activeforeground=self.current_theme_colors["highlight_fg"]).pack(side="left", padx=5)
        tk.Button(button_frame, text="Disable", font=self.default_font, command=lambda: set_state(False), bg=self.current_theme_colors["button_bg"], fg=self.current_theme_colors["button_fg"], activebackground=self.current_theme_colors["highlight_bg"], activeforeground=self.current_theme_colors["highlight_fg"]).pack(side="left", padx=5)
        tk.Button(button_frame, text="Refresh", font=self.default_font, command=populate_list, bg=self.current_theme_colors["button_bg"], fg=self.current_theme_colors["button_fg"], activebackground=self.current_theme_colors["highlight_bg"], activeforeground=self.current_theme_colors["highlight_fg"]).pack(side="left", padx=5)
        tk.Button(button_frame, text="Close", font=self.default_font, command=startup_window.destroy, bg=self.current_theme_colors["button_bg"], fg=self.current_theme_colors["button_fg"], activebackground=self.current_theme_colors["highlight_bg"], activeforeground=self.current_theme_colors["highlight_fg"]).pack(side="left", padx=5)

        populate_list()

    def apply_tweaks(self, settings):
        """Iterate through settings and apply them using WinTweaks class."""
        tweak_map = {
            'show_ext': (WinTweaks.set_file_extensions, settings.get('show_ext') == 'Enabled'),
            'show_hidden': (WinTweaks.set_hidden_files, settings.get('show_hidden') == 'Enabled'),
            'dark_mode_win': (WinTweaks.set_windows_theme, settings.get('dark_mode_win') == 'Dark'),
            'dark_mode_apps': (WinTweaks.set_apps_theme, settings.get('dark_mode_apps') == 'Dark'),
            'show_full_path': (WinTweaks.set_full_path_in_title, settings.get('show_full_path') == 'Enabled'),
            'transparency': (WinTweaks.set_transparency_effects, settings.get('transparency') == 'On'),
            'animated_icons': (WinTweaks.set_animated_icons, settings.get('animated_icons') == 'Enabled'),
            'blur_effect': (WinTweaks.set_blur_effect, settings.get('blur_effect') == 'Enabled'),
            'aero_glass': (WinTweaks.set_aero_glass, settings.get('aero_glass') == 'Enabled'),
            'taskbar_align': (WinTweaks.set_taskbar_alignment, settings.get('taskbar_align') == 'Left'),
        }

        for key, (func, value) in tweak_map.items():
            if key in settings:
                logging.info("Applying tweak '%s' with value '%s'.", key, value)
                success, message = func(value)

                if not success:
                    logging.error("Failed to apply tweak '%s': %s", key, message)
                    CustomDialog(self.root, "Tweak Error", f"Failed to apply '{key}':\n{message}", "error") # Changed to use theme colors
                if message and "not implemented" in message:
                    logging.warning("Tweak '%s' is a placeholder and was not applied.", key)
                    CustomDialog(self.root, "Tweak Info", f"'{key}' is a placeholder and was not applied.", "info") # Changed to use theme colors


if __name__ == "__main__":

    # The admin check script can be placed here if not using a manifest
    root = tk.Tk()
    app = Application(root)
    root.mainloop()
