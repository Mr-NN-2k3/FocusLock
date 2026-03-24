import os
import json
import logging
from datetime import datetime

# Define base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "backend", "data")
LOGS_DIR = os.path.join(DATA_DIR, "logs")

# Ensure directories exist
os.makedirs(LOGS_DIR, exist_ok=True)

class FocusLogger:
    def __init__(self):
        self.log_file = os.path.join(LOGS_DIR, f"activity_log_{datetime.now().strftime('%Y-%m-%d')}.jsonl")
        self.training_file = os.path.join(DATA_DIR, "training_data.csv")
        self.feedback_file = os.path.join(DATA_DIR, "feedback.json")
        
        self._init_files()

    def _init_files(self):
        # Create CSV header if it doesn't exist
        if not os.path.exists(self.training_file):
            with open(self.training_file, "w", encoding="utf-8") as f:
                f.write("timestamp,title,app,url,goal,mode,similarity,heuristic,confidence,label\n")
        
        # Create feedback json array
        if not os.path.exists(self.feedback_file):
            with open(self.feedback_file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def log_activity(self, timestamp, title, app, url, features, classification, reason):
        """
        Logs a structured event including features and the final classification decision.
        """
        entry = {
            "timestamp": timestamp,
            "title": title,
            "app": app,
            "url": url,
            "features": features,
            "classification": classification,
            "reason": reason
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_training_row(self, title, app, url, goal, mode, similarity, heuristic, confidence, label):
        """
        Appends a row to the training data CSV for future ML retrains.
        """
        timestamp = datetime.now().isoformat()
        row = f"{timestamp},\"{title}\",\"{app}\",\"{url}\",\"{goal}\",{mode},{max(0, similarity)},{heuristic},{confidence},{label}\n"
        with open(self.training_file, "a", encoding="utf-8") as f:
            f.write(row)

    def log_user_feedback(self, log_id, correct_label, comment=""):
        """
        Saves user corrections to the feedback file.
        """
        feedback = {
            "timestamp": datetime.now().isoformat(),
            "log_id": log_id,
            "correct_label": correct_label,
            "comment": comment
        }
        
        try:
            with open(self.feedback_file, "r+", encoding="utf-8") as f:
                data = json.load(f)
                data.append(feedback)
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
        except Exception:
            with open(self.feedback_file, "w", encoding="utf-8") as f:
                json.dump([feedback], f, indent=2)

# Global Instance
logger = FocusLogger()
