/**
 * Referral Tracker - Tracks referral links and clicks
 */
class ReferralTracker {
    constructor() {
        this.userId = localStorage.getItem('game_user_id') || 'default_user';
        this.referralCode = this.getReferralCode();
        this.init();
    }

    init() {
        // Check if user came from referral
        const urlParams = new URLSearchParams(window.location.search);
        const ref = urlParams.get('ref');
        if (ref && ref !== this.userId) {
            this.trackReferralVisit(ref);
        }

        // Add referral links to all buttons and links
        this.addReferralLinks();
        
        // Track all clicks
        this.trackClicks();
    }

    getReferralCode() {
        // Get or create referral code
        let code = localStorage.getItem('referral_code');
        if (!code) {
            code = this.userId.substring(0, 8) + Math.random().toString(36).substring(2, 8);
            localStorage.setItem('referral_code', code);
        }
        return code;
    }

    getReferralUrl(path = '/') {
        return `${window.location.origin}${path}?ref=${this.userId}`;
    }

    addReferralLinks() {
        // Add referral parameter to all internal links
        document.querySelectorAll('a[href^="/"], a[href^="/"]').forEach(link => {
            const href = link.getAttribute('href');
            if (href && !href.includes('?ref=') && !href.startsWith('http')) {
                const separator = href.includes('?') ? '&' : '?';
                link.href = `${href}${separator}ref=${this.userId}`;
                
                // Track referral click
                link.addEventListener('click', () => {
                    this.trackClick('link', link.id || link.textContent, href, true);
                });
            }
        });

        // Add referral to buttons that navigate
        document.querySelectorAll('button[data-href], button.onclick').forEach(button => {
            const href = button.getAttribute('data-href');
            if (href) {
                button.addEventListener('click', () => {
                    this.trackClick('button', button.id || button.textContent, href, true);
                });
            }
        });
    }

    trackClicks() {
        // Track all button clicks
        document.addEventListener('click', (e) => {
            const target = e.target.closest('button, a, .clickable');
            if (target) {
                const elementType = target.tagName.toLowerCase();
                const elementId = target.id || target.className || target.textContent.substring(0, 50);
                const url = target.href || window.location.pathname;
                const isReferral = target.href && target.href.includes('?ref=');
                
                this.trackClick(elementType, elementId, url, isReferral);
            }
        });
    }

    async trackClick(elementType, elementId, url, isReferral = false) {
        try {
            await fetch('/api/tracking/click', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    element_type: elementType,
                    element_id: elementId,
                    url: url,
                    referral: isReferral
                })
            });
        } catch (error) {
            console.error('Error tracking click:', error);
        }
    }

    async trackReferralVisit(referrerId) {
        try {
            await fetch('/api/tracking/click', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: referrerId,
                    element_type: 'referral_visit',
                    element_id: 'referral',
                    url: window.location.href,
                    referral: true
                })
            });
        } catch (error) {
            console.error('Error tracking referral visit:', error);
        }
    }

    async getClickStats() {
        try {
            const response = await fetch(`/api/tracking/stats?user_id=${this.userId}`);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error getting click stats:', error);
            return null;
        }
    }

    async getReferralStats() {
        try {
            const response = await fetch(`/api/tracking/referral?user_id=${this.userId}`);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error getting referral stats:', error);
            return null;
        }
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.referralTracker = new ReferralTracker();
    });
} else {
    window.referralTracker = new ReferralTracker();
}

