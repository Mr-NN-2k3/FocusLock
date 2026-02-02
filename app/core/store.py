import sqlite3
import json
from datetime import datetime

DB_FILE = "focuslock.db"


class EventStore:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT
                )
            """)

    # -------- CORE --------

    def append_event(self, event_type, payload):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "INSERT INTO events (event_type, timestamp, payload) VALUES (?, ?, ?)",
                (event_type, datetime.now().isoformat(), json.dumps(payload))
            )

    def get_events(self):
        with sqlite3.connect(DB_FILE) as conn:
            rows = conn.execute(
                "SELECT event_type, timestamp, payload FROM events ORDER BY id"
            ).fetchall()

        return [
            {
                "type": r[0],
                "timestamp": r[1],
                "payload": json.loads(r[2]) if r[2] else {}
            }
            for r in rows
        ]

    # -------- PROJECTIONS --------

    def get_current_session(self):
        current = None

        for e in self.get_events():
            if e["type"] == "SESSION_START":
                current = dict(e["payload"])
                current["start_time"] = e["timestamp"]

            elif e["type"] in ("SESSION_COMPLETE", "SESSION_BROKEN"):
                if current and e["payload"].get("session_id") == current["session_id"]:
                    current = None

        return current

    def session_completed(self, session_id):
        return any(
            e["type"] == "SESSION_COMPLETE"
            and e["payload"].get("session_id") == session_id
            for e in self.get_events()
        )

    # -------- PENALTIES --------

    def get_violation_count(self, session_id):
        return sum(
            1 for e in self.get_events()
            if e["type"] == "FOCUS_VIOLATION"
            and e["payload"].get("session_id") == session_id
        )

    def get_penalty_seconds(self, session_id):
        return sum(
            e["payload"]["penalty_seconds"]
            for e in self.get_events()
            if e["type"] == "FOCUS_VIOLATION"
            and e["payload"].get("session_id") == session_id
        )

    # -------- TAMPER --------

    def get_last_heartbeat(self, session_id):
        for e in reversed(self.get_events()):
            if e["type"] == "HEARTBEAT" and e["payload"].get("session_id") == session_id:
                return datetime.fromisoformat(e["timestamp"])
        return None

    def has_suspicious_gap(self, session_id):
        return any(
            e["type"] == "SUSPICIOUS_GAP"
            and e["payload"].get("session_id") == session_id
            for e in self.get_events()
        )

    # -------- PREDICTION DATA --------

    def historic_break_pattern(self, elapsed_seconds):
        """Detect if breaks usually happen near this time"""
        breaks = []

        for e in self.get_events():
            if e["type"] == "SESSION_BROKEN":
                breaks.append(
                    datetime.fromisoformat(e["timestamp"]).timestamp()
                )

        if len(breaks) < 3:
            return False

        avg = sum(breaks) / len(breaks)
        return abs(elapsed_seconds - avg) < 300  # 5-minute window
