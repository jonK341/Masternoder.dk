/**
 * Home: smart links, 4D starmap projection, intelligence news
 */
(function () {
    'use strict';

    const BASE = typeof window !== 'undefined' && window.location.origin ? window.location.origin : '';

    const VISIT_KEY = 'mn_nav_visits_v1';
    const SOUND_MODES = {
        focus: {
            label: 'Focus hum',
            status: 'Focus hum online: lavt drone-lag med blød systempuls.',
            wave: 'sine',
            tones: [92, 184, 276],
            filter: 820,
            noise: 0.055,
            beatMs: 2200,
            beatFreq: 740,
        },
        stars: {
            label: 'Star pulse',
            status: 'Star pulse online: lysere arpeggio til Star Map og navigation.',
            wave: 'triangle',
            tones: [136, 272, 408],
            filter: 1380,
            noise: 0.04,
            beatMs: 980,
            beatFreq: 1080,
        },
        battle: {
            label: 'Battle drive',
            status: 'Battle drive online: dybere motor og hurtigere battle-puls.',
            wave: 'sawtooth',
            tones: [55, 110, 165],
            filter: 620,
            noise: 0.075,
            beatMs: 560,
            beatFreq: 320,
        },
    };

    function createNoiseBuffer(ctx) {
        const seconds = 2;
        const buffer = ctx.createBuffer(1, ctx.sampleRate * seconds, ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < data.length; i += 1) {
            data[i] = (Math.random() * 2 - 1) * 0.24;
        }
        return buffer;
    }

    class FrontpageSoundSystem {
        constructor() {
            this.ctx = null;
            this.masterGain = null;
            this.nodes = [];
            this.beatTimer = null;
            this.mode = 'focus';
            this.volume = 0.35;
            this.isActive = false;
        }

        ensureContext() {
            const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
            if (!AudioContextCtor) {
                throw new Error('Web Audio API is not available in this browser');
            }
            if (!this.ctx) {
                this.ctx = new AudioContextCtor();
            }
            if (this.ctx.state === 'suspended') {
                return this.ctx.resume();
            }
            return Promise.resolve();
        }

        async start() {
            if (this.isActive) return;
            await this.ensureContext();
            this.isActive = true;
            this.rebuild();
        }

        stop() {
            this.isActive = false;
            this.clearBeat();
            this.stopNodes();
            if (this.masterGain) {
                const gainToDisconnect = this.masterGain;
                try {
                    gainToDisconnect.gain.cancelScheduledValues(this.ctx.currentTime);
                    gainToDisconnect.gain.setTargetAtTime(0, this.ctx.currentTime, 0.08);
                    setTimeout(() => {
                        try { gainToDisconnect.disconnect(); } catch (_) {}
                        if (this.masterGain === gainToDisconnect) {
                            this.masterGain = null;
                        }
                    }, 180);
                } catch (_) {
                    try { gainToDisconnect.disconnect(); } catch (__) {}
                    if (this.masterGain === gainToDisconnect) {
                        this.masterGain = null;
                    }
                }
            }
        }

        setMode(mode) {
            if (!SOUND_MODES[mode]) return;
            this.mode = mode;
            if (this.isActive) {
                this.rebuild();
                this.playPing(900, 0.025);
            }
        }

        setVolume(value) {
            this.volume = Math.max(0, Math.min(1, value));
            this.applyVolume();
        }

        rebuild() {
            if (!this.ctx || !this.isActive) return;
            this.clearBeat();
            this.stopNodes();
            if (this.masterGain) {
                try { this.masterGain.disconnect(); } catch (_) {}
                this.masterGain = null;
            }

            const config = SOUND_MODES[this.mode] || SOUND_MODES.focus;
            this.masterGain = this.ctx.createGain();
            this.masterGain.gain.value = 0;
            this.masterGain.connect(this.ctx.destination);
            this.applyVolume();

            const droneFilter = this.ctx.createBiquadFilter();
            droneFilter.type = 'lowpass';
            droneFilter.frequency.value = config.filter;
            droneFilter.Q.value = 0.7;
            droneFilter.connect(this.masterGain);
            this.nodes.push(droneFilter);

            config.tones.forEach((freq, index) => {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.type = config.wave;
                osc.frequency.value = freq;
                osc.detune.value = (index - 1) * 5;
                gain.gain.value = 0.035 / (index + 1);
                osc.connect(gain);
                gain.connect(droneFilter);
                osc.start();
                this.nodes.push(osc, gain);
            });

            const noise = this.ctx.createBufferSource();
            noise.buffer = createNoiseBuffer(this.ctx);
            noise.loop = true;
            const noiseFilter = this.ctx.createBiquadFilter();
            const noiseGain = this.ctx.createGain();
            noiseFilter.type = 'bandpass';
            noiseFilter.frequency.value = config.filter * 0.9;
            noiseFilter.Q.value = 0.5;
            noiseGain.gain.value = config.noise;
            noise.connect(noiseFilter);
            noiseFilter.connect(noiseGain);
            noiseGain.connect(this.masterGain);
            noise.start();
            this.nodes.push(noise, noiseFilter, noiseGain);

            this.playPing(config.beatFreq, 0.028);
            this.beatTimer = window.setInterval(() => this.playPing(config.beatFreq, 0.022), config.beatMs);
        }

        applyVolume() {
            if (!this.masterGain || !this.ctx) return;
            const target = this.isActive ? Math.pow(this.volume, 1.35) * 0.085 : 0;
            try {
                this.masterGain.gain.cancelScheduledValues(this.ctx.currentTime);
                this.masterGain.gain.setTargetAtTime(target, this.ctx.currentTime, 0.08);
            } catch (_) {
                this.masterGain.gain.value = target;
            }
        }

        playPing(freq, level) {
            if (!this.ctx || !this.masterGain || !this.isActive) return;
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, now);
            gain.gain.setValueAtTime(0.0001, now);
            gain.gain.exponentialRampToValueAtTime(level, now + 0.015);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
            osc.connect(gain);
            gain.connect(this.masterGain);
            osc.start(now);
            osc.stop(now + 0.2);
        }

        stopNodes() {
            this.nodes.forEach((node) => {
                try {
                    if (typeof node.stop === 'function') node.stop();
                } catch (_) {}
                try { node.disconnect(); } catch (_) {}
            });
            this.nodes = [];
        }

        clearBeat() {
            if (this.beatTimer) {
                window.clearInterval(this.beatTimer);
                this.beatTimer = null;
            }
        }
    }

    function wireSoundSystem() {
        const primaryToggle = document.getElementById('themeSoundToggle');
        const floatToggle = document.getElementById('themeSoundFloatToggle');
        const volume = document.getElementById('themeSoundVolume');
        const status = document.getElementById('themeSoundStatus');
        const modeButtons = Array.from(document.querySelectorAll('[data-sound-mode]'));
        if (!primaryToggle && !floatToggle) return;

        const sound = new FrontpageSoundSystem();

        const render = () => {
            const mode = SOUND_MODES[sound.mode] || SOUND_MODES.focus;
            document.body.classList.toggle('mn-sound-active', sound.isActive);
            if (primaryToggle) {
                primaryToggle.setAttribute('aria-pressed', String(sound.isActive));
                primaryToggle.innerHTML = `<span class="fp-sound-led" aria-hidden="true"></span>${sound.isActive ? 'Stop sound' : 'Start sound'}`;
            }
            if (floatToggle) {
                floatToggle.textContent = sound.isActive ? `${mode.label} on` : 'Sound offline';
            }
            if (status) {
                status.textContent = sound.isActive ? mode.status : 'Sound offline. Klik start for at aktivere.';
            }
            modeButtons.forEach((button) => {
                const active = button.dataset.soundMode === sound.mode;
                button.classList.toggle('is-active', active);
                button.setAttribute('aria-pressed', String(active));
            });
        };

        const toggle = async () => {
            if (sound.isActive) {
                sound.stop();
                render();
                return;
            }
            try {
                await sound.start();
            } catch (err) {
                if (status) status.textContent = 'Sound kunne ikke starte i denne browser.';
                console.warn('[Frontpage] sound', err);
            }
            render();
        };

        if (primaryToggle) primaryToggle.addEventListener('click', toggle);
        if (floatToggle) floatToggle.addEventListener('click', toggle);
        if (volume) {
            sound.setVolume(parseInt(volume.value, 10) / 100);
            volume.addEventListener('input', () => {
                sound.setVolume(parseInt(volume.value, 10) / 100);
                if (sound.isActive) sound.playPing(620 + sound.volume * 420, 0.015);
            });
        }
        modeButtons.forEach((button) => {
            button.addEventListener('click', () => {
                sound.setMode(button.dataset.soundMode);
                render();
            });
        });
        document.querySelectorAll('.fp-smart-card, .fp-portal-card, .fp-agent-card, .fp-primary-action, .fp-secondary-action, .fp-mn2-double-tile, .fp-mn2-badge, .fp-mn2-link').forEach((el) => {
            el.addEventListener('mouseenter', () => sound.playPing(880, 0.012));
            el.addEventListener('focus', () => sound.playPing(880, 0.012));
        });
        render();
    }

    function readVisits() {
        try {
            const raw = localStorage.getItem(VISIT_KEY);
            return raw ? JSON.parse(raw) : {};
        } catch (_) {
            return {};
        }
    }

    function bumpVisit(path) {
        try {
            const v = readVisits();
            v[path] = (v[path] || 0) + 1;
            localStorage.setItem(VISIT_KEY, JSON.stringify(v));
        } catch (_) {}
    }

    function wireVisitTracking() {
        document.querySelectorAll('a[href^="/"]').forEach((a) => {
            a.addEventListener('click', () => {
                try {
                    const u = new URL(a.getAttribute('href'), window.location.origin);
                    bumpVisit(u.pathname);
                } catch (_) {}
            });
        });
    }

    function topPicksIds() {
        if (typeof window !== 'undefined' && window.MN_NAV_TOP_PICKS_IDS && window.MN_NAV_TOP_PICKS_IDS.length) {
            return window.MN_NAV_TOP_PICKS_IDS.slice();
        }
        if (typeof window !== 'undefined' && window.MN_NAV_TOP_20_IDS && window.MN_NAV_TOP_20_IDS.length) {
            return window.MN_NAV_TOP_20_IDS.slice();
        }
        return [
            'generator', 'game', 'battle', 'trophies', 'explorer', 'shop',
            'creator', 'casino', 'wallets', 'agents', 'news', 'library',
        ];
    }

    function normalizePath(href) {
        try {
            const u = new URL(href, window.location.origin);
            let p = u.pathname.replace(/\/+$/, '') || '/';
            if (u.search) p += u.search;
            return p;
        } catch (_) {
            return href;
        }
    }

    function getPortalCatalog() {
        const raw = (typeof window !== 'undefined' && window.MN_NAV_LINKS) || [];
        return raw
            .filter((link) => link.id && link.id !== 'home')
            .map((link) => ({
                id: link.id,
                href: link.url.replace(window.location.origin, '') || link.url,
                label: link.name,
                icon: link.icon || '🔗',
                title: link.title || '',
            }));
    }

    function visitScore(href, visits) {
        const path = normalizePath(href);
        const alt = path.endsWith('/') && path.length > 1 ? path.slice(0, -1) : `${path}/`;
        return Math.max(visits[path] || 0, visits[alt] || 0);
    }

    function renderPortalGrid(links, visits, variant) {
        const sorted = [...links].sort((a, b) => {
            const diff = visitScore(b.href, visits) - visitScore(a.href, visits);
            if (diff !== 0) return diff;
            return a.label.localeCompare(b.label);
        });

        return `<div class="fp-portal-grid">${sorted
            .map((p) => {
                const n = visitScore(p.href, visits);
                const why = n >= 3 ? `${n} besøg` : (p.title || 'Portal');
                const titleAttr = p.title ? ` title="${p.title.replace(/"/g, '&quot;')}"` : '';
                return `<a class="fp-portal-card fp-portal-card--${variant}" href="${p.href}"${titleAttr}>
            <span class="icon">${p.icon}</span>
            <span class="label">${p.label}</span>
            <span class="why">${why}</span>
        </a>`;
            })
            .join('')}</div>`;
    }

    function renderClusterAccordions(catalog, visits) {
        const groups = (typeof window !== 'undefined' && window.MN_NAV_GROUPS) || [];
        const used = new Set();

        const sections = groups.map((grp) => {
            const grpLinks = catalog.filter((l) => l.group === grp.id);
            grpLinks.forEach((l) => used.add(l.id));
            if (!grpLinks.length) return '';
            const hub = grp.hubId ? catalog.find((l) => l.id === grp.hubId) : null;
            const hubLine = hub
                ? `<p class="fp-portal-merge">Hub: <a href="${hub.href}">${hub.label}</a>${grp.summary ? ` · ${grp.summary}` : ''}</p>`
                : (grp.summary ? `<p class="fp-portal-merge">${grp.summary}</p>` : '');
            return `<section class="fp-portal-accordion" data-cluster="${grp.id}">
                <button type="button" class="fp-portal-accordion-trigger" aria-expanded="false" aria-controls="fp-cluster-${grp.id}" id="fp-cluster-btn-${grp.id}">
                    <span class="fp-portal-accordion-label"><span aria-hidden="true">${grp.icon}</span> ${grp.label}</span>
                    <span class="fp-portal-accordion-meta">
                        <span class="fp-portal-accordion-count">${grpLinks.length}</span>
                        <span class="fp-portal-accordion-chevron" aria-hidden="true">▾</span>
                    </span>
                </button>
                <div class="fp-portal-accordion-panel" id="fp-cluster-${grp.id}" role="region" aria-labelledby="fp-cluster-btn-${grp.id}" hidden>
                    ${hubLine}
                    ${renderPortalGrid(grpLinks, visits, 'more')}
                </div>
            </section>`;
        }).join('');

        const orphan = catalog.filter((l) => !used.has(l.id));
        const orphanBlock = orphan.length
            ? `<section class="fp-portal-accordion" data-cluster="other">
                <button type="button" class="fp-portal-accordion-trigger" aria-expanded="false" aria-controls="fp-cluster-other" id="fp-cluster-btn-other">
                    <span class="fp-portal-accordion-label"><span aria-hidden="true">🔗</span> Other</span>
                    <span class="fp-portal-accordion-meta"><span class="fp-portal-accordion-count">${orphan.length}</span><span class="fp-portal-accordion-chevron" aria-hidden="true">▾</span></span>
                </button>
                <div class="fp-portal-accordion-panel" id="fp-cluster-other" role="region" aria-labelledby="fp-cluster-btn-other" hidden>
                    ${renderPortalGrid(orphan, visits, 'more')}
                </div>
            </section>`
            : '';

        return sections + orphanBlock;
    }

    function setFpAccordionOpen(accordion, open) {
        if (!accordion) return;
        const trigger = accordion.querySelector('.fp-portal-accordion-trigger');
        const panel = accordion.querySelector('.fp-portal-accordion-panel');
        if (!trigger || !panel) return;
        trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
        accordion.classList.toggle('is-open', open);
        panel.hidden = !open;
    }

    function wirePortalAccordions() {
        const root = document.getElementById('fp-portals-clusters');
        if (!root) return;

        root.querySelectorAll('.fp-portal-accordion-trigger').forEach((trigger) => {
            trigger.addEventListener('click', () => {
                const accordion = trigger.closest('.fp-portal-accordion');
                const isOpen = trigger.getAttribute('aria-expanded') === 'true';
                root.querySelectorAll('.fp-portal-accordion').forEach((acc) => {
                    if (acc !== accordion) setFpAccordionOpen(acc, false);
                });
                setFpAccordionOpen(accordion, !isOpen);
            });
        });

        const first = root.querySelector('.fp-portal-accordion');
        if (first) setFpAccordionOpen(first, true);
    }

    function buildPortalGrids() {
        const quickEl = document.getElementById('fp-portals-quick');
        const clustersEl = document.getElementById('fp-portals-clusters');
        if (!quickEl || !clustersEl) return;

        const catalog = getPortalCatalog().map((l) => {
            const raw = (window.MN_NAV_LINKS || []).find((n) => n.id === l.id);
            return raw ? { ...l, group: raw.group || null } : l;
        });
        const visits = readVisits();
        const pickIds = topPicksIds();
        const pickLinks = pickIds.map((id) => catalog.find((l) => l.id === id)).filter(Boolean);

        quickEl.innerHTML = renderPortalGrid(pickLinks, visits, 'top');
        clustersEl.innerHTML = renderClusterAccordions(catalog, visits);

        const hint = document.getElementById('fp-portal-hint');
        if (hint) {
            hint.textContent = `${pickLinks.length} hurtige genveje · ${catalog.length} portaler i 6 klynger nedenfor.`;
        }

        wirePortalAccordions();
    }

    function wireMissionTabs(starmap) {
        const tabs = Array.from(document.querySelectorAll('[data-fp-tab]'));
        const panels = Array.from(document.querySelectorAll('[data-fp-panel]'));
        if (!tabs.length || !panels.length) return;

        const activate = (id) => {
            tabs.forEach((tab) => {
                const active = tab.dataset.fpTab === id;
                tab.classList.toggle('is-active', active);
                tab.setAttribute('aria-selected', String(active));
            });
            panels.forEach((panel) => {
                const active = panel.dataset.fpPanel === id;
                panel.classList.toggle('is-active', active);
                panel.hidden = !active;
            });
            if (id === 'live' && starmap) {
                window.requestAnimationFrame(() => starmap.resize());
            }
            try {
                localStorage.setItem('fp_mission_tab_v1', id);
            } catch (_) {}
        };

        tabs.forEach((tab) => {
            tab.addEventListener('click', () => activate(tab.dataset.fpTab));
        });

        let saved = '';
        try {
            saved = localStorage.getItem('fp_mission_tab_v1') || '';
        } catch (_) {}
        if (saved && tabs.some((t) => t.dataset.fpTab === saved)) {
            activate(saved);
        }
    }


    async function loadNews() {
        const ul = document.getElementById('fp-news-list');
        if (!ul) return;
        ul.innerHTML = '<li class="fp-muted">Henter nyheder…</li>';
        try {
            const [platformRes, profitRes, feedRes] = await Promise.all([
                fetch(`${BASE}/api/news/platform?limit=5`).then((r) => r.json()).catch(() => ({ news: [] })),
                fetch(`${BASE}/api/profit-daemon/news?limit=4`).then((r) => r.json()).catch(() => ({ news: [] })),
                fetch(`${BASE}/api/aggregators/intelligence/news?limit=5`).then((r) => r.json()).catch(() => ({ news: [] })),
            ]);
            const profit = (profitRes && profitRes.news) || [];
            const platform = (platformRes && platformRes.news) || [];
            const profitIds = new Set(profit.map((n) => n.id));
            const platformFiltered = platform.filter((n) => !profitIds.has(n.id));
            const mergedPlatform = [...profit, ...platformFiltered].slice(0, 6);
            const external = (feedRes && feedRes.news) || [];
            if (!mergedPlatform.length && !external.length) {
                ul.innerHTML = '<li class="fp-muted">Ingen nyheder lige nu.</li>';
                return;
            }
            ul.textContent = '';
            mergedPlatform.forEach((n) => {
                const li = document.createElement('li');
                li.className = 'fp-news-platform' + ((n.channel || n.category) === 'profit' ? ' fp-news-profit' : '');
                const a = document.createElement('a');
                a.href = n.href || '/news/';
                a.textContent = (n.title || 'Platform update');
                const meta = document.createElement('span');
                meta.className = 'fp-news-meta';
                meta.textContent = ((n.channel || n.category) === 'profit' ? 'Profit · ' : 'MasterNoder · ') + (n.date || '').slice(0, 10);
                li.appendChild(a);
                li.appendChild(meta);
                if (n.summary) {
                    const sum = document.createElement('span');
                    sum.className = 'fp-news-summary';
                    sum.textContent = n.summary;
                    li.appendChild(sum);
                }
                ul.appendChild(li);
            });
            if (mergedPlatform.length && external.length) {
                const sep = document.createElement('li');
                sep.className = 'fp-news-divider';
                sep.textContent = 'Tech feed';
                ul.appendChild(sep);
            }
            external.forEach((n) => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = n.url || '#';
                a.target = '_blank';
                a.rel = 'noopener noreferrer';
                a.textContent = n.title || 'Uden titel';
                const meta = document.createElement('span');
                meta.className = 'fp-news-meta';
                const src = n.source || 'feed';
                const pub = (n.published || '').slice(0, 16);
                meta.textContent = `${src} · ${pub}`;
                li.appendChild(a);
                li.appendChild(meta);
                ul.appendChild(li);
            });
        } catch (_) {
            ul.innerHTML = '<li class="fp-muted">Nyheder midlertidigt utilgængelige.</li>';
        }
    }

    const SEGMENTUM_INDEX = {
        Solar: 0,
        Obscurus: 1,
        Pacificus: 2,
        Tempestus: 3,
        Ultima: 4,
        Unknown: 5,
    };

    function segmentumPhase(seg) {
        const k = SEGMENTUM_INDEX[seg] != null ? SEGMENTUM_INDEX[seg] : 5;
        return (k / 6) * Math.PI * 2;
    }

    function rotate4D(x, y, z, w, a1, a2) {
        const c1 = Math.cos(a1);
        const s1 = Math.sin(a1);
        let x1 = x * c1 - z * s1;
        let y1 = y;
        let z1 = x * s1 + z * c1;
        let w1 = w;

        const c2 = Math.cos(a2);
        const s2 = Math.sin(a2);
        const y2 = y1 * c2 - w1 * s2;
        const w2 = y1 * s2 + w1 * c2;
        return { x: x1, y: y2, z: z1, w: w2 };
    }

    function stereographic3(x, y, z, w) {
        const denom = 1.0001 - w;
        return { x: x / denom, y: y / denom, z: z / denom };
    }

    function dprScale(W) {
        return Math.min(W / 400, 1.8);
    }

    class StarMap4D {
        constructor(canvasId) {
            this.canvas = document.getElementById(canvasId);
            this.points = [];
            this.slider = document.getElementById('fp-starmap-w');
            this.t0 = performance.now();
            this._raf = null;
            window.addEventListener('resize', () => this.resize());
        }

        resize() {
            if (!this.canvas) return;
            const rect = this.canvas.getBoundingClientRect();
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            const w = Math.max(320, Math.floor(rect.width * dpr));
            const h = Math.floor(Math.max(260, rect.width * 0.42) * dpr);
            this.canvas.width = w;
            this.canvas.height = h;
        }

        async load() {
            if (!this.canvas) return;
            try {
                const res = await fetch(`${BASE}/api/star-map/25`);
                const data = await res.json();
                const sm = data && data.star_map_25;
                this.points = (sm && sm.points) || [];
            } catch (_) {
                this.points = [];
            }
            this.resize();
            this.startLoop();
        }

        startLoop() {
            if (this._raf) cancelAnimationFrame(this._raf);
            const tick = () => {
                this.drawFrame();
                this._raf = requestAnimationFrame(tick);
            };
            this._raf = requestAnimationFrame(tick);
        }

        drawFrame() {
            if (!this.canvas) return;
            const ctx = this.canvas.getContext('2d');
            const W = this.canvas.width;
            const H = this.canvas.height;
            if (W < 8 || H < 8) return;

            ctx.fillStyle = '#06060c';
            ctx.fillRect(0, 0, W, H);

            const cx = W * 0.5;
            const cy = H * 0.52;
            const scale = Math.min(W, H) * 0.22;

            const wSlider = this.slider ? parseInt(this.slider.value, 10) / 100 : 0.5;
            const t = (performance.now() - this.t0) / 1000;
            const a1 = t * 0.35 + wSlider * Math.PI;
            const a2 = t * 0.22 + wSlider * Math.PI * 0.5;

            if (!this.points.length) {
                ctx.fillStyle = 'rgba(255,255,255,0.5)';
                ctx.font = '14px system-ui,sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('Ingen stjernedata — tjek /api/star-map/25', cx, cy);
                ctx.textAlign = 'start';
                return;
            }

            const n = this.points.length;
            const ds = dprScale(W);
            this.points.forEach((p, i) => {
                const base = segmentumPhase(p.segmentum || 'Unknown');
                const u = i / n;
                const theta = base + u * Math.PI * 2;
                const phi = Math.acos(2 * u - 1) * 0.92;
                const r = 0.55 + (p.point_value || 10) / 40 * 0.25;
                const x = r * Math.sin(phi) * Math.cos(theta);
                const y = r * Math.sin(phi) * Math.sin(theta);
                const z = r * Math.cos(phi);
                const w4 = (u * 2 - 1) * 0.65 + (wSlider - 0.5) * 0.4;

                const q = rotate4D(x, y, z, w4, a1, a2);
                const proj = stereographic3(q.x, q.y, q.z, q.w);

                const px = cx + proj.x * scale;
                const py = cy + proj.y * scale;
                const size = 3.2 + ((p.point_value || 10) / 18) * ds;
                const hue = 140 + wSlider * 80 + (p.index || i) * 3;

                ctx.beginPath();
                ctx.arc(px, py, size, 0, Math.PI * 2);
                ctx.fillStyle = `hsla(${hue % 360}, 75%, 58%, 0.92)`;
                ctx.fill();
                ctx.strokeStyle = 'rgba(255,255,255,0.25)';
                ctx.lineWidth = 1;
                ctx.stroke();

                if (W > 700 && i < 18) {
                    ctx.font = `${10 * (W / 900)}px system-ui, sans-serif`;
                    ctx.fillStyle = 'rgba(230,240,255,0.5)';
                    const name = (p.name || p.id || '').slice(0, 22);
                    ctx.fillText(name, px + size + 2, py + 3);
                }
            });

            ctx.fillStyle = 'rgba(200,200,255,0.45)';
            ctx.font = `${11 * (W / 900)}px system-ui`;
            ctx.fillText('4D → stereographic 3D · tid (w) roterer hyper-rummet', 12, H - 12);
        }
    }

    function wireDailyMicroTxClaim() {
        const g = typeof window !== 'undefined' ? window : globalThis;
        if (g.MN2MicroTx && typeof g.MN2MicroTx.wireDailyClaimButton === 'function') {
            g.MN2MicroTx.wireDailyClaimButton('fp-claim-daily-btn');
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        buildPortalGrids();
        loadNews();
        wireVisitTracking();
        wireSoundSystem();
        const sm = new StarMap4D('fp-starmap4d');
        sm.load();
        wireMissionTabs(sm);
        wireDailyMicroTxClaim();
    });
})();
