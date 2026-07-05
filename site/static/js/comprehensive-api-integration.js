/**
 * Comprehensive API Integration
 * Handles all API calls with onclick handlers and error management
 */

class ComprehensiveAPI {
    constructor() {
        this.baseURL = '/api';
        this.userId = this.getUserId();
        this.errorHandlers = [];
    }

    getUserId() {
        // Try to get user ID from various sources
        const stored = localStorage.getItem('game_user_id') || localStorage.getItem('user_id');
        if (stored) return stored;
        
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('user_id')) return urlParams.get('user_id');
        
        return 'default_user';
    }

    /**
     * Make API call with error handling
     */
    async call(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                }
            };

            if (data && (method === 'POST' || method === 'PUT')) {
                options.body = JSON.stringify(data);
            }

            const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;
            const response = await fetch(url, options);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            return { success: true, data: result };
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            this.handleError(error, endpoint);
            return { success: false, error: error.message };
        }
    }

    handleError(error, endpoint) {
        // Call all registered error handlers
        this.errorHandlers.forEach(handler => {
            try {
                handler(error, endpoint);
            } catch (e) {
                console.error('Error handler failed:', e);
            }
        });
    }

    onError(handler) {
        this.errorHandlers.push(handler);
    }

    // ========================================================================
    // GAME MECHANICS API
    // ========================================================================

    async getSubjects() {
        return await this.call('/game-mechanics/subjects?user_id=' + this.userId);
    }

    async startSubject(subjectId) {
        return await this.call('/game-mechanics/subject/start', 'POST', {
            user_id: this.userId,
            subject_id: subjectId
        });
    }

    async useFunction(subjectId, functionName, functionType = 'practical') {
        return await this.call('/game-mechanics/function/use', 'POST', {
            user_id: this.userId,
            subject_id: subjectId,
            function_name: functionName,
            function_type: functionType
        });
    }

    async completeSubject(subjectId) {
        return await this.call('/game-mechanics/subject/complete', 'POST', {
            user_id: this.userId,
            subject_id: subjectId
        });
    }

    async getProgress() {
        return await this.call('/game-mechanics/progress?user_id=' + this.userId);
    }

    // ========================================================================
    // ULTRA RESOURCE CONTROLLER API
    // ========================================================================

    async getEnergyStatus() {
        return await this.call('/ultra-resource/energy?user_id=' + this.userId);
    }

    async createNode(nodeType, nodeData = {}) {
        return await this.call('/ultra-resource/node/create', 'POST', {
            user_id: this.userId,
            node_type: nodeType,
            node_data: nodeData
        });
    }

    async generatePassiveIncome() {
        return await this.call('/ultra-resource/income/generate', 'POST', {
            user_id: this.userId
        });
    }

    async createModularContent(contentData = {}) {
        return await this.call('/ultra-resource/content/create', 'POST', {
            user_id: this.userId,
            content_data: contentData
        });
    }

    async getResourceSummary() {
        return await this.call('/ultra-resource/summary?user_id=' + this.userId);
    }

    // ========================================================================
    // ENHANCED SYSTEMS API
    // ========================================================================

    async getTechTreeWithQuests(techId = null) {
        const url = techId 
            ? `/tech-tree/with-quests?user_id=${this.userId}&tech_id=${techId}`
            : `/tech-tree/with-quests?user_id=${this.userId}`;
        return await this.call(url);
    }

    async getAllAbilities() {
        return await this.call('/skills/abilities');
    }

    async unlockAbility(abilityId, questId = null) {
        return await this.call('/skills/unlock', 'POST', {
            user_id: this.userId,
            ability_id: abilityId,
            quest_id: questId
        });
    }

    async getUserAbilities() {
        return await this.call(`/skills/user?user_id=${this.userId}`);
    }

    async getPointsJSON(forceRefresh = false) {
        return await this.call(`/points/json/get?user_id=${this.userId}&force_refresh=${forceRefresh}`);
    }

    async incrementPoint(pointType, amount = 1) {
        return await this.call('/points/json/increment', 'POST', {
            user_id: this.userId,
            point_type: pointType,
            amount: amount
        });
    }

    // ========================================================================
    // NEW SYSTEMS API
    // ========================================================================

    async recordCompletion(taskType, taskId = null, completionData = {}) {
        return await this.call('/skill-reward/complete', 'POST', {
            user_id: this.userId,
            task_type: taskType,
            task_id: taskId || this.generateId(),
            completion_data: completionData
        });
    }

    async createCalendarPlan(planName, planData = {}) {
        return await this.call('/calendar/plan/create', 'POST', {
            user_id: this.userId,
            plan_name: planName,
            plan_data: planData
        });
    }

    async scheduleTask(taskData, agentId = null) {
        return await this.call('/calendar/task/schedule', 'POST', {
            user_id: this.userId,
            task_data: taskData,
            agent_id: agentId
        });
    }

    async getCalendarEvents(startDate = null, endDate = null) {
        let url = `/calendar/events?user_id=${this.userId}`;
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;
        return await this.call(url);
    }

    async createGroup(groupName, groupData = {}) {
        return await this.call('/groups/create', 'POST', {
            user_id: this.userId,
            group_name: groupName,
            group_data: groupData
        });
    }

    async joinGroup(groupId) {
        return await this.call('/groups/join', 'POST', {
            user_id: this.userId,
            group_id: groupId
        });
    }

    async scanBehavior(scanType = 'full') {
        return await this.call('/scanner/scan', 'POST', {
            user_id: this.userId,
            scan_type: scanType
        });
    }

    async getEfficiencyReport() {
        return await this.call(`/scanner/efficiency?user_id=${this.userId}`);
    }

    async getDecisionRecommendation(context = {}) {
        return await this.call('/decision-trees/recommendation', 'POST', {
            user_id: this.userId,
            context: context
        });
    }

    async createTodo(todoData = {}) {
        return await this.call('/todos/create', 'POST', {
            user_id: this.userId,
            todo_data: todoData
        });
    }

    async pauseTodo(todoId, reason = null) {
        return await this.call('/todos/pause', 'POST', {
            user_id: this.userId,
            todo_id: todoId,
            reason: reason
        });
    }

    async resumeTodo(todoId) {
        return await this.call('/todos/resume', 'POST', {
            user_id: this.userId,
            todo_id: todoId
        });
    }

    async completeTodo(todoId) {
        return await this.call('/todos/complete', 'POST', {
            user_id: this.userId,
            todo_id: todoId
        });
    }

    async getTodos(status = null) {
        let url = `/todos/list?user_id=${this.userId}`;
        if (status) url += `&status=${status}`;
        return await this.call(url);
    }

    // ========================================================================
    // FRONTEND INTEGRATION
    // ========================================================================

    async getQuickActions() {
        return await this.call('/comprehensive/frontend/quick-actions?user_id=' + this.userId);
    }

    async getNavigationLinks() {
        return await this.call('/comprehensive/frontend/navigation-links');
    }

    generateId() {
        return 'id_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
}

// Create global instance
window.comprehensiveAPI = new ComprehensiveAPI();

// Add default error handler
window.comprehensiveAPI.onError((error, endpoint) => {
    console.error(`API call failed: ${endpoint}`, error);
    // You can add toast notifications here
    if (window.showToast) {
        window.showToast(`API Error: ${error.message}`, 'error');
    }
});

// ========================================================================
// ONCLICK HANDLERS
// ========================================================================

/**
 * Setup onclick handlers for all API buttons
 */
function setupAPIHandlers() {
    // Game Mechanics handlers
    document.querySelectorAll('[data-api="start-subject"]').forEach(btn => {
        btn.onclick = async () => {
            const subjectId = btn.getAttribute('data-subject-id');
            const result = await window.comprehensiveAPI.startSubject(subjectId);
            if (result.success) {
                if (window.showToast) window.showToast('Subject started!', 'success');
            }
        };
    });

    document.querySelectorAll('[data-api="complete-subject"]').forEach(btn => {
        btn.onclick = async () => {
            const subjectId = btn.getAttribute('data-subject-id');
            const result = await window.comprehensiveAPI.completeSubject(subjectId);
            if (result.success) {
                if (window.showToast) window.showToast('Subject completed!', 'success');
            }
        };
    });

    // Ultra Resource handlers
    document.querySelectorAll('[data-api="check-energy"]').forEach(btn => {
        btn.onclick = async () => {
            const result = await window.comprehensiveAPI.getEnergyStatus();
            if (result.success && result.data) {
                console.log('Energy Status:', result.data);
                // Update UI with energy data
                updateEnergyDisplay(result.data);
            }
        };
    });

    document.querySelectorAll('[data-api="create-node"]').forEach(btn => {
        btn.onclick = async () => {
            const nodeType = btn.getAttribute('data-node-type') || 'affiliate';
            const result = await window.comprehensiveAPI.createNode(nodeType);
            if (result.success) {
                if (window.showToast) window.showToast('Node created!', 'success');
            }
        };
    });

    // Skills handlers
    document.querySelectorAll('[data-api="view-skills"]').forEach(btn => {
        btn.onclick = async () => {
            const result = await window.comprehensiveAPI.getAllAbilities();
            if (result.success && result.data) {
                displaySkills(result.data);
            }
        };
    });

    // Todos handlers
    document.querySelectorAll('[data-api="create-todo"]').forEach(btn => {
        btn.onclick = async () => {
            const todoText = prompt('Enter todo text:');
            if (todoText) {
                const result = await window.comprehensiveAPI.createTodo({
                    text: todoText,
                    priority: 'medium'
                });
                if (result.success) {
                    if (window.showToast) window.showToast('Todo created!', 'success');
                }
            }
        };
    });

    // Scanner handlers
    document.querySelectorAll('[data-api="scan-behavior"]').forEach(btn => {
        btn.onclick = async () => {
            const result = await window.comprehensiveAPI.scanBehavior();
            if (result.success && result.data) {
                displayScanResults(result.data);
            }
        };
    });

    // Calendar handlers
    document.querySelectorAll('[data-api="view-calendar"]').forEach(btn => {
        btn.onclick = async () => {
            const result = await window.comprehensiveAPI.getCalendarEvents();
            if (result.success && result.data) {
                displayCalendarEvents(result.data);
            }
        };
    });
}

/**
 * Update energy display
 */
function updateEnergyDisplay(energyData) {
    const energy = energyData.energy || {};
    document.querySelectorAll('[data-energy="mind"]').forEach(el => {
        el.textContent = energy.mind || 0;
    });
    document.querySelectorAll('[data-energy="power"]').forEach(el => {
        el.textContent = energy.power || 0;
    });
    document.querySelectorAll('[data-energy="time"]').forEach(el => {
        el.textContent = energy.time || 0;
    });
    document.querySelectorAll('[data-energy="place"]').forEach(el => {
        el.textContent = energy.place || 0;
    });
}

/**
 * Display skills
 */
function displaySkills(skillsData) {
    // Implementation for displaying skills
    console.log('Skills:', skillsData);
}

/**
 * Display scan results
 */
function displayScanResults(scanData) {
    // Implementation for displaying scan results
    console.log('Scan Results:', scanData);
}

/**
 * Display calendar events
 */
function displayCalendarEvents(eventsData) {
    // Implementation for displaying calendar events
    console.log('Calendar Events:', eventsData);
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupAPIHandlers);
} else {
    setupAPIHandlers();
}

