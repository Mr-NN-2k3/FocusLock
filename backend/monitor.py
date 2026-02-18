import ctypes
import threading
import time
import re

    # -------- INTENT ALIGNMENT ENGINE --------

class IntentAlignmentEngine:
    def __init__(self, user_intent, whitelist=None, blacklist=None, mode="deep"):
        self.user_intent = user_intent.lower() if user_intent else ""
        self.whitelist = whitelist or []
        self.blacklist = blacklist or []
        self.mode = mode
        
        # Base Safe List (Context-Aware)
        self.base_safe = [
            "focuslock", "code", "project", "research", "docs", "documentation",
            "python", "javascript", "html", "css", "java", "c++",
            "github", "gitlab", "stackoverflow", "machine learning", "ai",
            "model", "training", "dataset", "jupyter", "colab", "kaggle",
            "visual studio", "vscode", "sublime", "atom", "jetbrains",
            "pdf", "paper", "article", "university", "course", "lecture",
            "gpt", "chatgpt", "claude", "gemini", "bard", "llm", "transformer"
        ]

        # Base Distraction List
        self.base_distractions = [
            "youtube", "netflix", "facebook", "twitter", "instagram", "tiktok",
            "reddit", "pinterest", "twitch", "disney+", "hulu", "prime video",
            "steam", "game", "playing", "watch", "movie", "tv show",
            "whatsapp", "telegram", "discord", "messenger", "chat"
        ]

    def evaluate(self, activity_title):
        """
        Returns: (classification, score, reason)
        Score: 0-100 (High = Distraction)
        """
        title = activity_title.lower()
        
        # 0. System Whitelist (Always Allowed)
        if "focuslock" in title:
            return "PRODUCTIVE", 0, "System Authority"
            
        # 1. Strict Whitelist Mode Override
        if self.whitelist:
            for w in self.whitelist:
                if w in title:
                    return "PRODUCTIVE", 0, "User Whitelist"
            # In strict mode, if not whitelisted, it IS a distraction
            return "DISTRACTION", 100, "Not in Whitelist (Strict Mode)"

        # 2. Blacklist Mode Override (Absolute Block)
        for b in self.blacklist:
            if b in title:
                return "DISTRACTION", 100, "User Blacklist"

        # 3. Analyze Key Components
        intent_words = [w for w in self.user_intent.split() if len(w) > 3]
        educational_keywords = ["tutorial", "course", "lecture", "learn", "study", "documentation", "how to", "guide"]
        
        is_distraction_platform = any(d in title for d in self.base_distractions)
        matches_intent = any(w in title for w in intent_words) if intent_words else False
        is_educational = any(e in title for e in educational_keywords)
        is_safe_context = any(s in title for s in self.base_safe)

        # 4. Distraction Platform Logic (The Filter)
        if is_distraction_platform:
            # Platform is normally a distraction (e.g. YouTube, Netflix)
            
            # EXCEPTION A: Explicit Intent Match
            # e.g. Intent="Watch Movie", Title="Netflix..." -> Matches "Movie"? Maybe not.
            # e.g. Intent="Learn Python", Title="Python Tutorial - YouTube" -> Matches "Python"
            if matches_intent and (is_educational or "watch" in self.user_intent):
                 return "PRODUCTIVE", 20, "Distraction Platform allowed by specific Intent"
            
            # EXCEPTION B: General Educational Use
            if is_educational:
                return "NEUTRAL", 45, "Educational Content on Distraction Platform"

            # No Exception -> BLOCK
            return "DISTRACTION", 95, "Distraction Pattern Detected"

        # 5. Safe Context / Intent Match (Non-Distraction Platforms)
        if matches_intent:
            return "PRODUCTIVE", 10, "Aligned with Intent"
            
        if is_safe_context:
            return "PRODUCTIVE", 15, "Safe Productive Context"

        # 6. Default / Unknown
        # In Deep Mode, unknowns are suspicious but we shouldn't block blindly unless strict
        if self.mode == "deep":
            return "NEUTRAL", 55, "Unclassified Activity"
        
        return "PRODUCTIVE", 30, "Unclassified Activity (Standard)"


class WindowMonitor:
    def __init__(self, intent=None, whitelist=None, blacklist=None, mode="deep", callback_violation=None, callback_safe=None):
        self.engine = IntentAlignmentEngine(intent, whitelist, blacklist, mode)
        self.callback_violation = callback_violation
        self.callback_safe = callback_safe
        self.running = False
        self.thread = None
        self.last_title = ""
        self.is_distracted = False
        
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

    def _show_popup(self, title, reason):
        def popup():
            self.user32.MessageBoxW(0, f"DISTRACTION DETECTED:\n{title}\n\nREASON: {reason}\n\nGET BACK TO WORK.", "FOCUSLOCK AUTHORITY", 0x10 | 0x40000)
        threading.Thread(target=popup, daemon=True).start()

    def _monitor_loop(self):
        while self.running:
            title = self._get_active_window_title()
            
            if not title or title in ["Task Switching", "Task View", "Program Manager"]: 
                time.sleep(1)
                continue
            
            # Use Intent Engine
            classification, score, reason = self.engine.evaluate(title)
            
            # Threshold: > 60 is Distraction
            is_currently_distracted = score > 60

            if is_currently_distracted:
                if not self.is_distracted:
                    self.is_distracted = True
                    self._show_popup(title, reason)
                    
                    if self.callback_violation:
                        self.callback_violation(f"{reason}: {title}")
            else:
                if self.is_distracted:
                    self.is_distracted = False
                    if self.callback_safe:
                        self.callback_safe()

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
