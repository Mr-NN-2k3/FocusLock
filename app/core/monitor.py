import ctypes
import threading
import time
import re

class WindowMonitor:
    def __init__(self, allowed_keywords, callback_violation):
        self.allowed_keywords = [k.lower().strip() for k in allowed_keywords if k.strip()]
        self.callback = callback_violation
        self.running = False
        self.thread = None
        self.last_title = ""
        
        # Load user32.dll for Windows API
        self.user32 = ctypes.windll.user32

    def _get_active_window_title(self):
        try:
            hwnd = self.user32.GetForegroundWindow()
            length = self.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        except:
            return ""

    def _monitor_loop(self):
        while self.running:
            title = self._get_active_window_title()
            
            if title and title != self.last_title:
                self.last_title = title
                # Check if title is relevant (ignore empty or system UI often)
                if title in ["Task Switching", "Task View"]: 
                    continue
                    
                # INTELLIGENT DETECTION LOGIC
                # 1. By default, everything is suspended unless it matches an allowed keyword.
                # 2. FocusLock itself is always allowed.
                if "FocusLock" in title:
                    pass
                else:
                    is_allowed = False
                    for k in self.allowed_keywords:
                        if k in title.lower():
                            is_allowed = True
                            break
                    
                    if not is_allowed:
                        # IT'S A DISTRACTION
                        self.callback(f"Unauthorized Activity: {title}")

            time.sleep(2) # Check every 2 seconds

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
