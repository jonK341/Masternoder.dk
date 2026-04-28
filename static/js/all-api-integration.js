/**
 * Complete API Integration for Frontend
 * All missing and queued API routes with onclick handlers
 */

const API_BASE = '/api';
const userId = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';

// Game Mechanics API
const GameMechanicsAPI = {
    async getSubjects(userId = 'default_user') {
        try {
            const response = await fetch(`${API_BASE}/game-mechanics/subjects?user_id=${userId}`);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching subjects:', error);
            return {success: false, error: error.message};
        }
    },
    
    async startSubject(userId, subjectId) {
        try {
            const response = await fetch(`${API_BASE}/game-mechanics/subject/start`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: userId, subject_id: subjectId})
            });
            return await response.json();
        } catch (error) {
            console.error('Error starting subject:', error);
            return {success: false, error: error.message};
        }
    },
    
    async useFunction(userId, subjectId, functionName, functionType = 'practical') {
        try {
            const response = await fetch(`${API_BASE}/game-mechanics/function/use`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: userId,
                    subject_id: subjectId,
                    function_name: functionName,
                    function_type: functionType
                })
            });
            return await response.json();
        } catch (error) {
            console.error('Error using function:', error);
            return {success: false, error: error.message};
        }
    },
    
    async completeSubject(userId, subjectId) {
        try {
            const response = await fetch(`${API_BASE}/game-mechanics/subject/complete`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: userId, subject_id: subjectId})
            });
            return await response.json();
        } catch (error) {
            console.error('Error completing subject:', error);
            return {success: false, error: error.message};
        }
    },
    
    async getProgress(userId = 'default_user') {
        try {
            const response = await fetch(`${API_BASE}/game-mechanics/progress?user_id=${userId}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching progress:', error);
            return {success: false, error: error.message};
        }
    }
};

// Ultra Resource API
const UltraResourceAPI = {
    async getEnergy(userId = 'default_user') {
        try {
            const response = await fetch(`${API_BASE}/ultra-resource/energy?user_id=${userId}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching energy:', error);
            return {success: false, error: error.message};
        }
    },
    
    async createNode(userId, nodeType, nodeData = {}) {
        try {
            const response = await fetch(`${API_BASE}/ultra-resource/node/create`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: userId,
                    node_type: nodeType,
                    node_data: nodeData
                })
            });
            return await response.json();
        } catch (error) {
            console.error('Error creating node:', error);
            return {success: false, error: error.message};
        }
    },
    
    async generateIncome(userId) {
        try {
            const response = await fetch(`${API_BASE}/ultra-resource/income/generate`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: userId})
            });
            return await response.json();
        } catch (error) {
            console.error('Error generating income:', error);
            return {success: false, error: error.message};
        }
    },
    
    async getSummary(userId = 'default_user') {
        try {
            const response = await fetch(`${API_BASE}/ultra-resource/summary?user_id=${userId}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching summary:', error);
            return {success: false, error: error.message};
        }
    }
};

// Enhanced Systems API
const EnhancedSystemsAPI = {
    async getAbilities(userId = 'default_user') {
        try {
            const response = await fetch(`${API_BASE}/skills/abilities?user_id=${userId}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching abilities:', error);
            return {success: false, error: error.message};
        }
    },
    
    async getPoints(userId = 'default_user') {
        try {
            const response = await fetch(`${API_BASE}/points/json/get?user_id=${userId}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching points:', error);
            return {success: false, error: error.message};
        }
    }
};

// New Systems API
const NewSystemsAPI = {
    async getCalendarEvents(userId = 'default_user') {
        try {
            const response = await fetch(`${API_BASE}/calendar/events?user_id=${userId}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching calendar events:', error);
            return {success: false, error: error.message};
        }
    },
    
    async listTodos(userId = 'default_user') {
        try {
            const response = await fetch(`${API_BASE}/todos/list?user_id=${userId}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching todos:', error);
            return {success: false, error: error.message};
        }
    },
    
    async getUserGroups(userId = 'default_user') {
        try {
            const response = await fetch(`${API_BASE}/groups/user?user_id=${userId}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching groups:', error);
            return {success: false, error: error.message};
        }
    }
};

// Frontend Integration Functions with onclick handlers
function initAPIIntegration() {
    // Add onclick handlers to existing elements
    document.addEventListener('DOMContentLoaded', function() {
        // Game Mechanics Integration
        const gameMechanicsBtn = document.getElementById('game-mechanics-btn');
        if (gameMechanicsBtn) {
            gameMechanicsBtn.onclick = async function() {
                const progress = await GameMechanicsAPI.getProgress(userId);
                if (progress.success) {
                    showNotification('Game Mechanics Progress Loaded', 'success');
                    updateGameMechanicsDisplay(progress);
                }
            };
        }
        
        // Ultra Resource Integration
        const energyBtn = document.getElementById('energy-status-btn');
        if (energyBtn) {
            energyBtn.onclick = async function() {
                const energy = await UltraResourceAPI.getEnergy(userId);
                if (energy.success) {
                    showNotification('Energy Status Updated', 'success');
                    updateEnergyDisplay(energy);
                }
            };
        }
        
        // Calendar Integration
        const calendarBtn = document.getElementById('calendar-events-btn');
        if (calendarBtn) {
            calendarBtn.onclick = async function() {
                const events = await NewSystemsAPI.getCalendarEvents(userId);
                if (events.success) {
                    showNotification('Calendar Events Loaded', 'success');
                    updateCalendarDisplay(events);
                }
            };
        }
        
        // Todos Integration
        const todosBtn = document.getElementById('todos-list-btn');
        if (todosBtn) {
            todosBtn.onclick = async function() {
                const todos = await NewSystemsAPI.listTodos(userId);
                if (todos.success) {
                    showNotification('Todos Loaded', 'success');
                    updateTodosDisplay(todos);
                }
            };
        }
    });
}

// Display update functions
function updateGameMechanicsDisplay(progress) {
    const display = document.getElementById('game-mechanics-display');
    if (display && progress.data) {
        display.innerHTML = `
            <div class="progress-summary">
                <h3>Game Mechanics Progress</h3>
                <p>Subjects Completed: ${progress.data.completed_subjects || 0}</p>
                <p>Total Progress: ${progress.data.total_progress || 0}%</p>
            </div>
        `;
    }
}

function updateEnergyDisplay(energy) {
    const display = document.getElementById('energy-display');
    if (display && energy.energy) {
        display.innerHTML = `
            <div class="energy-status">
                <h3>Energy Status</h3>
                <p>Mind: ${energy.energy.mind || 0}/100</p>
                <p>Power: ${energy.energy.power || 0}/100</p>
                <p>Time: ${energy.energy.time || 0}/100</p>
                <p>Place: ${energy.energy.place || 0}/100</p>
                <p>Total: ${energy.total_energy || 0}/${energy.max_total || 400}</p>
            </div>
        `;
    }
}

function updateCalendarDisplay(events) {
    const display = document.getElementById('calendar-display');
    if (display && events.events) {
        let html = '<div class="calendar-events"><h3>Upcoming Events</h3><ul>';
        events.events.slice(0, 5).forEach(event => {
            html += `<li>${event.title || 'Event'} - ${event.date || 'TBD'}</li>`;
        });
        html += '</ul></div>';
        display.innerHTML = html;
    }
}

function updateTodosDisplay(todos) {
    const display = document.getElementById('todos-display');
    if (display && todos.todos) {
        let html = '<div class="todos-list"><h3>Your Todos</h3><ul>';
        todos.todos.slice(0, 5).forEach(todo => {
            const status = todo.status || 'pending';
            html += `<li class="todo-${status}">${todo.title || 'Todo'} - ${status}</li>`;
        });
        html += '</ul></div>';
        display.innerHTML = html;
    }
}

function showNotification(message, type = 'info') {
    // Use existing toast notification system if available
    if (window.showToast) {
        window.showToast(message, type);
    } else {
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}

// Export for global use
if (typeof window !== 'undefined') {
    window.GameMechanicsAPI = GameMechanicsAPI;
    window.UltraResourceAPI = UltraResourceAPI;
    window.EnhancedSystemsAPI = EnhancedSystemsAPI;
    window.NewSystemsAPI = NewSystemsAPI;
    window.initAPIIntegration = initAPIIntegration;
}

// Auto-initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAPIIntegration);
} else {
    initAPIIntegration();
}

