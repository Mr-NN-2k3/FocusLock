from datetime import datetime, timedelta
import time
import uuid
import threading

from .store import EventStore
from .monitor import WindowMonitor
from .classifier import classifier as clf
from .logger import logger

PENALTY_RULES = [60, 120, 300]
HEARTBEAT_THRESHOLD = 15
PREDICTION_THRESHOLD = 2

DRIFT_WINDOW_SEC = 60
DRIFT_THRESHOLD = 5

# Bug #9 Fix: Enforce explicit FSM state transitions
ALLOWED_TRANSITIONS = {
    "PRODUCTIVE": ["PRODUCTIVE", "WARNING"],
    "WARNING": ["WARNING", "DISTRACTION", "PRODUCTIVE"],
    "DISTRACTION": ["DISTRACTION", "WARNING"],
}

class FocusEngine:
    def __init__(self):
        self.store = EventStore()
        self.active_monitor = None

        # Bug #3 Fix: Lock to protect shared state accessed from monitor thread
        self._lock = threading.Lock()

        # Runtime session overrides
        self.is_paused = False
        self.total_paused_duration = 0
        self.pause_start_time = None

        # State Management
        self.current_state = "PRODUCTIVE"  # PRODUCTIVE, WARNING, DISTRACTION
        self.last_state = "PRODUCTIVE"
        self.last_alert_time = 0
        self.alert_cooldown = 10  # 10 secs before spamming again at the same state level

        self.last_classified_state = None  # To expose current app details to UI

        # Drift Tracking
        self.recent_switches = []

        self._check_resume_session()

    def _check_resume_session(self):
        """State Persistence: Recover session if app restarts"""
        session = self.store.get_current_session()
        if session:
            self.set_monitor(
                whitelist=session.get("whitelist", []), 
                blacklist=session.get("blacklist", []), 
                intent=session.get("intent", ""), 
                mode=session.get("mode", "deep")
            )

    # -------- SESSIONS --------

    def start_session(self, duration_minutes, mode="deep", whitelist=None, blacklist=None, intent=""):
        active_session = self.store.get_current_session()
        if active_session:
            self.store.append_event(
                "SESSION_BROKEN",
                {
                    "session_id": active_session["session_id"],
                    "excuse": "Force Restart"
                }
            )

        self.is_paused = False
        self.total_paused_duration = 0
        self.current_state = "PRODUCTIVE"

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
                "intent": intent,
                "whitelist": whitelist,
                "blacklist": blacklist
            }
        )

        self.set_monitor(whitelist, blacklist, intent, mode)

    def set_monitor(self, whitelist, blacklist, intent, mode):
        if self.active_monitor:
            self.active_monitor.stop()

        self.active_monitor = WindowMonitor(callback_state_change=self._on_state_change)
        self.active_monitor.start()

    # -------- EVENT DRIVEN PIPELINE --------

    def _on_state_change(self, raw_state):
        if self.is_paused:
            return
        session = self.store.get_current_session()
        if not session:
            return

        now = time.time()

        # 1. Drift Tracking (Bug #10 Fix: time-decay already in place, keep trimmed)
        with self._lock:
            self.recent_switches.append(now)
            self.recent_switches = [
                t for t in self.recent_switches if now - t <= DRIFT_WINDOW_SEC
            ]
            is_drifting = len(self.recent_switches) > DRIFT_THRESHOLD

        # 2. Extract Features
        features = clf.extract_features(
            state=raw_state,
            intent=session.get("intent", ""),
            mode=session.get("mode", "deep"),
            whitelist=session.get("whitelist", []),
            blacklist=session.get("blacklist", [])
        )

        # 3. Decision Logic
        new_state = "PRODUCTIVE"
        reason = "Aligned"
        confidence = features["confidence"]

        if features["whitelist_match"]:
            new_state = "PRODUCTIVE"
            reason = "Whitelist match"
        elif features["blacklist_match"]:
            new_state = "DISTRACTION"
            reason = "Blacklist match"
        else:
            h_score = features["heuristic_score"]
            if h_score < -15:
                if confidence < 75:
                    new_state = "WARNING"
                    reason = "Low confidence distraction"
                else:
                    new_state = "DISTRACTION"
                    reason = "Distraction detected"
            elif h_score > 15:
                new_state = "PRODUCTIVE"
                reason = "Aligned"
            else:
                new_state = "PRODUCTIVE"  # Ambiguous → productive by default unless drifting

        if is_drifting and new_state == "PRODUCTIVE":
            new_state = "WARNING"
            reason = "Drift Detected (Frequent Switching)"

        # Bug #9 Fix: Enforce FSM transitions — only allow valid state changes
        with self._lock:
            allowed = ALLOWED_TRANSITIONS.get(self.current_state, [])
            if new_state not in allowed:
                # Snap to the closest allowed state instead of jumping illegally
                new_state = self.current_state

            self.last_state = self.current_state
            self.current_state = new_state
            self.last_classified_state = {
                "app": raw_state.get("app", ""),
                "title": raw_state.get("title", ""),
                "state": new_state,
                "features": features,
                "reason": reason
            }
            last_alert_time_snapshot = self.last_alert_time

        # 4. Intervention & Cooldown Layer
        if self.current_state != "PRODUCTIVE":
            if self.current_state != self.last_state or (now - last_alert_time_snapshot) > self.alert_cooldown:
                with self._lock:
                    self.last_alert_time = now
                if self.current_state == "DISTRACTION":
                    self.register_violation(f"DISTRACTION: {reason}")

        # 5. Logging
        logger.log_activity(
            timestamp=datetime.now().isoformat(),
            title=raw_state.get("title", ""),
            app=raw_state.get("app", ""),
            url=raw_state.get("url", ""),
            features=features,
            classification=self.current_state,
            reason=reason
        )

        logger.log_training_row(
            title=raw_state.get("title", ""),
            app=raw_state.get("app", ""),
            url=raw_state.get("url", ""),
            goal=session.get("intent", ""),
            mode=session.get("mode", "deep"),
            similarity=features["semantic_similarity"],
            heuristic=features["heuristic_score"],
            confidence=features["confidence"],
            label=self.current_state
        )

    # -------- STATUS DISPLAY --------

    def get_status(self):
        session = self.store.get_current_session()
        if not session:
            if self.active_monitor:
                self.active_monitor.stop()
                self.active_monitor = None
            return {"active": False, "user_stats": self.store.get_user_stats()}

        now = datetime.now()
        base_end = datetime.fromisoformat(session["expected_end_time"])
        penalty_seconds = self.store.get_penalty_seconds(session["session_id"])
        total_paused_from_store = session.get("paused_duration", 0)
        
        current_pause_delta = 0
        if self.is_paused and self.pause_start_time:
            current_pause_delta = (now - self.pause_start_time).total_seconds()
            
        total_extension = penalty_seconds + total_paused_from_store + current_pause_delta
        adjusted_end = base_end + timedelta(seconds=total_extension)

        if now >= adjusted_end and not self.is_paused:
            if not self.store.session_completed(session["session_id"]):
                self.store.append_event("SESSION_COMPLETE", {"session_id": session["session_id"]})
                if self.active_monitor:
                    self.active_monitor.stop()
            return {
                "active": False, 
                "completed": True,
                "summary": {
                    "duration": session.get("expected_duration", 0),
                    "violations": self.store.get_violation_count(session["session_id"]),
                    "penalties": self.store.get_penalty_seconds(session["session_id"]),
                    "mode": session.get("mode", "deep"),
                    "intent": session.get("intent", "None"),
                    "streak": session.get("streak", 1)
                },
                "user_stats": self.store.get_user_stats()
            }

        remaining = max(0, int((adjusted_end - now).total_seconds()))
        prediction = self._predict_failure(session)
        
        return {
            "active": True,
            "mode": session.get("mode", "deep"),
            "remaining": remaining,
            "penalties": penalty_seconds,
            "prediction": prediction,
            "paused": self.is_paused,
            "current_state": self.current_state,  # PRODUCTIVE, WARNING, DISTRACTION
            "activity_snapshot": self.last_classified_state,
            "streak": session.get("streak", 1),
            "user_stats": self.store.get_user_stats()
        }

    # -------- VIOLATIONS & CONTROL --------

    def register_violation(self, violation_type):
        session = self.store.get_current_session()
        if not session: return

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

    def heartbeat(self):
        session = self.store.get_current_session()
        if not session: return

        last = self.store.get_last_heartbeat(session["session_id"])
        now = datetime.now()

        if last:
            gap = (now - last).total_seconds()
            if gap > HEARTBEAT_THRESHOLD:
                self.store.append_event("SUSPICIOUS_GAP", {"session_id": session["session_id"], "gap_seconds": int(gap)})

        self.store.append_event("HEARTBEAT", {"session_id": session["session_id"]})

    def extend_session(self, additional_minutes):
        session = self.store.get_current_session()
        if not session: return False
        self.store.append_event("SESSION_EXTEND", {"session_id": session["session_id"], "extension_minutes": int(additional_minutes)})
        return True

    def stop_session(self):
        session = self.store.get_current_session()
        if not session: return False
        self.store.append_event("SESSION_STOP", {"session_id": session["session_id"]})
        if self.active_monitor:
            self.active_monitor.stop()
            self.active_monitor = None
        return True

    def break_session(self, excuse):
        session = self.store.get_current_session()
        if not session: return
        self.store.append_event("SESSION_BREAK_ATTEMPT", {"session_id": session["session_id"]})
        self.store.append_event("SESSION_BROKEN", {"session_id": session["session_id"], "excuse": excuse})

    def pause_session(self):
        if self.is_paused: return
        self.is_paused = True
        self.pause_start_time = datetime.now()
        session = self.store.get_current_session()
        if session:
            self.store.append_event("SESSION_PAUSED", {"session_id": session["session_id"]})
            
    def resume_session(self):
        if not self.is_paused: return
        duration = datetime.now() - self.pause_start_time
        self.is_paused = False
        self.pause_start_time = None
        session = self.store.get_current_session()
        if session:
            self.store.append_event("SESSION_RESUMED", {"session_id": session["session_id"], "paused_seconds": duration.total_seconds()})

    # -------- FAILURE PREDICTION --------

    def _predict_failure(self, session):
        session_id = session["session_id"]
        now = datetime.now()
        total_paused = session.get("paused_duration", 0)
        elapsed_real = (now - datetime.fromisoformat(session["start_time"])).total_seconds()
        elapsed_active = elapsed_real - total_paused

        total = session["expected_duration"] * 60
        elapsed_ratio = elapsed_active / total if total > 0 else 0

        signals = 0
        reasons = []

        if self.store.get_violation_count(session_id) >= 2:
            signals += 1
            reasons.append("Repeated focus violations")
        if self.store.get_penalty_seconds(session_id) >= 180:
            signals += 1
            reasons.append("High accumulated penalties")
        if elapsed_ratio >= 0.7:
            signals += 1
            reasons.append("Late-session fatigue window")
        if self.store.has_suspicious_gap(session_id):
            signals += 1
            reasons.append("Suspicious inactivity detected")
        if self.store.historic_break_pattern(elapsed_active):
            signals += 1
            reasons.append("Matches historical failure pattern")

        if signals >= PREDICTION_THRESHOLD:
            self.store.append_event("FAILURE_PREDICTED", {"session_id": session_id, "signals": signals, "reasons": reasons})
            return {"warning": True, "signals": signals, "reasons": reasons}
        return None
