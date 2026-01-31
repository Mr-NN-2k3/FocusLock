from datetime import datetime, timedelta
from .store import EventStore

class FocusEngine:
    def __init__(self):
        self.store = EventStore()

    def start_session(self, duration_minutes, mode="deep"):
        """Starts a new focus session via Event."""
        if self.store.get_current_session():
            raise Exception("Session already active")

        # Calculate expectations (but don't store "State", store "Intent")
        now = datetime.now()
        end_time = now + timedelta(minutes=int(duration_minutes))

        payload = {
            "expected_duration": int(duration_minutes),
            "expected_end_time": end_time.isoformat(),
            "mode": mode
        }
        self.store.append_event("SESSION_START", payload)
        return payload

    def get_status(self):
        """Reconstructs status from the Event Store."""
        session = self.store.get_current_session()
        if not session:
            return {"active": False}
        
        now = datetime.now()
        # session['expected_end_time'] comes from the payload
        end_time = datetime.fromisoformat(session["expected_end_time"])
        
        if now >= end_time:
            # It's technically complete time-wise, but needs an event to close it officially?
            # For now, let's say it's "Done" but waiting for user to acknowledge?
            # Or we auto-complete? Let's suggest auto-complete logic in client/next ping.
            return {"active": True, "remaining": 0, "completed": True}
        
        remaining = (end_time - now).total_seconds()
        return {
            "active": True,
            "remaining": int(remaining),
            "total": int(session["expected_duration"]) * 60,
            "mode": session["mode"]
        }

    def break_session(self, excuse):
        """Logs a failure event."""
        session = self.store.get_current_session()
        if not session:
            return None
        
        self.store.append_event("SESSION_BROKEN", {"excuse": excuse})
        return {"status": "broken"}

    def complete_session(self):
        """Logs a completion event."""
        session = self.store.get_current_session()
        if not session:
            return
            
        self.store.append_event("SESSION_COMPLETE", {})
