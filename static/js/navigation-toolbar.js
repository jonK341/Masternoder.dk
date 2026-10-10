/**
 * Navigation Toolbar - Universal navigation system
 * Provides consistent navigation across all pages
 */

(function() {
    'use strict';

    const APP_BASE = (typeof window !== 'undefined' && window.APP_BASE !== undefined) ? window.APP_BASE : '';
    const NAV_PORTAL_ASSET_V = '20261002';

    /** Every page with the toolbar gets tema CSS before first paint when possible. */
    (function ensureNavPortalThemesCss() {
        if (typeof document === 'undefined' || !document.head) return;
        var href = APP_BASE + '/static/css/nav-portal-themes.css?v=' + NAV_PORTAL_ASSET_V;
        if (document.querySelector('link[href*="nav-portal-themes.css"]')) return;
        var link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        document.head.appendChild(link);
    })();

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
        staking_teams: APP_BASE + '/static/img/agents/social_engagement_agent.svg'
    };

        // Navigation configuration — primary product loop first, deep portals later.
    const NAV_CONFIG = {
        brand: {
            name: 'MasterNoder',
            icon: '🏠',
            iconImg: APP_BASE + '/static/img/nav/brand.svg',
            url: APP_BASE + '/'
        },
        favorites: ['generator', 'game', 'battle', 'trophies'], /* overridden by NavPortalTemplate */
        links: [
            { name: 'Home', icon: '🏠', url: APP_BASE + '/', id: 'home' },
            { name: 'Generator', icon: '🎬', url: APP_BASE + '/generator', id: 'generator', favorite: true },
            { name: 'Game', icon: '🎮', url: APP_BASE + '/game', id: 'game', favorite: true },
            { name: 'Battle', icon: '⚔️', url: APP_BASE + '/battle', id: 'battle', favorite: true },
            { name: 'Trophies', icon: '🏆', url: APP_BASE + '/trophies', id: 'trophies', favorite: true },
            { name: 'Quests', icon: '📜', url: APP_BASE + '/quests', id: 'quests' },
            { name: 'Shop', icon: '🛒', url: APP_BASE + '/shop', id: 'shop' },
            { name: 'Explorer', icon: '🔎', url: APP_BASE + '/explorer', id: 'explorer', title: 'MN2 Crypto Hub: explorer, staking, reserves, market' },
            { name: 'Profile', icon: '👤', url: APP_BASE + '/profile', id: 'profile', title: 'Points, stats, leaderboard, shop & inventory' },
            { name: 'AI Agents', icon: '🤖', url: APP_BASE + '/agents', id: 'agents' },
            { name: 'Podcast', icon: '🎙️', url: APP_BASE + '/podcast', id: 'podcast', title: 'YouTube, Facebook, Discord, GitHub — crypto rewards & AI encoder' },
            { name: 'Create App', icon: '📱', url: APP_BASE + '/create-app', id: 'create_app', title: 'Play Store + Podcast TWA · Super Encoder nr. 1 · 100 finish checks · MN2 rewards' },
            { name: 'News', icon: '📰', url: APP_BASE + '/news', id: 'news' },
            { name: 'Library', icon: '📖', url: APP_BASE + '/compendium/?calm=1', id: 'library', title: 'Calm reading — rulebooks V1–V16, compendium points' },
            { name: 'Lab', icon: '🔬', url: APP_BASE + '/lab', id: 'lab', title: 'Discussion, experiments, and system lab' },
            { name: 'Agent Support', icon: '🛠️', url: APP_BASE + '/agent_support', id: 'agent_support', title: 'Tickets, AI API keys, tools' },
            { name: 'Debugger', icon: '🔧', url: APP_BASE + '/debugger', id: 'debugger' },
            { name: 'Aggregator', icon: '📡', url: APP_BASE + '/aggregator', id: 'aggregator', title: '75 AI aggregators — catalog, top 25, control panel' },
            { name: 'Casino', icon: '🎰', url: APP_BASE + '/casino/', id: 'casino' },
            { name: 'Battlegrounds', icon: '🗺️', url: APP_BASE + '/battlegrounds', id: 'battlegrounds' },
            { name: 'Star Map 25', icon: '🗺️', url: APP_BASE + '/starmap25', id: 'starmap25' },
            { name: 'Gallery', icon: '🖼️', url: APP_BASE + '/gallery', id: 'gallery' },
            { name: 'Social', icon: '👥', url: APP_BASE + '/social', id: 'social' },
            { name: 'Wallets', icon: '💾', url: APP_BASE + '/wallets', id: 'wallets', title: 'MN2 wallet portal: deposit, withdraw, trusted addresses, and downloads' },
            { name: 'Exchange', icon: '💱', url: APP_BASE + '/exchange', id: 'exchange', title: '25-crypto exchange — swap, limits, staking, tax records' },
            { name: 'Market', icon: '📈', url: APP_BASE + '/market', id: 'market', title: 'P2P MN2 marketplace' },
            { name: 'NFT Hub', icon: '💎', url: APP_BASE + '/nft', id: 'nft', title: 'Numbered NFT editions — primary, resale, profile avatar' },
            { name: 'Staking Rank', icon: '🌱', url: APP_BASE + '/staking-leaderboard', id: 'staking_leaderboard', title: 'MN2 staking leaderboard' },
            { name: 'Staking Teams', icon: '🤝', url: APP_BASE + '/staking-teams', id: 'staking_teams', title: 'MN2 staking team leaderboard' },
            { name: 'Profit Daemon', icon: '⚡', url: APP_BASE + '/profit/', id: 'profit', title: '24/7 live profit daemon monitor, news, rentals' },
            { name: 'Agents Control', icon: '🤖', url: APP_BASE + '/dashboard/agents_control', id: 'agents_control', title: 'Agents control board' },
            { name: 'Customers', icon: '👥', url: APP_BASE + '/customers', id: 'customers', title: 'Customer directory' },
            { name: 'Hosting', icon: '🖥️', url: APP_BASE + '/hosting', id: 'hosting', title: 'Masternode hosting' },
            { name: 'Camgirls', icon: '💃', url: APP_BASE + '/camgirls', id: 'camgirls' }
        ],
        apiBase: window.location.origin + APP_BASE
    };

    var NAV_CAT_GIF_BASE = APP_BASE + '/static/img/nav/categories/';
    var NAV_CATEGORIES = [];

    function syncFromPortalTemplate() {
        var tpl = window.NavPortalTemplate;
        if (!tpl) return;
        NAV_CATEGORIES = tpl.getCategories();
        NAV_CAT_GIF_BASE = tpl.categoryGifBase();
        NAV_CONFIG.favorites = tpl.getFavorites();
    }

    function ensurePortalTemplate(done) {
        function run() {
            if (!window.NavPortalTemplate) {
                done();
                return;
            }
            window.NavPortalTemplate.boot().then(function () {
                syncFromPortalTemplate();
                done();
            }).catch(function () {
                done();
            });
            return;
        }
        if (window.NavPortalTemplate) {
            run();
            return;
        }
        var src = APP_BASE + '/static/js/nav-portal-template.js?v=' + NAV_PORTAL_ASSET_V;
        if (document.querySelector('script[src*="nav-portal-template.js"]')) {
            var waited = 0;
            var timer = setInterval(function () {
                waited += 50;
                if (window.NavPortalTemplate || waited > 3000) {
                    clearInterval(timer);
                    run();
                }
            }, 50);
            return;
        }
        var s = document.createElement('script');
        s.src = src;
        s.async = true;
        s.onload = run;
        s.onerror = function () { done(); };
        document.head.appendChild(s);
    }

    function _renderCategoryGif(cat, className) {
        const src = NAV_CAT_GIF_BASE + (cat.gif || cat.id + '.gif');
        const cls = className || 'nav-toolbar-cat-gif';
        return (
            '<img class="' + cls + '" src="' + src + '" alt="" width="28" height="28" loading="lazy" decoding="async">' +
            '<span class="nav-toolbar-cat-smiley" aria-hidden="true">' + (cat.smiley || '✨') + '</span>'
        );
    }

    function _renderCategoryMenuHead(cat) {
        const title = cat.menuTitle || cat.label;
        return (
            '<div class="nav-toolbar-cat-menu-head" data-nav-cat-head="' + cat.id + '">' +
            _renderCategoryGif(cat, 'nav-toolbar-cat-gif nav-toolbar-cat-gif--menu') +
            '<div class="nav-toolbar-cat-menu-head-text">' +
            '<strong>' + title + '</strong>' +
            '<span class="nav-toolbar-cat-menu-sub">' + cat.label + '</span>' +
            '</div></div>'
        );
    }

    function _linksById() {
        const map = {};
        NAV_CONFIG.links.forEach(function (link) {
            map[link.id] = link;
        });
        return map;
    }

    function _renderCategoryMenuLinks(links, linkClass, catSmiley) {
        return links.map(function (link) {
            const smiley = link.icon || catSmiley || '✨';
            const extraCls = linkClass ? ' ' + linkClass : '';
            return (
                '<a href="' + link.url + '" class="nav-toolbar-cat-link' + extraCls + '" data-page-id="' + link.id + '"' +
                (link.title ? ' title="' + link.title.replace(/"/g, '&quot;') + '"' : '') + '>' +
                '<span class="nav-toolbar-cat-link-smiley" aria-hidden="true">' + smiley + '</span>' +
                _renderIcon(link, { extraClass: ' nav-toolbar-cat-link-icon-wrap' }) +
                '<span class="nav-toolbar-cat-link-label">' + link.name + '</span>' +
                '</a>'
            );
        }).join('');
    }

    function _renderCategoryDropdowns(byId) {
        return NAV_CATEGORIES.map(function (cat) {
            const items = cat.ids.map(function (id) { return byId[id]; }).filter(Boolean);
            if (!items.length) return '';
            return (
                '<div class="nav-toolbar-cat" data-nav-cat="' + cat.id + '">' +
                '<button type="button" class="nav-toolbar-cat-btn" aria-expanded="false" aria-haspopup="true" aria-label="' + cat.label + ' menu">' +
                '<span class="nav-toolbar-cat-btn-art">' + _renderCategoryGif(cat, 'nav-toolbar-cat-gif nav-toolbar-cat-gif--btn') + '</span>' +
                '<span class="nav-toolbar-cat-label">' + cat.label + '</span>' +
                '<span class="nav-toolbar-cat-chevron" aria-hidden="true">▾</span>' +
                '</button>' +
                '<div class="nav-toolbar-cat-menu" role="menu" hidden data-nav-cat-menu="' + cat.id + '">' +
                _renderCategoryMenuHead(cat) +
                '<div class="nav-toolbar-cat-menu-links">' +
                _renderCategoryMenuLinks(items, '', cat.smiley) +
                '</div></div></div>'
            );
        }).join('');
    }

    function _renderCategorizedPortalPanel(byId) {
        return NAV_CATEGORIES.map(function (cat) {
            const items = cat.ids.map(function (id) { return byId[id]; }).filter(Boolean);
            if (!items.length) return '';
            return (
                '<section class="nav-toolbar-portal-section" aria-labelledby="nav-cat-' + cat.id + '">' +
                '<h3 class="nav-toolbar-portal-section-title" id="nav-cat-' + cat.id + '">' +
                '<span class="nav-toolbar-portal-section-art">' + _renderCategoryGif(cat, 'nav-toolbar-cat-gif nav-toolbar-cat-gif--section') + '</span>' +
                '<span>' + (cat.menuTitle || cat.label) + '</span></h3>' +
                '<div class="nav-toolbar-portal-grid">' +
                items.map(function (link) {
                    return _renderLinkAnchor(link, 'nav-toolbar-portal-grid-link');
                }).join('') +
                '</div></section>'
            );
        }).join('');
    }

    function _renderMobileMenuGrouped(byId) {
        const home = byId.home;
        let html = '';
        if (home) {
            html += '<a href="' + home.url + '" class="nav-toolbar-mobile-link" data-page-id="home">' +
                _renderIcon(home) + '<span>' + home.name + '</span></a>';
        }
        NAV_CATEGORIES.forEach(function (cat) {
            const items = cat.ids.map(function (id) { return byId[id]; }).filter(Boolean);
            if (!items.length) return;
            html += '<div class="nav-toolbar-mobile-group"><div class="nav-toolbar-mobile-group-title">' +
                '<span class="nav-toolbar-mobile-cat-smiley" aria-hidden="true">' + (cat.smiley || '') + '</span>' +
                (cat.menuTitle || cat.label) + '</div>';
            items.forEach(function (link) {
                const fav = link.favorite ? ' nav-toolbar-mobile-link-favorite' : '';
                html += '<a href="' + link.url + '" class="nav-toolbar-mobile-link' + fav + '" data-page-id="' + link.id + '">' +
                    _renderIcon(link) + '<span>' + link.name + '</span></a>';
            });
            html += '</div>';
        });
        return html;
    }

    function _renderUserBlock() {
        return (
            '<div class="nav-toolbar-user">' +
            '<div class="nav-toolbar-user-controls" id="navToolbarUserControls">' +
            '<button class="nav-toolbar-control-btn" id="navToolbarUserBtn" title="User Settings"><span>👤</span></button>' +
            '<button class="nav-toolbar-control-btn" id="navToolbarSettingsBtn" title="Settings"><span>⚙️</span></button>' +
            '<button class="nav-toolbar-control-btn" id="navToolbarNotificationsBtn" title="Notifications">' +
            '<span>🔔</span><span class="nav-toolbar-badge" id="navToolbarNotificationsBadge" style="display: none;">0</span></button>' +
            '</div>' +
            '<div class="nav-toolbar-currency" id="navToolbarCurrency">' +
            '<span class="nav-toolbar-currency-icon">🪙</span><span id="navToolbarCurrencyAmount">0</span></div>' +
            '<button class="nav-toolbar-toggle" id="navToolbarToggle" aria-label="Toggle menu">☰</button>' +
            '</div>'
        );
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
        const portalVoid = window.NavPortalTemplate
            ? window.NavPortalTemplate.isPortalVoid()
            : (typeof window !== 'undefined' && window.MN_NAV_PORTAL_VOID);
        const byId = _linksById();
        const categorizedPanelHTML = _renderCategorizedPortalPanel(byId);
        const favoriteLinksHTML = NAV_CONFIG.favorites.map(function (id) {
            const link = byId[id];
            return link ? _renderLinkAnchor(link, 'nav-toolbar-link--quick') : '';
        }).join('');
        const categoryDropdownsHTML = _renderCategoryDropdowns(byId);
        const mobileGroupedHTML = _renderMobileMenuGrouped(byId);

        if (portalVoid) {
            return `
            <nav class="nav-toolbar nav-toolbar--portal-void nav-toolbar--categorized" id="navToolbar">
                <div class="nav-toolbar-content">
                    <a href="${NAV_CONFIG.brand.url}" class="nav-toolbar-brand">
                        ${_renderIcon(NAV_CONFIG.brand, { extraClass: ' nav-toolbar-brand-icon-wrap', pulse: true, large: true })}
                        <span>${NAV_CONFIG.brand.name}</span>
                    </a>

                    <div class="nav-toolbar-portal-wrap">
                        <button type="button" class="nav-toolbar-portal-trigger" id="navPortalTrigger" aria-expanded="false" aria-haspopup="true" aria-controls="navPortalPanel">
                            <span class="nav-toolbar-portal-trigger-icon nav-toolbar-portal-trigger-icon--spin">🌀</span>
                            <span>Portals</span>
                        </button>
                    </div>

                    ${_renderUserBlock()}
                </div>

                <div id="navPortalPanel" class="nav-toolbar-portal-panel" role="menu" aria-hidden="true" hidden>
                    <div class="nav-toolbar-portal-inner">
                        <p class="nav-toolbar-portal-hint">Browse by category — all site portals</p>
                        <div class="nav-toolbar-portal-sections" id="navPortalGrid">
                            ${categorizedPanelHTML}
                        </div>
                    </div>
                </div>
            </nav>`;
        }

        return `
            <nav class="nav-toolbar nav-toolbar--categorized" id="navToolbar">
                <div class="nav-toolbar-content">
                    <a href="${NAV_CONFIG.brand.url}" class="nav-toolbar-brand">
                        ${_renderIcon(NAV_CONFIG.brand, { extraClass: ' nav-toolbar-brand-icon-wrap', pulse: true, large: true })}
                        <span>${NAV_CONFIG.brand.name}</span>
                    </a>
                    
                    <div class="nav-toolbar-nav" id="navToolbarLinks">
                        <div class="nav-toolbar-quick">${favoriteLinksHTML}</div>
                        <div class="nav-toolbar-categories">${categoryDropdownsHTML}</div>
                    </div>
                    
                    ${_renderUserBlock()}
                </div>
                
                <div class="nav-toolbar-mobile" id="navToolbarMobile">
                    ${mobileGroupedHTML}
                </div>
            </nav>
        `;
    }

    /**
     * Initialize navigation toolbar
     */
    function mountToolbar() {
        const toolbarHTML = createToolbarHTML();
        document.body.insertAdjacentHTML('afterbegin', toolbarHTML);
        highlightActiveLink();
        setupMobileMenu();
        setupCategoryMenus();
        loadCurrency();
        setupClickTracking();
        setupUserControls();
        ensureGlobalSystems();
    }

    function initToolbar() {
        if (document.getElementById('navToolbar')) {
            return;
        }
        ensurePortalTemplate(function () {
            if (!NAV_CATEGORIES.length) {
                NAV_CATEGORIES = [
                    { id: 'play', label: 'Play', menuTitle: 'Play portals', smiley: '🎮', gif: 'play.gif', ids: ['game', 'battle', 'trophies', 'quests', 'casino', 'battlegrounds', 'starmap25'] },
                    { id: 'account', label: 'Shop & profile', menuTitle: 'Shop & profile', smiley: '🛒', gif: 'account.gif', ids: ['shop', 'profile', 'market'] },
                    { id: 'finance', label: 'MN2 & exchange', menuTitle: 'MN2 & exchange', smiley: '💠', gif: 'finance.gif', ids: ['exchange', 'nft', 'wallets', 'explorer', 'profit', 'staking_leaderboard', 'staking_teams', 'hosting', 'market'] },
                    { id: 'create', label: 'Create', menuTitle: 'Create & publish', smiley: '🎬', gif: 'create.gif', ids: ['generator', 'create_app', 'podcast', 'gallery'] },
                    { id: 'intel', label: 'Lab & agents', menuTitle: 'Lab & agents', smiley: '🤖', gif: 'intel.gif', ids: ['lab', 'aggregator', 'agents', 'agent_support', 'agents_control', 'debugger'] },
                    { id: 'social', label: 'Social & news', menuTitle: 'Social & news', smiley: '💬', gif: 'social.gif', ids: ['social', 'news', 'library', 'camgirls', 'customers'] },
                ];
            }
            mountToolbar();
        });
    }

    function reinitToolbar() {
        var el = document.getElementById('navToolbar');
        if (el) el.remove();
        syncFromPortalTemplate();
        mountToolbar();
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
        document.querySelectorAll('.nav-toolbar-link, .nav-toolbar-mobile-link, .nav-toolbar-portal-grid-link, .nav-toolbar-cat-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelectorAll('.nav-toolbar-cat-btn').forEach(function (btn) {
            btn.classList.remove('active');
        });

        // Find and highlight active link
        document.querySelectorAll('.nav-toolbar-link, .nav-toolbar-mobile-link, .nav-toolbar-portal-grid-link, .nav-toolbar-cat-link').forEach(link => {
            const linkUrl = new URL(link.href, window.location.origin);
            const linkPath = linkUrl.pathname;

            // Exact match or starts with (for sub-pages)
            if (linkPath === currentPath || 
                (currentPath.startsWith(linkPath) && linkPath !== '/')) {
                link.classList.add('active');
                const catWrap = link.closest('.nav-toolbar-cat');
                if (catWrap) {
                    const btn = catWrap.querySelector('.nav-toolbar-cat-btn');
                    if (btn) btn.classList.add('active');
                }
            }
        });
    }

    /**
     * Category dropdowns in the compact top bar
     */
    function setupCategoryMenus() {
        const cats = document.querySelectorAll('.nav-toolbar-cat');
        if (!cats.length) return;

        function closeAll(except) {
            cats.forEach(function (wrap) {
                if (except && wrap === except) return;
                wrap.classList.remove('open');
                const menu = wrap.querySelector('.nav-toolbar-cat-menu');
                const btn = wrap.querySelector('.nav-toolbar-cat-btn');
                if (menu) menu.hidden = true;
                if (btn) btn.setAttribute('aria-expanded', 'false');
            });
        }

        cats.forEach(function (wrap) {
            const btn = wrap.querySelector('.nav-toolbar-cat-btn');
            const menu = wrap.querySelector('.nav-toolbar-cat-menu');
            if (!btn || !menu) return;

            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                const willOpen = !wrap.classList.contains('open');
                closeAll();
                if (willOpen) {
                    wrap.classList.add('open');
                    menu.hidden = false;
                    btn.setAttribute('aria-expanded', 'true');
                }
            });

            menu.querySelectorAll('a').forEach(function (a) {
                a.addEventListener('click', function () {
                    closeAll();
                });
            });
        });

        document.addEventListener('click', function (e) {
            const t = e.target;
            let inside = false;
            cats.forEach(function (wrap) {
                if (wrap.contains(t)) inside = true;
            });
            if (!inside) closeAll();
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeAll();
        });
    }

    /**
     * Setup mobile menu toggle
     */
    function setupMobileMenu() {
        const portalVoid = window.NavPortalTemplate
            ? window.NavPortalTemplate.isPortalVoid()
            : (typeof window !== 'undefined' && window.MN_NAV_PORTAL_VOID);
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
    async function loadCurrency() {
        try {
            const userId = localStorage.getItem('game_user_id') || 'default_user';
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
        document.querySelectorAll('.nav-toolbar-link, .nav-toolbar-mobile-link, .nav-toolbar-portal-grid-link').forEach(link => {
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
        reinit: reinitToolbar,
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
        const userId = localStorage.getItem('game_user_id') || 'default_user';
        const menu = `
            <div class="nav-toolbar-dropdown" id="userMenuDropdown">
                <div class="nav-toolbar-dropdown-header">
                    <strong id="userMenuHeaderText">👤 ${userId}</strong>
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
        var themeItems = '';
        var templateItems = '';
        if (window.NavPortalTemplate) {
            window.NavPortalTemplate.listThemes().forEach(function (th) {
                themeItems += '<div class="nav-toolbar-dropdown-item" onclick="applyNavTheme(\'' + th.id + '\')"><span>🎨</span> Tema: ' + th.label + '</div>';
            });
            window.NavPortalTemplate.listTemplates().forEach(function (tp) {
                templateItems += '<div class="nav-toolbar-dropdown-item" onclick="applyNavTemplate(\'' + tp.id + '\')"><span>📂</span> Template: ' + tp.label + '</div>';
            });
        }
        const menu = `
            <div class="nav-toolbar-dropdown" id="settingsMenuDropdown">
                <div class="nav-toolbar-dropdown-header">
                    <strong>⚙️ Settings</strong>
                </div>
                <div class="nav-toolbar-dropdown-header" style="font-size:0.75rem;opacity:0.85">Portal tema</div>
                ${themeItems || '<div class="nav-toolbar-dropdown-item" onclick="toggleTheme()"><span>🎨</span> Toggle Theme</div>'}
                <div class="nav-toolbar-dropdown-header" style="font-size:0.75rem;opacity:0.85;margin-top:6px">Portal template</div>
                ${templateItems || '<div class="nav-toolbar-dropdown-item" style="opacity:0.6">Templates loading…</div>'}
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
            const userId = localStorage.getItem('game_user_id') || 'default_user';
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
            const userId = localStorage.getItem('game_user_id') || 'default_user';
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

    window.applyNavTheme = function (themeId) {
        if (!window.NavPortalTemplate) return;
        window.NavPortalTemplate.setTheme(themeId, true);
        window.NavPortalTemplate.applyAndReloadToolbar();
    };

    window.applyNavTemplate = function (templateId) {
        if (!window.NavPortalTemplate) return;
        window.NavPortalTemplate.setTemplate(templateId, true);
        window.NavPortalTemplate.applyAndReloadToolbar();
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

    // Global MN2 bar + live activity stream on all toolbar pages
    (function loadMn2Global() {
        ['mn2-site-bridge.js?v=20260614d', 'mn2-global-bar.js?v=20260614d', 'mn2-activity-stream.js?v=20260614d'].forEach(function (src) {
            if (document.querySelector('script[src*="' + src.split('?')[0] + '"]')) return;
            var s = document.createElement('script');
            s.src = '/static/js/' + src;
            s.defer = true;
            document.body.appendChild(s);
        });
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

