import ctypes
from ctypes import wintypes
import threading
import time
import platform
import psutil

class WindowMonitor:
    """
    Monitor Layer: Extracts raw state (Window Title, App Name).
    Emits an event ONLY when the active state changes.
    Does NOT contain classification logic.
    """
    def __init__(self, callback_state_change=None):
        # Bug #1 Fix: Guard against non-Windows platforms
        if platform.system() != "Windows":
            raise NotImplementedError(
                f"WindowMonitor is only supported on Windows. "
                f"Current platform: {platform.system()}"
            )

        self.callback_state_change = callback_state_change
        self.running = False
        self.thread = None
        self.last_state_hash = None

        # Load Windows API DLLs
        self.user32 = ctypes.windll.user32
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD

    def _get_active_window_info(self):
        try:
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                return "", "Unknown"
            
            # Get Title
            length = self.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value

            # Get Process Name
            pid = wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            try:
                # psutil can throw NoSuchProcess if it died instantly
                process = psutil.Process(pid.value)
                app_name = process.name()
            except Exception:
                app_name = "Unknown"

            return title, app_name
        except Exception:
            return "", "Unknown"

    def _monitor_loop(self):
        while self.running:
            try:
                # Bug #12 Fix: Wrap the entire loop body so thread never dies silently
                title, app_name = self._get_active_window_info()

                # Ignore OS level switching overlays
                if title in ["Task Switching", "Task View", "Program Manager"]:
                    time.sleep(1)
                    continue

                state = {
                    "title": title,
                    "app": app_name,
                    "url": ""  # Reserved for future browser extension integration
                }

                state_hash = f"{title}_{app_name}"

                if state_hash != self.last_state_hash:
                    self.last_state_hash = state_hash
                    if self.callback_state_change:
                        self.callback_state_change(state)

                # Polling frequency - debounce on change so downstream NLP only fires when needed
                time.sleep(1)

            except Exception as e:
                # Log and keep running; don't let a transient error kill the thread
                print(f"[WindowMonitor] Error in monitor loop: {e}")
                time.sleep(1)

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
