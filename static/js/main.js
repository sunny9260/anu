// ==========================================================================
// J.A.R.V.I.S. Frontend Control Logic & Speech Integration (Upgraded)
// ==========================================================================

let isListening = false;
let recognition = null;
let currentLogs = [];
let currentTab = 'status';
let lastLockState = false;

// Voice parameters (dynamic sliders)
let selectedVoiceName = "";
let speechRate = 1.0;
let speechPitch = 0.9;

// Web Audio API Synthesizer (synthesized pings, alarms, lock sweeps)
const JarvisSynth = {
    ctx: null,
    init() {
        if (!this.ctx) {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        }
    },
    playChirp() {
        try {
            this.init();
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.type = "sine";
            osc.frequency.setValueAtTime(800, this.ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(1400, this.ctx.currentTime + 0.12);
            gain.gain.setValueAtTime(0.08, this.ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.12);
            osc.start();
            osc.stop(this.ctx.currentTime + 0.12);
        } catch (e) { console.warn("Audio Synth Error:", e); }
    },
    playGranted() {
        try {
            this.init();
            const now = this.ctx.currentTime;
            const playTone = (freq, start, dur) => {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.connect(gain);
                gain.connect(this.ctx.destination);
                osc.type = "sine";
                osc.frequency.setValueAtTime(freq, start);
                gain.gain.setValueAtTime(0.08, start);
                gain.gain.exponentialRampToValueAtTime(0.001, start + dur);
                osc.start(start);
                osc.stop(start + dur);
            };
            playTone(523.25, now, 0.15); // C5
            playTone(783.99, now + 0.12, 0.22); // G5
        } catch (e) { console.warn(e); }
    },
    playDenied() {
        try {
            this.init();
            const now = this.ctx.currentTime;
            const playTone = (freq, start, dur) => {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.connect(gain);
                gain.connect(this.ctx.destination);
                osc.type = "sawtooth";
                osc.frequency.setValueAtTime(freq, start);
                osc.frequency.linearRampToValueAtTime(freq - 100, start + dur);
                gain.gain.setValueAtTime(0.06, start);
                gain.gain.exponentialRampToValueAtTime(0.001, start + dur);
                osc.start(start);
                osc.stop(start + dur);
            };
            playTone(220, now, 0.2); // A3
            playTone(180, now + 0.15, 0.25);
        } catch (e) { console.warn(e); }
    },
    playAlert() {
        try {
            this.init();
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.type = "triangle";
            osc.frequency.setValueAtTime(880, now);
            osc.frequency.linearRampToValueAtTime(440, now + 0.18);
            osc.frequency.linearRampToValueAtTime(880, now + 0.35);
            gain.gain.setValueAtTime(0.08, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
            osc.start();
            osc.stop(now + 0.35);
        } catch (e) { console.warn(e); }
    }
};

// Initialize Speech Recognition
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        isListening = true;
        JarvisSynth.playChirp();
        document.getElementById('voice-arc-reactor').classList.add('listening');
        document.getElementById('voice-wave').classList.remove('hidden');
        document.getElementById('voice-status-text').innerText = "J.A.R.V.I.S. Active (Hands-Free Listening)...";
    };

    recognition.onend = () => {
        isListening = false;
        // Auto-restart to keep listening permanently in background
        setTimeout(startContinuousListening, 300);
    };

    recognition.onresult = (event) => {
        const resultIndex = event.resultIndex;
        const transcript = event.results[resultIndex][0].transcript.trim().toLowerCase();
        console.log("Heard:", transcript);
        
        // Define list of quick direct command terms
        const directWords = ["lock", "unlock", "volume", "sound", "mute", "unmute", "open", "hello", "wake up", "how are you", "who are you", "what time", "joke", "minimize", "desktop"];
        const isDirect = directWords.some(w => transcript.startsWith(w) || transcript.includes(" " + w));
        
        if (transcript.includes("jarvis") || isDirect) {
            let cleanCommand = transcript;
            if (transcript.includes("jarvis")) {
                const index = transcript.indexOf("jarvis");
                cleanCommand = transcript.substring(index + 6).trim();
                // Strip starting punctuation
                if (cleanCommand.startsWith(",") || cleanCommand.startsWith(".")) {
                    cleanCommand = cleanCommand.substring(1).trim();
                }
            }
            if (cleanCommand) {
                sendVoiceCommand(cleanCommand);
            }
        }
    };

    recognition.onerror = (event) => {
        if (event.error === 'not-allowed') {
            document.getElementById('voice-status-text').innerText = "Microphone access blocked. Enable in settings.";
        } else {
            console.log("Recognition error:", event.error);
        }
    };
    
    // Automatically start voice module
    setTimeout(startContinuousListening, 1000);
} else {
    document.getElementById('voice-status-text').innerText = "Speech API unsupported on this browser.";
}

function startContinuousListening() {
    if (recognition && !isListening) {
        try {
            recognition.start();
        } catch (e) {
            console.log("Start attempt skipped:", e);
        }
    }
}

// Warm up Voices dropdown
function loadSystemVoices() {
    if (!window.speechSynthesis) return;
    const voiceSelect = document.getElementById('voice-select');
    if (!voiceSelect) return;
    
    const voices = window.speechSynthesis.getVoices();
    voiceSelect.innerHTML = "";
    
    voices.forEach(voice => {
        if (voice.lang.startsWith('en')) {
            const option = document.createElement('option');
            option.value = voice.name;
            option.innerText = `${voice.name} (${voice.lang})`;
            // Select David or Google English as default if present
            if (voice.name.includes("David") || voice.name.includes("Google US English") || voice.name.includes("Zira")) {
                option.selected = true;
                selectedVoiceName = voice.name;
            }
            voiceSelect.appendChild(option);
        }
    });
}
if (window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = loadSystemVoices;
    loadSystemVoices();
}

// 1. Text-to-Speech (TTS)
function speak(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
    
    if (selectedVoiceName) {
        const voice = voices.find(v => v.name === selectedVoiceName);
        if (voice) utterance.voice = voice;
    }
    
    utterance.rate = speechRate;
    utterance.pitch = speechPitch;
    
    utterance.onstart = () => {
        document.getElementById('voice-wave').classList.remove('hidden');
        document.getElementById('voice-status-text').innerHTML = `<span style="color: var(--color-secondary); font-weight: 500;">JARVIS: "${text}"</span>`;
    };
    
    utterance.onend = () => {
        document.getElementById('voice-wave').classList.add('hidden');
        document.getElementById('voice-status-text').innerText = "Standby. Click Core to speak.";
    };
    
    window.speechSynthesis.speak(utterance);
}

// 2. Personalization Controls
function saveVoiceSettings() {
    const pVal = document.getElementById('voice-pitch').value;
    const rVal = document.getElementById('voice-rate').value;
    const voiceName = document.getElementById('voice-select').value;
    
    document.getElementById('pitch-val').innerText = pVal;
    document.getElementById('rate-val').innerText = rVal;
    
    speechPitch = parseFloat(pVal);
    speechRate = parseFloat(rVal);
    selectedVoiceName = voiceName;
}

// 3. Tab Navigation
function switchTab(tabId) {
    currentTab = tabId;
    
    // Toggle active panes
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
    document.getElementById(`pane-${tabId}`).classList.add('active');
    
    // Toggle active nav buttons
    document.querySelectorAll('.nav-tab').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`tab-btn-${tabId}`).classList.add('active');
    
    // Update dashboard header title
    const titles = {
        'status': 'SECURITY WATCHTOWER',
        'directives': 'SYSTEM DIRECTIVES & SCHEDULER',
        'processes': 'SYSTEM PROCESS INSPECTOR',
        'records': 'CENTRAL REGISTRY LOGS'
    };
    document.getElementById('dashboard-tab-title').innerText = titles[tabId];
    
    // Load content dynamically
    if (tabId === 'directives') {
        loadTasks();
        loadRules();
    } else if (tabId === 'processes') {
        loadProcesses();
    } else if (tabId === 'records') {
        loadRecords();
    }
}

// 4. Speech and Commands

function sendVoiceCommand(cmdText) {
    fetch('/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmdText })
    })
    .then(res => res.json())
    .then(data => {
        if (data.reply) speak(data.reply);
        // Refresh directives if active
        if (currentTab === 'directives') {
            loadTasks();
        }
    })
    .catch(err => console.error(err));
}

function sendTextCommand() {
    const input = document.getElementById('text-command-input');
    const cmdText = input.value.trim();
    if (!cmdText) return;
    input.value = "";
    sendVoiceCommand(cmdText);
}

// 5. System Status Loop & Polling
function fetchStatus() {
    fetch('/status')
    .then(res => res.json())
    .then(status => {
        updateUI(status);
    })
    .catch(err => console.error(err));
}

function updateUI(status) {
    const lockBadge = document.getElementById('badge-system-lock');
    const ownerBadge = document.getElementById('badge-owner-detected');
    const lockOverlay = document.getElementById('lock-screen-overlay');
    const bioText = document.getElementById('biometric-text');
    
    // Sound on Lock State Transitions
    if (status.locked !== lastLockState) {
        if (status.locked) JarvisSynth.playDenied();
        else JarvisSynth.playGranted();
        lastLockState = status.locked;
    }
    
    // Watchdog alerts for blacklisted violations
    if (status.violation_alert) {
        JarvisSynth.playAlert();
        speak(`Security Directive Violation: Terminated restricted application ${status.violation_alert}`);
        // Clear alert on backend
        fetch('/clear_alert', { method: 'POST' });
        if (currentTab === 'records') loadRecords();
    }
    
    // Lock Badges
    if (status.locked) {
        lockBadge.innerText = "LOCKED";
        lockBadge.className = "status-value offline";
    } else {
        lockBadge.innerText = "ACTIVE";
        lockBadge.className = "status-value active";
    }
    
    // Owner presence
    if (status.owner_detected) {
        ownerBadge.innerText = "OWNER PRESENT";
        ownerBadge.className = "status-value active";
    } else {
        ownerBadge.innerText = "AWAY / ESCAPED";
        ownerBadge.className = "status-value offline";
    }
    
    // Lock screen overlay control
    if (status.locked && status.lock_mode === "overlay") {
        lockOverlay.classList.remove('hidden');
        if (status.owner_detected) {
            bioText.innerText = "OWNER VERIFIED. AUTHORIZING ACCESS SYSTEM...";
            bioText.style.color = "var(--color-success)";
            bioText.parentElement.style.borderColor = "var(--color-success)";
        } else {
            bioText.innerText = "UNAUTHORIZED VISITOR IN VISION AREA";
            bioText.style.color = "var(--color-danger)";
            bioText.parentElement.style.borderColor = "var(--color-danger)";
        }
    } else {
        lockOverlay.classList.add('hidden');
    }
    
    // System log console updates (Tab 1 logs)
    if (JSON.stringify(status.logs) !== JSON.stringify(currentLogs)) {
        currentLogs = [...status.logs];
        const logConsole = document.getElementById('logs-list');
        logConsole.innerHTML = "";
        
        currentLogs.forEach(log => {
            const entry = document.createElement('div');
            if (log.includes("Rule Violation") || log.includes("Violated") || log.includes("Violations")) {
                entry.innerHTML = `<span style="color: var(--color-danger); font-weight:bold;">${log}</span>`;
            } else if (log.includes("Clearance") || log.includes("Unlocked")) {
                entry.innerHTML = `<span style="color: var(--color-success);">${log}</span>`;
            } else if (log.includes("Command")) {
                entry.innerHTML = `<span style="color: var(--color-secondary);">${log}</span>`;
            } else {
                entry.innerHTML = `<span>${log}</span>`;
            }
            logConsole.appendChild(entry);
        });
        logConsole.scrollTop = logConsole.scrollHeight;
    }
}

// 6. Telemetry & Hardware Info
function fetchTelemetry() {
    if (currentTab !== 'status') return;
    
    fetch('/telemetry')
    .then(res => res.json())
    .then(tel => {
        updateGauge('cpu-gauge-circle', 'cpu-value', tel.cpu);
        updateGauge('ram-gauge-circle', 'ram-value', tel.ram);
        
        document.getElementById('tel-pids').innerText = tel.process_count;
        document.getElementById('tel-battery').innerText = `${tel.battery}% ${tel.plugged ? '(Charging)' : '(On Cell)'}`;
    })
    .catch(err => console.error(err));
}

function updateGauge(circleId, valueId, percent) {
    const circle = document.getElementById(circleId);
    const text = document.getElementById(valueId);
    if (!circle || !text) return;
    
    const val = Math.round(percent);
    // Stroke-dasharray is 264
    const offset = 264 - (264 * val / 100);
    circle.style.strokeDashoffset = offset;
    text.innerText = `${val}%`;
}

// 7. Directives APIs (Tasks & Blacklist Rules)
function loadTasks() {
    fetch('/tasks')
    .then(res => res.json())
    .then(tasks => {
        const list = document.getElementById('tasks-list');
        list.innerHTML = "";
        
        let activeCount = 0;
        tasks.forEach(task => {
            if (!task.completed) activeCount++;
            
            const item = document.createElement('div');
            item.className = `directive-item ${task.completed ? 'completed' : ''}`;
            item.innerHTML = `
                <div class="directive-left">
                    <button class="check-btn" onclick="toggleTask(${task.id}, ${!task.completed})">
                        <i class="fa-solid fa-check"></i>
                    </button>
                    <span class="directive-text">${task.text}</span>
                    <span class="directive-time">${task.timestamp}</span>
                </div>
                <button class="delete-btn" onclick="deleteTask(${task.id})">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            `;
            list.appendChild(item);
        });
        document.getElementById('task-count-badge').innerText = `${activeCount} Active`;
    });
}

function addTask() {
    const input = document.getElementById('task-input');
    const text = input.value.trim();
    if (!text) return;
    
    fetch('/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text })
    })
    .then(() => {
        input.value = "";
        loadTasks();
    });
}

function toggleTask(id, completed) {
    fetch(`/tasks/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed: completed })
    })
    .then(() => loadTasks());
}

function deleteTask(id) {
    fetch(`/tasks/${id}`, { method: 'DELETE' })
    .then(() => loadTasks());
}

// Blacklist rules API
function loadRules() {
    fetch('/rules')
    .then(res => res.json())
    .then(rules => {
        const list = document.getElementById('rules-list');
        list.innerHTML = "";
        
        document.getElementById('rule-count-badge').innerText = `${rules.length} Rules`;
        
        rules.forEach(rule => {
            const item = document.createElement('div');
            item.className = 'directive-item';
            item.innerHTML = `
                <div class="directive-left">
                    <span class="rule-process-name"><i class="fa-solid fa-triangle-exclamation"></i> ${rule.process}</span>
                    <span class="rule-desc">${rule.description}</span>
                </div>
                <button class="delete-btn" onclick="deleteRule(${rule.id})">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            `;
            list.appendChild(item);
        });
    });
}

function addRule() {
    const input = document.getElementById('rule-input');
    const text = input.value.trim();
    if (!text) return;
    
    fetch('/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ process: text })
    })
    .then(() => {
        input.value = "";
        loadRules();
    });
}

function deleteRule(id) {
    fetch(`/rules/${id}`, { method: 'DELETE' })
    .then(() => loadRules());
}

// 8. Process Core list
function loadProcesses() {
    if (currentTab !== 'processes') return;
    
    fetch('/processes')
    .then(res => res.json())
    .then(procs => {
        const tbody = document.getElementById('processes-table-body');
        tbody.innerHTML = "";
        
        procs.forEach(proc => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${proc.pid}</td>
                <td>${proc.name}</td>
                <td>${proc.cpu}%</td>
                <td>${proc.mem}%</td>
                <td>
                    <button class="proc-kill-btn" onclick="killProcess(${proc.pid})">
                        <i class="fa-solid fa-skull"></i> TERMINATE
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    });
}

function killProcess(pid) {
    if (confirm(`Confirm termination instruction for Process PID: ${pid}?`)) {
        fetch(`/processes/${pid}`, { method: 'DELETE' })
        .then(() => {
            loadProcesses();
            JarvisSynth.playChirp();
        });
    }
}

// 9. Registry Logs Archives & Threats
let localRecords = [];
function loadRecords() {
    fetch('/records')
    .then(res => res.json())
    .then(records => {
        localRecords = records;
        renderRegistryTable(records);
        renderIntruderPhotos(records);
    });
}

function renderRegistryTable(records) {
    const tbody = document.getElementById('registry-table-body');
    tbody.innerHTML = "";
    
    records.forEach(rec => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${rec.timestamp}</td>
            <td><span class="registry-cat-badge ${rec.category}">${rec.category}</span></td>
            <td>${rec.message}</td>
        `;
        tbody.appendChild(row);
    });
}

function renderIntruderPhotos(records) {
    const grid = document.getElementById('intruder-photos-grid');
    grid.innerHTML = "";
    
    // Filter records containing intruder snapshots
    const intruderAlerts = records.filter(r => r.metadata && r.metadata.image_path);
    
    if (intruderAlerts.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1/3; text-align:center; padding:40px; color: var(--text-muted); font-size:11px;">
            <i class="fa-solid fa-shield" style="font-size:30px; margin-bottom:10px; display:block;"></i> No Threat Signatures Recorded.
        </div>`;
        return;
    }
    
    intruderAlerts.forEach(alert => {
        const card = document.createElement('div');
        card.className = "intruder-card";
        card.innerHTML = `
            <div class="intruder-img-box">
                <img src="${alert.metadata.image_path}" alt="Captured Security Snapshot">
                <span class="intruder-threat-banner">THREAT SIGNATURE</span>
            </div>
            <div class="intruder-details-box">
                <span class="intruder-time"><i class="fa-regular fa-clock"></i> ${alert.timestamp}</span>
                <p class="intruder-desc">${alert.message}</p>
            </div>
        `;
        grid.appendChild(card);
    });
}

function filterRegistry() {
    const query = document.getElementById('registry-search').value.toLowerCase();
    const filtered = localRecords.filter(r => 
        r.message.toLowerCase().includes(query) || 
        r.category.toLowerCase().includes(query) || 
        r.timestamp.toLowerCase().includes(query)
    );
    renderRegistryTable(filtered);
}

// 10. Dashboard Settings Sync
function updateConfig() {
    const mode = document.getElementById('select-lock-mode').value;
    const timeout = document.getElementById('input-lock-timeout').value;
    
    fetch('/set_lock_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lock_mode: mode, lock_timeout: timeout })
    })
    .catch(err => console.error(err));
}

function triggerLock() {
    fetch('/trigger_lock', { method: 'POST' })
    .catch(err => console.error(err));
}

function attemptBypass() {
    const password = document.getElementById('bypass-password').value;
    const errorMsg = document.getElementById('bypass-error');
    
    fetch('/trigger_unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: password })
    })
    .then(res => {
        if (res.ok) {
            errorMsg.classList.add('hidden');
            document.getElementById('bypass-password').value = "";
        } else {
            errorMsg.classList.remove('hidden');
            JarvisSynth.playDenied();
        }
    })
    .catch(err => console.error(err));
}

function adjustVolume(val) {
    document.getElementById('volume-val').innerText = `${val}%`;
    fetch('/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: `set volume to ${val}` })
    })
    .catch(err => console.error(err));
}

function clearLocalLogs() {
    const logConsole = document.getElementById('logs-list');
    logConsole.innerHTML = "<div>[SYSTEM] Local console logs cleared. Ready.</div>";
}

function syncInitialConfig() {
    fetch('/status')
    .then(res => res.json())
    .then(status => {
        document.getElementById('select-lock-mode').value = status.lock_mode;
        document.getElementById('input-lock-timeout').value = status.lock_timeout;
        fetchStatus();
    });
}

// Clock updates
setInterval(() => {
    const date = new Date();
    const days = ['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'];
    const timeStr = date.toLocaleTimeString();
    const dayStr = days[date.getDay()];
    document.getElementById('current-time').innerText = `${timeStr} - ${dayStr}`;
}, 1000);

// Set loops
syncInitialConfig();
setInterval(fetchStatus, 1000);
setInterval(fetchTelemetry, 2000);
setInterval(loadProcesses, 5000);
