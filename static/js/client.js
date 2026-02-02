/* =========================================================
   FocusLock Client Controller
   Role: UI + Signal Reporter
   Authority: SERVER ONLY
   ========================================================= */

// -------- SESSION START --------
function startSession() {
    const durationInput = document.getElementById("duration");
    const modeInput = document.getElementById("mode");

    if (!durationInput || !modeInput) return;

    const duration = durationInput.value;
    const mode = modeInput.value;

    // Basic client validation (not authority)
    if (duration < 1) {
        alert("Invalid session duration.");
        return;
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
        body: JSON.stringify({ duration, mode })
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

// -------- VISIBILITY VIOLATION (WATCHER) --------
document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
        fetch("/api/violation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ type: "TAB_SWITCH" })
        });

        alert(
            "⚠️ FOCUS BREACH DETECTED\n\n" +
            "Leaving this session has consequences."
        );
    }
});

// -------- HEARTBEAT (ANTI-TAMPER) --------
setInterval(() => {
    fetch("/api/heartbeat", { method: "POST" })
        .catch(() => {}); // silent
}, 5000);

// -------- SERVER-AUTH TIMER + PREDICTION --------
if (window.initialStatus) {
    const display = document.getElementById("timer-display");

    setInterval(() => {
        fetch("/api/status")
            .then(res => res.json())
            .then(data => {
                if (!data.active) {
                    window.location.href = "/";
                    return;
                }

                const minutes = Math.floor(data.remaining / 60)
                    .toString()
                    .padStart(2, "0");
                const seconds = (data.remaining % 60)
                    .toString()
                    .padStart(2, "0");

                if (display) {
                    display.innerText = `${minutes}:${seconds}`;
                }

                // ---- FAILURE PREDICTION WARNING ----
                if (data.prediction && data.prediction.warning) {
                    alert(
                        "⚠️ FOCUS FAILURE PREDICTED\n\n" +
                        data.prediction.reasons.join("\n")
                    );
                }
            })
            .catch(() => {
                // If server unreachable, do nothing
            });
    }, 1000);
}
