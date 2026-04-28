/**
 * Standard Navigation Component
 * Provides consistent navigation across all pages
 */
function createStandardNavigation(currentPage = '') {
    const pages = [
        { path: '/', name: 'Home', icon: '🏠', id: 'home' },
        { path: '/generator', name: 'Generator', icon: '🎬', id: 'generator' },
        { path: '/gallery', name: 'Gallery', icon: '🖼️', id: 'gallery' },
        { path: '/game', name: 'Game', icon: '🎮', id: 'game' },
        { path: '/battle', name: 'Battle', icon: '⚔️', id: 'battle' },
        { path: '/profile?tab=points', name: 'Profile hub', icon: '💎', id: 'profile-hub' },
        { path: '/profile', name: 'Profile', icon: '👤', id: 'profile' },
        { path: '/social', name: 'Social', icon: '👥', id: 'social' },
        { path: '/shop', name: 'Shop', icon: '🛒', id: 'shop' },
        { path: '/chat', name: 'Chat', icon: '💬', id: 'chat' },
        { path: '/debugger', name: 'Debugger', icon: '🔧', id: 'debugger' },
        { path: '/victory-tech-tree', name: 'Victory Tech Tree', icon: '🏆', id: 'victory-tech-tree' },
        { path: '/danish-divine-tech-tree', name: 'Danish Tech Tree', icon: '🇩🇰', id: 'danish-divine-tech-tree' }
    ];
    
    return `
        <nav class="page-nav">
            <div class="nav-container">
                <a href="/" class="nav-link nav-home">🏠 Home</a>
                <div class="nav-links">
                    ${pages.filter(p => p.id !== 'home').map(page => 
                        `<a href="${page.path}" class="nav-link ${currentPage === page.id ? 'active' : ''}">${page.icon} ${page.name}</a>`
                    ).join('')}
                </div>
            </div>
        </nav>
    `;
}

/**
 * Standard Footer Links Component
 */
function createStandardFooter() {
    const pages = [
        { path: '/', name: 'Hjem', icon: 'fas fa-home' },
        { path: '/generator', name: 'Generator', icon: 'fas fa-rocket' },
        { path: '/gallery', name: 'Galleri', icon: 'fas fa-images' },
        { path: '/game', name: 'Game', icon: 'fas fa-gamepad' },
        { path: '/battle', name: 'Battle', icon: 'fas fa-sword' },
        { path: '/profile?tab=points', name: 'Point & statistik', icon: 'fas fa-gem' },
        { path: '/profile', name: 'Profil', icon: 'fas fa-user' },
        { path: '/social', name: 'Social', icon: 'fas fa-users' },
        { path: '/shop', name: 'Shop', icon: 'fas fa-shopping-cart' },
        { path: '/chat', name: 'Chat', icon: 'fas fa-comments' },
        { path: '/debugger', name: 'Debugger', icon: 'fas fa-tools' },
        { path: '/victory-tech-tree', name: 'Victory Tech Tree', icon: 'fas fa-trophy' },
        { path: '/danish-divine-tech-tree', name: 'Danish Tech Tree', icon: 'fas fa-flag' }
    ];
    
    return `
        <div class="footer">
            <p style="color: var(--text-tertiary); margin-bottom: 20px;">&copy; 2024 MasterNoder.dk</p>
            <div class="footer-links">
                ${pages.map(page => 
                    `<a href="${page.path}" class="footer-link"><i class="${page.icon}"></i> ${page.name}</a>`
                ).join('')}
            </div>
        </div>
    `;
}

