document.getElementById('startBtn').addEventListener('click', async () => {
    const startBtn = document.getElementById('startBtn');
    
    // Grab elements by their exact case-sensitive IDs
    const guildIdElement = document.getElementById('guildId');
    const tokenInputElement = document.getElementById('tokenInput');

    // Safety Check
    if (!guildIdElement || !tokenInputElement) {
        alert("System Sync Error: Cannot locate input fields. Please ensure your index.html file has been fully updated on Vercel.");
        return;
    }

    // Extract values
    const guildId = guildIdElement.value.trim();
    const tokenInputText = tokenInputElement.value.trim();

    if(!guildId) {
        alert("Configuration Error: Target Guild ID is required.");
        return;
    }

    let tokens = [];
    if (tokenInputText) {
        tokens = tokenInputText.split('\n').map(t => t.trim()).filter(t => t.length > 0);
    }

    if(tokens.length === 0) {
        alert("Configuration Error: Please input one or more tokens.");
        return;
    }

    // Freeze layout elements for execution continuity
    startBtn.disabled = true;
    startBtn.querySelector('span').textContent = "Executing Pipeline Tasks...";
    
    appendLog("sys", `Pipeline sequence open. Dispatching queue of ${tokens.length} elements.`);

    for(const token of tokens) {
        await runJoinPipeline({ guildId, token });
    }

    // Restore interactives
    startBtn.disabled = false;
    startBtn.querySelector('span').textContent = "Launch Application Pipeline";
    appendLog("sys", "All queued worker operations concluded.");
});

async function runJoinPipeline(payload) {
    try {
        const response = await fetch('/api/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText.substring(0, 35)}`);
        }

        const result = await response.json();
        const simplifiedToken = payload.token.substring(0, 20) + "...";

        if(result.success) {
            appendLog("ok", `Status Code [SUCCESS] → ${result.message} (${simplifiedToken})`);
        } else {
            appendLog("err", `Status Code [FAILED] → ${result.message} (${simplifiedToken})`);
        }
    } catch (error) {
        appendLog("err", `Network Pipeline Intercept: ${error.message}`);
    }
}

function appendLog(type, message) {
    const screen = document.getElementById('logsOutput');
    const row = document.createElement('div');
    row.className = 'log-line';

    if(type === "ok") {
        row.className += ' success-log';
        row.textContent = `[+] ${message}`;
    } else if(type === "err") {
        row.className += ' error-log';
        row.textContent = `[-] ${message}`;
    } else {
        row.className += ' sys-log';
        row.textContent = `[*] ${message}`;
    }
    
    screen.appendChild(row);
    screen.scrollTop = screen.scrollHeight;
}

document.getElementById('clearLogs').addEventListener('click', () => {
    document.getElementById('logsOutput').innerHTML = '<div class="log-line sys-log">Terminal buffer wiped clean.</div>';
});
