// Stats Module JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const refreshButton = document.getElementById('refresh-button');
    
    // Load stats on page load
    loadStats();
    
    // Refresh stats every 5 seconds
    setInterval(loadStats, 5000);
    
    if (refreshButton) {
        refreshButton.addEventListener('click', loadStats);
    }
    
    async function loadStats() {
        try {
            const response = await fetch('/vidgenerator/api/stats');
            const data = await response.json();
            
            if (data.success) {
                updateStatsDisplay(data);
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
    
    function updateStatsDisplay(data) {
        const gen = data.generation || {};
        
        // Update generation stats
        if (document.getElementById('total-generated')) {
            document.getElementById('total-generated').textContent = gen.total || 0;
        }
        if (document.getElementById('completed-count')) {
            document.getElementById('completed-count').textContent = gen.completed || 0;
        }
        if (document.getElementById('generating-count')) {
            document.getElementById('generating-count').textContent = gen.generating || 0;
        }
        if (document.getElementById('failed-count')) {
            document.getElementById('failed-count').textContent = gen.failed || 0;
        }
        if (document.getElementById('generation-progress')) {
            const progress = gen.total > 0 ? (gen.completed / gen.total * 100) : 0;
            document.getElementById('generation-progress').style.width = progress + '%';
        }
        if (document.getElementById('success-rate')) {
            document.getElementById('success-rate').textContent = (gen.success_rate || 0) + '%';
        }
    }
});

