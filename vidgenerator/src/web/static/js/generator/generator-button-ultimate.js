(function() {
    'use strict';

    const MAX_ATTACH_ATTEMPTS = 10;
    let attachAttempts = 0;
    let handlerAttached = false;

    function log(message) {
        console.log(`[GenButton-Ultimate] ${message}`);
    }

    async function handleGenerateClick(event) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        const button = event.currentTarget;
        const btnText = button.querySelector('.btn-text');
        const btnLoader = button.querySelector('.btn-loader');

        const promptInput = document.getElementById('documentary-prompt') ||
                            document.getElementById('prompt-input') ||
                            document.querySelector('textarea[name="prompt"]') ||
                            document.querySelector('input[name="prompt"]');

        const prompt = promptInput?.value?.trim() || '';

        if (!prompt) {
            alert('Indtast venligst en prompt før generering.');
            promptInput?.focus();
            return;
        }

        // Disable button UI
        button.disabled = true;
        button.style.opacity = '0.6';
        if (btnText) btnText.textContent = 'Genererer...';
        if (btnLoader) btnLoader.style.display = 'inline-block';
        updateButtonStatus('running', 'Generating...');

        try {
            if (!window.generatorSimpleFlow) {
                throw new Error('Generator flow ikke indlæst.');
            }

            const result = await window.generatorSimpleFlow.start(prompt);
            if (result && result.success) {
                alert(`Generation startet! Document ID: ${result.doc_id || result.result?.doc_id || 'N/A'}`);
                updateButtonStatus('ready', 'Success');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                throw new Error('Ukendt fejl under generering.');
            }
        } catch (error) {
            console.error('[GenButton-Ultimate] Generation error:', error);
            alert('Generering fejlede: ' + error.message);
            updateButtonStatus('error', error.message);
            button.disabled = false;
            button.style.opacity = '1';
            if (btnText) btnText.textContent = 'Generate Documentary';
            if (btnLoader) btnLoader.style.display = 'none';
        }
    }

    function updateButtonStatus(state, message) {
        const statusEl = document.getElementById('flow-status-button');
        if (!statusEl) return;
        statusEl.className = `flow-status state-${state}`;
        statusEl.textContent = message;
    }

    function attachHandler() {
        attachAttempts += 1;
        const button = document.getElementById('generate-btn');

        if (!button) {
            if (attachAttempts < MAX_ATTACH_ATTEMPTS) {
                setTimeout(attachHandler, 400);
            } else {
                log('Button not found after maximum attempts.');
            }
            return;
        }

        if (handlerAttached) {
            log('Handler already attached.');
            return;
        }

        // Replace button to remove other handlers
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);

        newButton.addEventListener('click', handleGenerateClick, true);
        newButton.addEventListener('click', handleGenerateClick, false);
        newButton.onclick = handleGenerateClick;
        newButton.dataset.ultimateFix = 'true';
        handlerAttached = true;
        updateButtonStatus('ready', 'Ready');
        log('Handler attached successfully.');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', attachHandler);
    } else {
        attachHandler();
    }

    // Multiple retries
    for (let delay of [500, 1000, 2000, 3000, 5000]) {
        setTimeout(attachHandler, delay);
    }

    log('Ultimate generator button fix loaded.');
})();

