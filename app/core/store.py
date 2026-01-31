from datetime import datetime
import json
import os

DB_FILE = "focuslock_data.json"

class Store:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if not os.path.exists(DB_FILE):
            return {
                "user": {"name": "User", "intent": ""},
                "sessions": [],
                "current_session": None
            }
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return {
                "user": {"name": "User", "intent": ""},
                "sessions": [],
                "current_session": None
            }

    def save(self):
        with open(DB_FILE, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get_current_session(self):
        return self.data.get("current_session")

    def set_current_session(self, session_data):
        self.data["current_session"] = session_data
        self.save()

    def add_session_to_history(self, session):
        self.data["sessions"].append(session)
        self.save()
