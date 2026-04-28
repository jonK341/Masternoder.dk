/**
 * Enhanced Calendar with Appointments, Dates, and Game Keys
 * Includes secret keys that unlock generation features
 */

class EnhancedCalendar {
    constructor() {
        this.currentMonth = new Date();
        this.appointments = [];
        this.gameKeys = [];
        this.secretKeys = new Map(); // date -> key data
        this.initializeCalendar();
        this.loadAppointments();
        this.loadGameKeys();
    }
    
    initializeCalendar() {
        // Calendar initialization code
        const prevBtn = document.getElementById('prev-month');
        const nextBtn = document.getElementById('next-month');
        
        if (prevBtn) prevBtn.addEventListener('click', () => this.previousMonth());
        if (nextBtn) nextBtn.addEventListener('click', () => this.nextMonth());
        
        this.renderCalendar();
    }
    
    async loadAppointments() {
        // Load appointments from localStorage or API
        const stored = localStorage.getItem('calendar_appointments');
        if (stored) {
            this.appointments = JSON.parse(stored);
        } else {
            // Default appointments and useful dates
            this.appointments = [
                {
                    date: new Date().toISOString().split('T')[0],
                    title: 'Welcome!',
                    description: 'Start your video creation journey',
                    type: 'milestone',
                    icon: '🎬'
                },
                // Add more default appointments
                ...this.getDefaultAppointments()
            ];
            this.saveAppointments();
        }
        
        // Load monetization appointments
        await this.loadMonetizationAppointments();
    }
    
    getDefaultAppointments() {
        const today = new Date();
        const appointments = [];
        
        // Weekly milestones
        for (let i = 0; i < 4; i++) {
            const date = new Date(today);
            date.setDate(date.getDate() + (i * 7));
            appointments.push({
                date: date.toISOString().split('T')[0],
                title: `Week ${i + 1} Checkpoint`,
                description: 'Review your progress',
                type: 'planned',
                icon: '📅'
            });
        }
        
        // Monthly goals
        const nextMonth = new Date(today.getFullYear(), today.getMonth() + 1, 1);
        appointments.push({
            date: nextMonth.toISOString().split('T')[0],
            title: 'Monthly Goal',
            description: 'Set monthly video creation goal',
            type: 'milestone',
            icon: '🎯'
        });
        
        return appointments;
    }
    
    async loadMonetizationAppointments() {
        try {
            const response = await fetch('/vidgenerator/api/stats/calendar');
            const data = await response.json();
            
            if (data.appointments) {
                // Filter monetization appointments
                const monetizationApps = data.appointments.filter(app => 
                    app.category === 'monetization' || 
                    app.type === 'milestone' && app.phase ||
                    app.type === 'revenue' ||
                    app.type === 'workshop' && app.category === 'monetization'
                );
                
                // Add to appointments list
                this.appointments = [...this.appointments, ...monetizationApps];
                
                // Store monetization rewards
                if (data.monetization_rewards) {
                    this.monetizationRewards = data.monetization_rewards;
                }
            }
        } catch (error) {
            console.error('[Calendar] Error loading monetization appointments:', error);
        }
    }
    
    loadGameKeys() {
        // Load game keys that unlock secrets
        const stored = localStorage.getItem('calendar_game_keys');
        if (stored) {
            this.gameKeys = JSON.parse(stored);
        } else {
            // Default game keys
            this.gameKeys = this.generateGameKeys();
            this.saveGameKeys();
        }
        
        // Initialize secret keys map
        this.gameKeys.forEach(key => {
            this.secretKeys.set(key.date, key);
        });
        
        // Initialize monetization rewards
        this.monetizationRewards = {};
    }
    
    generateGameKeys() {
        const keys = [];
        const today = new Date();
        
        // Add level-based presents to calendar
        this.addLevelPresentsToCalendar(keys, today);
        
        // Add daily presents
        this.addDailyPresentsToCalendar(keys, today);
        
        // Generate keys for special dates
        const specialDates = [
            { date: new Date(today.getFullYear(), 0, 1), key: 'NEW_YEAR_BOOST', unlock: 'extra_clips' },
            { date: new Date(today.getFullYear(), 11, 25), key: 'CHRISTMAS_MAGIC', unlock: 'premium_theme' },
            { date: new Date(today.getFullYear(), today.getMonth(), 15), key: 'MID_MONTH_POWER', unlock: 'quality_boost' }
        ];
        
        // Add daily keys (unlock after completing videos)
        for (let i = 0; i < 30; i++) {
            const date = new Date(today);
            date.setDate(date.getDate() + i);
            keys.push({
                date: date.toISOString().split('T')[0],
                key: `DAILY_KEY_${i + 1}`,
                unlock: i % 3 === 0 ? 'extra_clips' : i % 3 === 1 ? 'faster_generation' : 'quality_boost',
                unlocked: false,
                requirement: `Complete ${i + 1} video${i > 0 ? 's' : ''}`
            });
        }
        
        return keys;
    }
    
    addLevelPresentsToCalendar(keys, today) {
        // Add presents for milestone levels
        const levelPresents = [
            { level: 5, date: this.getDateForLevel(5, today), present: 'level_5_present' },
            { level: 10, date: this.getDateForLevel(10, today), present: 'level_10_present' },
            { level: 15, date: this.getDateForLevel(15, today), present: 'level_15_present' },
            { level: 20, date: this.getDateForLevel(20, today), present: 'level_20_present' },
            { level: 25, date: this.getDateForLevel(25, today), present: 'level_25_present' },
            { level: 30, date: this.getDateForLevel(30, today), present: 'level_30_present' },
            { level: 50, date: this.getDateForLevel(50, today), present: 'level_50_present' }
        ];
        
        levelPresents.forEach(({ level, date, present }) => {
            keys.push({
                date: date.toISOString().split('T')[0],
                key: `LEVEL_${level}_PRESENT`,
                unlocks: {
                    present: present,
                    coins: level * 100,
                    premium_coins: level * 10,
                    message: `Level ${level} Milestone Present!`
                },
                requirement: `Reach Level ${level}`,
                unlocked: false
            });
        });
    }
    
    addDailyPresentsToCalendar(keys, today) {
        // Add daily present for next 30 days
        for (let i = 0; i < 30; i++) {
            const date = new Date(today);
            date.setDate(date.getDate() + i);
            
            keys.push({
                date: date.toISOString().split('T')[0],
                key: `DAILY_PRESENT_${i + 1}`,
                unlocks: {
                    present: 'daily_present',
                    coins: 50 + (i * 5), // Increasing daily rewards
                    premium_coins: 5,
                    message: `Daily Present Day ${i + 1}!`
                },
                requirement: 'Login daily',
                unlocked: false
            });
        }
    }
    
    getDateForLevel(level, baseDate) {
        // Estimate date when user might reach level
        // Assuming ~1000 XP per day average
        const xpNeeded = this.calculateXPForLevel(level);
        const daysNeeded = Math.ceil(xpNeeded / 1000);
        const date = new Date(baseDate);
        date.setDate(date.getDate() + daysNeeded);
        return date;
    }
    
    calculateXPForLevel(level) {
        let totalXP = 0;
        for (let i = 1; i < level; i++) {
            totalXP += Math.floor(1000 * Math.pow(1.5, i - 1));
        }
        return totalXP;
    }
    
    saveAppointments() {
        localStorage.setItem('calendar_appointments', JSON.stringify(this.appointments));
    }
    
    saveGameKeys() {
        localStorage.setItem('calendar_game_keys', JSON.stringify(this.gameKeys));
    }
    
    addAppointment(date, title, description, type = 'planned', icon = '📅') {
        const appointment = {
            date: date.toISOString().split('T')[0],
            title,
            description,
            type,
            icon
        };
        this.appointments.push(appointment);
        this.saveAppointments();
        this.renderCalendar();
    }
    
    unlockKey(date) {
        const key = this.secretKeys.get(date);
        if (key && !key.unlocked) {
            key.unlocked = true;
            this.saveGameKeys();
            this.renderCalendar();
            return key;
        }
        return null;
    }
    
    getUnlockedKeys() {
        return this.gameKeys.filter(k => k.unlocked);
    }
    
    getActiveUnlocks() {
        const unlocked = this.getUnlockedKeys();
        const unlocks = {
            extra_clips: 0,
            faster_generation: false,
            quality_boost: false,
            premium_theme: false
        };
        
        unlocked.forEach(key => {
            if (key.unlock === 'extra_clips') unlocks.extra_clips += 2;
            else if (key.unlock === 'faster_generation') unlocks.faster_generation = true;
            else if (key.unlock === 'quality_boost') unlocks.quality_boost = true;
            else if (key.unlock === 'premium_theme') unlocks.premium_theme = true;
        });
        
        return unlocks;
    }
    
    previousMonth() {
        this.currentMonth.setMonth(this.currentMonth.getMonth() - 1);
        this.renderCalendar();
    }
    
    nextMonth() {
        this.currentMonth.setMonth(this.currentMonth.getMonth() + 1);
        this.renderCalendar();
    }
    
    renderCalendar() {
        const grid = document.getElementById('calendar-grid');
        if (!grid) return;
        
        const year = this.currentMonth.getFullYear();
        const month = this.currentMonth.getMonth();
        
        // Update month display
        const monthDisplay = document.getElementById('current-month');
        if (monthDisplay) {
            monthDisplay.textContent = this.currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        }
        
        // Get first day of month and days in month
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        // Clear grid
        grid.innerHTML = '';
        
        // Add day labels
        const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        dayLabels.forEach(label => {
            const dayLabel = document.createElement('div');
            dayLabel.className = 'calendar-day-label';
            dayLabel.textContent = label;
            grid.appendChild(dayLabel);
        });
        
        // Add empty cells for days before month starts
        for (let i = 0; i < firstDay; i++) {
            const empty = document.createElement('div');
            empty.className = 'calendar-day empty';
            grid.appendChild(empty);
        }
        
        // Add days of month
        for (let day = 1; day <= daysInMonth; day++) {
            const dayCell = document.createElement('div');
            dayCell.className = 'calendar-day';
            
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const isToday = this.isToday(year, month, day);
            
            if (isToday) dayCell.classList.add('today');
            
            // Check for appointments
            const appointment = this.appointments.find(a => a.date === dateStr);
            if (appointment) {
                dayCell.classList.add(appointment.type);
                dayCell.innerHTML = `
                    <div class="day-number">${day}</div>
                    <div class="day-appointment">
                        <span class="appointment-icon">${appointment.icon}</span>
                        <span class="appointment-title">${appointment.title}</span>
                    </div>
                `;
                dayCell.title = appointment.description;
            } else {
                dayCell.innerHTML = `<div class="day-number">${day}</div>`;
            }
            
            // Check for game keys
            const key = this.secretKeys.get(dateStr);
            if (key) {
                if (key.unlocked) {
                    dayCell.classList.add('key-unlocked');
                    dayCell.innerHTML += `<div class="key-indicator">🔑</div>`;
                } else {
                    dayCell.classList.add('key-available');
                    dayCell.innerHTML += `<div class="key-indicator locked">🔒</div>`;
                }
                dayCell.title = key.requirement || 'Complete requirements to unlock';
            }
            
            // Add click handler
            dayCell.addEventListener('click', () => this.handleDayClick(dateStr, appointment, key));
            
            grid.appendChild(dayCell);
        }
    }
    
    isToday(year, month, day) {
        const today = new Date();
        return today.getFullYear() === year &&
               today.getMonth() === month &&
               today.getDate() === day;
    }
    
    handleDayClick(dateStr, appointment, key) {
        // Show day details modal
        const modal = this.createDayModal(dateStr, appointment, key);
        document.body.appendChild(modal);
    }
    
    createDayModal(dateStr, appointment, key) {
        const modal = document.createElement('div');
        modal.className = 'calendar-day-modal';
        
        // Check if appointment has rewards
        const hasRewards = appointment && appointment.reward;
        const reward = appointment?.reward || {};
        
        modal.innerHTML = `
            <div class="modal-content">
                <span class="modal-close">&times;</span>
                <h3>${new Date(dateStr).toLocaleDateString()}</h3>
                ${appointment ? `
                    <div class="modal-appointment ${appointment.category === 'monetization' ? 'monetization-appointment' : ''}">
                        <div class="appointment-header">
                            <h4>${appointment.icon || '📅'} ${appointment.title}</h4>
                            ${appointment.category === 'monetization' ? '<span class="monetization-badge">💰 Monetization</span>' : ''}
                            ${appointment.type === 'milestone' ? '<span class="milestone-badge">Milestone</span>' : ''}
                            ${appointment.type === 'revenue' ? '<span class="revenue-badge">Revenue</span>' : ''}
                        </div>
                        <p>${appointment.description}</p>
                        ${appointment.phase ? `<p class="appointment-phase">Phase: ${appointment.phase}</p>` : ''}
                        
                        ${hasRewards ? `
                            <div class="appointment-rewards">
                                <h5>🎁 Rewards:</h5>
                                <div class="rewards-list">
                                    ${reward.coins ? `<div class="reward-item"><i class="fas fa-coins"></i> ${reward.coins} Coins</div>` : ''}
                                    ${reward.xp ? `<div class="reward-item"><i class="fas fa-star"></i> ${reward.xp} XP</div>` : ''}
                                    ${reward.premium_coins ? `<div class="reward-item premium"><i class="fas fa-gem"></i> ${reward.premium_coins} Premium Coins</div>` : ''}
                                    ${reward.unlock ? `<div class="reward-item"><i class="fas fa-unlock"></i> Unlock: ${reward.unlock}</div>` : ''}
                                    ${reward.power_up ? `<div class="reward-item"><i class="fas fa-bolt"></i> Power-Up: ${reward.power_up}</div>` : ''}
                                    ${reward.subscription_discount ? `<div class="reward-item"><i class="fas fa-percent"></i> ${(reward.subscription_discount * 100)}% Subscription Discount</div>` : ''}
                                    ${reward.lifetime_discount ? `<div class="reward-item"><i class="fas fa-infinity"></i> ${(reward.lifetime_discount * 100)}% Lifetime Discount</div>` : ''}
                                    ${reward.lifetime_premium ? `<div class="reward-item"><i class="fas fa-crown"></i> Lifetime Premium Access</div>` : ''}
                                    ${reward.event_pass ? `<div class="reward-item"><i class="fas fa-ticket"></i> ${reward.event_pass} Free Event Pass</div>` : ''}
                                    ${reward.marketplace_credit ? `<div class="reward-item"><i class="fas fa-store"></i> $${reward.marketplace_credit} Marketplace Credit</div>` : ''}
                                    ${reward.api_credits ? `<div class="reward-item"><i class="fas fa-code"></i> ${reward.api_credits} API Credits</div>` : ''}
                                </div>
                                <button class="btn-claim-reward" onclick="window.enhancedCalendar.claimReward('${dateStr}', '${appointment.title}')">
                                    Claim Reward
                                </button>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
                ${key ? `
                    <div class="modal-key">
                        <h4>🔑 Game Key: ${key.key}</h4>
                        <p>${key.requirement || 'Complete to unlock'}</p>
                        ${key.unlocked ? `
                            <div class="key-unlocked-badge">✓ Unlocked: ${key.unlock}</div>
                        ` : `
                            <button class="unlock-key-btn" data-date="${dateStr}">Unlock Key</button>
                        `}
                    </div>
                ` : ''}
                <button class="add-appointment-btn" data-date="${dateStr}">Add Appointment</button>
            </div>
        `;
        
        modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
        modal.querySelector('.add-appointment-btn')?.addEventListener('click', () => {
            this.showAddAppointmentForm(dateStr);
            modal.remove();
        });
        modal.querySelector('.unlock-key-btn')?.addEventListener('click', (e) => {
            const date = e.target.dataset.date;
            this.attemptUnlockKey(date);
            modal.remove();
        });
        
        return modal;
    }
    
    showAddAppointmentForm(dateStr) {
        const title = prompt('Appointment Title:');
        if (title) {
            const description = prompt('Description:');
            this.addAppointment(new Date(dateStr), title, description || '');
        }
    }
    
    attemptUnlockKey(dateStr) {
        const key = this.secretKeys.get(dateStr);
        if (!key) return;
        
        // Check if requirements are met
        // In real implementation, check user stats
        const unlocked = this.unlockKey(dateStr);
        if (unlocked) {
            alert(`Key unlocked! You gained: ${unlocked.unlock}`);
            // Apply unlock to generation settings
            this.applyUnlock(unlocked.unlock);
        } else {
            alert(`Requirements not met: ${key.requirement}`);
        }
    }
    
    applyUnlock(unlockType) {
        // Apply unlock to generation settings
        const unlocks = this.getActiveUnlocks();
        localStorage.setItem('generation_unlocks', JSON.stringify(unlocks));
        
        // Notify generator if it's open
        if (window.generatorUnlocks) {
            window.generatorUnlocks.updateUnlocks(unlocks);
        }
    }
}

// Initialize calendar
let enhancedCalendar = null;
document.addEventListener('DOMContentLoaded', () => {
    enhancedCalendar = new EnhancedCalendar();
    window.enhancedCalendar = enhancedCalendar; // Make available globally
});

