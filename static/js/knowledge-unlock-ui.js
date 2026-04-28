/**
 * Knowledge Unlock UI
 * UI for unlocking knowledge nodes in the tech tree
 */
class KnowledgeUnlockUI {
    constructor() {
        this.baseURL = '/api/knowledge';
        this.userId = this.getUserId();
        this.knowledgeNodes = [];
    }

    getUserId() {
        const stored = localStorage.getItem('user_id');
        if (stored) return stored;
        return 'default_user';
    }

    /**
     * Load user knowledge
     */
    async loadUserKnowledge() {
        try {
            const response = await fetch(`${this.baseURL}/user?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.success) {
                this.knowledgeNodes = data.knowledge_nodes || [];
                this.renderKnowledgeTree();
                return data;
            }
        } catch (error) {
            console.error('Error loading knowledge:', error);
            return {success: false, error: error.message};
        }
    }

    /**
     * Unlock knowledge node
     */
    async unlockKnowledge(knowledgeId) {
        try {
            const response = await fetch(`${this.baseURL}/unlock`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.userId,
                    knowledge_id: knowledgeId
                })
            });
            const data = await response.json();
            
            if (data.success) {
                // Show unlock animation
                this.showUnlockAnimation(knowledgeId);
                // Reload knowledge
                await this.loadUserKnowledge();
                return data;
            } else {
                this.showError(data.error || 'Failed to unlock knowledge');
                return data;
            }
        } catch (error) {
            console.error('Error unlocking knowledge:', error);
            this.showError(error.message);
            return {success: false, error: error.message};
        }
    }

    /**
     * Render knowledge tree
     */
    renderKnowledgeTree() {
        const container = document.getElementById('knowledge-tree-container');
        if (!container) return;

        let html = '<div class="knowledge-tree-grid">';
        
        this.knowledgeNodes.forEach(node => {
            const isUnlocked = node.unlocked || false;
            const canUnlock = this.canUnlock(node);
            
            html += `
                <div class="knowledge-node ${isUnlocked ? 'unlocked' : 'locked'} ${canUnlock ? 'can-unlock' : ''}" 
                     data-node-id="${node.node_id}">
                    <div class="node-header">
                        <div class="node-icon">${isUnlocked ? '✅' : '🔒'}</div>
                        <div class="node-title">${node.name || node.node_id}</div>
                    </div>
                    <div class="node-description">${node.description || ''}</div>
                    ${node.prerequisites && node.prerequisites.length > 0 ? `
                        <div class="node-prerequisites">
                            <strong>Prerequisites:</strong>
                            <ul>
                                ${node.prerequisites.map(prereq => `
                                    <li class="${this.isPrerequisiteMet(prereq) ? 'met' : 'not-met'}">
                                        ${prereq}
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    <div class="node-actions">
                        ${!isUnlocked && canUnlock ? `
                            <button class="unlock-btn" onclick="knowledgeUnlockUI.unlockKnowledge('${node.node_id}')">
                                Unlock (${node.knowledge_points_cost || 0} KP)
                            </button>
                        ` : isUnlocked ? `
                            <span class="unlocked-badge">Unlocked</span>
                        ` : `
                            <span class="locked-badge">Locked</span>
                        `}
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        container.innerHTML = html;
    }

    /**
     * Check if node can be unlocked
     */
    canUnlock(node) {
        if (node.unlocked) return false;
        
        // Check prerequisites
        if (node.prerequisites && node.prerequisites.length > 0) {
            return node.prerequisites.every(prereq => this.isPrerequisiteMet(prereq));
        }
        
        return true;
    }

    /**
     * Check if prerequisite is met
     */
    isPrerequisiteMet(prereq) {
        const prereqNode = this.knowledgeNodes.find(n => 
            n.node_id === prereq || n.name === prereq
        );
        return prereqNode && prereqNode.unlocked;
    }

    /**
     * Show unlock animation
     */
    showUnlockAnimation(knowledgeId) {
        const node = document.querySelector(`[data-node-id="${knowledgeId}"]`);
        if (!node) return;

        // Add animation class
        node.classList.add('unlocking');
        
        // Create particle effect
        this.createParticleEffect(node);
        
        // Remove animation class after animation
        setTimeout(() => {
            node.classList.remove('unlocking');
            node.classList.add('unlocked');
        }, 1000);
    }

    /**
     * Create particle effect
     */
    createParticleEffect(element) {
        const rect = element.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        
        for (let i = 0; i < 20; i++) {
            const particle = document.createElement('div');
            particle.className = 'knowledge-particle';
            particle.style.cssText = `
                position: fixed;
                left: ${centerX}px;
                top: ${centerY}px;
                width: 8px;
                height: 8px;
                background: #00ff88;
                border-radius: 50%;
                pointer-events: none;
                z-index: 10000;
                animation: particle-float-${i} 1s ease-out forwards;
            `;
            
            const angle = (Math.PI * 2 * i) / 20;
            const distance = 50 + Math.random() * 50;
            const x = Math.cos(angle) * distance;
            const y = Math.sin(angle) * distance;
            
            const style = document.createElement('style');
            style.textContent = `
                @keyframes particle-float-${i} {
                    to {
                        transform: translate(${x}px, ${y}px);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
            
            document.body.appendChild(particle);
            setTimeout(() => particle.remove(), 1000);
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        const notification = document.createElement('div');
        notification.className = 'knowledge-error-notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255, 68, 68, 0.9);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            z-index: 10000;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.3s';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Global instance
const knowledgeUnlockUI = new KnowledgeUnlockUI();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        knowledgeUnlockUI.loadUserKnowledge();
    });
} else {
    knowledgeUnlockUI.loadUserKnowledge();
}

