/**
 * Battle Shop Integration
 * Smooth shop links and functionality for battle page
 */
class BattleShopIntegration {
    constructor(baseUrl = '', userId = 'default_user') {
        this.BASE_URL = baseUrl;
        this.userId = userId;
        this.init();
    }
    
    init() {
        console.log('[BattleShop] Initializing shop integration...');
        
        // Enhance all shop links
        this.enhanceShopLinks();
        
        // Add shop quick access
        this.addShopQuickAccess();
        
        // Track shop clicks
        this.trackShopClicks();
    }
    
    enhanceShopLinks() {
        // Find all shop links
        const shopLinks = document.querySelectorAll('a[href*="/shop"], a[href*="shop"]');
        
        shopLinks.forEach(link => {
            // Ensure proper href
            if (!link.href.includes('/shop')) {
                link.href = '/shop';
            }
            
            // Add smooth transition
            link.style.transition = 'all 0.3s ease';
            link.style.cursor = 'pointer';
            
            // Add hover effects
            link.addEventListener('mouseenter', () => {
                link.style.transform = 'translateX(5px)';
                link.style.opacity = '0.9';
            });
            
            link.addEventListener('mouseleave', () => {
                link.style.transform = 'translateX(0)';
                link.style.opacity = '1';
            });
            
            // Add click handler for smooth navigation - DO NOT prevent default
            link.addEventListener('click', (e) => {
                // Track navigation but don't block it
                this.trackShopNavigation(link.href);
                // Allow normal navigation to proceed
            });
        });
        
        console.log(`[BattleShop] Enhanced ${shopLinks.length} shop links`);
    }
    
    trackShopNavigation(url) {
        // Track shop navigation (non-blocking)
        if (window.epicGaming) {
            try {
                window.epicGaming.trackActivity('shop_visit', {
                    source: 'battle_page',
                    url: url
                });
            } catch (e) {
                console.log('[BattleShop] Tracking error (non-critical):', e);
            }
        }
    }
    
    addShopQuickAccess() {
        // Add shop quick access button in resources tab
        const resourcesTab = document.getElementById('tab-resources');
        if (resourcesTab) {
            // Check if shop quick access already exists
            if (!document.getElementById('battle-shop-quick-access')) {
                const shopQuickAccess = document.createElement('div');
                shopQuickAccess.id = 'battle-shop-quick-access';
                shopQuickAccess.style.cssText = `
                    position: sticky;
                    top: 80px;
                    background: linear-gradient(135deg, rgba(0, 255, 136, 0.15), rgba(0, 212, 255, 0.15));
                    border: 2px solid var(--primary);
                    border-radius: var(--radius-lg);
                    padding: var(--spacing-lg);
                    margin-bottom: var(--spacing-lg);
                    z-index: 100;
                `;
                shopQuickAccess.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3 style="margin: 0 0 var(--spacing-xs) 0; color: var(--primary);">🛒 Battle Shop</h3>
                            <p style="margin: 0; color: var(--text-secondary); font-size: var(--font-size-sm);">
                                Purchase equipment, power-ups, and battle items
                            </p>
                        </div>
                        <a href="/shop" class="btn-battle" style="padding: var(--spacing-md) var(--spacing-lg); text-decoration: none; display: inline-block;">
                            Visit Shop →
                        </a>
                    </div>
                `;
                
                // Insert at the beginning of resources tab
                resourcesTab.insertBefore(shopQuickAccess, resourcesTab.firstChild);
                
                // Enhance the button
                const shopButton = shopQuickAccess.querySelector('a');
                if (shopButton) {
                    shopButton.addEventListener('click', (e) => {
                        // Track but don't block navigation
                        this.trackShopNavigation('/shop');
                        // Allow normal navigation
                    });
                }
            }
        }
    }
    
    trackShopClicks() {
        // Track all shop-related clicks
        document.addEventListener('click', (e) => {
            const target = e.target.closest('a[href*="/shop"]');
            if (target) {
                // Track in analytics if available
                if (window.trackAction) {
                    window.trackAction('shop_click', {
                        source: 'battle_page',
                        link_text: target.textContent.trim()
                    });
                }
            }
        });
    }
    
    async loadShopPreview() {
        // Load a preview of shop items relevant to battle
        try {
            const response = await fetch(`${this.BASE_URL}/api/shop/items?category=battle`);
            const data = await response.json();
            
            if (data.success && data.items) {
                return data.items;
            }
        } catch (error) {
            console.warn('[BattleShop] Could not load shop preview:', error);
        }
        return null;
    }
}

// Auto-initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (window.location.pathname.includes('/battle')) {
            const userId = localStorage.getItem('game_user_id') || 'default_user';
            window.battleShopIntegration = new BattleShopIntegration('', userId);
        }
    });
} else {
    if (window.location.pathname.includes('/battle')) {
        const userId = localStorage.getItem('game_user_id') || 'default_user';
        window.battleShopIntegration = new BattleShopIntegration('', userId);
    }
}
