(function() {
    'use strict';

    const MAX_ATTEMPTS = 10;
    const logElement = document.getElementById('flow-log');
    const attemptsElement = document.getElementById('flow-attempts');

    const statusElements = {
        serviceWorker: document.getElementById('flow-status-service-worker'),
        aiEngine: document.getElementById('flow-status-ai-engine'),
        api: document.getElementById('flow-status-api'),
        button: document.getElementById('flow-status-button')
    };

    function addLog(message, type = 'info') {
        if (!logElement) return;
        const entry = document.createElement('div');
        entry.className = `flow-log-entry ${type === 'error' ? 'error' : ''}`;
        entry.innerHTML = `<span>[${type.toUpperCase()}]</span>${message}`;
        logElement.prepend(entry);
        const entries = logElement.querySelectorAll('.flow-log-entry');
        if (entries.length > 25) {
            logElement.removeChild(entries[entries.length - 1]);
        }
    }

    function updateStatus(key, state, message) {
        const el = statusElements[key];
        if (!el) return;
        el.className = `flow-status state-${state}`;
        el.textContent = message;
    }

    const generatorSimpleFlow = {
        attempts: 0,
        async start(prompt) {
            this.attempts += 1;
            if (attemptsElement) {
                attemptsElement.textContent = `Attempts: ${this.attempts} / ${MAX_ATTEMPTS}`;
            }

            if (this.attempts > MAX_ATTEMPTS) {
                const message = 'Maksimalt antal forsøg nået. Genindlæs siden.';
                addLog(message, 'error');
                updateStatus('button', 'error', 'Max attempts');
                throw new Error(message);
            }

            addLog(`Starting generation attempt ${this.attempts}`, 'info');

            try {
                this.checkServiceWorker();

                // Try Service Worker AI Integration first
                if (window.serviceWorkerAIIntegration) {
                    updateStatus('serviceWorker', 'running', 'Gathering intelligence...');
                    addLog('Service Worker AI Integration available', 'info');
                    try {
                        const result = await window.serviceWorkerAIIntegration.startCompleteGeneration(prompt, prompt);
                        if (result && result.success) {
                            updateStatus('serviceWorker', 'ready', 'Intelligence ready');
                            updateStatus('aiEngine', 'ready', 'Generation started');
                            addLog('Generation started via Service Worker AI Integration', 'info');
                            return result;
                        }
                    } catch (error) {
                        addLog(`Service Worker AI failed: ${error.message}`, 'error');
                        updateStatus('serviceWorker', 'error', 'Failed');
                    }
                } else {
                    updateStatus('serviceWorker', 'error', 'Not available');
                }

                // Try Simple AI Engine
                if (window.simpleAIEngine) {
                    addLog('Using Simple AI Engine fallback', 'info');
                    try {
                        if (!window.simpleAIEngine.isReady) {
                            addLog('Waiting for Simple AI Engine to initialize...', 'info');
                            await new Promise(resolve => setTimeout(resolve, 1000));
                        }
                        updateStatus('aiEngine', 'running', 'Generating...');
                        const result = await window.simpleAIEngine.generate(prompt, prompt);
                        if (result && result.success) {
                            updateStatus('aiEngine', 'ready', 'Generation started');
                            addLog('Generation started via Simple AI Engine', 'info');
                            return result;
                        }
                    } catch (error) {
                        addLog(`Simple AI Engine failed: ${error.message}`, 'error');
                        updateStatus('aiEngine', 'error', 'Failed');
                    }
                } else {
                    updateStatus('aiEngine', 'error', 'Not available');
                }

                // Direct API fallback
                addLog('Using direct API fallback', 'info');
                updateStatus('api', 'running', 'Calling API...');
                const apiPaths = [
                    '/vidgenerator/api/documentary/generate',
                    '/api/documentary/generate',
                    'http://masternoder.dk/vidgenerator/api/documentary/generate',
                    'http://masternoder.dk/api/documentary/generate'
                ];

                for (const apiPath of apiPaths) {
                    try {
                        const response = await fetch(apiPath, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ prompt })
                        });

                        if (response.ok) {
                            const data = await response.json();
                            if (data.success) {
                                updateStatus('api', 'ready', 'Generation started');
                                addLog(`Generation started via API (${apiPath})`, 'info');
                                return data;
                            }
                        } else {
                            addLog(`API ${apiPath} returned ${response.status}`, 'error');
                        }
                    } catch (error) {
                        addLog(`API ${apiPath} failed: ${error.message}`, 'error');
                        continue;
                    }
                }

                updateStatus('api', 'error', 'All API paths failed');
                throw new Error('All generation methods failed');
            } catch (error) {
                addLog(`Generation error: ${error.message}`, 'error');
                throw error;
            }
        },
        checkServiceWorker() {
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.getRegistrations()
                    .then(regs => {
                        if (regs.length > 0) {
                            updateStatus('serviceWorker', 'ready', `${regs.length} registration(s)`);
                        } else {
                            updateStatus('serviceWorker', 'error', 'Not registered');
                        }
                    })
                    .catch(() => updateStatus('serviceWorker', 'error', 'Check failed'));
            } else {
                updateStatus('serviceWorker', 'error', 'Not supported');
            }
        }
    };

    window.generatorSimpleFlow = generatorSimpleFlow;
})();

