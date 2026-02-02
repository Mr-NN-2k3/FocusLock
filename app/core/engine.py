from datetime import datetime, timedelta
from .store import EventStore
import uuid

PENALTY_RULES = [60, 120, 300]
HEARTBEAT_THRESHOLD = 15
PREDICTION_THRESHOLD = 2  # conditions needed


class FocusEngine:
    def __init__(self):
        self.store = EventStore()

    # -------- SESSION --------

    def start_session(self, duration_minutes, mode="deep"):
        if self.store.get_current_session():
            raise Exception("Session already active")

        session_id = str(uuid.uuid4())
        now = datetime.now()
        end_time = now + timedelta(minutes=int(duration_minutes))

        self.store.append_event(
            "SESSION_START",
            {
                "session_id": session_id,
                "expected_duration": int(duration_minutes),
                "expected_end_time": end_time.isoformat(),
                "mode": mode
            }
        )

    def get_status(self):
        session = self.store.get_current_session()
        if not session:
            return {"active": False}

        now = datetime.now()
        base_end = datetime.fromisoformat(session["expected_end_time"])

        penalty_seconds = self.store.get_penalty_seconds(session["session_id"])
        adjusted_end = base_end + timedelta(seconds=penalty_seconds)

        # --- AUTO COMPLETE ---
        if now >= adjusted_end:
            if not self.store.session_completed(session["session_id"]):
                self.store.append_event(
                    "SESSION_COMPLETE",
                    {"session_id": session["session_id"]}
                )
            return {"active": False, "completed": True}

        remaining = int((adjusted_end - now).total_seconds())

        # --- PREDICTION CHECK ---
        prediction = self._predict_failure(session)

        return {
            "active": True,
            "remaining": remaining,
            "penalties": penalty_seconds,
            "prediction": prediction
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

    # -------- FAILURE PREDICTION --------

    def _predict_failure(self, session):
        """Returns prediction object or None"""

        session_id = session["session_id"]
        now = datetime.now()

        elapsed = (
            now - datetime.fromisoformat(session["start_time"])
        ).total_seconds()

        total = session["expected_duration"] * 60
        elapsed_ratio = elapsed / total

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
        if self.store.historic_break_pattern(elapsed):
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
