document.addEventListener('DOMContentLoaded', () => {
    // Views and Forms
    const startForm = document.getElementById('start-form');
    const sessionSetupView = document.getElementById('session-setup-view');
    const sessionActiveView = document.getElementById('session-active-view');
    
    // Displays
    const timerDisplay = document.getElementById('timer-display');
    const statePill = document.getElementById('session-state-pill');
    const intentDisplay = document.getElementById('current-intent-display');
    
    // Telemetry Elements
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
    const warningOverlay = document.getElementById('warning-edge');
    const warningToast = document.getElementById('warning-toast');
    const warningReason = document.getElementById('warning-reason');
    const themeToggle = document.getElementById('theme-toggle');

    let currentTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);

    themeToggle.addEventListener('click', () => {
        currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', currentTheme);
        localStorage.setItem('theme', currentTheme);
    });

    let localRemaining = 0;
    let timerInterval = null;

    function startLocalTimer() {
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(() => {
            if (localRemaining > 0) {
                localRemaining--;
                let m = Math.floor(localRemaining / 60).toString().padStart(2, '0');
                let s = (localRemaining % 60).toString().padStart(2, '0');
                if (timerDisplay) timerDisplay.textContent = `${m}:${s}`;
            } else {
                checkStatus();
            }
        }, 1000);
    }

    if (startForm) {
        startForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const duration = document.getElementById('duration').value;
            const mode = document.getElementById('mode').value;
            const intent = document.getElementById('intent').value.trim();
            
            try {
                const res = await fetch('/api/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ duration, mode, intent, whitelist: [], blacklist: [] })
                });
                const data = await res.json();
                if (data.status === 'started') {
                    checkStatus();
                }
            } catch (err) { console.error("Start failed", err); }
        });
    }

    document.getElementById('break-btn')?.addEventListener('click', async () => {
        await fetch('/api/break', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ excuse: 'Emergency Stop' }) });
        checkStatus();
    });

    async function checkStatus() {
        try {
            const res = await fetch('/api/status');
            const status = await res.json();
            
            if (status.user_stats) {
                document.getElementById('user-level').textContent = status.user_stats.level;
                document.getElementById('user-xp').textContent = status.user_stats.xp;
                document.getElementById('session-penalties').textContent = status.penalties || 0;
            }

            if (status.active) {
                sessionSetupView.classList.add('hidden');
                sessionActiveView.classList.remove('hidden');
                
                localRemaining = status.remaining;
                startLocalTimer();
                
                updateVisuals(status);
            } else {
                if (timerInterval) clearInterval(timerInterval);
                sessionSetupView.classList.remove('hidden');
                sessionActiveView.classList.add('hidden');
                violationOverlay?.classList.add('hidden');
                warningToast?.classList.add('hidden');
                document.getElementById('warning-overlay')?.classList.add('hidden');
            }
        } catch (err) {
            console.error("Status check failed", err);
        }
    }

    function updateVisuals(status) {
        // Handle explicit states
        const state = status.current_state || "PRODUCTIVE"; // PRODUCTIVE, WARNING, DISTRACTION
        
        statePill.textContent = state;
        statePill.className = "status-pill";
        if (state === "PRODUCTIVE") statePill.classList.add("active");
        else if (state === "WARNING") statePill.classList.add("warning");
        else statePill.classList.add("danger");

        // UI Overlays
        const wOverlay = document.getElementById('warning-overlay');
        if (state === "DISTRACTION") {
            violationOverlay.classList.remove('hidden');
            wOverlay?.classList.add('hidden');
            warningToast.classList.add('hidden');
            distReason.textContent = (status.activity_snapshot?.reason || "Behavior not aligned with intent.");
        } else if (state === "WARNING") {
            violationOverlay.classList.add('hidden');
            wOverlay?.classList.remove('hidden');
            warningToast.classList.remove('hidden');
            warningReason.textContent = (status.activity_snapshot?.reason || "Drifting from goal...");
        } else {
            violationOverlay.classList.add('hidden');
            wOverlay?.classList.add('hidden');
            warningToast.classList.add('hidden');
        }

        // Snapshot details
        const snap = status.activity_snapshot;
        if (snap) {
            elAppName.textContent = snap.app || "Unknown.exe";
            elWindowTitle.textContent = snap.title || "No Title";
            
            if (snap.features) {
                elLatency.textContent = snap.features.latency_ms + "ms";
                
                const conf = snap.features.confidence || 0;
                barConf.style.width = `${conf}%`;
                textConf.textContent = `${conf}%`;

                const sim = snap.features.semantic_similarity || 0;
                barSim.style.width = `${Math.min(100, sim * 100)}%`;
                textSim.textContent = `${sim.toFixed(2)}`;
            }
        }
        
        if (status.summary?.intent) {
            intentDisplay.textContent = `🎯 Goal: ${status.summary.intent}`;
        }
    }

    // Refresh telemetry
    setInterval(checkStatus, 2000);
    checkStatus();
});
