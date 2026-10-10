/**
 * Simple Generator Button with AI Engine
 * Uses SimpleAIEngine for generation
 */
(function() {
    'use strict';
    
    console.log('[GenButton-SimpleAI] Initializing...');
    
    let buttonInitialized = false;
    let generating = false;
    
    function initializeButton() {
        const btn = document.getElementById('generate-btn');
        if (!btn) {
            setTimeout(initializeButton, 500);
            return;
        }
        
        if (buttonInitialized) {
            return;
        }
        
        console.log('[GenButton-SimpleAI] Setting up button...');
        
        // Clone button
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);
        newBtn.dataset.simpleAI = 'true';
        
        // Enable button
        newBtn.disabled = false;
        newBtn.style.opacity = '1';
        newBtn.style.cursor = 'pointer';
        
        const btnText = newBtn.querySelector('.btn-text');
        const btnLoader = newBtn.querySelector('.btn-loader');
        
        const clickHandler = async function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            if (generating) {
                console.log('[GenButton-SimpleAI] Already generating');
                return;
            }
            
            console.log('[GenButton-SimpleAI] Button clicked');
            
            // Disable button
            newBtn.disabled = true;
            newBtn.style.opacity = '0.6';
            if (btnText) btnText.textContent = 'Genererer...';
            if (btnLoader) btnLoader.style.display = 'inline-block';
            generating = true;
            
            // Get prompt
            const promptInput = document.getElementById('documentary-prompt') || 
                               document.getElementById('prompt-input');
            const prompt = promptInput?.value?.trim() || '';
            
            if (!prompt) {
                alert('Indtast venligst en prompt');
                newBtn.disabled = false;
                newBtn.style.opacity = '1';
                if (btnText) btnText.textContent = 'Generate Documentary';
                if (btnLoader) btnLoader.style.display = 'none';
                generating = false;
                return;
            }
            
            try {
                // Wait for AI engine to be ready
                if (!window.simpleAIEngine || !window.simpleAIEngine.isReady) {
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    if (!window.simpleAIEngine) {
                        throw new Error('AI Engine not available');
                    }
                }
                
                // Generate using simple AI engine
                console.log('[GenButton-SimpleAI] Starting generation with AI engine...');
                const result = await window.simpleAIEngine.generate(prompt, prompt);
                
                console.log('[GenButton-SimpleAI] Generation started:', result);
                
                if (result.success && result.result) {
                    const docId = result.result.doc_id || result.result.id;
                    if (docId) {
                        alert(`Generation startet! Document ID: ${docId}`);
                        // Reload after delay
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    } else {
                        alert('Generation startet!');
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    }
                } else {
                    throw new Error('Generation failed');
                }
                
            } catch (error) {
                console.error('[GenButton-SimpleAI] Error:', error);
                alert('Generering fejlede: ' + error.message);
                newBtn.disabled = false;
                newBtn.style.opacity = '1';
                if (btnText) btnText.textContent = 'Generate Documentary';
                if (btnLoader) btnLoader.style.display = 'none';
                generating = false;
            }
        };
        
        // Add click handler
        newBtn.addEventListener('click', clickHandler, true);
        newBtn.onclick = clickHandler;
        
        // Visual confirmation
        newBtn.style.border = '3px solid #00ff88';
        setTimeout(() => {
            newBtn.style.border = '';
        }, 2000);
        
        buttonInitialized = true;
        console.log('[GenButton-SimpleAI] ✓ Button ready');
    }
    
    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeButton);
    } else {
        setTimeout(initializeButton, 100);
    }
    
    // Retry
    setTimeout(initializeButton, 1000);
    setTimeout(initializeButton, 3000);
    
    console.log('[GenButton-SimpleAI] Script loaded');
})();

