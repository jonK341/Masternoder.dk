/**
 * Generator Button Final Fix
 * Ultimate fix for generator button - ensures it always works
 */
(function() {
    'use strict';
    
    console.log('[GenButton-Final] Initializing final generator button fix...');
    
    let buttonReady = false;
    let attempts = 0;
    const maxAttempts = 10;
    
    function fixGeneratorButton() {
        attempts++;
        console.log(`[GenButton-Final] Attempt ${attempts}/${maxAttempts}...`);
        
        const btn = document.getElementById('generate-btn');
        if (!btn) {
            if (attempts < maxAttempts) {
                setTimeout(fixGeneratorButton, 500);
            } else {
                console.error('[GenButton-Final] Button not found after all attempts');
            }
            return;
        }
        
        if (buttonReady) {
            console.log('[GenButton-Final] Button already fixed');
            return;
        }
        
        console.log('[GenButton-Final] Found button, setting up...');
        
        // Clone button to remove all event listeners
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);
        
        // Mark as fixed
        newBtn.dataset.finalFix = 'true';
        newBtn.dataset.fixedAt = new Date().toISOString();
        
        // Ensure button is enabled and visible
        newBtn.disabled = false;
        newBtn.style.opacity = '1';
        newBtn.style.cursor = 'pointer';
        newBtn.style.pointerEvents = 'auto';
        newBtn.style.display = '';
        
        const btnText = newBtn.querySelector('.btn-text');
        const btnLoader = newBtn.querySelector('.btn-loader');
        const btnContent = newBtn.querySelector('.btn-content');
        
        // Create click handler
        const handleClick = async function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            console.log('[GenButton-Final] Button clicked!');
            
            // Disable button
            newBtn.disabled = true;
            newBtn.style.opacity = '0.6';
            if (btnText) btnText.textContent = 'Genererer...';
            if (btnLoader) btnLoader.style.display = 'inline-block';
            
            // Get prompt
            const promptInput = document.getElementById('documentary-prompt') || 
                               document.getElementById('prompt-input') ||
                               document.querySelector('textarea[name="prompt"]') ||
                               document.querySelector('input[name="prompt"]');
            
            const prompt = promptInput?.value?.trim() || '';
            
            if (!prompt) {
                alert('Indtast venligst en prompt før generering');
                newBtn.disabled = false;
                newBtn.style.opacity = '1';
                if (btnText) btnText.textContent = 'Generate Documentary';
                if (btnLoader) btnLoader.style.display = 'none';
                return;
            }
            
            console.log('[GenButton-Final] Starting generation with prompt:', prompt.substring(0, 50));
            
            try {
                // Try multiple generation methods in order
                let success = false;
                
                // Method 1: Simple AI Engine
                if (window.simpleAIEngine && window.simpleAIEngine.isReady) {
                    console.log('[GenButton-Final] Using Simple AI Engine');
                    try {
                        const result = await window.simpleAIEngine.generate(prompt, prompt);
                        if (result && result.success) {
                            console.log('[GenButton-Final] Generation started via Simple AI Engine');
                            alert(`Generation startet! Document ID: ${result.result?.doc_id || 'N/A'}`);
                            success = true;
                            setTimeout(() => window.location.reload(), 2000);
                        }
                    } catch (e) {
                        console.warn('[GenButton-Final] Simple AI Engine failed:', e);
                    }
                }
                
                // Method 2: Service Worker AI Integration
                if (!success && window.serviceWorkerAIIntegration) {
                    console.log('[GenButton-Final] Using Service Worker AI Integration');
                    try {
                        const result = await window.serviceWorkerAIIntegration.startCompleteGeneration(prompt, prompt);
                        if (result && result.success) {
                            console.log('[GenButton-Final] Generation started via Service Worker AI');
                            alert(`Generation startet! Document ID: ${result.doc_id || 'N/A'}`);
                            success = true;
                            setTimeout(() => window.location.reload(), 2000);
                        }
                    } catch (e) {
                        console.warn('[GenButton-Final] Service Worker AI failed:', e);
                    }
                }
                
                // Method 3: Fixed Generator Button
                if (!success && window.fixedGeneratorButton) {
                    console.log('[GenButton-Final] Using Fixed Generator Button');
                    try {
                        await window.fixedGeneratorButton.startCompleteGeneration();
                        success = true;
                        setTimeout(() => window.location.reload(), 2000);
                    } catch (e) {
                        console.warn('[GenButton-Final] Fixed Generator Button failed:', e);
                    }
                }
                
                // Method 4: Simplified Generator
                if (!success && window.simplifiedGenerator) {
                    console.log('[GenButton-Final] Using Simplified Generator');
                    try {
                        await window.simplifiedGenerator.startGeneration();
                        success = true;
                        setTimeout(() => window.location.reload(), 2000);
                    } catch (e) {
                        console.warn('[GenButton-Final] Simplified Generator failed:', e);
                    }
                }
                
                // Method 5: Direct API call (fallback)
                if (!success) {
                    console.log('[GenButton-Final] Using direct API call');
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
                                body: JSON.stringify({ prompt: prompt })
                            });
                            
                            if (response.ok) {
                                const data = await response.json();
                                if (data.success) {
                                    console.log('[GenButton-Final] Generation started via direct API');
                                    alert(`Generation startet! Document ID: ${data.doc_id || 'N/A'}`);
                                    success = true;
                                    setTimeout(() => window.location.reload(), 2000);
                                    break;
                                }
                            }
                        } catch (e) {
                            console.warn(`[GenButton-Final] API path failed (${apiPath}):`, e);
                            continue;
                        }
                    }
                }
                
                if (!success) {
                    throw new Error('Alle generation metoder fejlede');
                }
                
            } catch (error) {
                console.error('[GenButton-Final] Generation error:', error);
                alert('Generering fejlede: ' + error.message + '\n\nPrøv igen eller kontakt support.');
                newBtn.disabled = false;
                newBtn.style.opacity = '1';
                if (btnText) btnText.textContent = 'Generate Documentary';
                if (btnLoader) btnLoader.style.display = 'none';
            }
        };
        
        // Remove all existing listeners and add new one
        const newBtnClone = newBtn.cloneNode(true);
        newBtn.parentNode.replaceChild(newBtnClone, newBtn);
        
        // Add click handler with capture phase
        newBtnClone.addEventListener('click', handleClick, true);
        newBtnClone.addEventListener('click', handleClick, false);
        newBtnClone.onclick = handleClick;
        
        // Visual confirmation
        newBtnClone.style.border = '3px solid #00ff88';
        newBtnClone.style.boxShadow = '0 0 10px rgba(0, 255, 136, 0.5)';
        setTimeout(() => {
            newBtnClone.style.border = '';
            newBtnClone.style.boxShadow = '';
        }, 3000);
        
        buttonReady = true;
        console.log('[GenButton-Final] ✓ Button fixed and ready!');
        
        // Dispatch event
        window.dispatchEvent(new CustomEvent('generatorButtonFixed', {
            detail: { button: newBtnClone }
        }));
    }
    
    // Initialize immediately
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fixGeneratorButton);
    } else {
        fixGeneratorButton();
    }
    
    // Multiple retries
    setTimeout(fixGeneratorButton, 500);
    setTimeout(fixGeneratorButton, 1000);
    setTimeout(fixGeneratorButton, 2000);
    setTimeout(fixGeneratorButton, 3000);
    setTimeout(fixGeneratorButton, 5000);
    
    console.log('[GenButton-Final] Script loaded');
})();

