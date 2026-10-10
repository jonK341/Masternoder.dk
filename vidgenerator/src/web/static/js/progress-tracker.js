/**
 * Automatic Progress Tracking System
 * Tracks todos, tasks, and system progress automatically
 */

class ProgressTracker {
    constructor() {
        this.todos = [];
        this.completedTasks = [];
        this.inProgressTasks = [];
        this.pendingTasks = [];
        this.stats = {
            total: 0,
            completed: 0,
            inProgress: 0,
            pending: 0,
            completionRate: 0
        };
        this.apiBase = window.location.origin;
        this.init();
    }
    
    async init() {
        await this.loadTodos();
        this.updateStats();
        this.renderProgress();
        this.startAutoUpdate();
    }
    
    async loadTodos() {
        try {
            // Try to load from localStorage first
            const stored = localStorage.getItem('progress_todos');
            if (stored) {
                this.todos = JSON.parse(stored);
                this.categorizeTasks();
                return;
            }
            
            // If no stored data, initialize with default todos
            this.initializeDefaultTodos();
        } catch (error) {
            console.error('[ProgressTracker] Error loading todos:', error);
            this.initializeDefaultTodos();
        }
    }
    
    initializeDefaultTodos() {
        this.todos = [
            { id: 'service_worker_enhance', content: 'Enhance Service Worker with better intelligence gathering and error handling', status: 'completed', category: 'backend' },
            { id: 'ai_improvements', content: 'Improve AI generation with better prompts, context, and fallbacks', status: 'completed', category: 'backend' },
            { id: 'ui_revamp', content: 'Revamp UI/UX for professional, user-friendly design', status: 'completed', category: 'frontend' },
            { id: 'auto_progress_system', content: 'Create automatic progress tracking through todos', status: 'in_progress', category: 'system' },
            { id: 'documentation_system', content: 'Create comprehensive documentation system for fixes and improvements', status: 'pending', category: 'system' },
            { id: 'theme_debugger_engine', content: 'Create theme debugger engine for all 12 themes with WWII special logic', status: 'completed', category: 'features' },
            { id: 'comprehensive_debugger', content: 'Create comprehensive debugger with enhanced options and migration analysis', status: 'completed', category: 'system' },
            { id: 'hunters_game', content: 'Create Hunters Game with theme logic and XP system', status: 'completed', category: 'features' },
            { id: 'landing_page_complete', content: 'Complete landing page with navigation, footer, dynamic content, and engagement', status: 'completed', category: 'frontend' },
            { id: 'fix_static_permissions', content: 'Fix permissions for static directories', status: 'completed', category: 'system' }
        ];
        this.saveTodos();
    }
    
    categorizeTasks() {
        this.completedTasks = this.todos.filter(t => t.status === 'completed');
        this.inProgressTasks = this.todos.filter(t => t.status === 'in_progress');
        this.pendingTasks = this.todos.filter(t => t.status === 'pending');
    }
    
    updateStats() {
        this.categorizeTasks();
        this.stats.total = this.todos.length;
        this.stats.completed = this.completedTasks.length;
        this.stats.inProgress = this.inProgressTasks.length;
        this.stats.pending = this.pendingTasks.length;
        this.stats.completionRate = this.stats.total > 0 
            ? Math.round((this.stats.completed / this.stats.total) * 100) 
            : 0;
    }
    
    saveTodos() {
        try {
            localStorage.setItem('progress_todos', JSON.stringify(this.todos));
        } catch (error) {
            console.error('[ProgressTracker] Error saving todos:', error);
        }
    }
    
    updateTaskStatus(taskId, newStatus) {
        const task = this.todos.find(t => t.id === taskId);
        if (task) {
            task.status = newStatus;
            task.updatedAt = new Date().toISOString();
            this.saveTodos();
            this.updateStats();
            this.renderProgress();
            return true;
        }
        return false;
    }
    
    addTask(content, category = 'general') {
        const newTask = {
            id: `task_${Date.now()}`,
            content: content,
            status: 'pending',
            category: category,
            createdAt: new Date().toISOString()
        };
        this.todos.push(newTask);
        this.saveTodos();
        this.updateStats();
        this.renderProgress();
        return newTask;
    }
    
    renderProgress() {
        const container = document.getElementById('progress-tracker');
        if (!container) return;
        
        container.innerHTML = `
            <div class="progress-tracker-container">
                <div class="progress-header">
                    <h3>📊 Progress Tracker</h3>
                    <div class="progress-stats">
                        <span class="stat-item">
                            <span class="stat-value">${this.stats.completionRate}%</span>
                            <span class="stat-label">Complete</span>
                        </span>
                        <span class="stat-item">
                            <span class="stat-value">${this.stats.completed}</span>
                            <span class="stat-label">Done</span>
                        </span>
                        <span class="stat-item">
                            <span class="stat-value">${this.stats.inProgress}</span>
                            <span class="stat-label">In Progress</span>
                        </span>
                        <span class="stat-item">
                            <span class="stat-value">${this.stats.pending}</span>
                            <span class="stat-label">Pending</span>
                        </span>
                    </div>
                </div>
                
                <div class="progress-bar-container">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${this.stats.completionRate}%"></div>
                    </div>
                    <div class="progress-text">${this.stats.completed} of ${this.stats.total} tasks completed</div>
                </div>
                
                <div class="progress-categories">
                    ${this.renderCategory('Backend', 'backend')}
                    ${this.renderCategory('Frontend', 'frontend')}
                    ${this.renderCategory('Features', 'features')}
                    ${this.renderCategory('System', 'system')}
                    ${this.renderCategory('General', 'general')}
                </div>
                
                <div class="progress-actions">
                    <button class="btn btn-sm" onclick="progressTracker.refresh()">🔄 Refresh</button>
                    <button class="btn btn-sm" onclick="progressTracker.export()">📥 Export</button>
                    <button class="btn btn-sm" onclick="progressTracker.clear()">🗑️ Clear</button>
                </div>
            </div>
        `;
    }
    
    renderCategory(title, category) {
        const categoryTasks = this.todos.filter(t => t.category === category);
        if (categoryTasks.length === 0) return '';
        
        const completed = categoryTasks.filter(t => t.status === 'completed').length;
        const inProgress = categoryTasks.filter(t => t.status === 'in_progress').length;
        const pending = categoryTasks.filter(t => t.status === 'pending').length;
        
        return `
            <div class="progress-category">
                <div class="category-header">
                    <h4>${title}</h4>
                    <span class="category-stats">${completed}/${categoryTasks.length} completed</span>
                </div>
                <div class="category-tasks">
                    ${categoryTasks.map(task => this.renderTask(task)).join('')}
                </div>
            </div>
        `;
    }
    
    renderTask(task) {
        const statusIcon = {
            'completed': '✅',
            'in_progress': '🔄',
            'pending': '⏳'
        }[task.status] || '⏳';
        
        const statusClass = `task-${task.status}`;
        
        return `
            <div class="progress-task ${statusClass}" data-task-id="${task.id}">
                <span class="task-icon">${statusIcon}</span>
                <span class="task-content">${task.content}</span>
                <div class="task-actions">
                    ${task.status !== 'completed' ? `
                        <button class="btn-icon" onclick="progressTracker.markComplete('${task.id}')" title="Mark Complete">✓</button>
                    ` : ''}
                    ${task.status !== 'in_progress' ? `
                        <button class="btn-icon" onclick="progressTracker.markInProgress('${task.id}')" title="Mark In Progress">🔄</button>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    markComplete(taskId) {
        this.updateTaskStatus(taskId, 'completed');
    }
    
    markInProgress(taskId) {
        this.updateTaskStatus(taskId, 'in_progress');
    }
    
    refresh() {
        this.loadTodos();
        this.updateStats();
        this.renderProgress();
    }
    
    export() {
        const data = {
            todos: this.todos,
            stats: this.stats,
            exportedAt: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `progress_${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
    
    clear() {
        if (confirm('Are you sure you want to clear all progress data?')) {
            localStorage.removeItem('progress_todos');
            this.todos = [];
            this.updateStats();
            this.renderProgress();
        }
    }
    
    startAutoUpdate() {
        // Update every 30 seconds
        setInterval(() => {
            this.updateStats();
            this.renderProgress();
        }, 30000);
    }
    
    // API integration for server-side tracking
    async syncWithServer() {
        try {
            const response = await fetch(`${this.apiBase}/vidgenerator/api/progress/sync`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    todos: this.todos,
                    stats: this.stats
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.todos) {
                    this.todos = data.todos;
                    this.saveTodos();
                    this.updateStats();
                    this.renderProgress();
                }
            }
        } catch (error) {
            console.error('[ProgressTracker] Error syncing with server:', error);
        }
    }
}

// Initialize global instance
let progressTracker;
document.addEventListener('DOMContentLoaded', () => {
    progressTracker = new ProgressTracker();
    window.progressTracker = progressTracker; // Make it globally available
});

