/* =========================================================
   FocusLock Client Controller
   Role: UI + Signal Reporter
   Authority: SERVER ONLY
   ========================================================= */

// -------- UI TOGGLE --------
function toggleDeepSettings() {
    const mode = document.getElementById("mode").value;
    const settings = document.getElementById("deep-settings");
    if (settings) {
        settings.style.display = mode === "deep" ? "block" : "none";
    }
}

// -------- SESSION START --------
function startSession() {
    const durationInput = document.getElementById("duration");
    const modeInput = document.getElementById("mode");
    const keywordsInput = document.getElementById("allowed-keywords");

    if (!durationInput || !modeInput) return;

    const duration = durationInput.value;
    const mode = modeInput.value;
    const allowed_keywords = keywordsInput ? keywordsInput.value : "";

    // Basic client validation (not authority)
    if (duration < 1) {
        alert("Invalid session duration.");
        return;
    }

    // Requests Fullscreen (Must be user initiated)
    if (mode === "deep") {
        document.documentElement.requestFullscreen().catch((e) => {
            console.log("Fullscreen denied", e);
        });
    }

    // Disable button to prevent double-start
    const btn = document.querySelector(".btn-primary");
    if (btn) {
        btn.disabled = true;
        btn.innerText = "SYSTEM INITIALIZING...";
    }

    fetch("/api/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ duration, mode, allowed_keywords })
    })
        .then(res => {
            if (!res.ok) throw new Error("Start failed");
            return res.json();
        })
        .then(() => {
            // Hard navigation (prevents reload race condition)
            window.location.href = "/";
        })
        .catch(err => {
            console.error(err);
            alert("System error. Check server.");
            if (btn) {
                btn.disabled = false;
                btn.innerText = "Initialize Lock";
            }
        });
}

// -------- SESSION BREAK --------
function breakSession() {
    window.location.href = "/excuse";
}

// -------- EXCUSE SUBMISSION --------
function submitExcuse() {
    const input = document.getElementById("excuse");
    if (!input) return;

    const excuse = input.value.trim();
    if (excuse.length < 5) {
        alert("Excuse must be explicit.");
        return;
    }

    fetch("/api/break", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ excuse })
    })
        .then(() => {
            window.location.href = "/";
        })
        .catch(() => {
            alert("Failed to submit excuse.");
        });
}

// -------- ACTIVITY CHECK (SMART AI) --------
let hiddenStart = 0;

document.addEventListener("visibilitychange", () => {
    // Only monitor visibility if we are in an active session
    if (!window.initialStatus) return;

    if (document.hidden) {
        hiddenStart = Date.now();
    } else {
        if (hiddenStart === 0) return;
        
        const duration = (Date.now() - hiddenStart) / 1000;
        hiddenStart = 0;

        if (duration < 5) return; // Ignore brief flicks

        // Demand explanation
        const reason = prompt(
            "⚠️ EXTERNAL ACTIVITY DETECTED ⚠️\n\n" +
            "You were away for " + Math.floor(duration) + " seconds.\n" +
            "State your purpose to the system:"
        );

        if (!reason || reason.trim() === "") {
            // No answer = Admission of Guilt
            fetch("/api/violation", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ type: "SILENT_DISTRACTION" })
            });
        } else {
            // AI JUDGEMENT
            fetch("/api/evaluate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ reason })
            })
            .then(r => r.json())
            .then(data => {
                if (data.classification === "distraction") {
                    alert("❌ SYSTEM RULING: DISTRACTION.\nPenalty Applied.");
                } else {
                    console.log("System ruling: Productive Context Switch");
                }
            });
        }
    }
});

// -------- HEARTBEAT (ANTI-TAMPER) --------
setInterval(() => {
    if (!window.initialStatus) return;
    
    fetch("/api/heartbeat", { method: "POST" })
        .catch(() => {}); // silent
}, 5000);

// -------- SERVER-AUTH TIMER + PREDICTION --------
if (window.initialStatus && document.getElementById("timer-display")) {
    const display = document.getElementById("timer-display");
    let lastPredictionHash = "";
    
    // AFK STATE
    let afkTimer = null;
    let isAfk = false;
    const AFK_LIMIT = 30 * 60 * 1000; // 30 mins

    function resetAfk() {
        if (isAfk) {
            // Resume
            isAfk = false;
            fetch('/api/afk', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status: false})
            });
            document.body.style.opacity = "1";
        }
        clearTimeout(afkTimer);
        afkTimer = setTimeout(goAfk, AFK_LIMIT);
    }
    
    function goAfk() {
        isAfk = true;
        fetch('/api/afk', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({status: true})
        });
        
        // Display Overlay
        document.body.innerHTML = `
            <div style="position:fixed; top:0; left:0; width:100%; height:100%; background:black; color:red; display:flex; justify-content:center; align-items:center; font-size:5rem; font-weight:bold; z-index:9999;">
                GET FOCUS
            </div>
        `;
    }

    // Monitor Activity
    document.addEventListener('mousemove', resetAfk);
    document.addEventListener('keydown', resetAfk);
    resetAfk();

    setInterval(() => {
        fetch("/api/status")
            .then(res => res.json())
            .then(data => {
                if (!data.active && !data.completed) {
                    window.location.href = "/";
                    return;
                }
                
                if (data.completed) {
                     alert("SESSION COMPLETE!");
                     window.location.href = "/analytics";
                     return;
                }

                // TIME DISPLAY
                const minutes = Math.floor(data.remaining / 60)
                    .toString()
                    .padStart(2, "0");
                const seconds = (data.remaining % 60)
                    .toString()
                    .padStart(2, "0");

                if (display) {
                    display.innerText = `${minutes}:${seconds}`;
                    if (data.paused) {
                        display.innerText += " (PAUSED)";
                        display.style.color = "yellow";
                    } else {
                        display.style.color = "";
                    }
                }

                // ---- DISTRACTION FLASH ----
                if (data.distraction) {
                    // Flash screen
                    const originalBg = document.body.style.backgroundColor;
                    document.body.style.backgroundColor = "red";
                    alert(`⚠️ GET BACK TO WORK!\n\nDetected: ${data.distraction}`);
                    document.body.style.backgroundColor = originalBg;
                }

                // ---- FAILURE PREDICTION WARNING ----
                if (data.prediction && data.prediction.warning) {
                    const currentHash = data.prediction.reasons.join("|");
                    if (currentHash !== lastPredictionHash) {
                        alert(
                            "⚠️ FOCUS FAILURE PREDICTED\n\n" +
                            data.prediction.reasons.join("\n")
                        );
                        lastPredictionHash = currentHash;
                    }
                }
            })
            .catch(() => {
                // If server unreachable, do nothing
            });
    }, 1000);
}
