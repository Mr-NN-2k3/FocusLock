
import ctypes
import threading
import time
import re
import os
import joblib
import numpy as np
from sentence_transformers import SentenceTransformer, util

# -------- INTENT ALIGNMENT ENGINE (ML-POWERED) --------

class IntentAlignmentEngine:
    def __init__(self, user_intent, whitelist=None, blacklist=None, mode="deep"):
        self.user_intent = user_intent.lower() if user_intent else "general work and productivity"
        self.whitelist = whitelist or []
        self.blacklist = blacklist or []
        self.mode = mode
        
        # Load ML Artifacts
        self.model_path = os.path.join(os.path.dirname(__file__), "focus_model.pkl")
        self.ml_ready = False
        self.model = None
        self.tfidf = None
        self.embedder = None
        
        try:
            if os.path.exists(self.model_path):
                print(f"Loading ML Model from {self.model_path}...")
                artifacts = joblib.load(self.model_path)
                self.model = artifacts["model"]
                self.tfidf = artifacts["tfidf"]
                # SBERT is loaded separately as it's not pickled
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                self.ml_ready = True
                print("ANTI-GRAVITY V2 ENGINE: ML Model Loaded Successfully")
            else:
                print("ANTI-GRAVITY V2 ENGINE: Model not found, using heuristics only.")
        except Exception as e:
            print(f"Failed to load ML model: {e}")
            self.ml_ready = False

        # Fallback Heuristics (SHE)
        self.concept_weights = {
            "python": 25, "javascript": 25, "typescript": 25, "c++": 25, "java": 25, "rust": 25,
            "go": 25, "html": 15, "css": 15, "sql": 20, "db": 15, "json": 10, "xml": 10,
            "code": 20, "coding": 20, "frontend": 20, "backend": 20, "fullstack": 20,
            "git": 15, "github": 15, "gitlab": 15, "merge": 10, "pull request": 15, "repo": 15,
            "vs code": 30, "visual studio": 30, "pycharm": 30, "intellij": 30, "sublime": 20, "atom": 20,
            "terminal": 15, "powershell": 15, "cmd": 15, "bash": 15, "zsh": 15, "debug": 25,
            "documentation": 25, "docs": 20, "api": 15, "reference": 15, "manual": 15,
            "tutorial": 15, "course": 20, "lecture": 20, "learn": 15, "study": 15, "university": 20,
            "leetcode": 30, "hackerrank": 30, "interview": 30, "glassdoor": 20, "system design": 25, "algorithm": 20,
            "stackoverflow": 30, "stack exchange": 25, "geeksforgeeks": 15, "medium": 5,
            "pdf": 10, "article": 5, "paper": 15, "arxiv": 20, "journal": 15, "research": 20,
            "writing": 15, "reading": 15, "book": 15, "deep work": 30,
            "chatgpt": 20, "claude": 20, "gemini": 20, "bard": 10, "openai": 15, "llm": 20, "ai": 15,
            "jira": 25, "trello": 20, "asana": 20, "notion": 20, "linear": 25,
            "slack": 10, "teams": 10, "discord": -5,
            "outlook": 15, "mail": 5, "calendar": 10, "meeting": 10, "zoom": 5,
            "word": 10, "excel": 15, "powerpoint": 10, "spreadsheet": 15,
            "youtube": -40, "netflix": -80, "twitch": -60, "hulu": -80, "disney+": -80, "prime video": -60, "video": -30,
            "watch": -20, "movie": -50, "tv show": -50, "series": -50, "episode": -40, "streaming": -40,
            "facebook": -60, "twitter": -50, "x": -40, "instagram": -70, "tiktok": -90, "reddit": -45, "social": -40,
            "pinterest": -40, "linkedin": 10,
            "whatsapp": -50, "telegram": -40, "messenger": -50, "chat": -20, "messaging": -20,
            "steam": -70, "game": -60, "playing": -60, "play": -30, "gamer": -50, "roblox": -60, "xbox": -60, "epic games": -60,
            "amazon": -50, "ebay": -50, "walmart": -50, "shopping": -40, "buy": -30, "store": -20,
            "news": -30, "cnn": -40, "bbc": -40, "fox news": -40, "buzzfeed": -50,
            "comedy": -50, "standup": -50, "stand-up": -50, "joke": -40, "entertainment": -40
        }

    def evaluate(self, activity_title):
        """
        Returns: (classification, score, reason)
        """
        title = activity_title.lower()
        
        # 0. System Authority (Always Productive)
        if "focuslock" in title:
            return "PRODUCTIVE", 0, "System Authority"

        # 1. Strict Whitelist (Highest Priority)
        if self.whitelist:
            for w in self.whitelist:
                if w.lower() in title:
                    return "PRODUCTIVE", 0, "User Whitelist"
            return "DISTRACTION", 100, "Not in Whitelist (Strict Mode)"

        # 2. Blacklist (Absolute Block)
        for b in self.blacklist:
            if b.lower() in title:
                return "DISTRACTION", 100, f"User Blacklist: {b}"

        # 3. ML PREDICTION (Anti-Gravity v2)
        if self.ml_ready:
            try:
                # Prepare Features
                # A. Embedding Similarity
                g_emb = self.embedder.encode(self.user_intent, convert_to_tensor=True)
                t_emb = self.embedder.encode(activity_title, convert_to_tensor=True) # use original casing for bert
                
                # Cosine Similarity
                similarity = util.cos_sim(g_emb, t_emb).item()

                # B. Mode Encoding
                mode_val = 2 if self.mode == "deep" else 1

                # C. TF-IDF
                tfidf_vec = self.tfidf.transform([activity_title]).toarray()

                # Assemble Vector
                # [similarity, mode, ...tfidf...]
                features = np.hstack(([[similarity, mode_val]], tfidf_vec))
                
                # Predict
                prediction = self.model.predict(features)[0]
                probs = self.model.predict_proba(features)[0]
                classes = self.model.classes_

                confidence = np.max(probs) * 100
                
                # If high confidence (>60%), trust the ML
                if confidence > 60:
                     score = 0
                     if prediction == "DISTRACTION":
                         score = int(confidence)
                         return "DISTRACTION", score, f"AI Predicted Distraction ({int(confidence)}%)"
                     elif prediction == "PRODUCTIVE":
                         score = 100 - int(confidence)
                         return "PRODUCTIVE", max(0, score), f"AI Predicted Productive ({int(confidence)}%)"
                     else:
                         return "NEUTRAL", 50, f"AI Predicted Neutral ({int(confidence)}%)"

            except Exception as e:
                print(f"ML Inference Error: {e}")
                # Fallthrough to Heuristics

        # 4. Fallback: Semantic Heuristic Engine (SHE)
        return self._heuristic_evaluate(title)

    def _heuristic_evaluate(self, title):
        semantic_score = 0
        reasons = []
        
        intent_words = [w for w in self.user_intent.split() if len(w) > 3]
        for word in intent_words:
            if word in title:
                semantic_score += 40
                reasons.append(f"Intent Match ({word})")

        found_concepts = []
        for concept, weight in self.concept_weights.items():
            if concept in title:
                final_weight = weight
                if weight > 0 and any(i in concept for i in intent_words):
                    final_weight *= 2
                semantic_score += final_weight
                found_concepts.append(f"{concept}({final_weight})")

        if not found_concepts and len(title) > 0:
            if self.mode == "deep":
                semantic_score -= 10
                reasons.append("Unknown Context")
            else:
                semantic_score += 5
        
        distraction_prob = 50 - (semantic_score / 1.5)
        distraction_prob = max(0, min(100, distraction_prob))
        
        reason_str = ", ".join(reasons + found_concepts)
        if not reason_str: reason_str = "Neutral Activity"

        if distraction_prob > 60:
            return "DISTRACTION", int(distraction_prob), f"High Distraction Score: {reason_str}"
        elif distraction_prob < 40:
            return "PRODUCTIVE", int(distraction_prob), f"High Focus Score: {reason_str}"
        else:
            return "NEUTRAL", int(distraction_prob), f"Ambiguous Activity: {reason_str}"


class WindowMonitor:
    def __init__(self, intent=None, whitelist=None, blacklist=None, mode="deep", callback_violation=None, callback_safe=None):
        self.engine = IntentAlignmentEngine(intent, whitelist, blacklist, mode)
        self.callback_violation = callback_violation
        self.callback_safe = callback_safe
        self.running = False
        self.thread = None
        self.last_title = ""
        self.is_distracted = False
        
        # Load user32.dll for Windows API
        self.user32 = ctypes.windll.user32

    def _get_active_window_title(self):
        try:
            hwnd = self.user32.GetForegroundWindow()
            length = self.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        except:
            return ""

    def _show_popup(self, title, reason):
        # We disabled the native Windows alert popup because we are using the new Lightbox Modal System UI
        pass

    def _monitor_loop(self):
        while self.running:
            title = self._get_active_window_title()
            
            if not title or title in ["Task Switching", "Task View", "Program Manager"]: 
                time.sleep(1)
                continue
            
            # Use Intent Engine
            classification, score, reason = self.engine.evaluate(title)
            
            # Threshold: > 60 is Distraction
            is_currently_distracted = score > 60

            if is_currently_distracted:
                if not self.is_distracted:
                    self.is_distracted = True
                    self._show_popup(title, reason)
                    
                    if self.callback_violation:
                        self.callback_violation(f"{reason}: {title}")
            else:
                if self.is_distracted:
                    self.is_distracted = False
                    if self.callback_safe:
                        self.callback_safe()

            time.sleep(1)

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
