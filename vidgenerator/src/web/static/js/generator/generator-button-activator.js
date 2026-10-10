/**
 * Generator Button Activator - Ensures button works correctly
 * This script runs after all other scripts to ensure the button is properly initialized
 */

(function() {
    'use strict';
    
    console.log('[GeneratorActivator] Initializing generator button activator...');
    
    let buttonInitialized = false;
    let initializationAttempts = 0;
    const maxAttempts = 10;
    
    function initializeGeneratorButton() {
        initializationAttempts++;
        
        const generateBtn = document.getElementById('generate-btn');
        if (!generateBtn) {
            if (initializationAttempts < maxAttempts) {
                console.log(`[GeneratorActivator] Button not found, retrying... (${initializationAttempts}/${maxAttempts})`);
                setTimeout(initializeGeneratorButton, 500);
            } else {
                console.error('[GeneratorActivator] Generate button not found after max attempts!');
            }
            return;
        }
        
        if (buttonInitialized) {
            console.log('[GeneratorActivator] Button already initialized');
            return;
        }
        
        console.log('[GeneratorActivator] Found generate button, setting up...');
        
        // Remove all existing event listeners by cloning
        const newBtn = generateBtn.cloneNode(true);
        generateBtn.parentNode.replaceChild(newBtn, generateBtn);
        
        // Get the new button reference
        const btn = document.getElementById('generate-btn');
        
        // Ensure button is enabled
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.style.cursor = 'pointer';
        btn.style.pointerEvents = 'auto';
        
        // Add click handler with multiple fallbacks
        const clickHandler = async (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            console.log('[GeneratorActivator] Generate button clicked!');
            
            // Disable button during generation
            btn.disabled = true;
            btn.style.opacity = '0.6';
            
            try {
                // Try FixedGeneratorButton first
                if (window.fixedGeneratorButton && typeof window.fixedGeneratorButton.startCompleteGeneration === 'function') {
                    console.log('[GeneratorActivator] Using FixedGeneratorButton');
                    await window.fixedGeneratorButton.startCompleteGeneration();
                }
                // Try SimplifiedTwoPhaseGenerator
                else if (window.simplifiedGenerator && typeof window.simplifiedGenerator.startGeneration === 'function') {
                    console.log('[GeneratorActivator] Using SimplifiedTwoPhaseGenerator');
                    await window.simplifiedGenerator.startGeneration();
                }
                // Try generator-integration
                else if (window.generatorIntegration && typeof window.generatorIntegration.startGeneration === 'function') {
                    console.log('[GeneratorActivator] Using generatorIntegration');
                    await window.generatorIntegration.startGeneration();
                }
                // Fallback: Direct API call
                else {
                    console.log('[GeneratorActivator] Using direct API fallback');
                    await startGenerationDirect();
                }
            } catch (error) {
                console.error('[GeneratorActivator] Generation error:', error);
                alert('Generation failed: ' + error.message);
            } finally {
                // Re-enable button
                btn.disabled = false;
                btn.style.opacity = '1';
            }
        };
        
        // Add multiple event listeners to ensure it works
        btn.addEventListener('click', clickHandler, true); // Capture phase
        btn.addEventListener('click', clickHandler, false); // Bubble phase
        btn.onclick = clickHandler; // Direct handler
        
        // Also handle Enter key in prompt input
        const promptInput = document.getElementById('documentary-prompt') || document.getElementById('prompt-input');
        if (promptInput) {
            promptInput.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.key === 'Enter') {
                    e.preventDefault();
                    clickHandler(e);
                }
            });
        }
        
        buttonInitialized = true;
        console.log('[GeneratorActivator] ✓ Button initialized and ready!');
        
        // Visual confirmation
        btn.style.border = '2px solid #00ff00';
        setTimeout(() => {
            btn.style.border = '';
        }, 2000);
    }
    
    async function startGenerationDirect() {
        const promptInput = document.getElementById('documentary-prompt') || document.getElementById('prompt-input');
        const prompt = promptInput?.value?.trim() || '';
        
        if (!prompt) {
            alert('Please enter a prompt');
            return;
        }
        
        // Show progress
        const progressContainer = document.getElementById('progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }
        
        try {
            const response = await fetch('/vidgenerator/api/documentary/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });
            
            if (!response.ok) {
                throw new Error('Generation failed');
            }
            
            const data = await response.json();
            console.log('[GeneratorActivator] Generation started:', data);
        } catch (error) {
            console.error('[GeneratorActivator] Direct generation error:', error);
            throw error;
        }
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeGeneratorButton);
    } else {
        // DOM already loaded
        setTimeout(initializeGeneratorButton, 100);
    }
    
    // Also try after a delay to catch late-loading scripts
    setTimeout(initializeGeneratorButton, 2000);
    
    // Expose for debugging
    window.initializeGeneratorButton = initializeGeneratorButton;
    
    console.log('[GeneratorActivator] Script loaded, waiting for button...');
})();

