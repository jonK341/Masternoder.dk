/**
 * Generator Button with Page Reload
 * Ensures button works and reloads page after generation starts
 */
(function() {
    'use strict';
    
    console.log('[ButtonReload] Initializing generator button with reload...');
    
    let buttonInitialized = false;
    let generationStarted = false;
    
    function initializeButton() {
        const btn = document.getElementById('generate-btn');
        if (!btn) {
            console.log('[ButtonReload] Button not found, retrying...');
            setTimeout(initializeButton, 500);
            return;
        }
        
        if (buttonInitialized) {
            return;
        }
        
        console.log('[ButtonReload] Setting up button...');
        
        // Clone to remove all listeners
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);
        newBtn.dataset.reloadFixApplied = 'true';
        
        // Ensure button is enabled
        newBtn.disabled = false;
        newBtn.style.opacity = '1';
        newBtn.style.cursor = 'pointer';
        newBtn.style.pointerEvents = 'auto';
        
        const btnText = newBtn.querySelector('.btn-text');
        const btnLoader = newBtn.querySelector('.btn-loader');
        
        const clickHandler = async function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            if (generationStarted) {
                console.log('[ButtonReload] Generation already started');
                return;
            }
            
            console.log('[ButtonReload] Button clicked!');
            
            // Disable button
            newBtn.disabled = true;
            newBtn.style.opacity = '0.6';
            if (btnText) btnText.style.display = 'none';
            if (btnLoader) btnLoader.style.display = 'inline-block';
            
            // Get prompt
            const promptInput = document.getElementById('documentary-prompt') || 
                               document.getElementById('prompt-input');
            const prompt = promptInput?.value?.trim() || '';
            
            if (!prompt) {
                alert('Indtast venligst en prompt');
                newBtn.disabled = false;
                newBtn.style.opacity = '1';
                if (btnText) btnText.style.display = '';
                if (btnLoader) btnLoader.style.display = 'none';
                return;
            }
            
            try {
                generationStarted = true;
                
                // Try existing generators first
                if (window.fixedGeneratorButton && typeof window.fixedGeneratorButton.startCompleteGeneration === 'function') {
                    console.log('[ButtonReload] Using FixedGeneratorButton');
                    await window.fixedGeneratorButton.startCompleteGeneration();
                } else if (window.simplifiedGenerator && typeof window.simplifiedGenerator.startGeneration === 'function') {
                    console.log('[ButtonReload] Using SimplifiedTwoPhaseGenerator');
                    await window.simplifiedGenerator.startGeneration();
                } else {
                    // Direct API call
                    console.log('[ButtonReload] Using direct API call');
                    let response;
                    const apiPaths = [
                        '/vidgenerator/api/documentary/generate',
                        '/api/documentary/generate'
                    ];
                    
                    for (const apiPath of apiPaths) {
                        try {
                            response = await fetch(apiPath, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ prompt })
                            });
                            
                            if (response.ok) {
                                const data = await response.json();
                                console.log('[ButtonReload] Generation started:', data);
                                
                                if (data.success && data.doc_id) {
                                    // Reload page after short delay
                                    setTimeout(() => {
                                        console.log('[ButtonReload] Reloading page...');
                                        window.location.reload();
                                    }, 2000);
                                    return;
                                }
                                break;
                            }
                        } catch (e) {
                            console.warn(`[ButtonReload] API path failed (${apiPath}):`, e);
                            if (apiPaths.indexOf(apiPath) === apiPaths.length - 1) {
                                throw e;
                            }
                        }
                    }
                    
                    if (!response || !response.ok) {
                        throw new Error('Failed to start generation');
                    }
                }
                
                // Reload page after generation starts
                setTimeout(() => {
                    console.log('[ButtonReload] Reloading page after generation start...');
                    window.location.reload();
                }, 2000);
                
            } catch (error) {
                console.error('[ButtonReload] Error:', error);
                alert('Generering fejlede: ' + error.message);
                generationStarted = false;
                newBtn.disabled = false;
                newBtn.style.opacity = '1';
                if (btnText) btnText.style.display = '';
                if (btnLoader) btnLoader.style.display = 'none';
            }
        };
        
        // Add multiple listeners
        newBtn.addEventListener('click', clickHandler, true);
        newBtn.addEventListener('click', clickHandler, false);
        newBtn.onclick = clickHandler;
        
        // Visual confirmation
        newBtn.style.border = '3px solid #00ff88';
        setTimeout(() => {
            newBtn.style.border = '';
        }, 2000);
        
        buttonInitialized = true;
        console.log('[ButtonReload] ✓ Button ready with reload!');
    }
    
    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeButton);
    } else {
        setTimeout(initializeButton, 100);
    }
    
    // Multiple retries
    setTimeout(initializeButton, 1000);
    setTimeout(initializeButton, 3000);
    
    console.log('[ButtonReload] Script loaded');
})();

