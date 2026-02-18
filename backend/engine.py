from datetime import datetime, timedelta
from .store import EventStore
import uuid

PENALTY_RULES = [60, 120, 300]
HEARTBEAT_THRESHOLD = 15
PREDICTION_THRESHOLD = 2  # conditions needed


class FocusEngine:
    def __init__(self):
        self.store = EventStore()
        self.active_monitor = None
        self.is_paused = False
        self.total_paused_duration = 0
        self.pause_start_time = None
        self.is_distracted = False # New state for blocking overlay

    # -------- SESSION --------

    def start_session(self, duration_minutes, mode="deep", whitelist=None, blacklist=None, intent=""):
        if self.store.get_current_session():
            raise Exception("Session already active")

        # Reset state
        self.is_paused = False
        self.total_paused_duration = 0
        self.is_distracted = False

        session_id = str(uuid.uuid4())
        now = datetime.now()
        end_time = now + timedelta(minutes=int(duration_minutes))

        self.store.append_event(
            "SESSION_START",
            {
                "session_id": session_id,
                "expected_duration": int(duration_minutes),
                "expected_end_time": end_time.isoformat(),
                "mode": mode,
                "intent": intent
            }
        )

        # Start Monitor
        self.set_monitor(whitelist, blacklist, intent, mode)

    # -------- MONITORING & AFK --------

    def set_monitor(self, whitelist, blacklist, intent, mode):
        from .monitor import WindowMonitor
        
        # Stop existing if any
        if self.active_monitor:
            self.active_monitor.stop()

        self.active_monitor = WindowMonitor(
            intent=intent,
            whitelist=whitelist,
            blacklist=blacklist,
            mode=mode,
            callback_violation=self._on_monitor_violation,
            callback_safe=self._on_monitor_safe
        )
        self.active_monitor.start()
    # -------- CLASSIFICATION --------

    def classify_activity(self, activity_text):
        """Simple keyword-based classification for MVP.
        In production, this would use a local LLM or API.
        """
        productive_keywords = [
            "research", "docs", "documentation", "reference", 
            "reading", "learning", "study", "debug", "overflow"
        ]
        
        text = activity_text.lower()
        is_productive = any(k in text for k in productive_keywords)
        
        if is_productive:
             self.store.append_event(
                "CONTEXT_SWITCH",
                {"reason": activity_text, "classification": "productive"}
            )
             return "productive"
        
        # Else, it's a violation
        self.register_violation("DISTRACTION_CONFIRMED")
        return "distraction"

    def get_status(self):
        session = self.store.get_current_session()
        if not session:
            # Cleanup monitor if session ended unexpectedly
            if self.active_monitor:
                self.active_monitor.stop()
                self.active_monitor = None
                
            return {
                "active": False,
                "user_stats": self.store.get_user_stats()
            }

        now = datetime.now()
        
        # If paused, we don't count time moving forward effectively for the deadline
        # But we do need to show remaining time.
        # Adjusted end time = original end + penalties + total_paused
        
        base_end = datetime.fromisoformat(session["expected_end_time"])
        penalty_seconds = self.store.get_penalty_seconds(session["session_id"])
        
        # Extend end time by pause duration
        current_pause_delta = 0
        if self.is_paused:
            current_pause_delta = (now - self.pause_start_time).total_seconds()
            
        total_extension = penalty_seconds + self.total_paused_duration + current_pause_delta
        adjusted_end = base_end + timedelta(seconds=total_extension)

        # --- AUTO COMPLETE ---
        if now >= adjusted_end and not self.is_paused:
            if not self.store.session_completed(session["session_id"]):
                self.store.append_event(
                    "SESSION_COMPLETE",
                    {"session_id": session["session_id"]}
                )
                if self.active_monitor:
                    self.active_monitor.stop()
                    
            return {
                "active": False, 
                "completed": True
            }

        remaining = int((adjusted_end - now).total_seconds())
        if remaining < 0: remaining = 0

        # --- PREDICTION CHECK ---
        prediction = self._predict_failure(session)
        
        return {
            "active": True,
            "mode": session.get("mode", "deep"),
            "remaining": remaining,
            "penalties": penalty_seconds,
            "prediction": prediction,
            "paused": self.is_paused,
            "is_distracted": self.is_distracted, # UI Overlay Trigger
            "user_stats": self.store.get_user_stats()
        }

    # -------- VIOLATIONS --------

    def register_violation(self, violation_type):
        session = self.store.get_current_session()
        if not session:
            return

        count = self.store.get_violation_count(session["session_id"])
        penalty = PENALTY_RULES[min(count, len(PENALTY_RULES) - 1)]

        self.store.append_event(
            "FOCUS_VIOLATION",
            {
                "session_id": session["session_id"],
                "violation": violation_type,
                "penalty_seconds": penalty
            }
        )

    # -------- HEARTBEAT / TAMPER --------

    def heartbeat(self):
        session = self.store.get_current_session()
        if not session:
            return

        last = self.store.get_last_heartbeat(session["session_id"])
        now = datetime.now()

        if last:
            gap = (now - last).total_seconds()
            if gap > HEARTBEAT_THRESHOLD:
                self.store.append_event(
                    "SUSPICIOUS_GAP",
                    {
                        "session_id": session["session_id"],
                        "gap_seconds": int(gap)
                    }
                )

        self.store.append_event(
            "HEARTBEAT",
            {"session_id": session["session_id"]}
        )

    # -------- BREAK --------

    def break_session(self, excuse):
        session = self.store.get_current_session()
        if not session:
            return

        self.store.append_event(
            "SESSION_BREAK_ATTEMPT",
            {"session_id": session["session_id"]}
        )

        self.store.append_event(
            "SESSION_BROKEN",
            {
                "session_id": session["session_id"],
                "excuse": excuse
            }
        )

    # -------- MONITORING & AFK --------

    def set_monitor(self, whitelist, blacklist):
        from .monitor import WindowMonitor
        
        # Stop existing if any
        if self.active_monitor:
            self.active_monitor.stop()

        self.active_monitor = WindowMonitor(
            whitelist=whitelist,
            blacklist=blacklist,
            callback_violation=self._on_monitor_violation,
            callback_safe=self._on_monitor_safe
        )
        self.active_monitor.start()

    def _on_monitor_violation(self, reason):
        # Callback: Distraction Active
        if not self.is_distracted:
            self.is_distracted = True
            self.pause_session() # Pause timer
            print(f"DISTRACTION DETECTED: {reason} - PAUSING")

    def _on_monitor_safe(self):
        # Callback: Distraction Cleared
        if self.is_distracted:
            self.is_distracted = False
            self.resume_session() # Resume timer
            print("DISTRACTION CLEARED - RESUMING")

    def pause_session(self):
        """Called when AFK detected > 30m"""
        if self.is_paused: return
        self.is_paused = True
        self.pause_start_time = datetime.now()
        
    def resume_session(self):
        """Called when user returns"""
        if not self.is_paused: return
        
        # Calculate how long we were paused and extend the end time
        duration = datetime.now() - self.pause_start_time
        self.total_paused_duration += duration.total_seconds()
        
        self.is_paused = False
        self.pause_start_time = None

    # -------- FAILURE PREDICTION --------

    def _predict_failure(self, session):
        """Returns prediction object or None"""
        # (Existing logic unchanged, just keeping the method signature context)
        session_id = session["session_id"]
        now = datetime.now()

        # Adjust elapsed for pause
        elapsed_real = (now - datetime.fromisoformat(session["start_time"])).total_seconds()
        elapsed_active = elapsed_real - self.total_paused_duration

        total = session["expected_duration"] * 60
        elapsed_ratio = elapsed_active / total if total > 0 else 0

        signals = 0
        reasons = []

        # Signal 1: Violations
        if self.store.get_violation_count(session_id) >= 2:
            signals += 1
            reasons.append("Repeated focus violations")

        # Signal 2: Penalties
        if self.store.get_penalty_seconds(session_id) >= 180:
            signals += 1
            reasons.append("High accumulated penalties")

        # Signal 3: Late-session fatigue
        if elapsed_ratio >= 0.7:
            signals += 1
            reasons.append("Late-session fatigue window")

        # Signal 4: Suspicious gaps
        if self.store.has_suspicious_gap(session_id):
            signals += 1
            reasons.append("Suspicious inactivity detected")

        # Signal 5: Historical failure timing
        if self.store.historic_break_pattern(elapsed_active):
            signals += 1
            reasons.append("Matches historical failure pattern")

        if signals >= PREDICTION_THRESHOLD:
            self.store.append_event(
                "FAILURE_PREDICTED",
                {
                    "session_id": session_id,
                    "signals": signals,
                    "reasons": reasons
                }
            )
            return {
                "warning": True,
                "signals": signals,
                "reasons": reasons
            }

        return None
