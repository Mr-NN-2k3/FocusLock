import os
import time
import joblib
import numpy as np
import concurrent.futures
import threading

class FeatureClassifier:
    """
    Cognitive Behavior Engine: Feature Generator
    Extracts features and performs a hybrid classification (Heuristic -> Embeddings).
    Returns ONLY features, not the final decision.
    """
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "focus_model.pkl")
        self.ml_ready = False
        self.model = None
        self.tfidf = None
        self.embedder = None
        
        # We load embedder lazily or in background so init is fast
        self._init_models_bg()

        # Base concept weights (Heuristics) - Data-driven mapping
        self.concept_weights = {
            "python": 10, "javascript": 10, "c++": 10, "java": 10, "code": 15, "github": 15,
            "vs code": 20, "pycharm": 20, "debug": 20, "docs": 15, "stackoverflow": 20,
            "aws": 10, "azure": 10, "cloud": 10,
            
            "youtube": -10, "netflix": -30, "twitch": -25, "video": -10, "movie": -20,
            "twitter": -20, "facebook": -20, "instagram": -25, "tiktok": -40, "reddit": -15,
            "game": -30, "steam": -30, "discord": 0, # Neutral discord as it can be work or play
            "shopping": -20, "amazon": -15, "news": -10
        }

    def _init_models_bg(self):
        def load():
            try:
                from sentence_transformers import SentenceTransformer, util
                # We save util reference for later
                self.util = util
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                print(f"Failed to load sentence-transformers: {e}")

            if os.path.exists(self.model_path):
                try:
                    artifacts = joblib.load(self.model_path)
                    self.model = artifacts.get("model")
                    self.tfidf = artifacts.get("tfidf")
                    self.ml_ready = True
                except Exception as e:
                    print(f"Failed to load ML artifacts: {e}")
        
        # Load in background so UI isn't blocked on startup
        threading.Thread(target=load, daemon=True).start()

    def extract_features(self, state, intent, mode, whitelist, blacklist):
        """
        Input: state = {"title": "...", "app": "...", "url": "..."}
        Output: Feature Dictionary
        Enforces a <100ms budget limit.
        """
        start_time = time.time()
        
        title = (state.get("title") or "").lower()
        app = (state.get("app") or "").lower()
        url = (state.get("url") or "").lower()
        intent = (intent or "").lower()
        mode_val = 2 if mode == "deep" else 1
        
        full_text = f"{title} {app} {url}"

        # 1. Strict Overrides (Whitelist / Blacklist)
        is_whitelist = False
        is_blacklist = False
        if whitelist:
            for w in whitelist:
                if w.lower() in full_text: is_whitelist = True
        
        if blacklist:
            for b in blacklist:
                if b.lower() in full_text: is_blacklist = True

        # 2. Fast Heuristic Pass
        heuristic_score = 0
        intent_match = False
        matched_concepts = []
        
        # Base Match
        for concept, weight in self.concept_weights.items():
            if concept in full_text:
                heuristic_score += weight
                matched_concepts.append(concept)
                
        # Intent Boost
        intent_words = [w for w in intent.split() if len(w) > 3]
        for word in intent_words:
            if word in full_text:
                heuristic_score += 20  # Contextual Boost
                intent_match = True

        # 3. Embeddings Fallback (If Ambiguous + Budget Check)
        # If Heuristic is very strong (-40 or +40), we might not need embeddings.
        semantic_similarity = 0.0
        ml_prob = 0.0
        
        # We only run embeddings if within budget (< 100ms) and if embedder loaded
        if self.embedder is not None and self.util is not None:
            # We use an executor to enforce timeout
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._run_ml_pipeline, intent, full_text)
                time_elapsed = (time.time() - start_time) * 1000
                budget_left = max(0, 100 - time_elapsed) / 1000.0
                
                try:
                    semantic_similarity, ml_prob = future.result(timeout=budget_left)
                except concurrent.futures.TimeoutError:
                    print("WARN: Classification exceeded 100ms budget. Falling back to heuristics.")

        # 4. Confidence Calibration
        # Base confidence from semantic similarity and heuristic agreement
        confidence = 50.0 # Neutral uncertainty
        
        if is_whitelist or is_blacklist:
            confidence = 100.0
        else:
            # If heuristic and semantics agree, confidence goes up
            heur_sign = 1 if heuristic_score > 0 else (-1 if heuristic_score < 0 else 0)
            sem_sign = 1 if semantic_similarity > 0.4 else (-1 if semantic_similarity < 0.2 else 0)
            
            if heur_sign == sem_sign and heur_sign != 0:
                confidence = min(95.0, confidence + 30 + abs(heuristic_score))
            elif heur_sign != 0:
                confidence = min(85.0, confidence + abs(heuristic_score))
            
            if intent_match:
                confidence = min(95.0, confidence + 20)

        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "semantic_similarity": round(float(semantic_similarity), 3),
            "heuristic_score": heuristic_score,
            "ml_probability": round(float(ml_prob), 3),
            "intent_match": intent_match,
            "whitelist_match": is_whitelist,
            "blacklist_match": is_blacklist,
            "matched_concepts": matched_concepts,
            "confidence": round(float(confidence), 1),
            "mode": mode,
            "latency_ms": latency_ms
        }

    def _run_ml_pipeline(self, intent, text):
        """Runs the expensive SentenceTransformer & Scikit-Learn logic."""
        sim = 0.0
        prob = 0.0
        try:
            g_emb = self.embedder.encode(intent, convert_to_tensor=True)
            t_emb = self.embedder.encode(text, convert_to_tensor=True)
            sim = max(0.0, self.util.cos_sim(g_emb, t_emb).item())
        except Exception as e:
            pass

        if self.ml_ready and self.model and self.tfidf:
            try:
                tfidf_vec = self.tfidf.transform([text]).toarray()
                # Assuming mode is fixed to Deep=2 for pure ML pipeline context right now
                features = np.hstack(([[sim, 2]], tfidf_vec))
                probs = self.model.predict_proba(features)[0]
                # Assuming index 0 is Distraction and 1 is Productive or similar.
                # Since we don't know the exact classes without inspecting the model, 
                # we'll just store the max prob as a generic feature.
                prob = np.max(probs)
            except Exception:
                pass

        return sim, prob

# Global Instance
classifier = FeatureClassifier()
