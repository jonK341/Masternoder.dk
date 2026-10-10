/**
 * Enhanced Stats Page JavaScript
 * Trophy Hunter, Calendar, Milestones, XP, High Scores
 */

(function() {
    'use strict';
    
    // State
    let currentWeek = getCurrentWeek();
    let currentMonth = new Date();
    let userStats = {
        xp: 0,
        level: 1,
        trophies: [],
        milestones: [],
        highScores: {}
    };
    
    // Initialize
    document.addEventListener('DOMContentLoaded', () => {
        loadUserProfile();
        loadTrophies();
        loadMilestones();
        loadXPAndScores();
        loadStatistics();
        initializeCalendar();
        initializeWeekSelector();
    });
    
    // Get current week (Monday to Sunday)
    function getCurrentWeek() {
        const now = new Date();
        const day = now.getDay();
        const diff = now.getDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
        const monday = new Date(now.setDate(diff));
        return monday;
    }
    
    // Load User Profile
    async function loadUserProfile() {
        try {
            const response = await fetch('/vidgenerator/api/stats/profile');
            if (response.ok) {
                const data = await response.json();
                userStats = data;
                updateProfileDisplay();
            }
        } catch (error) {
            console.error('Failed to load profile:', error);
        }
    }
    
    // Update Profile Display
    function updateProfileDisplay() {
        document.getElementById('user-name').textContent = userStats.name || 'User';
        document.getElementById('user-title').textContent = userStats.title || 'Novice Creator';
        document.getElementById('user-level').textContent = userStats.level || 1;
        document.getElementById('user-xp').textContent = formatNumber(userStats.xp || 0);
        document.getElementById('user-high-score').textContent = formatNumber(userStats.highScores?.total || 0);
    }
    
    // Load Trophies
    async function loadTrophies() {
        try {
            const response = await fetch(`/vidgenerator/api/stats/trophies?week=${currentWeek.toISOString()}`);
            if (response.ok) {
                const data = await response.json();
                displayTrophies(data.weekly || [], 'weekly-trophies');
                displayTrophies(data.allTime || [], 'all-time-trophies');
            }
        } catch (error) {
            console.error('Failed to load trophies:', error);
        }
    }
    
    // Display Trophies
    function displayTrophies(trophies, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        if (trophies.length === 0) {
            container.innerHTML = '<p class="no-trophies">No trophies yet. Keep creating!</p>';
            return;
        }
        
        container.innerHTML = trophies.map(trophy => `
            <div class="trophy-item ${trophy.earned ? 'earned' : 'locked'}">
                <div class="trophy-icon">${trophy.icon || '🏆'}</div>
                <div class="trophy-info">
                    <h4>${trophy.name}</h4>
                    <p>${trophy.description}</p>
                    ${trophy.earned ? `<span class="trophy-date">Earned: ${formatDate(trophy.earnedDate)}</span>` : ''}
                </div>
                ${trophy.xpReward ? `<div class="trophy-xp">+${trophy.xpReward} XP</div>` : ''}
            </div>
        `).join('');
    }
    
    // Load Milestones
    async function loadMilestones() {
        try {
            const response = await fetch('/vidgenerator/api/stats/milestones');
            if (response.ok) {
                const data = await response.json();
                displayMilestones(data);
            }
        } catch (error) {
            console.error('Failed to load milestones:', error);
        }
    }
    
    // Display Milestones
    function displayMilestones(data) {
        const container = document.getElementById('milestones-list');
        if (!container) return;
        
        const milestones = data.milestones || [];
        const progress = data.progress || 0;
        
        // Update progress bar
        const progressBar = document.getElementById('milestone-progress');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        
        container.innerHTML = milestones.map((milestone, index) => `
            <div class="milestone-item ${milestone.completed ? 'completed' : milestone.unlocked ? 'unlocked' : 'locked'}">
                <div class="milestone-number">${index + 1}</div>
                <div class="milestone-content">
                    <h4>${milestone.name}</h4>
                    <p>${milestone.description}</p>
                    ${milestone.reward ? `<span class="milestone-reward">Reward: ${milestone.reward}</span>` : ''}
                </div>
                ${milestone.completed ? '<div class="milestone-check">✓</div>' : ''}
            </div>
        `).join('');
    }
    
    // Load XP and High Scores
    async function loadXPAndScores() {
        try {
            const response = await fetch('/vidgenerator/api/stats/xp-scores');
            if (response.ok) {
                const data = await response.json();
                updateXPDisplay(data.xp || {});
                updateHighScores(data.highScores || {});
            }
        } catch (error) {
            console.error('Failed to load XP and scores:', error);
        }
    }
    
    // Update XP Display
    function updateXPDisplay(xpData) {
        document.getElementById('total-xp').textContent = formatNumber(xpData.total || 0);
        document.getElementById('xp-generations').textContent = formatNumber(xpData.fromGenerations || 0);
        document.getElementById('xp-trophies').textContent = formatNumber(xpData.fromTrophies || 0);
        document.getElementById('xp-milestones').textContent = formatNumber(xpData.fromMilestones || 0);
    }
    
    // Update High Scores
    function updateHighScores(scores) {
        document.getElementById('highscore-quality').textContent = (scores.bestQuality || 0).toFixed(1);
        document.getElementById('highscore-duration').textContent = formatDuration(scores.longestVideo || 0);
        document.getElementById('highscore-clips').textContent = scores.mostClips || 0;
        document.getElementById('highscore-speed').textContent = scores.fastestGeneration || '--';
    }
    
    // Load Statistics
    async function loadStatistics() {
        try {
            const response = await fetch('/vidgenerator/api/statistics');
            if (response.ok) {
                const data = await response.json();
                const stats = data.statistics || {};
                document.getElementById('total-documentaries').textContent = stats.total_documentaries || 0;
                document.getElementById('total-duration').textContent = formatDuration(stats.total_duration || 0);
                document.getElementById('avg-quality').textContent = (stats.avg_quality || 0).toFixed(1);
                document.getElementById('total-trophies').textContent = stats.total_trophies || 0;
            }
        } catch (error) {
            console.error('Failed to load statistics:', error);
        }
    }
    
    // Initialize Calendar
    function initializeCalendar() {
        renderCalendar();
        
        document.getElementById('prev-month')?.addEventListener('click', () => {
            currentMonth.setMonth(currentMonth.getMonth() - 1);
            renderCalendar();
        });
        
        document.getElementById('next-month')?.addEventListener('click', () => {
            currentMonth.setMonth(currentMonth.getMonth() + 1);
            renderCalendar();
        });
    }
    
    // Render Calendar
    function renderCalendar() {
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December'];
        
        document.getElementById('current-month').textContent = 
            `${monthNames[currentMonth.getMonth()]} ${currentMonth.getFullYear()}`;
        
        const firstDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
        const lastDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0);
        const daysInMonth = lastDay.getDate();
        const startingDayOfWeek = firstDay.getDay();
        
        const grid = document.getElementById('calendar-grid');
        if (!grid) return;
        
        let html = '<div class="calendar-weekday">Sun</div>';
        html += '<div class="calendar-weekday">Mon</div>';
        html += '<div class="calendar-weekday">Tue</div>';
        html += '<div class="calendar-weekday">Wed</div>';
        html += '<div class="calendar-weekday">Thu</div>';
        html += '<div class="calendar-weekday">Fri</div>';
        html += '<div class="calendar-weekday">Sat</div>';
        
        // Empty cells for days before the first day of the month
        for (let i = 0; i < startingDayOfWeek; i++) {
            html += '<div class="calendar-day empty"></div>';
        }
        
        // Days of the month
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
            const isToday = isSameDay(date, new Date());
            const hasActivity = checkDayActivity(date);
            
            html += `<div class="calendar-day ${isToday ? 'today' : ''} ${hasActivity ? 'has-activity' : ''}">
                <span class="day-number">${day}</span>
                ${hasActivity ? '<span class="activity-indicator"></span>' : ''}
            </div>`;
        }
        
        grid.innerHTML = html;
    }
    
    // Check if day has activity
    function checkDayActivity(date) {
        // TODO: Check against actual activity data
        return false;
    }
    
    // Initialize Week Selector
    function initializeWeekSelector() {
        updateWeekDisplay();
        
        document.getElementById('prev-week')?.addEventListener('click', () => {
            currentWeek.setDate(currentWeek.getDate() - 7);
            updateWeekDisplay();
            loadTrophies();
        });
        
        document.getElementById('next-week')?.addEventListener('click', () => {
            currentWeek.setDate(currentWeek.getDate() + 7);
            updateWeekDisplay();
            loadTrophies();
        });
    }
    
    // Update Week Display
    function updateWeekDisplay() {
        const weekEnd = new Date(currentWeek);
        weekEnd.setDate(weekEnd.getDate() + 6);
        
        document.getElementById('week-date').textContent = 
            `${formatDate(currentWeek)} - ${formatDate(weekEnd)}`;
    }
    
    // Utility Functions
    function formatNumber(num) {
        return num.toLocaleString();
    }
    
    function formatDate(date) {
        return new Date(date).toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
    }
    
    function formatDuration(seconds) {
        if (seconds < 60) return `${seconds}s`;
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        if (minutes < 60) return `${minutes}m ${secs}s`;
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return `${hours}h ${mins}m`;
    }
    
    function isSameDay(date1, date2) {
        return date1.getFullYear() === date2.getFullYear() &&
               date1.getMonth() === date2.getMonth() &&
               date1.getDate() === date2.getDate();
    }
})();

