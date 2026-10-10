"""
Enhanced Debugger Dashboard with 10 Tools and Editable Interface
"""
from flask import Blueprint, Response

debugger_dashboard_bp = Blueprint('debugger_dashboard', __name__)

@debugger_dashboard_bp.route('/debugger/dashboard')
@debugger_dashboard_bp.route('/debugger/dashboard/')
@debugger_dashboard_bp.route('/vidgenerator/debugger/dashboard')
@debugger_dashboard_bp.route('/vidgenerator/debugger/dashboard/')
def debugger_dashboard():
    """Enhanced debugger dashboard with editable tools"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Debugger Dashboard - MasterNoder.dk</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .dashboard-header {
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .dashboard-header h1 {
            color: #333;
            margin-bottom: 10px;
        }
        
        .dashboard-controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 15px;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            font-weight: 500;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-primary:hover {
            background: #5568d3;
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-success {
            background: #28a745;
            color: white;
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        
        .tools-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .tool-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            position: relative;
        }
        
        .tool-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
        }
        
        .tool-card.editable {
            border: 2px dashed #667eea;
        }
        
        .tool-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .tool-header h3 {
            color: #333;
            font-size: 18px;
        }
        
        .tool-icon {
            font-size: 24px;
            margin-right: 10px;
        }
        
        .tool-body {
            color: #666;
            margin-bottom: 15px;
        }
        
        .tool-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .tool-actions .btn {
            flex: 1;
            min-width: 100px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 500;
        }
        
        .form-group input,
        .form-group select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        
        .status-message {
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
            display: none;
        }
        
        .status-message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status-message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .status-message.show {
            display: block;
        }
        
        .view-toggle {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .view-toggle .btn {
            flex: 1;
        }
        
        .view-toggle .btn.active {
            background: #667eea;
            color: white;
        }
        
        .stats-panel {
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .stat-item {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        
        .monitor-panel {
            background: rgba(0, 0, 0, 0.8);
            color: #0f0;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
            margin-top: 15px;
        }
        
        .monitor-line {
            margin-bottom: 5px;
        }
        
        .monitor-line.error {
            color: #f00;
        }
        
        .monitor-line.success {
            color: #0f0;
        }
        
        .monitor-line.info {
            color: #0ff;
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="dashboard-header">
            <h1>🔧 Debugger Dashboard</h1>
            <p>Comprehensive debugging and testing tools with editable interface</p>
            
            <div class="dashboard-controls">
                <button class="btn btn-primary" onclick="toggleEditMode()">✏️ Edit Mode</button>
                <button class="btn btn-secondary" onclick="saveLayout()">💾 Save Layout</button>
                <button class="btn btn-secondary" onclick="resetLayout()">🔄 Reset Layout</button>
                <button class="btn btn-success" onclick="refreshStats()">🔄 Refresh Stats</button>
            </div>
            
            <div class="view-toggle">
                <button class="btn btn-primary active" onclick="setView('grid')">📊 Grid View</button>
                <button class="btn btn-primary" onclick="setView('list')">📋 List View</button>
                <button class="btn btn-primary" onclick="setView('monitor')">🖥️ Monitor View</button>
            </div>
        </div>
        
        <div class="stats-panel" id="statsPanel">
            <h2>📈 Test Data Statistics</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value" id="statUsers">-</div>
                    <div class="stat-label">Test Users</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="statAgents">-</div>
                    <div class="stat-label">Test Agents</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="statTotal">-</div>
                    <div class="stat-label">Total Test Data</div>
                </div>
            </div>
        </div>
        
        <div id="monitorPanel" class="monitor-panel" style="display: none;">
            <div class="monitor-line info">[SYSTEM] Debugger Dashboard Monitor Active</div>
            <div class="monitor-line info">[SYSTEM] Waiting for commands...</div>
        </div>
        
        <div class="tools-grid" id="toolsGrid">
            <!-- Tool 1: Test User Generator -->
            <div class="tool-card" data-tool-id="1">
                <div class="tool-header">
                    <h3><span class="tool-icon">👤</span> Test User Generator</h3>
                </div>
                <div class="tool-body">
                    <p>Generate a single test user with random points</p>
                    <div class="form-group">
                        <label>Username:</label>
                        <input type="text" id="userUsername" placeholder="Auto-generated if empty">
                    </div>
                    <div class="form-group">
                        <label>User ID:</label>
                        <input type="text" id="userUserId" placeholder="Auto-generated if empty">
                    </div>
                </div>
                <div class="tool-actions">
                    <button class="btn btn-success" onclick="generateUser()">Generate User</button>
                </div>
                <div class="status-message" id="userStatus"></div>
            </div>
            
            <!-- Tool 2: Test Agent Generator -->
            <div class="tool-card" data-tool-id="2">
                <div class="tool-header">
                    <h3><span class="tool-icon">🤖</span> Test Agent Generator</h3>
                </div>
                <div class="tool-body">
                    <p>Generate a single test agent with random stats</p>
                    <div class="form-group">
                        <label>Agent Name:</label>
                        <input type="text" id="agentName" placeholder="Auto-generated if empty">
                    </div>
                    <div class="form-group">
                        <label>User ID:</label>
                        <input type="text" id="agentUserId" placeholder="test_user_0">
                    </div>
                    <div class="form-group">
                        <label>Agent Type:</label>
                        <select id="agentType">
                            <option value="personal_assistant">Personal Assistant</option>
                            <option value="creative_partner">Creative Partner</option>
                            <option value="strategist">Strategist</option>
                        </select>
                    </div>
                </div>
                <div class="tool-actions">
                    <button class="btn btn-success" onclick="generateAgent()">Generate Agent</button>
                </div>
                <div class="status-message" id="agentStatus"></div>
            </div>
            
            <!-- Tool 3: Database Health Check -->
            <div class="tool-card" data-tool-id="3">
                <div class="tool-header">
                    <h3><span class="tool-icon">💾</span> Database Health</h3>
                </div>
                <div class="tool-body">
                    <p>Check database connection and health status</p>
                </div>
                <div class="tool-actions">
                    <button class="btn btn-primary" onclick="checkDatabase()">Check Database</button>
                </div>
                <div class="status-message" id="dbStatus"></div>
            </div>
            
            <!-- Tool 4: API Endpoint Tester -->
            <div class="tool-card" data-tool-id="4">
                <div class="tool-header">
                    <h3><span class="tool-icon">🔌</span> API Tester</h3>
                </div>
                <div class="tool-body">
                    <p>Test API endpoints and view responses</p>
                    <div class="form-group">
                        <label>Endpoint URL:</label>
                        <input type="text" id="apiEndpoint" placeholder="/api/points/all">
                    </div>
                    <div class="form-group">
                        <label>Method:</label>
                        <select id="apiMethod">
                            <option value="GET">GET</option>
                            <option value="POST">POST</option>
                        </select>
                    </div>
                </div>
                <div class="tool-actions">
                    <button class="btn btn-primary" onclick="testAPI()">Test API</button>
                </div>
                <div class="status-message" id="apiStatus"></div>
            </div>
            
            <!-- Tool 5: Cache Monitor -->
            <div class="tool-card" data-tool-id="5">
                <div class="tool-header">
                    <h3><span class="tool-icon">⚡</span> Cache Monitor</h3>
                </div>
                <div class="tool-body">
                    <p>Monitor cache performance and clear cache</p>
                </div>
                <div class="tool-actions">
                    <button class="btn btn-primary" onclick="checkCache()">Check Cache</button>
                    <button class="btn btn-danger" onclick="clearCache()">Clear Cache</button>
                </div>
                <div class="status-message" id="cacheStatus"></div>
            </div>
            
            <!-- Tool 6: Log Viewer -->
            <div class="tool-card" data-tool-id="6">
                <div class="tool-header">
                    <h3><span class="tool-icon">📜</span> Log Viewer</h3>
                </div>
                <div class="tool-body">
                    <p>View and search application logs</p>
                    <div class="form-group">
                        <label>Log Type:</label>
                        <select id="logType">
                            <option value="debug">Debug</option>
                            <option value="error">Error</option>
                            <option value="system">System</option>
                        </select>
                    </div>
                </div>
                <div class="tool-actions">
                    <button class="btn btn-primary" onclick="viewLogs()">View Logs</button>
                </div>
                <div class="status-message" id="logStatus"></div>
            </div>
            
            <!-- Tool 7: Performance Monitor -->
            <div class="tool-card" data-tool-id="7">
                <div class="tool-header">
                    <h3><span class="tool-icon">📊</span> Performance Monitor</h3>
                </div>
                <div class="tool-body">
                    <p>Monitor system performance metrics</p>
                </div>
                <div class="tool-actions">
                    <button class="btn btn-primary" onclick="monitorPerformance()">Start Monitor</button>
                </div>
                <div class="status-message" id="perfStatus"></div>
            </div>
            
            <!-- Tool 8: Route Inspector -->
            <div class="tool-card" data-tool-id="8">
                <div class="tool-header">
                    <h3><span class="tool-icon">🛣️</span> Route Inspector</h3>
                </div>
                <div class="tool-body">
                    <p>Inspect registered routes and endpoints</p>
                </div>
                <div class="tool-actions">
                    <button class="btn btn-primary" onclick="inspectRoutes()">Inspect Routes</button>
                </div>
                <div class="status-message" id="routeStatus"></div>
            </div>
            
            <!-- Tool 9: Session Manager -->
            <div class="tool-card" data-tool-id="9">
                <div class="tool-header">
                    <h3><span class="tool-icon">🔐</span> Session Manager</h3>
                </div>
                <div class="tool-body">
                    <p>Manage user sessions and authentication</p>
                </div>
                <div class="tool-actions">
                    <button class="btn btn-primary" onclick="manageSessions()">View Sessions</button>
                </div>
                <div class="status-message" id="sessionStatus"></div>
            </div>
            
            <!-- Tool 10: System Analyzer -->
            <div class="tool-card" data-tool-id="10">
                <div class="tool-header">
                    <h3><span class="tool-icon">🔍</span> System Analyzer</h3>
                </div>
                <div class="tool-body">
                    <p>Analyze system configuration and health</p>
                </div>
                <div class="tool-actions">
                    <button class="btn btn-primary" onclick="analyzeSystem()">Analyze System</button>
                </div>
                <div class="status-message" id="systemStatus"></div>
            </div>
        </div>
    </div>
    
    <script>
        let editMode = false;
        let currentView = 'grid';
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            refreshStats();
        });
        
        function toggleEditMode() {
            editMode = !editMode;
            const cards = document.querySelectorAll('.tool-card');
            cards.forEach(card => {
                if (editMode) {
                    card.classList.add('editable');
                    card.style.cursor = 'move';
                } else {
                    card.classList.remove('editable');
                    card.style.cursor = 'default';
                }
            });
        }
        
        function setView(view) {
            currentView = view;
            const grid = document.getElementById('toolsGrid');
            const monitor = document.getElementById('monitorPanel');
            
            document.querySelectorAll('.view-toggle .btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            if (view === 'monitor') {
                grid.style.display = 'none';
                monitor.style.display = 'block';
            } else {
                grid.style.display = 'grid';
                monitor.style.display = 'none';
                if (view === 'list') {
                    grid.style.gridTemplateColumns = '1fr';
                } else {
                    grid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(300px, 1fr))';
                }
            }
        }
        
        function showStatus(elementId, message, isSuccess) {
            const status = document.getElementById(elementId);
            status.textContent = message;
            status.className = 'status-message ' + (isSuccess ? 'success' : 'error') + ' show';
            setTimeout(() => {
                status.classList.remove('show');
            }, 5000);
        }
        
        function addMonitorLine(message, type = 'info') {
            const monitor = document.getElementById('monitorPanel');
            const line = document.createElement('div');
            line.className = 'monitor-line ' + type;
            line.textContent = '[' + new Date().toLocaleTimeString() + '] ' + message;
            monitor.appendChild(line);
            monitor.scrollTop = monitor.scrollHeight;
        }
        
        async function generateUser() {
            const username = document.getElementById('userUsername').value;
            const userId = document.getElementById('userUserId').value;
            
            try {
                const response = await fetch('/vidgenerator/api/debugger/test-data/generate-user', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, user_id: userId})
                });
                
                const data = await response.json();
                if (data.success) {
                    showStatus('userStatus', data.message, true);
                    addMonitorLine('User generated: ' + data.user.username, 'success');
                    refreshStats();
                } else {
                    showStatus('userStatus', data.error || 'Failed to generate user', false);
                    addMonitorLine('Error: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (error) {
                showStatus('userStatus', 'Error: ' + error.message, false);
                addMonitorLine('Error: ' + error.message, 'error');
            }
        }
        
        async function generateAgent() {
            const agentName = document.getElementById('agentName').value;
            const userId = document.getElementById('agentUserId').value;
            const agentType = document.getElementById('agentType').value;
            
            try {
                const response = await fetch('/vidgenerator/api/debugger/test-data/generate-agent', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({agent_name: agentName, user_id: userId, agent_type: agentType})
                });
                
                const data = await response.json();
                if (data.success) {
                    showStatus('agentStatus', data.message, true);
                    addMonitorLine('Agent generated: ' + data.agent.agent_name, 'success');
                    refreshStats();
                } else {
                    showStatus('agentStatus', data.error || 'Failed to generate agent', false);
                    addMonitorLine('Error: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (error) {
                showStatus('agentStatus', 'Error: ' + error.message, false);
                addMonitorLine('Error: ' + error.message, 'error');
            }
        }
        
        async function refreshStats() {
            try {
                const response = await fetch('/vidgenerator/api/debugger/test-data/stats');
                const data = await response.json();
                if (data.success) {
                    document.getElementById('statUsers').textContent = data.stats.test_users;
                    document.getElementById('statAgents').textContent = data.stats.test_agents;
                    document.getElementById('statTotal').textContent = data.stats.total_test_data;
                }
            } catch (error) {
                console.error('Error refreshing stats:', error);
            }
        }
        
        function checkDatabase() {
            showStatus('dbStatus', 'Database check not implemented yet', false);
            addMonitorLine('Database check requested', 'info');
        }
        
        function testAPI() {
            showStatus('apiStatus', 'API test not implemented yet', false);
            addMonitorLine('API test requested', 'info');
        }
        
        function checkCache() {
            showStatus('cacheStatus', 'Cache check not implemented yet', false);
            addMonitorLine('Cache check requested', 'info');
        }
        
        function clearCache() {
            showStatus('cacheStatus', 'Cache clear not implemented yet', false);
            addMonitorLine('Cache clear requested', 'info');
        }
        
        function viewLogs() {
            showStatus('logStatus', 'Log viewer not implemented yet', false);
            addMonitorLine('Log view requested', 'info');
        }
        
        function monitorPerformance() {
            showStatus('perfStatus', 'Performance monitor not implemented yet', false);
            addMonitorLine('Performance monitor started', 'info');
        }
        
        function inspectRoutes() {
            showStatus('routeStatus', 'Route inspector not implemented yet', false);
            addMonitorLine('Route inspection requested', 'info');
        }
        
        function manageSessions() {
            showStatus('sessionStatus', 'Session manager not implemented yet', false);
            addMonitorLine('Session management requested', 'info');
        }
        
        function analyzeSystem() {
            showStatus('systemStatus', 'System analyzer not implemented yet', false);
            addMonitorLine('System analysis requested', 'info');
        }
        
        function saveLayout() {
            const layout = Array.from(document.querySelectorAll('.tool-card')).map(card => ({
                id: card.dataset.toolId,
                order: Array.from(card.parentNode.children).indexOf(card)
            }));
            localStorage.setItem('debuggerLayout', JSON.stringify(layout));
            showStatus('userStatus', 'Layout saved to localStorage', true);
        }
        
        function resetLayout() {
            localStorage.removeItem('debuggerLayout');
            location.reload();
        }
    </script>
</body>
</html>
    """
    return Response(html_content, mimetype='text/html; charset=utf-8')
