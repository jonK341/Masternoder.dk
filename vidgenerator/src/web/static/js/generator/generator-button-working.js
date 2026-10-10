/**
 * Generator Button - Working Solution
 * Simple, direct solution that always works
 */
(function() {
    'use strict';
    
    console.log('[GenButton-Working] Loading...');
    
    let buttonFound = false;
    let attempts = 0;
    const MAX_ATTEMPTS = 15;
    
    function attachButtonHandler() {
        attempts++;
        console.log(`[GenButton-Working] Attempt ${attempts}/${MAX_ATTEMPTS}`);
        
        const btn = document.getElementById('generate-btn');
        if (!btn) {
            if (attempts < MAX_ATTEMPTS) {
                setTimeout(attachButtonHandler, 300);
            } else {
                console.error('[GenButton-Working] Button not found after all attempts');
            }
            return;
        }
        
        if (buttonFound) {
            console.log('[GenButton-Working] Button already handled');
            return;
        }
        
        console.log('[GenButton-Working] Found button, attaching handler...');
        
        // Clone button to remove all existing listeners
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);
        
        // Mark as handled
        newBtn.dataset.workingFix = 'true';
        newBtn.dataset.fixedAt = Date.now();
        
        // Ensure button is enabled
        newBtn.disabled = false;
        newBtn.style.opacity = '1';
        newBtn.style.cursor = 'pointer';
        newBtn.style.pointerEvents = 'auto';
        
        const btnText = newBtn.querySelector('.btn-text');
        const btnLoader = newBtn.querySelector('.btn-loader');
        
        // Click handler - SIMPLE AND DIRECT
        const clickHandler = async function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            console.log('[GenButton-Working] BUTTON CLICKED!');
            
            // Get prompt
            const promptInput = document.getElementById('documentary-prompt') || 
                               document.getElementById('prompt-input') ||
                               document.querySelector('textarea[name="prompt"]') ||
                               document.querySelector('input[name="prompt"]');
            
            const prompt = promptInput?.value?.trim() || '';
            
            if (!prompt) {
                alert('Indtast venligst en prompt før generering');
                promptInput?.focus();
                return;
            }
            
            console.log('[GenButton-Working] Prompt:', prompt.substring(0, 50));
            
            // Disable button
            newBtn.disabled = true;
            newBtn.style.opacity = '0.6';
            if (btnText) btnText.textContent = 'Genererer...';
            if (btnLoader) btnLoader.style.display = 'inline-block';
            
            try {
                // Try multiple API paths
                const apiPaths = [
                    '/vidgenerator/api/documentary/generate',
                    '/api/documentary/generate',
                    window.location.origin + '/vidgenerator/api/documentary/generate',
                    window.location.origin + '/api/documentary/generate'
                ];
                
                let success = false;
                let lastError = null;
                
                for (const apiPath of apiPaths) {
                    try {
                        console.log('[GenButton-Working] Trying API:', apiPath);
                        
                        const response = await fetch(apiPath, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Accept': 'application/json'
                            },
                            body: JSON.stringify({ 
                                prompt: prompt,
                                title: prompt.substring(0, 100)
                            })
                        });
                        
                        console.log('[GenButton-Working] Response status:', response.status);
                        
                        if (!response.ok) {
                            const text = await response.text();
                            console.warn('[GenButton-Working] Response not OK:', response.status, text.substring(0, 200));
                            lastError = `HTTP ${response.status}`;
                            continue;
                        }
                        
                        const contentType = response.headers.get('content-type') || '';
                        if (!contentType.includes('application/json')) {
                            const text = await response.text();
                            console.warn('[GenButton-Working] Not JSON response:', contentType, text.substring(0, 200));
                            lastError = 'Not JSON response';
                            continue;
                        }
                        
                        const data = await response.json();
                        console.log('[GenButton-Working] Response data:', data);
                        
                        if (data.success) {
                            console.log('[GenButton-Working] SUCCESS! Document ID:', data.doc_id);
                            alert(`Generation startet! Document ID: ${data.doc_id || 'N/A'}`);
                            success = true;
                            
                            // Reload page after delay
                            setTimeout(() => {
                                console.log('[GenButton-Working] Reloading page...');
                                window.location.reload();
                            }, 2000);
                            break;
                        } else {
                            lastError = data.error || 'Unknown error';
                            console.warn('[GenButton-Working] API returned success=false:', lastError);
                        }
                    } catch (error) {
                        console.error(`[GenButton-Working] API path failed (${apiPath}):`, error);
                        lastError = error.message;
                        continue;
                    }
                }
                
                if (!success) {
                    throw new Error(`Alle API paths fejlede. Sidste fejl: ${lastError || 'Ukendt'}`);
                }
                
            } catch (error) {
                console.error('[GenButton-Working] Generation error:', error);
                alert('Generering fejlede: ' + error.message);
                
                // Re-enable button
                newBtn.disabled = false;
                newBtn.style.opacity = '1';
                if (btnText) btnText.textContent = 'Generate Documentary';
                if (btnLoader) btnLoader.style.display = 'none';
            }
        };
        
        // Attach handler with capture and bubble
        newBtn.addEventListener('click', clickHandler, true);
        newBtn.addEventListener('click', clickHandler, false);
        newBtn.onclick = clickHandler;
        
        // Visual confirmation
        newBtn.style.border = '3px solid #00ff88';
        newBtn.style.boxShadow = '0 0 15px rgba(0, 255, 136, 0.5)';
        setTimeout(() => {
            newBtn.style.border = '';
            newBtn.style.boxShadow = '';
        }, 3000);
        
        buttonFound = true;
        console.log('[GenButton-Working] ✓ Button handler attached successfully!');
        
        // Dispatch event
        window.dispatchEvent(new CustomEvent('generatorButtonReady', {
            detail: { button: newBtn }
        }));
    }
    
    // Start immediately
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', attachButtonHandler);
    } else {
        attachButtonHandler();
    }
    
    // Multiple retries
    setTimeout(attachButtonHandler, 200);
    setTimeout(attachButtonHandler, 500);
    setTimeout(attachButtonHandler, 1000);
    setTimeout(attachButtonHandler, 2000);
    setTimeout(attachButtonHandler, 3000);
    setTimeout(attachButtonHandler, 5000);
    
    console.log('[GenButton-Working] Script loaded');
})();

