"""
UserProfile — Per-Intent Personalization Layer
===============================================
Manages per-user, per-intent weight deltas that are layered on top of
the global DEFAULT_PROFILES base weights.

Learning happens in two layers:
  Layer 1 (Automatic): session completions reward productive apps,
                        violations penalize distraction apps, drift penalizes switches.
  Layer 2 (Manual):    user thumbs-up/down corrections apply a larger, immediate delta.

Profile JSON structure (backend/data/user_profile.json):
{
  "global":  { "concept": delta },   ← cross-intent corrections
  "coding":  { "concept": delta },   ← learned only during coding sessions
  "design":  { "concept": delta },
  "writing": { "concept": delta },
  "learning":{ "concept": delta },
  "research":{ "concept": delta },
  "_meta":   { "total_sessions": N, "intent_aliases": {...}, "last_updated": "..." }
}
Values are DELTAS — effective_weight = DEFAULT_PROFILES[intent][concept] + delta.
"""

import os
import json
import threading
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_FILE = os.path.join(BASE_DIR, "data", "user_profile.json")

# ── Pre-seeded base weights per intent domain ─────────────────────────────────
# These are the starting point for each user. Weight deltas learned over time
# are stored separately and merged at runtime.
DEFAULT_PROFILES = {
    "global": {
        "python": 10, "javascript": 10, "c++": 10, "java": 10, "rust": 10,
        "code": 15, "github": 15, "vs code": 20, "pycharm": 20,
        "debug": 20, "docs": 15, "stackoverflow": 20,
        "aws": 10, "azure": 10, "cloud": 10,
        "youtube": -10, "netflix": -30, "twitch": -25, "video": -10,
        "movie": -20, "twitter": -20, "facebook": -20, "instagram": -25,
        "tiktok": -40, "reddit": -15, "game": -30, "steam": -30,
        "discord": 0,  # neutral — can be work or play
        "shopping": -20, "amazon": -15, "news": -10,
    },
    "coding": {
        "pycharm": 25, "vs code": 25, "vscode": 25, "github": 20,
        "stackoverflow": 25, "terminal": 20, "docker": 15,
        "python": 15, "javascript": 15, "c++": 15, "java": 15, "rust": 15,
        "debug": 25, "git": 20, "code": 20, "intellij": 20, "jupyter": 15,
        "postman": 15, "insomnia": 15,
        "youtube": -20, "reddit": -20, "twitter": -25,
        "instagram": -30, "tiktok": -45, "netflix": -35,
        "steam": -35, "game": -35, "discord": -5,
    },
    "design": {
        "figma": 30, "photoshop": 25, "illustrator": 25, "canva": 20,
        "sketch": 25, "dribbble": 15, "behance": 15, "xd": 20,
        "affinity": 20, "zeplin": 20, "framer": 20,
        "color": 10, "font": 10, "icon": 10, "ui": 15, "ux": 15,
        # Instagram can be design inspiration — softer penalty
        "instagram": -10, "pinterest": 10,
        "youtube": -15, "reddit": -20, "twitter": -20,
        "tiktok": -40, "netflix": -30, "steam": -35, "game": -35, "discord": -5,
    },
    "writing": {
        "docs": 30, "notion": 25, "word": 25, "grammarly": 20,
        "obsidian": 20, "typora": 20, "medium": 15,
        "google docs": 30, "hemingway": 20, "scrivener": 20,
        # Reddit can be light research for writing
        "reddit": -10,
        "youtube": -25, "twitter": -20, "instagram": -30,
        "tiktok": -45, "netflix": -35, "steam": -35, "game": -35, "discord": -10,
    },
    "learning": {
        # YouTube is POSITIVE for learning — intentional override
        "youtube": 15, "udemy": 30, "coursera": 30,
        "github": 20, "stackoverflow": 25, "docs": 25, "medium": 15,
        "khan academy": 30, "wikipedia": 10, "edx": 30, "pluralsight": 25,
        "reddit": 5,   # slightly positive — r/learnprogramming etc.
        "twitter": -20, "instagram": -30, "tiktok": -45,
        "netflix": -35, "steam": -35, "game": -35, "discord": -5,
    },
    "research": {
        "google": 10, "wikipedia": 15, "scholar": 25, "docs": 20,
        "notion": 20, "medium": 15, "github": 15, "reddit": 10,
        "stackoverflow": 15,
        "twitter": -15, "instagram": -30, "tiktok": -45,
        "netflix": -35, "steam": -35, "game": -35,
    },
}


class UserProfile:
    """
    Per-intent weight profiles with global fallback.

    Layer 1 — Automatic learning (zero friction):
      • Session completed  → reward productive apps (+LEARNING_RATE_AUTO)
      • Violation fired    → penalize the offending app (-LEARNING_RATE_AUTO)
      • Session broken     → double-penalize all violated apps

    Layer 2 — Manual correction (optional, high accuracy):
      • User sends thumbs-up/down via /api/feedback
      • Applies LEARNING_RATE_MANUAL (larger step, faster convergence)
    """

    LEARNING_RATE_AUTO   = 3    # small, continuous nudges
    LEARNING_RATE_MANUAL = 8    # user corrections — bigger, immediate signal
    MAX_DELTA            = 40   # cap so deltas can't completely override base weights

    def __init__(self):
        self._lock   = threading.Lock()
        self._deltas = {}       # { intent_key: { concept: delta } }
        self._meta   = {
            "total_sessions": 0,
            "intent_aliases": {},
            "last_updated":   None,
        }
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
        if os.path.exists(PROFILE_FILE):
            try:
                with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._meta   = data.pop("_meta", self._meta)
                self._deltas = data
                print(f"[UserProfile] Loaded — {len(self._deltas)} intent bucket(s)")
            except Exception as e:
                print(f"[UserProfile] Load failed, starting fresh: {e}")
        else:
            print("[UserProfile] No profile found — starting fresh.")

    def _save(self):
        """Persist deltas to disk. Must be called while holding self._lock."""
        try:
            data = dict(self._deltas)
            data["_meta"] = dict(self._meta)
            data["_meta"]["last_updated"] = datetime.now().isoformat()
            with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[UserProfile] Save failed: {e}")

    # ── Weight lookup ─────────────────────────────────────────────────────────

    def get_weight(self, concept: str, intent_key: str = "global") -> int:
        """
        Effective weight = base_default(intent) + user_delta(global) + user_delta(intent).
        Falls back: intent-specific default → global default → 0.
        """
        concept    = concept.lower()
        intent_key = self._resolve_intent_key(intent_key)

        base = (
            DEFAULT_PROFILES.get(intent_key, {}).get(concept)
            or DEFAULT_PROFILES["global"].get(concept, 0)
        )

        with self._lock:
            g_delta = self._deltas.get("global",     {}).get(concept, 0)
            i_delta = self._deltas.get(intent_key,   {}).get(concept, 0)

        return base + g_delta + i_delta

    def get_all_weights(self, intent_key: str = "global") -> dict:
        """
        Return a fully merged weight map for classification.
        global_defaults → intent_defaults → global_deltas → intent_deltas.
        """
        intent_key = self._resolve_intent_key(intent_key)

        merged = dict(DEFAULT_PROFILES.get("global", {}))
        merged.update(DEFAULT_PROFILES.get(intent_key, {}))

        with self._lock:
            for concept, delta in self._deltas.get("global", {}).items():
                merged[concept] = merged.get(concept, 0) + delta
            for concept, delta in self._deltas.get(intent_key, {}).items():
                merged[concept] = merged.get(concept, 0) + delta

        return merged

    # ── Learning ──────────────────────────────────────────────────────────────

    def apply_feedback(
        self,
        concept:    str,
        direction:  str,           # "positive" | "negative"
        intent_key: str  = "global",
        manual:     bool = False,  # True → Layer 2 (user correction)
    ):
        """
        Apply a learning signal to a concept within an intent bucket.
        Automatically persists to disk after every update.
        """
        concept    = concept.lower().strip()
        intent_key = self._resolve_intent_key(intent_key)
        rate       = self.LEARNING_RATE_MANUAL if manual else self.LEARNING_RATE_AUTO
        delta      = rate if direction == "positive" else -rate

        with self._lock:
            bucket = self._deltas.setdefault(intent_key, {})
            current = bucket.get(concept, 0)
            bucket[concept] = max(-self.MAX_DELTA, min(self.MAX_DELTA, current + delta))
            self._save()

    def record_session_outcome(
        self,
        intent_key:      str,
        productive_apps: list,
        violated_apps:   list,
        completed:       bool,
    ):
        """
        Layer 1 automatic learning — called by engine after session ends.
        Completed:      reward productive apps, lightly penalize violated apps.
        Broken/stopped: double-penalize violated apps (stronger signal).
        """
        intent_key = self._resolve_intent_key(intent_key)

        if completed:
            for app in productive_apps:
                self.apply_feedback(app, "positive", intent_key, manual=False)
            for app in violated_apps:
                self.apply_feedback(app, "negative", intent_key, manual=False)
        else:
            # Session broken — violated apps get a stronger negative signal
            for app in violated_apps:
                self.apply_feedback(app, "negative", intent_key, manual=False)
                self.apply_feedback(app, "negative", intent_key, manual=False)

        with self._lock:
            self._meta["total_sessions"] = self._meta.get("total_sessions", 0) + 1
            self._save()

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _resolve_intent_key(self, intent_key: str) -> str:
        """Normalise intent key. Falls back to 'global' if unrecognised."""
        if not intent_key:
            return "global"
        key = intent_key.lower().strip()
        aliases = self._meta.get("intent_aliases", {})
        if key in aliases:
            return aliases[key]
        known = set(DEFAULT_PROFILES.keys()) | set(self._deltas.keys())
        return key if key in known else "global"

    def get_summary(self) -> dict:
        """Serialisable summary for the /api/profile endpoint."""
        with self._lock:
            return {
                "meta":           dict(self._meta),
                "intent_buckets": sorted(
                    set(DEFAULT_PROFILES.keys()) | set(self._deltas.keys())
                ),
                "user_deltas":    {k: dict(v) for k, v in self._deltas.items()
                                   if k != "_meta"},
            }


# Global singleton — shared by classifier and engine
user_profile = UserProfile()
