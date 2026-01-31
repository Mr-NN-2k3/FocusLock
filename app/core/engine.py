from datetime import datetime, timedelta
from .store import Store

class FocusEngine:
    def __init__(self):
        self.store = Store()

    def start_session(self, duration_minutes, mode="deep"):
        """Starts a new focus session."""
        if self.store.get_current_session():
            raise Exception("Session already active")

        now = datetime.now()
        end_time = now + timedelta(minutes=int(duration_minutes))

        session = {
            "start_time": now.isoformat(),
            "expected_end_time": end_time.isoformat(),
            "duration_minutes": duration_minutes,
            "mode": mode,
            "status": "active"
        }
        self.store.set_current_session(session)
        return session

    def get_status(self):
        """Returns the current state of the system."""
        session = self.store.get_current_session()
        if not session:
            return {"active": False}
        
        now = datetime.now()
        end_time = datetime.fromisoformat(session["expected_end_time"])
        
        if now >= end_time:
            # Natural completion
            return {"active": True, "remaining": 0, "completed": True}
        
        remaining = (end_time - now).total_seconds()
        return {
            "active": True,
            "remaining": int(remaining),
            "total": int(session["duration_minutes"]) * 60,
            "mode": session["mode"]
        }

    def break_session(self, excuse):
        """Forcefully breaks a session with an excuse."""
        session = self.store.get_current_session()
        if not session:
            return None
        
        session["status"] = "broken"
        session["actual_end_time"] = datetime.now().isoformat()
        session["excuse"] = excuse
        
        self.store.add_session_to_history(session)
        self.store.set_current_session(None)
        return session

    def complete_session(self):
        """Marks a session as successfully completed."""
        session = self.store.get_current_session()
        if not session:
            return
            
        session["status"] = "completed"
        session["actual_end_time"] = datetime.now().isoformat()
        
        self.store.add_session_to_history(session)
        self.store.set_current_session(None)
