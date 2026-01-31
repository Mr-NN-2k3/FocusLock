import sqlite3
import json
import os
from datetime import datetime

DB_FILE = "focuslock.db"

class EventStore:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        # Event Log Table: The Source of Truth
        c.execute('''CREATE TABLE IF NOT EXISTS events
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      event_type TEXT NOT NULL,
                      timestamp TEXT NOT NULL,
                      payload TEXT)''') # Payload is JSON
        conn.commit()
        conn.close()

    def append_event(self, event_type, payload={}):
        """
        The ONLY way to change state.
        events: SESSION_START, SESSION_COMPLETE, SESSION_BREAK_ATTEMPT, SESSION_BROKEN
        """
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute("INSERT INTO events (event_type, timestamp, payload) VALUES (?, ?, ?)",
                  (event_type, timestamp, json.dumps(payload)))
        conn.commit()
        conn.close()
        return timestamp

    def get_events(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT event_type, timestamp, payload FROM events ORDER BY id ASC")
        rows = c.fetchall()
        conn.close()
        
        events = []
        for r in rows:
            events.append({
                "type": r[0],
                "timestamp": r[1],
                "payload": json.loads(r[2]) if r[2] else {}
            })
        return events

    # --- Projections (Deriving State from Events) ---

    def get_current_session(self):
        """Replays events to find the active session state."""
        events = self.get_events()
        current_session = None

        for e in events:
            if e['type'] == 'SESSION_START':
                current_session = e['payload']
                current_session['start_time'] = e['timestamp']
                current_session['status'] = 'active'
            
            elif e['type'] == 'SESSION_COMPLETE':
                if current_session: current_session = None
            
            elif e['type'] == 'SESSION_BROKEN':
                if current_session: current_session = None
                
        return current_session

    def get_history(self):
        """Derives clean history list from events."""
        events = self.get_events()
        history = []
        current_processing = None

        for e in events:
            if e['type'] == 'SESSION_START':
                current_processing = e['payload']
                current_processing['start_time'] = e['timestamp']
                current_processing['events'] = []
            
            elif current_processing:
                if e['type'] == 'SESSION_BREAK_ATTEMPT':
                    current_processing['events'].append("Break Attempted")
                
                elif e['type'] == 'SESSION_BROKEN':
                    current_processing['end_time'] = e['timestamp']
                    current_processing['status'] = 'broken'
                    current_processing['excuse'] = e['payload'].get('excuse')
                    history.append(current_processing)
                    current_processing = None
                
                elif e['type'] == 'SESSION_COMPLETE':
                    current_processing['end_time'] = e['timestamp']
                    current_processing['status'] = 'completed'
                    history.append(current_processing)
                    current_processing = None
        
        return history
