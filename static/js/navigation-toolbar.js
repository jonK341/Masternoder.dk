/**
 * Navigation Toolbar - Universal navigation system
 * Provides consistent navigation across all pages
 */

(function() {
    'use strict';

    const APP_BASE = (typeof window !== 'undefined' && window.APP_BASE !== undefined) ? window.APP_BASE : '';

    // Small image icons for upper nav (SVG / agent avatars). Emoji kept as fallback.
    const NAV_ICON_IMAGES = {
        home: APP_BASE + '/static/img/nav/home.svg',
        battle: APP_BASE + '/static/img/agents/battle_strategy_agent.svg',
        trophies: APP_BASE + '/static/img/nav/trophy.svg',
        stories: APP_BASE + '/static/img/nav/stories.svg',
        game: APP_BASE + '/static/img/nav/game.svg',
        casino: APP_BASE + '/static/img/nav/casino.svg',
        generator: APP_BASE + '/static/img/agents/content_generator_agent.svg',
        podcast: APP_BASE + '/static/img/nav/news.svg',
        quests: APP_BASE + '/static/img/agents/workflow_agent.svg',
        agents: APP_BASE + '/static/img/agents/ai_intelligence_agent.svg',
        agent_support: APP_BASE + '/static/img/agents/master_fix_agent.svg',
        gallery: APP_BASE + '/static/img/agents/user_experience_agent.svg',
        battlegrounds: APP_BASE + '/static/img/nav/battlegrounds.svg',
        profile: APP_BASE + '/static/img/nav/profile.svg',
        social: APP_BASE + '/static/img/agents/social_engagement_agent.svg',
        shop: APP_BASE + '/static/img/nav/shop.svg',
        market: APP_BASE + '/static/img/agents/analytics_agent.svg',
        customers: APP_BASE + '/static/img/nav/customers.svg',
        agents_control: APP_BASE + '/static/img/agents/master_dashboard_agent.svg',
        chat: APP_BASE + '/static/img/nav/chat.svg',
        debugger: APP_BASE + '/static/img/agents/tester_agent.svg',
        lab: APP_BASE + '/static/img/nav/lab.svg',
        starmap25: APP_BASE + '/static/img/nav/starmap.svg',
        explorer: APP_BASE + '/static/img/nav/explorer.svg',
        news: APP_BASE + '/static/img/nav/news.svg',
        library: APP_BASE + '/static/img/nav/stories.svg',
        wallets: APP_BASE + '/static/img/nav/profile.svg',
        staking_leaderboard: APP_BASE + '/static/img/nav/trophy.svg',
        staking_teams: APP_BASE + '/static/img/agents/social_engagement_agent.svg',
        creator: APP_BASE + '/static/img/agents/content_generator_agent.svg',
        command_center: APP_BASE + '/static/img/agents/master_dashboard_agent.svg',
        exchange: APP_BASE + '/static/img/agents/analytics_agent.svg',
        profit: APP_BASE + '/static/img/nav/explorer.svg'
    };

    /** Practical portal clusters — same structure on toolbar, dropdown, and frontpage. */
    const NAV_GROUPS = [
        { id: 'create', label: 'Create', icon: '🎬', hubId: 'generator', summary: 'Generator, encoder, gallery' },
        { id: 'play', label: 'Play', icon: '🎮', hubId: 'game', summary: 'Game, battle, casino, trophies' },
        { id: 'mn2', label: 'MN2 Money', icon: '🪙', hubId: 'explorer', summary: 'Wallet, shop, exchange, staking' },
        { id: 'tools', label: 'Tools', icon: '🔧', hubId: 'command_center', summary: 'Agents, lab, debugger, aggregator' },
        { id: 'community', label: 'Community', icon: '📰', summary: 'News, podcast, social, library' },
        { id: 'archive', label: 'More & archive', icon: '🗂️', summary: 'Legacy pages & extras' },
    ];

    /** Desktop top bar — 6 most-used only; rest live in Portaler accordion. */
    const TOP_BAR_IDS = new Set([
        'generator', 'game', 'battle', 'trophies', 'explorer', 'shop',
    ]);

    /** Homepage quick picks — mirrors top bar + one anchor per cluster. */
    const TOP_PICKS_IDS = [
        'generator', 'game', 'battle', 'trophies', 'explorer', 'shop',
        'creator', 'casino', 'wallets', 'agents', 'news', 'library',
    ];

    /** @deprecated alias — use TOP_PICKS_IDS */
    const TOP_20_IDS = TOP_PICKS_IDS.slice();

    const NAV_CONFIG = {
        brand: {
            name: 'MasterNoder',
            icon: '🏠',
            iconImg: APP_BASE + '/static/img/nav/brand.svg',
            url: APP_BASE + '/'
        },
        favorites: ['generator', 'game', 'battle', 'trophies'],
        links: [
            { name: 'Home', icon: '🏠', url: APP_BASE + '/', id: 'home', tier: 'bar', group: null },
            { name: 'Generator', icon: '🎬', url: APP_BASE + '/generator', id: 'generator', tier: 'bar', group: 'create', favorite: true },
            { name: 'Super Encoder', icon: '🎵', url: APP_BASE + '/creator/', id: 'creator', tier: 'portal', group: 'create', title: 'Music, songs & video — one-click AI encoder' },
            { name: 'Game', icon: '🎮', url: APP_BASE + '/game', id: 'game', tier: 'bar', group: 'play', favorite: true, title: 'Game hub — campaign, stats, social tabs' },
            { name: 'Battle', icon: '⚔️', url: APP_BASE + '/battle', id: 'battle', tier: 'bar', group: 'play', favorite: true },
            { name: 'Trophies', icon: '🏆', url: APP_BASE + '/trophies', id: 'trophies', tier: 'bar', group: 'play', favorite: true },
            { name: 'Shop', icon: '🛒', url: APP_BASE + '/shop', id: 'shop', tier: 'bar', group: 'mn2' },
            { name: 'Explorer', icon: '🔎', url: APP_BASE + '/explorer', id: 'explorer', tier: 'bar', group: 'mn2', title: 'MN2 Crypto Hub — staking, market, reserves, hosting' },
            { name: 'Profile', icon: '👤', url: APP_BASE + '/profile', id: 'profile', tier: 'portal', group: 'mn2', title: 'Unified hub — points, wallet, shop, leaderboard, activity' },

            { name: 'Gallery', icon: '🖼️', url: APP_BASE + '/gallery', id: 'gallery', tier: 'portal', group: 'create' },
            { name: 'Podcast', icon: '🎙️', url: APP_BASE + '/podcast', id: 'podcast', tier: 'portal', group: 'community', title: 'YouTube, Facebook, Discord, GitHub feeds' },
            { name: 'Camgirls', icon: '💃', url: APP_BASE + '/camgirls', id: 'camgirls', tier: 'portal', group: 'create', title: 'Studio integration portal' },

            { name: 'Quests', icon: '📜', url: APP_BASE + '/quests', id: 'quests', tier: 'portal', group: 'play' },
            { name: 'Casino', icon: '🎰', url: APP_BASE + '/casino/', id: 'casino', tier: 'portal', group: 'play', title: 'Casino cockpit — games, contests, income' },
            { name: 'Battlegrounds', icon: '🗺️', url: APP_BASE + '/battlegrounds', id: 'battlegrounds', tier: 'portal', group: 'play' },
            { name: 'Star Map 25', icon: '🗺️', url: APP_BASE + '/starmap25', id: 'starmap25', tier: 'portal', group: 'play' },
            { name: 'Champions League', icon: '🏅', url: APP_BASE + '/champions-league', id: 'champions_league', tier: 'portal', group: 'play', title: 'Season ladder — linked from Command Center' },

            { name: 'Wallets', icon: '💾', url: APP_BASE + '/wallets', id: 'wallets', tier: 'portal', group: 'mn2', title: 'MN2 deposit, withdraw, trusted addresses' },
            { name: 'Exchange', icon: '💱', url: APP_BASE + '/exchange', id: 'exchange', tier: 'portal', group: 'mn2', title: '25-crypto exchange — swap, on-ramp, tax records' },
            { name: 'Market', icon: '📈', url: APP_BASE + '/market', id: 'market', tier: 'portal', group: 'mn2', title: 'P2P MN2 marketplace — also in Explorer' },
            { name: 'Staking Rank', icon: '🌱', url: APP_BASE + '/staking-leaderboard', id: 'staking_leaderboard', tier: 'portal', group: 'mn2', title: 'Staking leaderboard — Explorer tab' },
            { name: 'Staking Teams', icon: '🤝', url: APP_BASE + '/staking-teams', id: 'staking_teams', tier: 'portal', group: 'mn2', title: 'Team staking — Explorer tab' },
            { name: 'Staking Monitor', icon: '📊', url: APP_BASE + '/staking-monitor', id: 'staking_monitor', tier: 'portal', group: 'mn2', title: 'Live staking monitor — Explorer satellite' },
            { name: 'Proof of Reserves', icon: '🏦', url: APP_BASE + '/proof-of-reserves', id: 'proof_of_reserves', tier: 'portal', group: 'mn2', title: 'MN2 reserves audit — Explorer tab' },
            { name: 'Hosting', icon: '🖥️', url: APP_BASE + '/hosting', id: 'hosting', tier: 'portal', group: 'mn2', title: 'Masternode hosting — Explorer tab' },
            { name: 'Profit Daemon', icon: '⚡', url: APP_BASE + '/profit/', id: 'profit', tier: 'portal', group: 'mn2', title: '24/7 profit monitor, news, rentals' },

            { name: 'AI Agents', icon: '🤖', url: APP_BASE + '/agents', id: 'agents', tier: 'portal', group: 'tools' },
            { name: 'Lab', icon: '🔬', url: APP_BASE + '/lab', id: 'lab', tier: 'portal', group: 'tools', title: 'Discussion & experiments — replaces /chat' },
            { name: 'Agent Support', icon: '🛠️', url: APP_BASE + '/agent_support', id: 'agent_support', tier: 'portal', group: 'tools', title: 'Tickets, AI API keys, tools' },
            { name: 'Debugger', icon: '🔧', url: APP_BASE + '/debugger', id: 'debugger', tier: 'portal', group: 'tools' },
            { name: 'Aggregator', icon: '📡', url: APP_BASE + '/aggregator', id: 'aggregator', tier: 'portal', group: 'tools', title: '75 AI aggregators — catalog & control' },
            { name: 'Agents Control', icon: '🎛️', url: APP_BASE + '/dashboard/agents_control', id: 'agents_control', tier: 'portal', group: 'tools', title: 'Agents control board' },
            { name: 'Command Center', icon: '🛰️', url: APP_BASE + '/command-center', id: 'command_center', tier: 'portal', group: 'tools', title: 'Cross-feature ops map — battle, game, exchange, casino' },
            { name: 'Business Control', icon: '🏢', url: APP_BASE + '/business-control', id: 'business_control', tier: 'portal', group: 'tools', title: 'Exchange payout & business ops board' },

            { name: 'News', icon: '📰', url: APP_BASE + '/news', id: 'news', tier: 'portal', group: 'community' },
            { name: 'Library', icon: '📖', url: APP_BASE + '/compendium/?calm=1', id: 'library', tier: 'portal', group: 'community', title: 'Rulebooks V1–V16, calm reader' },
            { name: 'Social', icon: '👥', url: APP_BASE + '/social', id: 'social', tier: 'portal', group: 'community' },
            { name: 'Customers', icon: '📇', url: APP_BASE + '/customers', id: 'customers', tier: 'portal', group: 'community', title: 'Customer directory' },

            { name: 'Metal Systems', icon: '🤘', url: APP_BASE + '/metal', id: 'metal', tier: 'portal', group: 'archive', title: 'Hardcore AI metal progression' },
            { name: 'Milkyway', icon: '🌌', url: APP_BASE + '/milkyway', id: 'milkyway', tier: 'portal', group: 'archive' },
            { name: 'Editor', icon: '✂️', url: APP_BASE + '/editor', id: 'editor', tier: 'portal', group: 'archive' },
            { name: 'Monetization', icon: '💰', url: APP_BASE + '/monetization', id: 'monetization', tier: 'portal', group: 'archive' },
            { name: 'Theme Points', icon: '🎨', url: APP_BASE + '/theme-points', id: 'theme_points', tier: 'portal', group: 'archive' },
            { name: 'Theme Premium', icon: '✨', url: APP_BASE + '/theme_premium', id: 'theme_premium', tier: 'portal', group: 'archive' },
            { name: 'Beta Testing', icon: '🧪', url: APP_BASE + '/beta_testing', id: 'beta_testing', tier: 'portal', group: 'archive' },
            { name: 'Calculator', icon: '🧮', url: APP_BASE + '/advanced_calculator', id: 'advanced_calculator', tier: 'portal', group: 'archive' },
            { name: 'Rights Law', icon: '⚖️', url: APP_BASE + '/rights-law', id: 'rights_law', tier: 'portal', group: 'archive' },
            { name: 'Victory Tech Tree', icon: '🌳', url: APP_BASE + '/victory-tech-tree', id: 'victory_tech_tree', tier: 'portal', group: 'archive' },
            { name: 'Divine Tech Tree', icon: '🌲', url: APP_BASE + '/danish-divine-tech-tree', id: 'danish_divine_tech_tree', tier: 'portal', group: 'archive' },
            { name: 'Academic View', icon: '🎓', url: APP_BASE + '/academic-perspective', id: 'academic_perspective', tier: 'portal', group: 'archive' },
            { name: 'Time Guides', icon: '⏱️', url: APP_BASE + '/time-achievement-guides', id: 'time_achievement_guides', tier: 'portal', group: 'archive' },
            { name: 'Social Monitor', icon: '📡', url: APP_BASE + '/social-monitor', id: 'social_monitor', tier: 'portal', group: 'archive' },
        ],
        apiBase: window.location.origin + APP_BASE
    };

    function isBarLink(link) {
        return link && link.id !== 'home' && (link.tier === 'bar' || TOP_BAR_IDS.has(link.id));
    }

    function portalLinksOnly() {
        return NAV_CONFIG.links.filter((link) => link.id !== 'home' && !isBarLink(link));
    }

    function _renderPortalPanelHTML() {
        const pool = portalLinksOnly();
        const barPool = NAV_CONFIG.links.filter((l) => l.id !== 'home' && isBarLink(l));
        return NAV_GROUPS.map((grp) => {
            const portalLinks = pool.filter((l) => l.group === grp.id);
            const barLinks = barPool.filter((l) => l.group === grp.id);
            const links = [...barLinks, ...portalLinks];
            if (!links.length) return '';
            const hub = grp.hubId ? NAV_CONFIG.links.find((l) => l.id === grp.hubId) : null;
            const hubLine = hub
                ? `<p class="nav-toolbar-portal-merge">Hub: <a href="${hub.url}" class="nav-toolbar-portal-merge-link" data-page-id="${hub.id}">${hub.name}</a>${grp.summary ? ` · ${grp.summary}` : ''}</p>`
                : (grp.summary ? `<p class="nav-toolbar-portal-merge">${grp.summary}</p>` : '');
            return `<section class="nav-toolbar-portal-accordion" data-cluster="${grp.id}">
                <button type="button" class="nav-toolbar-portal-accordion-trigger" aria-expanded="false" aria-controls="nav-cluster-${grp.id}" id="nav-cluster-btn-${grp.id}">
                    <span class="nav-toolbar-portal-accordion-label"><span class="nav-toolbar-portal-accordion-icon" aria-hidden="true">${grp.icon}</span> ${grp.label}</span>
                    <span class="nav-toolbar-portal-accordion-meta">
                        <span class="nav-toolbar-portal-accordion-count">${links.length}</span>
                        <span class="nav-toolbar-portal-accordion-chevron" aria-hidden="true">▾</span>
                    </span>
                </button>
                <div class="nav-toolbar-portal-accordion-panel" id="nav-cluster-${grp.id}" role="region" aria-labelledby="nav-cluster-btn-${grp.id}" hidden>
                    ${hubLine}
                    <div class="nav-toolbar-portal-grid">${links.map((link) => _renderLinkAnchor(link, 'nav-toolbar-portal-grid-link')).join('')}</div>
                </div>
            </section>`;
        }).join('');
    }

    if (typeof window !== 'undefined') {
        window.MN_NAV_LINKS = NAV_CONFIG.links;
        window.MN_NAV_GROUPS = NAV_GROUPS;
        window.MN_NAV_TOP_BAR_IDS = Array.from(TOP_BAR_IDS);
        window.MN_NAV_TOP_PICKS_IDS = TOP_PICKS_IDS.slice();
        window.MN_NAV_TOP_20_IDS = TOP_20_IDS.slice();
    }

    function _resolveIconImg(link) {
        return link.iconImg || NAV_ICON_IMAGES[link.id] || null;
    }

    function _renderIcon(link, options) {
        const opts = options || {};
        const imgSrc = _resolveIconImg(link);
        const pulseClass = (link.favorite || opts.pulse) ? ' nav-toolbar-link-img--pulse' : '';
        const sizeClass = opts.large ? ' nav-toolbar-link-img--lg' : '';
        const avatarClass = imgSrc && imgSrc.indexOf('/agents/') !== -1 ? ' nav-toolbar-link-img--avatar' : '';

        if (imgSrc) {
            return `<span class="nav-toolbar-link-icon${opts.extraClass || ''}"><img class="nav-toolbar-link-img${pulseClass}${sizeClass}${avatarClass}" src="${imgSrc}" alt="" width="20" height="20" loading="lazy" decoding="async" onerror="this.style.display='none';var fb=this.nextElementSibling;if(fb){fb.hidden=false;}"><span class="nav-toolbar-link-emoji-fallback" hidden aria-hidden="true">${link.icon}</span></span>`;
        }
        return `<span class="nav-toolbar-link-icon${opts.extraClass || ''}">${link.icon}</span>`;
    }

    function _renderLinkAnchor(link, extraClasses) {
        const badge = link.badge ? `<span class="nav-toolbar-badge">${link.badge}</span>` : '';
        const favoriteClass = link.favorite ? ' nav-toolbar-link-favorite' : '';
        const titleAttr = link.title ? ` title="${link.title.replace(/"/g, '&quot;')}"` : (link.favorite ? ' title="Favorite"' : '');
        const ec = extraClasses ? ` ${extraClasses}` : '';
        return `
                <a href="${link.url}" class="nav-toolbar-link${ec}${favoriteClass}" data-page-id="${link.id}"${titleAttr}>
                    ${_renderIcon(link)}
                    <span>${link.name}</span>
                    ${badge}
                </a>
            `;
    }

    /**
     * Create navigation toolbar HTML
     */
    function createToolbarHTML() {
        const portalVoid = typeof window !== 'undefined' && window.MN_NAV_PORTAL_VOID;

        const barLinksHTML = NAV_CONFIG.links.filter((link) => isBarLink(link)).map((link) => _renderLinkAnchor(link, '')).join('');
        const linksHTML = portalVoid ? barLinksHTML : NAV_CONFIG.links.map((link) => _renderLinkAnchor(link, '')).join('');
        const quickLinksHTML = NAV_CONFIG.links.filter((link) => isBarLink(link)).map((link) => _renderLinkAnchor(link, 'nav-toolbar-quick-link')).join('');
        const portalPanelHTML = _renderPortalPanelHTML();

        if (portalVoid) {
            return `
            <nav class="nav-toolbar nav-toolbar--portal-void" id="navToolbar">
                <div class="nav-toolbar-content">
                    <a href="${NAV_CONFIG.brand.url}" class="nav-toolbar-brand">
                        ${_renderIcon(NAV_CONFIG.brand, { extraClass: ' nav-toolbar-brand-icon-wrap', pulse: true, large: true })}
                        <span>${NAV_CONFIG.brand.name}</span>
                    </a>

                    <div class="nav-toolbar-quicklinks" id="navToolbarQuickLinks" aria-label="Hurtig navigation">
                        ${quickLinksHTML}
                    </div>

                    <div class="nav-toolbar-portal-wrap">
                        <button type="button" class="nav-toolbar-portal-trigger" id="navPortalTrigger" aria-expanded="false" aria-haspopup="true" aria-controls="navPortalPanel">
                            <span class="nav-toolbar-portal-trigger-icon nav-toolbar-portal-trigger-icon--spin">🌀</span>
                            <span>Portaler</span>
                        </button>
                    </div>

                    <div class="nav-toolbar-user">
                        <div class="nav-toolbar-user-controls" id="navToolbarUserControls">
                            <button class="nav-toolbar-control-btn" id="navToolbarUserBtn" title="User Settings">
                                <span>👤</span>
                            </button>
                            <button class="nav-toolbar-control-btn" id="navToolbarSettingsBtn" title="Settings">
                                <span>⚙️</span>
                            </button>
                            <button class="nav-toolbar-control-btn" id="navToolbarNotificationsBtn" title="Notifications">
                                <span>🔔</span>
                                <span class="nav-toolbar-badge" id="navToolbarNotificationsBadge" style="display: none;">0</span>
                            </button>
                        </div>
                        <div class="nav-toolbar-mn2-wallet" id="navToolbarMn2Wallet" role="button" tabindex="0" title="MN2 Wallet — click for actions, double-click to open (W)" aria-haspopup="true" aria-label="MN2 wallet balance and quick actions">
                            <span class="nav-toolbar-mn2-icon">⚡</span>
                            <span class="nav-toolbar-mn2-label">MN2</span>
                            <strong id="navToolbarMn2Balance">—</strong>
                            <span class="nav-toolbar-mn2-chevron" aria-hidden="true">▾</span>
                        </div>
                        <div class="nav-toolbar-currency" id="navToolbarCurrency" title="Shop coins">
                            <span class="nav-toolbar-currency-icon">🪙</span>
                            <span id="navToolbarCurrencyAmount">0</span>
                        </div>
                        <button class="nav-toolbar-toggle" id="navToolbarToggle" aria-label="Toggle portals menu">
                            ☰
                        </button>
                    </div>
                </div>

                <div id="navPortalPanel" class="nav-toolbar-portal-panel" role="menu" aria-hidden="true" hidden>
                    <div class="nav-toolbar-portal-inner">
                        <p class="nav-toolbar-portal-hint">6 praktiske klynger — fold ud for alle portaler</p>
                        <div class="nav-toolbar-portal-sections" id="navPortalGrid">
                            ${portalPanelHTML}
                        </div>
                    </div>
                </div>
            </nav>`;
        }

        return `
            <nav class="nav-toolbar" id="navToolbar">
                <div class="nav-toolbar-content">
                    <a href="${NAV_CONFIG.brand.url}" class="nav-toolbar-brand">
                        ${_renderIcon(NAV_CONFIG.brand, { extraClass: ' nav-toolbar-brand-icon-wrap', pulse: true, large: true })}
                        <span>${NAV_CONFIG.brand.name}</span>
                    </a>
                    
                    <div class="nav-toolbar-links" id="navToolbarLinks">
                        ${linksHTML}
                    </div>
                    
                    <div class="nav-toolbar-user">
                        <div class="nav-toolbar-user-controls" id="navToolbarUserControls">
                            <button class="nav-toolbar-control-btn" id="navToolbarUserBtn" title="User Settings">
                                <span>👤</span>
                            </button>
                            <button class="nav-toolbar-control-btn" id="navToolbarSettingsBtn" title="Settings">
                                <span>⚙️</span>
                            </button>
                            <button class="nav-toolbar-control-btn" id="navToolbarNotificationsBtn" title="Notifications">
                                <span>🔔</span>
                                <span class="nav-toolbar-badge" id="navToolbarNotificationsBadge" style="display: none;">0</span>
                            </button>
                        </div>
                        <div class="nav-toolbar-mn2-wallet" id="navToolbarMn2Wallet" role="button" tabindex="0" title="MN2 Wallet — click for actions, double-click to open (W)" aria-haspopup="true" aria-label="MN2 wallet balance and quick actions">
                            <span class="nav-toolbar-mn2-icon">⚡</span>
                            <span class="nav-toolbar-mn2-label">MN2</span>
                            <strong id="navToolbarMn2Balance">—</strong>
                            <span class="nav-toolbar-mn2-chevron" aria-hidden="true">▾</span>
                        </div>
                        <div class="nav-toolbar-currency" id="navToolbarCurrency" title="Shop coins">
                            <span class="nav-toolbar-currency-icon">🪙</span>
                            <span id="navToolbarCurrencyAmount">0</span>
                        </div>
                        <button class="nav-toolbar-toggle" id="navToolbarToggle" aria-label="Toggle menu">
                            ☰
                        </button>
                    </div>
                </div>
                
                <div class="nav-toolbar-mobile" id="navToolbarMobile">
                    ${NAV_CONFIG.links.map(link => `
                        <a href="${link.url}" class="nav-toolbar-mobile-link${link.favorite ? ' nav-toolbar-mobile-link-favorite' : ''}" data-page-id="${link.id}">
                            ${_renderIcon(link)}
                            <span>${link.name}</span>
                        </a>
                    `).join('')}
                </div>
            </nav>
        `;
    }

    /**
     * Initialize navigation toolbar
     */
    function initToolbar() {
        // Check if toolbar already exists
        if (document.getElementById('navToolbar')) {
            return;
        }

        // Create and insert toolbar
        const toolbarHTML = createToolbarHTML();
        document.body.insertAdjacentHTML('afterbegin', toolbarHTML);

        // Highlight active link
        highlightActiveLink();

        // Setup mobile menu toggle + portal accordions
        setupMobileMenu();
        setupPortalAccordions();

        // Load currency
        loadCurrency();

        // Setup click tracking
        setupClickTracking();
        
        // Setup user controls
        setupUserControls();

        // Ensure AI + points systems are available across pages.
        ensureGlobalSystems();
    }

    /**
     * Load global AI + points integrations for pages that include the nav toolbar.
     */
    function ensureGlobalSystems() {
        const sharedScripts = [
            APP_BASE + '/static/js/unified-point-counters.js',
            APP_BASE + '/static/js/stats-achievements-tracker.js',
            APP_BASE + '/static/js/comprehensive-api-integration.js',
            APP_BASE + '/static/js/agent-skill-sets.js',
        ];

        sharedScripts.forEach(loadScriptOnce);
    }

    function loadScriptOnce(src) {
        if (!src) return;
        const existing = document.querySelector(`script[src*="${src}"]`);
        if (existing) return;
        const s = document.createElement('script');
        s.src = src;
        s.defer = true;
        s.dataset.injectedBy = 'navigation-toolbar';
        s.onerror = () => console.warn('[NavigationToolbar] Failed to load shared script:', src);
        document.head.appendChild(s);
    }

    /**
     * Highlight active navigation link
     */
    function highlightActiveLink() {
        const currentPath = window.location.pathname;
        const currentUrl = window.location.href;

        // Remove all active classes
        document.querySelectorAll('.nav-toolbar-link, .nav-toolbar-mobile-link, .nav-toolbar-portal-grid-link, .nav-toolbar-quick-link, .nav-toolbar-portal-merge-link').forEach(link => {
            link.classList.remove('active');
        });

        // Find and highlight active link
        document.querySelectorAll('.nav-toolbar-link, .nav-toolbar-mobile-link, .nav-toolbar-portal-grid-link, .nav-toolbar-quick-link, .nav-toolbar-portal-merge-link').forEach(link => {
            const linkUrl = new URL(link.href, window.location.origin);
            const linkPath = linkUrl.pathname;

            // Exact match or starts with (for sub-pages)
            if (linkPath === currentPath || 
                (currentPath.startsWith(linkPath) && linkPath !== '/')) {
                link.classList.add('active');
            }
        });
    }

    function setPortalAccordionOpen(accordion, open) {
        if (!accordion) return;
        const trigger = accordion.querySelector('.nav-toolbar-portal-accordion-trigger');
        const panel = accordion.querySelector('.nav-toolbar-portal-accordion-panel');
        if (!trigger || !panel) return;
        trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
        accordion.classList.toggle('is-open', open);
        panel.hidden = !open;
    }

    function expandActivePortalCluster() {
        const panel = document.getElementById('navPortalPanel');
        if (!panel) return;
        const activeLink = panel.querySelector('.nav-toolbar-portal-grid-link.active, .nav-toolbar-portal-merge-link.active');
        const targetAccordion = activeLink
            ? activeLink.closest('.nav-toolbar-portal-accordion')
            : panel.querySelector('.nav-toolbar-portal-accordion');
        panel.querySelectorAll('.nav-toolbar-portal-accordion').forEach((acc) => setPortalAccordionOpen(acc, false));
        if (targetAccordion) setPortalAccordionOpen(targetAccordion, true);
    }

    /**
     * Collapsible cluster sections inside the Portaler panel.
     */
    function setupPortalAccordions() {
        const panel = document.getElementById('navPortalPanel');
        if (!panel) return;

        panel.querySelectorAll('.nav-toolbar-portal-accordion-trigger').forEach((trigger) => {
            trigger.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const accordion = trigger.closest('.nav-toolbar-portal-accordion');
                const isOpen = trigger.getAttribute('aria-expanded') === 'true';
                panel.querySelectorAll('.nav-toolbar-portal-accordion').forEach((acc) => {
                    if (acc !== accordion) setPortalAccordionOpen(acc, false);
                });
                setPortalAccordionOpen(accordion, !isOpen);
            });
        });
    }

    /**
     * Setup mobile menu toggle
     */
    function setupMobileMenu() {
        const portalVoid = typeof window !== 'undefined' && window.MN_NAV_PORTAL_VOID;
        const toggle = document.getElementById('navToolbarToggle');
        const mobileMenu = document.getElementById('navToolbarMobile');
        const portalPanel = document.getElementById('navPortalPanel');
        const portalTrigger = document.getElementById('navPortalTrigger');

        if (portalVoid && portalPanel && portalTrigger) {
            const syncToggleIcon = () => {
                if (!toggle) return;
                toggle.textContent = portalPanel.classList.contains('open') ? '✕' : '☰';
            };
            const closePortal = () => {
                portalPanel.classList.remove('open');
                portalPanel.hidden = true;
                portalPanel.setAttribute('aria-hidden', 'true');
                portalTrigger.setAttribute('aria-expanded', 'false');
                syncToggleIcon();
            };
            const openPortal = () => {
                portalPanel.hidden = false;
                portalPanel.classList.add('open');
                portalPanel.setAttribute('aria-hidden', 'false');
                portalTrigger.setAttribute('aria-expanded', 'true');
                expandActivePortalCluster();
                syncToggleIcon();
            };
            const togglePortal = () => {
                if (portalPanel.classList.contains('open')) closePortal();
                else openPortal();
            };

            portalTrigger.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                togglePortal();
            });

            if (toggle) {
                toggle.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    togglePortal();
                });
            }

            document.addEventListener('click', function(e) {
                const t = e.target;
                if (portalTrigger.contains(t)) return;
                if (portalPanel.contains(t)) return;
                if (toggle && toggle.contains(t)) return;
                closePortal();
            });

            portalPanel.querySelectorAll('a').forEach((a) => {
                a.addEventListener('click', closePortal);
            });

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') closePortal();
            });
            return;
        }

        if (toggle && mobileMenu) {
            toggle.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                mobileMenu.classList.toggle('active');
                toggle.textContent = mobileMenu.classList.contains('active') ? '✕' : '☰';
            });

            // Close mobile menu when clicking outside
            document.addEventListener('click', function(e) {
                if (!toggle.contains(e.target) && !mobileMenu.contains(e.target)) {
                    mobileMenu.classList.remove('active');
                    toggle.textContent = '☰';
                }
            });

            // Close mobile menu when clicking a link
            mobileMenu.querySelectorAll('.nav-toolbar-mobile-link').forEach(link => {
                link.addEventListener('click', function() {
                    mobileMenu.classList.remove('active');
                    toggle.textContent = '☰';
                });
            });
        }
    }

    /**
     * Load user currency
     */
    function resolveNavUserId() {
        const game = localStorage.getItem('game_user_id');
        const user = localStorage.getItem('user_id');
        if (game && game !== 'default_user') return game;
        if (user && user !== 'default_user') {
            localStorage.setItem('game_user_id', user);
            return user;
        }
        return 'default_user';
    }

    async function loadCurrency() {
        try {
            const userId = resolveNavUserId();
            const response = await fetch(`${NAV_CONFIG.apiBase}/api/shop/currency?user_id=${userId}`);
            
            if (response.ok) {
                const data = await response.json();
                const amount = data.currency || 0;
                
                const currencyElement = document.getElementById('navToolbarCurrencyAmount');
                if (currencyElement) {
                    currencyElement.textContent = amount.toLocaleString();
                }
            }
        } catch (error) {
            console.error('Error loading currency:', error);
        }
    }

    /**
     * Setup click tracking for navigation
     */
    function setupClickTracking() {
        document.querySelectorAll('.nav-toolbar-link, .nav-toolbar-mobile-link, .nav-toolbar-portal-grid-link, .nav-toolbar-quick-link, .nav-toolbar-portal-merge-link').forEach(link => {
            link.addEventListener('click', function(e) {
                const pageId = this.getAttribute('data-page-id');
                
                // Track navigation click
                if (typeof trackAction === 'function') {
                    trackAction('navigation_click', {
                        page_id: pageId,
                        url: this.href
                    });
                }

                // Track with referral system if available
                if (window.ReferralTracker) {
                    try {
                        const tracker = new window.ReferralTracker();
                        tracker.trackClick('navigation', {
                            page_id: pageId,
                            url: this.href
                        });
                    } catch (err) {
                        console.error('Referral tracking error:', err);
                    }
                }
            });
        });
    }

    /**
     * Update currency display
     */
    function updateCurrency(amount) {
        const currencyElement = document.getElementById('navToolbarCurrencyAmount');
        if (currencyElement) {
            currencyElement.textContent = amount.toLocaleString();
        }
    }

    /**
     * Update badge for a navigation link
     */
    function updateBadge(pageId, count) {
        const links = document.querySelectorAll(`[data-page-id="${pageId}"]`);
        links.forEach(link => {
            let badge = link.querySelector('.nav-toolbar-badge');
            if (count > 0) {
                if (!badge) {
                    badge = document.createElement('span');
                    badge.className = 'nav-toolbar-badge';
                    link.appendChild(badge);
                }
                badge.textContent = count > 99 ? '99+' : count;
            } else if (badge) {
                badge.remove();
            }
        });
    }

    /**
     * Refresh navigation (re-highlight, reload currency, etc.)
     */
    function refreshNavigation() {
        highlightActiveLink();
        loadCurrency();
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initToolbar);
    } else {
        initToolbar();
    }

    // Expose API
    window.NavigationToolbar = {
        init: initToolbar,
        refresh: refreshNavigation,
        updateCurrency: updateCurrency,
        updateBadge: updateBadge,
        highlightActive: highlightActiveLink
    };

    /**
     * Setup user controls (user menu, settings, notifications)
     */
    function setupUserControls() {
        const userBtn = document.getElementById('navToolbarUserBtn');
        const settingsBtn = document.getElementById('navToolbarSettingsBtn');
        const notificationsBtn = document.getElementById('navToolbarNotificationsBtn');
        
        if (userBtn) {
            userBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                showUserMenu();
            });
        }
        
        if (settingsBtn) {
            settingsBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                showSettingsMenu();
            });
        }
        
        if (notificationsBtn) {
            notificationsBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                showNotificationsMenu();
            });
        }
        
        // Load notifications count
        loadNotificationsCount();
    }
    
    /**
     * Show user menu
     */
    function showUserMenu() {
        const userId = resolveNavUserId();
        const menu = `
            <div class="nav-toolbar-dropdown" id="userMenuDropdown">
                <div class="nav-toolbar-dropdown-header">
                    <strong id="userMenuHeaderText">👤 ${userId}</strong>
                </div>
                <div class="nav-toolbar-dropdown-item" onclick="window.location.href='/wallets'">
                    <span>⚡</span> MN2 Wallet
                </div>
                <div class="nav-toolbar-dropdown-item" onclick="window.location.href='/profile?tab=wallet'">
                    <span>🌱</span> Staking &amp; deposits
                </div>
                <div class="nav-toolbar-dropdown-item" onclick="window.location.href='/profile'">
                    <span>📊</span> View Profile
                </div>
                <div class="nav-toolbar-dropdown-item" onclick="window.location.href='/profile?tab=points'">
                    <span>📈</span> Points &amp; statistics
                </div>
                <div class="nav-toolbar-dropdown-item" onclick="window.location.href='/achievements'">
                    <span>🏆</span> Achievements
                </div>
                <div class="nav-toolbar-dropdown-item" onclick="showUserSettings()">
                    <span>⚙️</span> Settings
                </div>
                <div class="nav-toolbar-dropdown-item" onclick="logout()">
                    <span>🚪</span> Logout
                </div>
            </div>
        `;
        showDropdown('navToolbarUserBtn', menu);
        loadUserMenuHeader(userId);
    }
    
    /**
     * Load and update the user display name in the top-right user dropdown.
     * Backend: GET /api/user/profile/<user_id>/display -> profile.display_name
     */
    async function loadUserMenuHeader(userId) {
        try {
            const url = `${NAV_CONFIG.apiBase}/api/user/profile/${encodeURIComponent(userId)}/display`;
            const response = await fetch(url);
            if (!response.ok) return;
            const data = await response.json();
            const displayName = data?.profile?.display_name || data?.profile?.username || userId;
            const headerEl = document.getElementById('userMenuHeaderText');
            if (headerEl) headerEl.textContent = `👤 ${displayName}`;
        } catch (e) {
            // Keep fallback userId already rendered in the header.
        }
    }

    /**
     * Show settings menu
     */
    function showSettingsMenu() {
        const menu = `
            <div class="nav-toolbar-dropdown" id="settingsMenuDropdown">
                <div class="nav-toolbar-dropdown-header">
                    <strong>⚙️ Settings</strong>
                </div>
                <div class="nav-toolbar-dropdown-item" onclick="toggleTheme()">
                    <span>🎨</span> Toggle Theme
                </div>
                <div class="nav-toolbar-dropdown-item" onclick="toggleNotifications()">
                    <span>🔔</span> Notifications
                </div>
                <div class="nav-toolbar-dropdown-item" onclick="window.location.href='/debugger'">
                    <span>🔧</span> Debugger
                </div>
                <div class="nav-toolbar-dropdown-item" onclick="clearCache()">
                    <span>🗑️</span> Clear Cache
                </div>
            </div>
        `;
        showDropdown('navToolbarSettingsBtn', menu);
    }
    
    /**
     * Show notifications menu
     */
    function showNotificationsMenu() {
        // Load notifications and show dropdown
        loadNotifications().then(notifications => {
            const menu = `
                <div class="nav-toolbar-dropdown" id="notificationsMenuDropdown">
                    <div class="nav-toolbar-dropdown-header">
                        <strong>🔔 Notifications</strong>
                    </div>
                    ${notifications.length > 0 ? 
                        notifications.map(n => `
                            <div class="nav-toolbar-dropdown-item">
                                <span>${n.icon || '📢'}</span> ${n.message}
                            </div>
                        `).join('') :
                        '<div class="nav-toolbar-dropdown-item" style="opacity: 0.7;">No notifications</div>'
                    }
                </div>
            `;
            showDropdown('navToolbarNotificationsBtn', menu);
        });
    }
    
    /**
     * Show dropdown menu
     */
    function showDropdown(buttonId, menuHTML) {
        // Remove existing dropdowns
        document.querySelectorAll('.nav-toolbar-dropdown').forEach(d => d.remove());
        
        const button = document.getElementById(buttonId);
        if (!button) return;
        
        const dropdown = document.createElement('div');
        dropdown.innerHTML = menuHTML;
        dropdown.className = 'nav-toolbar-dropdown';
        dropdown.style.position = 'absolute';
        dropdown.style.top = button.offsetTop + button.offsetHeight + 'px';
        dropdown.style.right = '10px';
        dropdown.style.zIndex = '1000';
        
        document.body.appendChild(dropdown);
        
        // Close on outside click
        setTimeout(() => {
            document.addEventListener('click', function closeDropdown(e) {
                if (!dropdown.contains(e.target) && !button.contains(e.target)) {
                    dropdown.remove();
                    document.removeEventListener('click', closeDropdown);
                }
            });
        }, 100);
    }
    
    /**
     * Load notifications count
     */
    async function loadNotificationsCount() {
        try {
            const userId = resolveNavUserId();
            const response = await fetch(`${NAV_CONFIG.apiBase}/api/notifications/count?user_id=${userId}`);
            const count = response.ok ? ((await response.json()).count || 0) : 0;
            const badge = document.getElementById('navToolbarNotificationsBadge');
            if (badge) {
                if (count > 0) {
                    badge.textContent = count > 99 ? '99+' : count;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error loading notifications count:', error);
        }
    }
    
    /**
     * Load notifications
     */
    async function loadNotifications() {
        try {
            const userId = resolveNavUserId();
            const response = await fetch(`${NAV_CONFIG.apiBase}/api/notifications?user_id=${userId}`);
            
            if (response.ok) {
                const data = await response.json();
                return data.notifications || [];
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
        return [];
    }
    
    // Helper functions for dropdown actions
    window.showUserSettings = function() {
        alert('User settings - Coming soon!');
    };
    
    window.toggleTheme = function() {
        document.body.classList.toggle('dark-theme');
        localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark' : 'light');
    };
    
    window.toggleNotifications = function() {
        const enabled = localStorage.getItem('notifications_enabled') !== 'false';
        localStorage.setItem('notifications_enabled', !enabled);
        alert(`Notifications ${!enabled ? 'enabled' : 'disabled'}`);
    };
    
    window.clearCache = function() {
        if (confirm('Clear cache? This will reload the page.')) {
            localStorage.clear();
            sessionStorage.clear();
            location.reload();
        }
    };
    
    window.logout = function() {
        if (confirm('Logout?')) {
            fetch('/api/user/logout', { method: 'POST', credentials: 'same-origin' }).catch(function() {});
            localStorage.removeItem('game_user_id');
            localStorage.removeItem('user_id');
            localStorage.removeItem('user_token');
            window.location.href = '/';
        }
    };

    // Auto-refresh on navigation (for SPA-like behavior)
    window.addEventListener('popstate', function() {
        setTimeout(refreshNavigation, 100);
    });

    // Refresh currency periodically
    setInterval(loadCurrency, 120000); // Every 2 minutes (reduced from 30 seconds)
    
    // Refresh notifications count periodically
    setInterval(loadNotificationsCount, 60000); // Every minute

    // Global MN2 bar + wallet quick access + live activity stream on all toolbar pages
    (function loadMn2Global() {
        var mn2Scripts = [
            'mn2-site-bridge.js?v=20260910b',
            'mn2-wallet-quick-access.js?v=20260910a',
            'mn2-global-bar.js?v=20260910a',
            'mn2-activity-stream.js?v=20260614d',
        ];
        mn2Scripts.forEach(function (src) {
            if (document.querySelector('script[src*="' + src.split('?')[0] + '"]')) return;
            var s = document.createElement('script');
            s.src = '/static/js/' + src;
            s.defer = true;
            document.body.appendChild(s);
        });
        if (!document.querySelector('link[href*="mn2-wallet-quick-access.css"]')) {
            var link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = '/static/css/mn2-wallet-quick-access.css?v=20260910a';
            document.head.appendChild(link);
        }
    })();

    // Calm library launcher on non-compendium pages; full reader shell on /compendium/*
    (function loadCalmReader() {
        var path = window.location.pathname || '';
        var onComp = /\/compendium(\/|$)/.test(path);
        var src = onComp ? 'calm-reader.js?v=20260617' : 'reader-launcher.js?v=20260617';
        if (document.querySelector('script[src*="' + src.split('?')[0] + '"]')) return;
        var s = document.createElement('script');
        s.src = '/static/js/' + src;
        s.defer = true;
        document.body.appendChild(s);
    })();

})();

