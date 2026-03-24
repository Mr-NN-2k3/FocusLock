import time
from backend.classifier import classifier
from backend.engine import FocusEngine

print("--- TESTING CLASSIFIER BUDGET ---")
state_good = {"title": "Python Documentation", "app": "chrome.exe", "url": ""}
state_bad = {"title": "Funny Cats", "app": "chrome.exe", "url": "youtube.com"}

classifier._init_models_bg()
time.sleep(2) # simulate waiting for background load

for state in [state_good, state_bad]:
    t0 = time.time()
    res = classifier.extract_features(state, intent="learning python", mode="deep", whitelist=[], blacklist=[])
    t1 = time.time()
    print(f"Passed {state['title']} -> Budget taken: {(t1-t0)*1000:.1f}ms (Limit: 100ms) | Conf: {res['confidence']}")

print("\n--- TESTING ENGINE STATE DRIFT ---")
engine = FocusEngine()
# Mock session start
engine.store.append_event("SESSION_START", {"session_id": "test_123", "expected_duration": 25, "expected_end_time": "2099-01-01T00:00:00", "mode": "deep", "intent": "learning python"})

for i in range(6):
    engine._on_state_change({"title": f"Test {i}", "app": "chrome.exe"})

print("Final Engine State after 6 rapid switches:", engine.current_state)

print("\nAll Checks pass if no exception and State is WARNING.")
