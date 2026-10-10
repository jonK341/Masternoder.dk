/**
 * Generator Button Debug - Comprehensive debugging and testing
 * This script ensures the button works and provides detailed debugging
 */

(function() {
    'use strict';
    
    console.log('[ButtonDebug] Initializing generator button debugger...');
    
    const DEBUG = true;
    const log = DEBUG ? console.log.bind(console, '[ButtonDebug]') : () => {};
    const error = console.error.bind(console, '[ButtonDebug] ERROR:');
    
    let buttonFound = false;
    let buttonInitialized = false;
    let clickCount = 0;
    
    function debugButton() {
        const btn = document.getElementById('generate-btn');
        
        if (!btn) {
            log('Button not found');
            return {
                found: false,
                enabled: false,
                visible: false,
                hasListeners: false
            };
        }
        
        buttonFound = true;
        
        // Check button state
        const rect = btn.getBoundingClientRect();
        const isVisible = rect.width > 0 && rect.height > 0;
        const isEnabled = !btn.disabled;
        const style = window.getComputedStyle(btn);
        const isClickable = style.pointerEvents !== 'none' && style.opacity !== '0';
        
        // Try to detect listeners (not perfect, but helpful)
        const hasOnClick = btn.onclick !== null;
        
        log('Button state:', {
            found: true,
            enabled: isEnabled,
            visible: isVisible,
            clickable: isClickable,
            hasOnClick: hasOnClick,
            disabled: btn.disabled,
            opacity: style.opacity,
            pointerEvents: style.pointerEvents,
            position: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
        });
        
        return {
            found: true,
            enabled: isEnabled,
            visible: isVisible,
            clickable: isClickable,
            hasListeners: hasOnClick,
            disabled: btn.disabled,
            opacity: style.opacity,
            pointerEvents: style.pointerEvents
        };
    }
    
    function setupButton() {
        const btn = document.getElementById('generate-btn');
        if (!btn) {
            log('Button not found, will retry...');
            setTimeout(setupButton, 500);
            return;
        }
        
        if (buttonInitialized) {
            log('Button already initialized');
            return;
        }
        
        log('Setting up button...');
        
        // Debug current state
        const debugInfo = debugButton();
        log('Initial button state:', debugInfo);
        
        // Clone to remove all listeners
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);
        newBtn.dataset.debugApplied = 'true';
        
        // Force enable
        newBtn.disabled = false;
        newBtn.style.opacity = '1';
        newBtn.style.cursor = 'pointer';
        newBtn.style.pointerEvents = 'auto';
        newBtn.style.userSelect = 'none';
        
        // Add comprehensive click handler
        const clickHandler = async function(e) {
            clickCount++;
            log(`Button clicked! (count: ${clickCount})`);
            
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            // Disable button
            newBtn.disabled = true;
            newBtn.style.opacity = '0.6';
            
            // Get prompt
            const promptInput = document.getElementById('documentary-prompt') || 
                               document.getElementById('prompt-input');
            const prompt = promptInput?.value?.trim() || '';
            
            log('Prompt:', prompt ? prompt.substring(0, 50) + '...' : 'EMPTY');
            
            if (!prompt) {
                alert('Indtast venligst en prompt');
                newBtn.disabled = false;
                newBtn.style.opacity = '1';
                return;
            }
            
            // Show loading
            const btnText = newBtn.querySelector('.btn-text');
            const btnLoader = newBtn.querySelector('.btn-loader');
            if (btnText) btnText.style.display = 'none';
            if (btnLoader) btnLoader.style.display = 'inline-block';
            
            try {
                log('Attempting generation...');
                
                // Try existing generators first
                if (window.fixedGeneratorButton && typeof window.fixedGeneratorButton.startCompleteGeneration === 'function') {
                    log('Using FixedGeneratorButton');
                    await window.fixedGeneratorButton.startCompleteGeneration();
                    log('FixedGeneratorButton completed');
                } else if (window.simplifiedGenerator && typeof window.simplifiedGenerator.startGeneration === 'function') {
                    log('Using SimplifiedTwoPhaseGenerator');
                    await window.simplifiedGenerator.startGeneration();
                    log('SimplifiedTwoPhaseGenerator completed');
                } else {
                    log('Using direct API call (no generators found)');
                    
                    // Try multiple API paths
                    let response;
                    let apiPath = null;
                    const paths = [
                        '/vidgenerator/api/documentary/generate',
                        '/api/documentary/generate'
                    ];
                    
                    for (const path of paths) {
                        try {
                            log(`Trying API path: ${path}`);
                            response = await fetch(path, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ prompt })
                            });
                            apiPath = path;
                            log(`API call successful: ${path} - Status: ${response.status}`);
                            break;
                        } catch (e) {
                            log(`API path failed: ${path} - ${e.message}`);
                            if (paths.indexOf(path) === paths.length - 1) {
                                throw e;
                            }
                        }
                    }
                    
                    if (!response.ok) {
                        const errorText = await response.text();
                        log(`API error: ${response.status} - ${errorText.substring(0, 200)}`);
                        throw new Error(`HTTP ${response.status}: ${errorText.substring(0, 200)}`);
                    }
                    
                    const data = await response.json();
                    log('Generation response:', data);
                    
                    if (data.success && data.doc_id) {
                        alert(`Generation startet! Document ID: ${data.doc_id}`);
                        log('Generation started successfully');
                    } else if (data.error) {
                        throw new Error(data.error);
                    }
                }
            } catch (error) {
                error('Generation failed:', error);
                alert('Generering fejlede: ' + error.message);
            } finally {
                // Re-enable button
                newBtn.disabled = false;
                newBtn.style.opacity = '1';
                if (btnText) btnText.style.display = '';
                if (btnLoader) btnLoader.style.display = 'none';
                log('Button re-enabled');
            }
        };
        
        // Add multiple listeners
        newBtn.addEventListener('click', clickHandler, true);
        newBtn.addEventListener('click', clickHandler, false);
        newBtn.onclick = clickHandler;
        
        // Also handle Enter key
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
        log('✓ Button initialized and ready!');
        
        // Visual confirmation
        newBtn.style.border = '3px solid #00ff00';
        setTimeout(() => {
            newBtn.style.border = '';
        }, 2000);
        
        // Expose debug function
        window.debugGeneratorButton = debugButton;
        window.testGeneratorButton = () => {
            log('Manual test triggered');
            clickHandler(new Event('click'));
        };
    }
    
    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupButton);
    } else {
        setTimeout(setupButton, 100);
    }
    
    // Multiple retries
    setTimeout(setupButton, 1000);
    setTimeout(setupButton, 3000);
    setTimeout(setupButton, 5000);
    
    // Debug info on window
    window.generatorButtonDebug = {
        debug: debugButton,
        test: () => {
            const btn = document.getElementById('generate-btn');
            if (btn) {
                btn.click();
            }
        },
        info: () => {
            return {
                buttonFound,
                buttonInitialized,
                clickCount,
                generators: {
                    fixedGeneratorButton: !!window.fixedGeneratorButton,
                    simplifiedGenerator: !!window.simplifiedGenerator
                }
            };
        }
    };
    
    log('Debug script loaded. Use window.generatorButtonDebug for debugging.');
})();

