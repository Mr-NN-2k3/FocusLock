import sqlite3
import json
import hashlib
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
                    payload TEXT,
                    previous_hash TEXT,
                    hash TEXT
                )
            """)
            self._ensure_columns(conn)

    def _ensure_columns(self, conn):
        """Ensure hash columns exist for existing databases"""
        cursor = conn.execute("PRAGMA table_info(events)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "previous_hash" not in columns:
            conn.execute("ALTER TABLE events ADD COLUMN previous_hash TEXT")
        if "hash" not in columns:
            conn.execute("ALTER TABLE events ADD COLUMN hash TEXT")

    # -------- LOGIC --------

    def _calculate_hash(self, prev_hash, event_type, timestamp, payload):
        """Create a purely cryptographic chain"""
        content = f"{prev_hash}|{event_type}|{timestamp}|{payload}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _get_last_hash(self, conn):
        row = conn.execute("SELECT hash FROM events ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row and row[0] else "GENESIS_HASH"

    # -------- CORE --------

    def append_event(self, event_type, payload):
        timestamp = datetime.now().isoformat()
        payload_json = json.dumps(payload)
        
        with sqlite3.connect(DB_FILE) as conn:
            prev_hash = self._get_last_hash(conn)
            current_hash = self._calculate_hash(prev_hash, event_type, timestamp, payload_json)
            
            conn.execute(
                """INSERT INTO events 
                   (event_type, timestamp, payload, previous_hash, hash) 
                   VALUES (?, ?, ?, ?, ?)""",
                (event_type, timestamp, payload_json, prev_hash, current_hash)
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
        
    def verify_integrity(self):
        """Re-calculate all hashes to verify chain has not been tampered"""
        with sqlite3.connect(DB_FILE) as conn:
            rows = conn.execute(
                "SELECT id, event_type, timestamp, payload, previous_hash, hash FROM events ORDER BY id"
            ).fetchall()
            
        last_hash = "GENESIS_HASH"
        for r in rows:
            calc_hash = self._calculate_hash(last_hash, r[1], r[2], r[3])
            
            # Check previous hash pointer
            if r[5]: # If this row has a hash
                if r[4] and r[4] != last_hash:
                     return False, f"Broken Chain at ID {r[0]}: Previous hash mismatch"
                 
                if r[5] != calc_hash:
                    return False, f"Integrity Failure at ID {r[0]}: Content modified"
                
            last_hash = r[5] if r[5] else "GENESIS_HASH"
            
        return True, "Integrity Verified"

    # -------- PROJECTIONS --------

    def get_current_session(self):
        current = None

        for e in self.get_events():
            if e["type"] == "SESSION_START":
                if not e["payload"].get("session_id"):
                    continue
                current = dict(e["payload"])
                current["start_time"] = e["timestamp"]
                current["paused_duration"] = 0

            elif e["type"] in ("SESSION_STOP", "SESSION_BROKEN"):
                if current and e["payload"].get("session_id") == current.get("session_id"):
                    current = None
            elif e["type"] == "SESSION_EXTEND":
                if current and e["payload"].get("session_id") == current.get("session_id"):
                    current["expected_duration"] += e["payload"].get("extension_minutes", 0)
                    from datetime import timedelta
                    end_time_dt = datetime.fromisoformat(current["expected_end_time"]) + timedelta(minutes=e["payload"].get("extension_minutes", 0))
                    current["expected_end_time"] = end_time_dt.isoformat()
                    current["streak"] = current.get("streak", 1) + 1
            elif e["type"] == "SESSION_RESUMED":
                if current and e["payload"].get("session_id") == current.get("session_id"):
                    current["paused_duration"] += e["payload"].get("paused_seconds", 0)

        return current

    def session_completed(self, session_id):
        # Check if the latest completion happened after the latest extend
        events = self.get_events()
        last_comp = -1
        last_ext = -1
        for i, e in enumerate(events):
            if e["payload"].get("session_id") == session_id:
                if e["type"] == "SESSION_COMPLETE": last_comp = i
                elif e["type"] == "SESSION_EXTEND": last_ext = i
        return last_comp > last_ext

    # -------- PENALTIES & DEBT --------

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

    # -------- GAMIFICATION --------

    def get_user_stats(self):
        """Calculate XP and Level based on history"""
        xp = 0
        total_sessions = 0
        completed_sessions = 0
        
        events = self.get_events()
        
        # We need to track session status
        sessions = {}
        
        for e in events:
            # Safely get payload and session_id
            payload = e.get("payload", {})
            if not isinstance(payload, dict): continue
            
            sid = payload.get("session_id")
            if not sid and e["type"] == "SESSION_START":
                # Skip malformed start events
                continue

            if e["type"] == "SESSION_START":
                sessions[sid] = {
                    "duration": payload.get("expected_duration", 25), # Default to 25 if missing
                    "violations": 0,
                    "completed": False,
                    "broken": False
                }
                total_sessions += 1
                
            elif e["type"] == "FOCUS_VIOLATION":
                if sid and sid in sessions:
                    sessions[sid]["violations"] += 1
            
            elif e["type"] == "SESSION_COMPLETE":
                if sid and sid in sessions:
                    sessions[sid]["completed"] = True
                    completed_sessions += 1

            elif e["type"] == "SESSION_EXTEND":
                if sid and sid in sessions:
                    sessions[sid]["duration"] += payload.get("extension_minutes", 0)

            elif e["type"] == "SESSION_BROKEN":
                if sid and sid in sessions:
                    sessions[sid]["broken"] = True

        for sid, data in sessions.items():
            if data["completed"]:
                # 10 XP per minute
                xp += data["duration"] * 10 
                # Bonus for 0 violations
                if data["violations"] == 0:
                    xp += 100
            
            # Penalize violations
            xp -= (data["violations"] * 50)
            
            # Penalize broken sessions
            if data["broken"]:
                xp -= 100

        if xp < 0: xp = 0
        
        level = 1 + int(xp / 1000)
        
        return {
            "xp": xp,
            "level": level,
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions
        }

