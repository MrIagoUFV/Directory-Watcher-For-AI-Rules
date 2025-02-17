import customtkinter as ctk
import threading
import queue
import time
from pathlib import Path
from watcher import DirectoryWatcher

class WatcherGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("Directory Watcher")
        self.geometry("600x400")
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Create frames
        self.create_settings_frame()
        self.create_log_frame()
        self.create_control_frame()

        # Initialize variables
        self.watcher_thread = None
        self.is_running = False
        self.log_queue = queue.Queue()
        self.after(100, self.check_log_queue)

    def create_settings_frame(self):
        """Create the settings frame with checkboxes and interval input"""
        settings_frame = ctk.CTkFrame(self)
        settings_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)

        # Rules files checkboxes
        self.cursor_var = ctk.BooleanVar(value=True)
        self.windsurf_var = ctk.BooleanVar(value=True)
        self.copilot_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(settings_frame, text=".cursorrules", 
                       variable=self.cursor_var).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkCheckBox(settings_frame, text=".windsurfrules", 
                       variable=self.windsurf_var).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkCheckBox(settings_frame, text="copilot-instructions.md", 
                       variable=self.copilot_var).grid(row=0, column=2, padx=5, pady=5)

        # Interval input
        interval_frame = ctk.CTkFrame(settings_frame)
        interval_frame.grid(row=1, column=0, columnspan=3, pady=5, sticky="ew")
        interval_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(interval_frame, text="Update interval (seconds):").grid(row=0, column=0, padx=5)
        self.interval_var = ctk.StringVar(value="30")
        self.interval_entry = ctk.CTkEntry(interval_frame, textvariable=self.interval_var, width=100)
        self.interval_entry.grid(row=0, column=1, padx=5, sticky="ew")

    def create_log_frame(self):
        """Create the log frame with text area"""
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(log_frame, wrap="word")
        self.log_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

    def create_control_frame(self):
        """Create the control frame with start/stop button"""
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.start_button = ctk.CTkButton(control_frame, text="Start", command=self.toggle_watcher)
        self.start_button.pack(pady=5)

    def log_message(self, message):
        """Add message to the log queue"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}\n")

    def check_log_queue(self):
        """Check for new log messages and update the text area"""
        while not self.log_queue.empty():
            message = self.log_queue.get()
            self.log_text.insert("end", message)
            self.log_text.see("end")
        self.after(100, self.check_log_queue)

    def toggle_watcher(self):
        """Start or stop the watcher thread"""
        if not self.is_running:
            try:
                interval = int(self.interval_var.get())
                if interval < 1:
                    raise ValueError("Interval must be at least 1 second")
                
                # Create watcher with selected options
                watcher = DirectoryWatcher(
                    use_cursor=self.cursor_var.get(),
                    use_windsurf=self.windsurf_var.get(),
                    use_copilot=self.copilot_var.get(),
                    interval=interval,
                    log_callback=self.log_message
                )
                
                # Start watcher thread
                self.watcher_thread = threading.Thread(target=watcher.run, daemon=True)
                self.watcher_thread.start()
                
                self.is_running = True
                self.start_button.configure(text="Stop")
                self.log_message("Watcher started")
                
                # Disable settings while running
                self.interval_entry.configure(state="disabled")
                
            except ValueError as e:
                self.log_message(f"Error: {str(e)}")
                
        else:
            self.is_running = False
            self.start_button.configure(text="Start")
            self.log_message("Watcher stopped")
            
            # Enable settings
            self.interval_entry.configure(state="normal")

def main():
    app = WatcherGUI()
    app.mainloop()

if __name__ == "__main__":
    main() 