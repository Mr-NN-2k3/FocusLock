document.addEventListener('DOMContentLoaded', () => {
    // ─── Element Refs ───
    const mainContainer = document.getElementById('main-container');
    const startForm = document.getElementById('start-form');
    const sessionSetupView = document.getElementById('session-setup-view');
    const sessionActiveView = document.getElementById('session-active-view');
    const timerDisplay = document.getElementById('timer-display');
    const statePill = document.getElementById('session-state-pill');
    const penaltyPill = document.getElementById('penalty-pill');
    const intentDisplay = document.getElementById('current-intent-display');

    // Telemetry
    const elAppName = document.getElementById('app-name');
    const elWindowTitle = document.getElementById('window-title');
    const elLatency = document.getElementById('latency-ms');
    const barConf = document.getElementById('conf-bar');
    const textConf = document.getElementById('conf-text');
    const barSim = document.getElementById('sim-bar');
    const textSim = document.getElementById('sim-text');

    // Overlays
    const violationOverlay = document.getElementById('violation-overlay');
    const distReason = document.getElementById('distraction-reason');
    const warningEdge = document.getElementById('warning-overlay');
    const warningToast = document.getElementById('warning-toast');
    const warningReason = document.getElementById('warning-reason');
    const completionOverlay = document.getElementById('completion-overlay');
    const completionDesc = document.getElementById('completion-desc');
    const breakOverlay = document.getElementById('break-overlay');
    const predictionAlert = document.getElementById('prediction-alert');
    const predictionReason = document.getElementById('prediction-reason');

    // Buttons
    const breakBtn = document.getElementById('break-btn');
    const btnContinue = document.getElementById('btn-continue');
    const btnStop = document.getElementById('btn-stop');
    const confirmBreakBtn = document.getElementById('btn-confirm-break');
    const cancelBreakBtn = document.getElementById('btn-cancel-break');
    const breakInput = document.getElementById('break-excuse-input');

    // ─── Timer ───
    let localRemaining = 0;
    let timerInterval = null;
    let isTimerRunning = false;

    function startLocalTimer() {
        if (isTimerRunning) return;
        isTimerRunning = true;
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(() => {
            if (localRemaining > 0) {
                localRemaining--;
                renderTime(localRemaining);
            } else {
                checkStatus();
            }
        }, 1000);
    }

    function stopLocalTimer() {
        isTimerRunning = false;
        if (timerInterval) clearInterval(timerInterval);
    }

    function renderTime(sec) {
        if (!timerDisplay) return;
        const m = Math.floor(sec / 60).toString().padStart(2, '0');
        const s = (sec % 60).toString().padStart(2, '0');
        timerDisplay.textContent = `${m}:${s}`;
    }

    // ─── Start Session ───
    if (startForm) {
        startForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const duration = document.getElementById('duration').value;
            const mode = document.getElementById('mode').value;
            const intent = document.getElementById('intent').value.trim();
            const whitelist = document.getElementById('whitelist').value.trim();

            try {
                const res = await fetch('/api/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ duration, mode, intent, whitelist, blacklist: "" })
                });
                const data = await res.json();
                if (data.status === 'started') {
                    checkStatus();
                }
            } catch (err) {
                console.error("Start failed", err);
            }
        });
    }

    // ─── Break Flow ───
    if (breakBtn) {
        breakBtn.addEventListener('click', () => {
            if (breakOverlay) breakOverlay.classList.remove('hidden');
        });
    }
    if (cancelBreakBtn) {
        cancelBreakBtn.addEventListener('click', () => {
            if (breakOverlay) breakOverlay.classList.add('hidden');
        });
    }
    if (confirmBreakBtn) {
        confirmBreakBtn.addEventListener('click', async () => {
            const excuse = (breakInput && breakInput.value.trim()) ? breakInput.value.trim() : 'No reason';
            if (breakOverlay) breakOverlay.classList.add('hidden');
            await fetch('/api/break', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ excuse })
            });
            showSetup();
            checkStatus();
        });
    }

    // ─── Completion Flow ───
    if (btnContinue) {
        btnContinue.addEventListener('click', async () => {
            await fetch('/api/continue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ duration: 10 })
            });
            if (completionOverlay) completionOverlay.classList.add('hidden');
            checkStatus();
        });
    }
    if (btnStop) {
        btnStop.addEventListener('click', async () => {
            await fetch('/api/stop', { method: 'POST' });
            if (completionOverlay) completionOverlay.classList.add('hidden');
            showSetup();
        });
    }

    // ─── Status Polling ───
    async function checkStatus() {
        try {
            const res = await fetch('/api/status');
            const status = await res.json();

            // User Stats
            if (status.user_stats) {
                const lvl = document.getElementById('user-level');
                const xp = document.getElementById('user-xp');
                if (lvl) lvl.textContent = status.user_stats.level;
                if (xp) xp.textContent = status.user_stats.xp;
            }

            if (status.active) {
                showActiveSession(status);
            } else {
                stopLocalTimer();
                if (status.completed && status.summary) {
                    showCompletion(status);
                } else {
                    showSetup();
                }
            }
        } catch (err) {
            console.error("Status check failed", err);
        }
    }

    function showActiveSession(status) {
        sessionSetupView.classList.add('hidden');
        sessionActiveView.classList.remove('hidden');

        // Main glass card dynamic state classes
        const state = status.current_state || "PRODUCTIVE";
        if (mainContainer) {
            mainContainer.classList.remove('focus-animate', 'state-drift', 'state-danger');
            if (state === "PRODUCTIVE") mainContainer.classList.add('focus-animate');
            else if (state === "WARNING") mainContainer.classList.add('state-drift');
            else if (state === "DISTRACTION") mainContainer.classList.add('state-danger');
        }

        // Sync Timer
        localRemaining = status.remaining;
        renderTime(localRemaining);
        startLocalTimer();

        // Penalties
        if (penaltyPill) penaltyPill.textContent = `DEBT ${status.penalties || 0}s`;

        // State Pill
        if (statePill) {
            statePill.textContent = state;
            statePill.className = "status-pill";
            if (state === "PRODUCTIVE") statePill.classList.add("active");
            else if (state === "WARNING") statePill.classList.add("warning");
            else statePill.classList.add("danger");
        }

        // Overlays
        if (state === "DISTRACTION") {
            violationOverlay?.classList.remove('hidden');
            warningEdge?.classList.add('hidden');
            warningToast?.classList.add('hidden');
            if (distReason && status.activity_snapshot) {
                distReason.textContent = status.activity_snapshot.reason || "Activity not aligned.";
            }
        } else if (state === "WARNING") {
            violationOverlay?.classList.add('hidden');
            warningEdge?.classList.remove('hidden');
            warningToast?.classList.remove('hidden');
            if (warningReason && status.activity_snapshot) {
                warningReason.textContent = status.activity_snapshot.reason || "Drifting...";
            }
        } else {
            violationOverlay?.classList.add('hidden');
            warningEdge?.classList.add('hidden');
            warningToast?.classList.add('hidden');
        }

        // Telemetry Snapshot
        const snap = status.activity_snapshot;
        if (snap) {
            if (elAppName) elAppName.textContent = snap.app || "—";
            if (elWindowTitle) elWindowTitle.textContent = snap.title || "Waiting...";

            if (snap.features) {
                if (elLatency) elLatency.textContent = `${snap.features.latency_ms || 0}ms`;

                const conf = snap.features.confidence || 0;
                if (barConf) barConf.style.width = `${Math.max(5, conf)}%`;
                if (textConf) textConf.textContent = `${Math.round(conf)}%`;

                const sim = snap.features.semantic_similarity || 0;
                if (barSim) barSim.style.width = `${Math.max(5, Math.min(100, sim * 100))}%`;
                if (textSim) textSim.textContent = sim.toFixed(2);
            }
        }

        // Intent Display
        if (intentDisplay) {
            const intent = status.activity_snapshot?.features?.intent_match
                ? "🎯 Intent Aligned"
                : "";
            if (intent) {
                intentDisplay.textContent = intent;
                intentDisplay.classList.remove('hidden');
            } else {
                intentDisplay.classList.add('hidden');
            }
        }

        // Prediction
        if (predictionAlert) {
            if (status.prediction && status.prediction.warning) {
                predictionAlert.classList.remove('hidden');
                if (predictionReason) predictionReason.textContent = status.prediction.reasons.join(", ");
            } else {
                predictionAlert.classList.add('hidden');
            }
        }

        // Paused Visual
        if (timerDisplay) {
            timerDisplay.style.opacity = status.paused ? "0.4" : "1";
        }
    }

    function showCompletion(status) {
        sessionSetupView.classList.add('hidden');
        sessionActiveView.classList.add('hidden');
        violationOverlay?.classList.add('hidden');
        warningEdge?.classList.add('hidden');
        warningToast?.classList.add('hidden');

        if (mainContainer) mainContainer.classList.remove('focus-animate', 'state-drift', 'state-danger');

        const s = status.summary;
        const desc = [
            `Duration: ${s.duration} mins`,
            `Mode: ${s.mode.toUpperCase()}`,
            `Goal: ${s.intent || 'None'}`,
            `Violations: ${s.violations}`,
            `Penalties: ${s.penalties}s`,
            `XP Earned: ${status.user_stats?.xp || 0}`
        ].join('\n');

        if (completionDesc) completionDesc.textContent = desc;
        if (completionOverlay) completionOverlay.classList.remove('hidden');
    }

    function showSetup() {
        stopLocalTimer();
        sessionSetupView.classList.remove('hidden');
        sessionActiveView.classList.add('hidden');
        violationOverlay?.classList.add('hidden');
        warningEdge?.classList.add('hidden');
        warningToast?.classList.add('hidden');
        completionOverlay?.classList.add('hidden');
        breakOverlay?.classList.add('hidden');
        
        if (mainContainer) mainContainer.classList.remove('focus-animate', 'state-drift', 'state-danger');
    }

    // ─── Init ───
    setInterval(checkStatus, 3000);
    checkStatus();
});
