"""
FeatureClassifier — Cognitive Behaviour Engine (Feature Generator)
==================================================================
Extracts features and performs hybrid classification:
  Heuristic (personalized, intent-aware) → Embeddings (semantic) → ML model

Key upgrades over the original:
  • concept_weights are now per-intent, pulled live from UserProfile
  • Intent scoring replaced with IntentProfile.score_activity() — signals + strength
  • apply_session_feedback() supports real-time weight correction (auto + manual)
  • ml_error / ml_status exposed for health checks
  • 100 ms classification budget enforced as before
"""

import os
import time
import joblib
import numpy as np
import concurrent.futures
import threading

from .user_profile import user_profile
from .intent_engine import IntentProfile


class FeatureClassifier:

    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "focus_model.pkl")
        self.ml_ready   = False
        self.model      = None
        self.tfidf      = None
        self.embedder   = None
        self.util       = None

        self._init_models_bg()

    # ── Model Loading ─────────────────────────────────────────────────────────

    def _init_models_bg(self):
        """Load heavy models in a background thread so startup stays fast."""
        self.ml_error = None

        def load():
            # Sentence-Transformer
            try:
                from sentence_transformers import SentenceTransformer, util
                self.util     = util
                self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
                print("[Classifier] SentenceTransformer loaded successfully.")
            except Exception as e:
                self.ml_error = f"SentenceTransformer failed: {e}"
                print(f"[Classifier] WARNING: {self.ml_error} — heuristics only.")

            # Scikit-Learn model
            if os.path.exists(self.model_path):
                try:
                    artifacts  = joblib.load(self.model_path)
                    self.model = artifacts.get("model")
                    self.tfidf = artifacts.get("tfidf")
                    self.ml_ready = True
                    print("[Classifier] ML model loaded successfully.")
                except Exception as e:
                    err = f"ML artifact load failed: {e}"
                    self.ml_error = (
                        (self.ml_error + " | " + err) if self.ml_error else err
                    )
                    print(f"[Classifier] WARNING: {err}")
            else:
                msg = f"Model not found at {self.model_path}. Run train_model.py."
                self.ml_error = (
                    (self.ml_error + " | " + msg) if self.ml_error else msg
                )
                print(f"[Classifier] WARNING: {msg}")

        threading.Thread(target=load, daemon=True).start()

    def ml_status(self) -> dict:
        """Expose ML health state for /api/status and /api/profile."""
        return {
            "ml_ready":    self.ml_ready,
            "ml_error":    self.ml_error,
            "embedder_ok": self.embedder is not None,
        }

    # ── Feature Extraction ────────────────────────────────────────────────────

    def extract_features(
        self,
        state:          dict,
        intent:         str,
        mode:           str,
        whitelist:      list,
        blacklist:      list,
        intent_profile: "IntentProfile | None" = None,
    ) -> dict:
        """
        Input:  state = {"title": "...", "app": "...", "url": "..."}
        Output: feature dictionary consumed by the engine's decision layer.

        Pipeline (< 100 ms budget):
          1. Whitelist / Blacklist overrides   (O(n) string scan)
          2. Personalized heuristic pass        (UserProfile.get_all_weights)
          3. Intent-aware scoring               (IntentProfile.score_activity)
          4. Semantic embeddings fallback       (capped at budget remainder)
          5. Confidence calibration
        """
        start_time = time.time()

        title  = (state.get("title") or "").lower()
        app    = (state.get("app")   or "").lower()
        url    = (state.get("url")   or "").lower()
        intent = (intent or "").lower()

        intent_key = intent_profile.intent_key if intent_profile else "global"
        full_text  = f"{title} {app} {url}"

        # ── 1. Strict Overrides ───────────────────────────────────────────────
        is_whitelist = any(w.lower() in full_text for w in (whitelist or []))
        is_blacklist = any(b.lower() in full_text for b in (blacklist or []))

        # ── 2. Personalized Heuristic Pass ────────────────────────────────────
        # Pull merged weights (base defaults + user-learned deltas) for this intent
        concept_weights = user_profile.get_all_weights(intent_key)

        heuristic_score  = 0
        matched_concepts = []

        for concept, weight in concept_weights.items():
            if concept in full_text:
                heuristic_score += weight
                matched_concepts.append(concept)

        # ── 3. Intent-Aware Scoring ───────────────────────────────────────────
        intent_boost      = 0
        negative_override = False
        intent_reason     = "No intent profile"
        intent_match      = False

        if intent_profile and intent_profile.strength > 0:
            result            = intent_profile.score_activity(full_text)
            intent_boost      = result["intent_boost"]
            negative_override = result["negative_override"]
            intent_reason     = result["intent_reason"]
            intent_match      = intent_boost != 0

            heuristic_score  += intent_boost

        else:
            # Legacy flat keyword boost (fallback when no IntentProfile supplied)
            intent_words = [w for w in intent.split() if len(w) > 3]
            for word in intent_words:
                if word in full_text:
                    heuristic_score += 20
                    intent_match     = True
            intent_reason = "Legacy intent keyword boost"

        # ── 4. Semantic Embeddings Fallback ───────────────────────────────────
        semantic_similarity = 0.0
        ml_prob             = 0.0

        if self.embedder is not None and self.util is not None:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._run_ml_pipeline, intent, full_text)
                elapsed_ms  = (time.time() - start_time) * 1000
                budget_left = max(0.0, 100.0 - elapsed_ms) / 1000.0
                try:
                    semantic_similarity, ml_prob = future.result(timeout=budget_left)
                except concurrent.futures.TimeoutError:
                    print("[Classifier] WARN: Budget exceeded — heuristics only.")

        # ── 5. Confidence Calibration ─────────────────────────────────────────
        if is_whitelist or is_blacklist or negative_override:
            confidence = 100.0
        else:
            confidence = 50.0  # neutral baseline

            heur_sign = 1 if heuristic_score > 0 else (-1 if heuristic_score < 0 else 0)
            sem_sign  = (
                1  if semantic_similarity > 0.4
                else (-1 if semantic_similarity < 0.2 else 0)
            )

            if heur_sign == sem_sign and heur_sign != 0:
                confidence = min(95.0, confidence + 30 + abs(heuristic_score))
            elif heur_sign != 0:
                confidence = min(85.0, confidence + abs(heuristic_score))

            if intent_match:
                confidence = min(95.0, confidence + 20)

            # Intent profile strength amplifies confidence further (more specific = more sure)
            if intent_profile and intent_profile.strength > 0.5:
                confidence = min(98.0, confidence + 10 * intent_profile.strength)

        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "semantic_similarity": round(float(semantic_similarity), 3),
            "heuristic_score":     heuristic_score,
            "ml_probability":      round(float(ml_prob), 3),
            "intent_match":        intent_match,
            "intent_boost":        intent_boost,
            "intent_reason":       intent_reason,
            "negative_override":   negative_override,
            "whitelist_match":     is_whitelist,
            "blacklist_match":     is_blacklist,
            "matched_concepts":    matched_concepts,
            "confidence":          round(float(confidence), 1),
            "mode":                mode,
            "intent_key":          intent_key,
            "latency_ms":          latency_ms,
        }

    # ── Real-time Feedback (Layer 1 + Layer 2) ────────────────────────────────

    def apply_session_feedback(
        self,
        app:           str,
        title:         str,
        correct_label: str,   # "PRODUCTIVE" | "WARNING" | "DISTRACTION"
        intent_key:    str  = "global",
        manual:        bool = False,
    ):
        """
        Apply a real-time learning signal to the user profile.

        Layer 1 (auto):   called by engine on violation or session-end.
        Layer 2 (manual): called by engine on user thumbs-up/down feedback.

        The concept learned is the app process name (normalised) so that
        future classifications of the same app in the same intent context
        get a personalized score immediately — no retraining required.
        """
        concept   = (app or title or "").lower().strip().split(".")[0]  # strip .exe etc.
        direction = "negative" if correct_label == "DISTRACTION" else "positive"

        if concept:
            user_profile.apply_feedback(
                concept    = concept,
                direction  = direction,
                intent_key = intent_key,
                manual     = manual,
            )
            action = "Manual" if manual else "Auto"
            print(
                f"[Classifier] {action} feedback → '{concept}' "
                f"({direction}) in intent '{intent_key}'"
            )

    # ── ML Pipeline (budget-capped) ───────────────────────────────────────────

    def _run_ml_pipeline(self, intent: str, text: str):
        """Runs SentenceTransformer + Scikit-Learn inside the 100 ms budget."""
        sim  = 0.0
        prob = 0.0

        try:
            g_emb = self.embedder.encode(intent, convert_to_tensor=True)
            t_emb = self.embedder.encode(text,   convert_to_tensor=True)
            sim   = max(0.0, self.util.cos_sim(g_emb, t_emb).item())
        except Exception:
            pass

        if self.ml_ready and self.model and self.tfidf:
            try:
                tfidf_vec = self.tfidf.transform([text]).toarray()
                features  = np.hstack(([[sim, 2]], tfidf_vec))
                probs     = self.model.predict_proba(features)[0]
                prob      = float(np.max(probs))
            except Exception:
                pass

        return sim, prob


# Global singleton
classifier = FeatureClassifier()
