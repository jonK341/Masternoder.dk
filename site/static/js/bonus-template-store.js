/**
 * Bonus Template Store
 * Client-side integration for bonus template store
 */
class BonusTemplateStore {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl || window.location.origin;
        this.userId = localStorage.getItem('game_user_id') || 'default_user';
        this.init();
    }

    init() {
        // Load user's owned templates
        this.loadOwnedTemplates();
    }

    async loadOwnedTemplates() {
        try {
            const response = await fetch(`${this.baseUrl}/api/templates/store/user/${this.userId}/owned`);
            const data = await response.json();
            if (data.success) {
                this.ownedTemplates = data.templates.map(t => t.id);
                return data.templates;
            }
            return [];
        } catch (error) {
            console.error('Error loading owned templates:', error);
            return [];
        }
    }

    async listTemplates() {
        try {
            const response = await fetch(`${this.baseUrl}/api/templates/store/list?user_id=${this.userId}`);
            const data = await response.json();
            if (data.success) {
                return data.templates;
            }
            return [];
        } catch (error) {
            console.error('Error listing templates:', error);
            return [];
        }
    }

    async getTemplate(templateId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/templates/store/${templateId}?user_id=${this.userId}`);
            const data = await response.json();
            if (data.success) {
                return data.template;
            }
            return null;
        } catch (error) {
            console.error('Error getting template:', error);
            return null;
        }
    }

    async purchaseTemplate(templateId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/templates/store/${templateId}/purchase`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.userId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Reload owned templates
                await this.loadOwnedTemplates();
                
                // Show success notification
                this.showNotification('success', data.message || 'Template purchased successfully!');
                
                return data;
            } else {
                // Handle downscale errors
                if (data.error_type === 'network_instability') {
                    this.showNotification('error', data.error + ' Retrying in ' + (data.retry_after || 5) + ' seconds...');
                    // Auto-retry after delay
                    setTimeout(() => this.purchaseTemplate(templateId), (data.retry_after || 5) * 1000);
                } else if (data.error_type === 'insufficient_funds') {
                    this.showNotification('warning', data.error);
                } else {
                    this.showNotification('error', data.error || 'Purchase failed');
                }
                
                return data;
            }
        } catch (error) {
            console.error('Error purchasing template:', error);
            this.showNotification('error', 'Network error. Please try again.');
            return { success: false, error: error.message };
        }
    }

    async applyTemplate(templateId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/templates/store/user/${this.userId}/apply/${templateId}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('success', data.message || 'Template applied successfully!');
                
                // Reload page to apply template
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
                
                return data;
            } else {
                this.showNotification('error', data.error || 'Failed to apply template');
                return data;
            }
        } catch (error) {
            console.error('Error applying template:', error);
            this.showNotification('error', 'Network error. Please try again.');
            return { success: false, error: error.message };
        }
    }

    showNotification(type, message) {
        const notification = document.createElement('div');
        notification.className = `template-notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => notification.classList.add('show'), 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    renderStore(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        this.listTemplates().then(templates => {
            container.innerHTML = `
                <div class="template-store-header">
                    <h2>Bonus Template Store</h2>
                    <p>Premium templates with exclusive features and effects</p>
                </div>
                <div class="template-store-grid">
                    ${templates.map(template => this.renderTemplateCard(template)).join('')}
                </div>
            `;

            // Add event listeners
            container.querySelectorAll('.purchase-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const templateId = e.target.dataset.templateId;
                    this.handlePurchase(templateId, e.target);
                });
            });

            container.querySelectorAll('.apply-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const templateId = e.target.dataset.templateId;
                    this.applyTemplate(templateId);
                });
            });
        });
    }

    renderTemplateCard(template) {
        const owned = template.owned || false;
        
        return `
            <div class="template-card ${owned ? 'owned' : ''}">
                <div class="template-preview">
                    <img src="${template.preview_image}" alt="${template.name}" onerror="this.src='/static/img/placeholder.png'">
                    ${owned ? '<div class="owned-badge">✓ Owned</div>' : ''}
                </div>
                <div class="template-info">
                    <h3>${template.name}</h3>
                    <p class="template-description">${template.description}</p>
                    <div class="template-features">
                        ${template.features.map(f => `<span class="feature-tag">${f}</span>`).join('')}
                    </div>
                    <div class="template-price">
                        ${owned ? 
                            `<button class="apply-btn" data-template-id="${template.id}">Apply Template</button>` :
                            `<div class="price">${template.price} points</div>
                             <button class="purchase-btn" data-template-id="${template.id}">Purchase</button>`
                        }
                    </div>
                </div>
            </div>
        `;
    }

    async handlePurchase(templateId, button) {
        const originalText = button.textContent;
        button.textContent = 'Processing...';
        button.disabled = true;

        const result = await this.purchaseTemplate(templateId);

        if (result.success) {
            // Reload store
            this.renderStore(button.closest('.template-store-grid').parentElement.id);
        } else {
            button.textContent = originalText;
            button.disabled = false;
        }
    }
}

// Initialize bonus template store
window.bonusTemplateStore = new BonusTemplateStore();
