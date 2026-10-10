/**
 * Simple Generator Button Fix - Ensures button always works
 * This is a fallback that will work even if other scripts fail
 */

(function() {
    'use strict';
    
    console.log('[SimpleButtonFix] Loading...');
    
    function setupButton() {
        const btn = document.getElementById('generate-btn');
        if (!btn) {
            console.log('[SimpleButtonFix] Button not found, retrying...');
            setTimeout(setupButton, 500);
            return;
        }
        
        // Check if already has our handler
        if (btn.dataset.simpleFixApplied === 'true') {
            return;
        }
        
        console.log('[SimpleButtonFix] Setting up button...');
        
        // Remove all existing listeners by cloning
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);
        newBtn.dataset.simpleFixApplied = 'true';
        
        // Ensure button is enabled
        newBtn.disabled = false;
        newBtn.style.opacity = '1';
        newBtn.style.cursor = 'pointer';
        newBtn.style.pointerEvents = 'auto';
        
        // Add robust click handler
        const clickHandler = async function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            console.log('[SimpleButtonFix] Button clicked!');
            
            // Disable button
            newBtn.disabled = true;
            newBtn.style.opacity = '0.6';
            
            // Get prompt
            const promptInput = document.getElementById('documentary-prompt') || 
                               document.getElementById('prompt-input');
            const prompt = promptInput?.value?.trim() || '';
            
            if (!prompt) {
                alert('Please enter a prompt');
                newBtn.disabled = false;
                newBtn.style.opacity = '1';
                return;
            }
            
            // Show loading state
            const btnText = newBtn.querySelector('.btn-text');
            const btnLoader = newBtn.querySelector('.btn-loader');
            if (btnText) btnText.style.display = 'none';
            if (btnLoader) btnLoader.style.display = 'inline-block';
            
            try {
                // Try to use existing generators first
                if (window.fixedGeneratorButton && typeof window.fixedGeneratorButton.startCompleteGeneration === 'function') {
                    console.log('[SimpleButtonFix] Using FixedGeneratorButton');
                    await window.fixedGeneratorButton.startCompleteGeneration();
                } else if (window.simplifiedGenerator && typeof window.simplifiedGenerator.startGeneration === 'function') {
                    console.log('[SimpleButtonFix] Using SimplifiedTwoPhaseGenerator');
                    await window.simplifiedGenerator.startGeneration();
                } else {
                    // Direct API call
                    console.log('[SimpleButtonFix] Using direct API call');
                    const response = await fetch('/vidgenerator/api/documentary/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt })
                    });
                    
                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(`HTTP ${response.status}: ${errorText.substring(0, 200)}`);
                    }
                    
                    const data = await response.json();
                    console.log('[SimpleButtonFix] Generation started:', data);
                    
                    // Show success message
                    if (data.success && data.doc_id) {
                        alert(`Generation started! Document ID: ${data.doc_id}`);
                    }
                }
            } catch (error) {
                console.error('[SimpleButtonFix] Error:', error);
                alert('Generation failed: ' + error.message);
            } finally {
                // Re-enable button
                newBtn.disabled = false;
                newBtn.style.opacity = '1';
                if (btnText) btnText.style.display = '';
                if (btnLoader) btnLoader.style.display = 'none';
            }
        };
        
        // Add multiple event listeners to ensure it works
        newBtn.addEventListener('click', clickHandler, true); // Capture phase
        newBtn.addEventListener('click', clickHandler, false); // Bubble phase
        newBtn.onclick = clickHandler; // Direct handler
        
        console.log('[SimpleButtonFix] ✓ Button ready!');
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupButton);
    } else {
        setTimeout(setupButton, 100);
    }
    
    // Also try after delays to catch late-loading
    setTimeout(setupButton, 1000);
    setTimeout(setupButton, 3000);
    
    console.log('[SimpleButtonFix] Script loaded');
})();

