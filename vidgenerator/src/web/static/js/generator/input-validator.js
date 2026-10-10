/**
 * Input Validator for Generator
 * Validates and sanitizes user input before submission
 */

class GeneratorInputValidator {
    constructor() {
        this.config = {
            minPromptLength: 10,
            maxPromptLength: 5000,
            minTitleLength: 3,
            maxTitleLength: 200,
            allowedSpecialChars: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/g,
            profanityPatterns: [] // Can be populated with patterns if needed
        };
        
        this.init();
    }
    
    init() {
        // Setup real-time validation if prompt input exists
        const promptInput = document.getElementById('prompt-input');
        if (promptInput) {
            promptInput.addEventListener('input', (e) => this.validatePrompt(e.target.value));
            promptInput.addEventListener('blur', (e) => this.validatePrompt(e.target.value, true));
        }
        
        // Setup title validation if exists
        const titleInput = document.getElementById('title-input');
        if (titleInput) {
            titleInput.addEventListener('input', (e) => this.validateTitle(e.target.value));
            titleInput.addEventListener('blur', (e) => this.validateTitle(e.target.value, true));
        }
    }
    
    validatePrompt(prompt, showErrors = false) {
        const errors = [];
        const warnings = [];
        
        // Length validation
        if (!prompt || prompt.trim().length === 0) {
            if (showErrors) {
                errors.push('Prompt cannot be empty');
            }
            return { valid: false, errors, warnings };
        }
        
        const trimmedPrompt = prompt.trim();
        
        if (trimmedPrompt.length < this.config.minPromptLength) {
            errors.push(`Prompt must be at least ${this.config.minPromptLength} characters`);
        }
        
        if (trimmedPrompt.length > this.config.maxPromptLength) {
            errors.push(`Prompt must be no more than ${this.config.maxPromptLength} characters`);
        }
        
        // Check for excessive special characters (potential spam)
        const specialCharCount = (trimmedPrompt.match(this.config.allowedSpecialChars) || []).length;
        if (specialCharCount > trimmedPrompt.length * 0.3) {
            warnings.push('High number of special characters detected');
        }
        
        // Check for repeated characters (potential spam)
        if (this.hasExcessiveRepeats(trimmedPrompt)) {
            warnings.push('Repeated characters detected');
        }
        
        // Check for profanity (if patterns exist)
        if (this.config.profanityPatterns.length > 0) {
            const hasProfanity = this.config.profanityPatterns.some(pattern => 
                new RegExp(pattern, 'i').test(trimmedPrompt)
            );
            if (hasProfanity) {
                warnings.push('Inappropriate content detected');
            }
        }
        
        // Update UI feedback
        this.updatePromptFeedback(errors, warnings, trimmedPrompt.length);
        
        return {
            valid: errors.length === 0,
            errors,
            warnings,
            sanitized: this.sanitize(trimmedPrompt),
            length: trimmedPrompt.length
        };
    }
    
    validateTitle(title, showErrors = false) {
        const errors = [];
        const warnings = [];
        
        if (!title || title.trim().length === 0) {
            // Title is optional, so no error
            return { valid: true, errors, warnings };
        }
        
        const trimmedTitle = title.trim();
        
        if (trimmedTitle.length < this.config.minTitleLength) {
            errors.push(`Title must be at least ${this.config.minTitleLength} characters`);
        }
        
        if (trimmedTitle.length > this.config.maxTitleLength) {
            errors.push(`Title must be no more than ${this.config.maxTitleLength} characters`);
        }
        
        return {
            valid: errors.length === 0,
            errors,
            warnings,
            sanitized: this.sanitize(trimmedTitle),
            length: trimmedTitle.length
        };
    }
    
    validateAll(inputs) {
        const promptValidation = this.validatePrompt(inputs.prompt || '', true);
        const titleValidation = this.validateTitle(inputs.title || '', true);
        
        return {
            valid: promptValidation.valid && titleValidation.valid,
            prompt: promptValidation,
            title: titleValidation,
            allErrors: [...promptValidation.errors, ...titleValidation.errors],
            allWarnings: [...promptValidation.warnings, ...titleValidation.warnings]
        };
    }
    
    sanitize(text) {
        // Remove potentially dangerous characters while preserving content
        return text
            .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '') // Remove script tags
            .replace(/<[^>]+>/g, '') // Remove HTML tags
            .replace(/javascript:/gi, '') // Remove javascript: protocol
            .replace(/on\w+\s*=/gi, '') // Remove event handlers
            .trim();
    }
    
    hasExcessiveRepeats(text) {
        // Check for patterns like "aaaa" or "123123123"
        const repeatPattern = /(.)\1{4,}/; // Same character 5+ times
        return repeatPattern.test(text);
    }
    
    updatePromptFeedback(errors, warnings, length) {
        const promptInput = document.getElementById('prompt-input');
        if (!promptInput) return;
        
        // Remove existing feedback
        const existingFeedback = promptInput.parentElement.querySelector('.input-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }
        
        // Create feedback element
        const feedback = document.createElement('div');
        feedback.className = 'input-feedback';
        
        // Add character count
        const countEl = document.createElement('div');
        countEl.className = 'input-count';
        const remaining = this.config.maxPromptLength - length;
        countEl.textContent = `${length} / ${this.config.maxPromptLength} characters`;
        if (remaining < 50) {
            countEl.classList.add('warning');
        }
        if (remaining < 0) {
            countEl.classList.add('error');
        }
        feedback.appendChild(countEl);
        
        // Add errors
        if (errors.length > 0) {
            const errorEl = document.createElement('div');
            errorEl.className = 'input-error';
            errorEl.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${errors[0]}`;
            feedback.appendChild(errorEl);
            promptInput.classList.add('input-invalid');
        } else {
            promptInput.classList.remove('input-invalid');
        }
        
        // Add warnings
        if (warnings.length > 0) {
            const warningEl = document.createElement('div');
            warningEl.className = 'input-warning';
            warningEl.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${warnings[0]}`;
            feedback.appendChild(warningEl);
        }
        
        // Insert feedback
        promptInput.parentElement.appendChild(feedback);
    }
    
    getValidationSummary(validation) {
        if (validation.valid) {
            return {
                message: 'Input is valid',
                type: 'success'
            };
        }
        
        return {
            message: validation.allErrors.join(', '),
            type: 'error',
            errors: validation.allErrors,
            warnings: validation.allWarnings
        };
    }
}

// Global instance
const generatorInputValidator = new GeneratorInputValidator();

// Make available globally
if (typeof window !== 'undefined') {
    window.generatorInputValidator = generatorInputValidator;
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GeneratorInputValidator;
}

