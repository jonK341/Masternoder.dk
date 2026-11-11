/**
 * Home: smart links, Profit Daemon monitor, intelligence news
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
                        try { gainToDisconnect.disconnect(); } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'frontpage-home.js', context: 'catch' }); }}
                        if (this.masterGain === gainToDisconnect) {
                            this.masterGain = null;
                        }
                    }, 180);
                } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'frontpage-home.js', context: 'catch' }); }
                    try { gainToDisconnect.disconnect(); } catch (__) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(__ instanceof Error ? __ : new Error(String(__)), { source: 'frontpage-home.js', context: 'catch' }); }}
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
                try { this.masterGain.disconnect(); } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'frontpage-home.js', context: 'catch' }); }}
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
            } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'frontpage-home.js', context: 'catch' }); }
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
                } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'frontpage-home.js', context: 'catch' }); }}
                try { node.disconnect(); } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'frontpage-home.js', context: 'catch' }); }}
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

    const SOUND_VOL_KEY = 'mn_sound_analog_volume_v1';

    function volumeToDb(linear) {
        const v = Math.max(0.0001, Math.min(1, linear));
        return 20 * Math.log10(v);
    }

    function analogGain(linear) {
        return Math.pow(Math.max(0, Math.min(1, linear)), 1.35);
    }

    function updateSoundbarUI(linear) {
        const dbEl = document.getElementById('themeSoundDb');
        const pctEl = document.getElementById('themeSoundPct');
        const pct = Math.round(linear * 100);
        const analog = analogGain(linear);
        if (dbEl) dbEl.textContent = volumeToDb(analog * 0.85).toFixed(1) + ' dB';
        if (pctEl) pctEl.textContent = pct + '%';
    }

    function wireSoundSystem() {
        const primaryToggle = document.getElementById('themeSoundToggle');
        const floatToggle = document.getElementById('themeSoundFloatToggle');
        const volume = document.getElementById('themeSoundVolume');
        const status = document.getElementById('themeSoundStatus');
        const modeButtons = Array.from(document.querySelectorAll('[data-sound-mode]'));
        if (!primaryToggle && !floatToggle) return;

        const sound = new FrontpageSoundSystem();
        try {
            const saved = parseInt(localStorage.getItem(SOUND_VOL_KEY), 10);
            if (!Number.isNaN(saved) && saved >= 0 && saved <= 100 && volume) {
                volume.value = String(saved);
                sound.setVolume(saved / 100);
            }
        } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'frontpage-home.js', context: 'catch' }); }}

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
                status.textContent = sound.isActive
                    ? mode.status + ' · Soundbar analog: ' + Math.round(sound.volume * 100) + '%'
                    : 'Sound offline. Klik start for at aktivere.';
            }
            updateSoundbarUI(sound.volume);
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
            } catch (err) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(err instanceof Error ? err : new Error(String(err)), { source: 'frontpage-home.js', context: 'catch' }); }
                if (status) status.textContent = 'Sound kunne ikke starte i denne browser.';
                console.warn('[Frontpage] sound', err);
            }
            render();
        };

        if (primaryToggle) primaryToggle.addEventListener('click', toggle);
        if (floatToggle) floatToggle.addEventListener('click', toggle);
        if (volume) {
            const applyVol = () => {
                const lin = parseInt(volume.value, 10) / 100;
                sound.setVolume(lin);
                try { localStorage.setItem(SOUND_VOL_KEY, String(volume.value)); } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'frontpage-home.js', context: 'catch' }); }}
                volume.setAttribute('aria-valuetext', volume.value + ' procent');
                updateSoundbarUI(lin);
                if (sound.isActive) sound.playPing(620 + lin * 420, 0.015);
            };
            applyVol();
            volume.addEventListener('input', applyVol);
        }

        const pwaDl = document.getElementById('fp-download-pwa');
        if (pwaDl) {
            pwaDl.addEventListener('click', (ev) => {
                if (window.__mnInstallPwa) {
                    ev.preventDefault();
                    window.__mnInstallPwa();
                }
            });
        }
        modeButtons.forEach((button) => {
            button.addEventListener('click', () => {
                sound.setMode(button.dataset.soundMode);
                render();
            });
        });
        document.querySelectorAll('.fp-smart-card, .fp-agent-card, .fp-primary-action, .fp-secondary-action').forEach((el) => {
            el.addEventListener('mouseenter', () => sound.playPing(880, 0.012));
            el.addEventListener('focus', () => sound.playPing(880, 0.012));
        });
        render();
    }

    function readVisits() {
        try {
            const raw = localStorage.getItem(VISIT_KEY);
            return raw ? JSON.parse(raw) : {};
        } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'frontpage-home.js', context: 'catch' }); }
            return {};
        }
    }

    function bumpVisit(path) {
        try {
            const v = readVisits();
            v[path] = (v[path] || 0) + 1;
            localStorage.setItem(VISIT_KEY, JSON.stringify(v));
        } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'frontpage-home.js', context: 'catch' }); }}
    }

    function wireVisitTracking() {
        document.querySelectorAll('a[href^="/"]').forEach((a) => {
            a.addEventListener('click', () => {
                try {
                    const u = new URL(a.getAttribute('href'), window.location.origin);
                    bumpVisit(u.pathname);
                } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'frontpage-home.js', context: 'catch' }); }}
            });
        });
    }

    const POOL = [
        { href: '/generator', label: 'Generator', icon: '🎬', tags: ['create', 'morning'] },
        { href: '/game', label: 'Game', icon: '🎮', tags: ['play', 'evening'] },
        { href: '/battle', label: 'Battle', icon: '⚔️', tags: ['compete'] },
        { href: '/wallets', label: 'Wallets', icon: '💾', tags: ['economy', 'account'] },
        { href: '/staking-leaderboard', label: 'Staking Rank', icon: '🌱', tags: ['economy', 'progress'] },
        { href: '/staking-teams', label: 'Staking Teams', icon: '🤝', tags: ['economy', 'progress'] },
        { href: '/shop', label: 'Shop', icon: '🛒', tags: ['economy'] },
        { href: '/nft', label: 'NFT Hub', icon: '💎', tags: ['economy', 'collect'] },
        { href: '/exchange', label: 'Exchange', icon: '💱', tags: ['economy'] },
        { href: '/explorer', label: 'Explorer', icon: '🔎', tags: ['economy', 'explore'] },
        { href: '/profile', label: 'Profile', icon: '👤', tags: ['account'] },
        { href: '/quests', label: 'Quests', icon: '📜', tags: ['progress'] },
        { href: '/trophies', label: 'Trophies', icon: '🏆', tags: ['collect'] },
        { href: '/agents', label: 'AI Agents', icon: '🤖', tags: ['agents'] },
        { href: '/podcast', label: 'Podcast', icon: '🎙️', tags: ['read'] },
        { href: '/news', label: 'News', icon: '📰', tags: ['read'] },
        { href: '/compendium/?calm=1', label: 'Library', icon: '📖', tags: ['read'] },
        { href: '/lab', label: 'Lab', icon: '🔬', tags: ['agents'] },
        { href: '/debugger', label: 'Debugger', icon: '🔧', tags: ['dev'] },
        { href: '/gallery', label: 'Gallery', icon: '🖼️', tags: ['create'] },
        { href: '/starmap25/', label: 'Star Map 25', icon: '🗺️', tags: ['explore'] },
        { href: '/profit/', label: 'Profit Daemon', icon: '⚡', tags: ['economy', 'evening'] },
    ];

    function hourTag() {
        const h = new Date().getHours();
        if (h >= 5 && h < 12) return 'morning';
        if (h >= 12 && h < 17) return 'day';
        if (h >= 17 && h < 23) return 'evening';
        return 'night';
    }

    function buildSmartLinks() {
        const el = document.getElementById('fp-smart-links');
        if (!el) return;

        const visits = readVisits();
        const ht = hourTag();

        const scored = POOL.map((p) => {
            let score = 0;
            const u = new URL(p.href, window.location.origin);
            score += (visits[u.pathname] || 0) * 3;
            if (p.tags && p.tags.includes(ht)) score += 2;
            if (ht === 'morning' && p.tags && p.tags.includes('create')) score += 1;
            if (ht === 'evening' && p.tags && p.tags.includes('play')) score += 1;
            return { ...p, score };
        });

        scored.sort((a, b) => b.score - a.score);

        const pick = [];
        const seen = new Set();
        for (const p of scored) {
            if (pick.length >= 6) break;
            if (seen.has(p.href)) continue;
            seen.add(p.href);
            pick.push(p);
        }

        const whyFor = (p) => {
            const u = new URL(p.href, window.location.origin);
            const n = visits[u.pathname] || 0;
            if (n >= 3) return 'Ofte brugt — hurtig genvej';
            if (p.tags && p.tags.includes(ht)) return 'Valgt til dit tidspunkt på dagen';
            if (p.href.indexOf('starmap') !== -1) return 'Kort over systemer';
            return 'Anbefalet på tværs af platformen';
        };

        el.innerHTML = `<div class="fp-smart-grid">${pick
            .map(
                (p) => `<a class="fp-smart-card" href="${p.href}">
            <span class="icon">${p.icon}</span>
            <span class="label">${p.label}</span>
            <span class="why">${whyFor(p)}</span>
        </a>`
            )
            .join('')}</div>`;
    }

    async function loadNews() {
        const ul = document.getElementById('fp-news-list');
        if (!ul) return;
        ul.innerHTML = '<li class="fp-muted">Henter nyheder…</li>';
        try {
            const [platformRes, profitRes, feedRes] = await Promise.all([
                fetch(`${BASE}/api/news/platform?limit=5`).then((r) => r.json()).catch(() => ({ if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'frontpage-home.js', context: 'catch' }); } news: [] })),
                fetch(`${BASE}/api/profit-daemon/news?limit=4`).then((r) => r.json()).catch(() => ({ if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'frontpage-home.js', context: 'catch' }); } news: [] })),
                fetch(`${BASE}/api/aggregators/intelligence/news?limit=5`).then((r) => r.json()).catch(() => ({ if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(new Error('caught'), { source: 'frontpage-home.js', context: 'catch' }); } news: [] })),
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
        } catch (_) { if (window.ErrorManager && window.ErrorManager.logJSError) { window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), { source: 'frontpage-home.js', context: 'catch' }); }
            ul.innerHTML = '<li class="fp-muted">Nyheder midlertidigt utilgængelige.</li>';
        }
    }

    function escHtml(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
            return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
        });
    }

    function voterId(key) {
        try {
            var id = localStorage.getItem(key);
            if (!id) {
                id = 'v' + Math.random().toString(36).slice(2, 10);
                localStorage.setItem(key, id);
            }
            return id;
        } catch (_) {
            return 'anon';
        }
    }

    class ProfitDaemonMonitor {
        constructor() {
            this.root = document.querySelector('.fp-profit-monitor');
            this._timer = null;
        }

        start() {
            if (!this.root) return;
            this.bindVotes();
            this.refresh();
            this._timer = setInterval(() => this.refresh(), 8000);
        }

        bindVotes() {
            var self = this;
            var localBtn = document.getElementById('fp-profit-vote-local');
            var subBtn = document.getElementById('fp-profit-vote-sub');
            var dcBtn = document.getElementById('fp-profit-vote-dc');
            if (localBtn) localBtn.onclick = function () { self.vote('local'); };
            if (subBtn) subBtn.onclick = function () { self.vote('youtube_subscriber'); };
            if (dcBtn) dcBtn.onclick = function () { self.vote('discord'); };
        }

        vote(audience) {
            var body = { voter: voterId('fp_profit_vote_' + audience), audience: audience };
            if (audience === 'youtube_subscriber') {
                body.self_attest_subscriber = true;
            }
            if (audience === 'discord') {
                body.discord_id = voterId('fp_profit_discord_id');
            }
            fetch(BASE + '/api/youtube/trade-stream-interest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            })
                .then(function (r) { return r.json(); })
                .then(() => this.refresh())
                .catch(function (_) { /* ignore */ });
        }

        async refresh() {
            var self = this;
            try {
                var streamRes = await fetch(BASE + '/api/youtube/trade-stream-interest?with_trades=1');
                var stream = await streamRes.json();
                self.paintInterest(stream.interest || stream);
                self.paintFeed(stream.trades || []);
            } catch (_) {
                if (window.ErrorManager && window.ErrorManager.logJSError) {
                    window.ErrorManager.logJSError(_ instanceof Error ? _ : new Error(String(_)), {
                        source: 'frontpage-home.js',
                        context: 'profit-stream',
                    });
                }
                var feed = document.getElementById('fp-profit-feed');
                if (feed) feed.innerHTML = '<div class="fp-profit-empty">Trade stream unavailable.</div>';
            }
            try {
                var stRes = await fetch(BASE + '/api/profit-daemon/status');
                var st = await stRes.json();
                self.paintDaemon(st);
            } catch (_) {
                var dEl = document.getElementById('fp-profit-daemon');
                if (dEl) dEl.textContent = 'daemon offline';
            }
        }

        paintInterest(interest) {
            interest = interest || {};
            var audiences = interest.audiences || {};
            var local = audiences.local || {};
            var sub = audiences.youtube_subscriber || {};
            var dc = audiences.discord || {};
            var modeEl = document.getElementById('fp-profit-mode');
            var localEl = document.getElementById('fp-profit-votes-local');
            var subEl = document.getElementById('fp-profit-votes-sub');
            var dcEl = document.getElementById('fp-profit-votes-dc');
            if (localEl) {
                localEl.textContent = 'local ' + (local.votes || interest.local_votes || 0) + '/' + (local.threshold || interest.local_threshold || 5);
                localEl.className = 'fp-profit-pill' + (local.interested_enough ? ' hot' : '');
            }
            if (subEl) {
                subEl.textContent = 'subscribers ' + (sub.votes || interest.subscriber_votes || 0) + '/' + (sub.threshold || interest.subscriber_threshold || 5);
                subEl.className = 'fp-profit-pill yt' + (sub.interested_enough ? ' hot' : '');
            }
            if (dcEl) {
                dcEl.textContent = 'discord ' + (dc.votes || interest.discord_votes || 0) + '/' + (dc.threshold || interest.discord_threshold || 5);
                dcEl.className = 'fp-profit-pill dc' + (dc.interested_enough ? ' hot' : '');
            }
            if (modeEl) {
                modeEl.textContent = interest.interested_enough ? 'ready for YouTube' : 'collecting interest';
                modeEl.className = 'fp-profit-pill' + (interest.interested_enough ? ' hot' : '');
            }
        }

        paintDaemon(st) {
            st = st || {};
            var dEl = document.getElementById('fp-profit-daemon');
            var mode = st.mode || st.daemon_mode || '—';
            var profile = st.profile || '';
            var running = !!st.running;
            if (dEl) {
                dEl.textContent = (running ? (st.health || 'live') : 'idle') + ' · ' + String(mode)
                    + (profile ? ' · ' + profile : '');
                dEl.className = 'fp-profit-pill' + (running ? ' hot' : '');
            }
            var byName = {};
            var loops = st.loops || [];
            if (Array.isArray(loops)) {
                loops.forEach(function (row) {
                    if (row && row.loop) byName[row.loop] = row;
                });
            } else if (loops && typeof loops === 'object') {
                byName = loops;
            }
            var hl = st.highlights || {};
            var exchange = byName.exchange || {};
            var fast = byName.fast || {};
            var kpis = document.getElementById('fp-profit-kpis');
            if (!kpis) return;
            var ready = st.profit_readiness_pct;
            var rows = [
                ['Health', st.health || (running ? 'online' : 'offline')],
                ['Arb', hl.arb_exec || '—'],
                ['Best', hl.best_bps != null ? (Number(hl.best_bps).toFixed(1) + ' bps') : '—'],
                ['Fast', (fast.summary || exchange.summary || '—').toString().slice(0, 48)],
                ['Readiness', ready != null && ready !== '' ? (Number(ready).toFixed(0) + '%') : '—'],
            ];
            kpis.innerHTML = rows.map(function (r) {
                return '<div class="fp-profit-kpi"><div class="l">' + escHtml(r[0]) + '</div><div class="v">' + escHtml(r[1]) + '</div></div>';
            }).join('');
        }

        paintFeed(trades) {
            var el = document.getElementById('fp-profit-feed');
            if (!el) return;
            var rows = (trades || []).slice().reverse().slice(0, 20);
            if (!rows.length) {
                el.innerHTML = '<div class="fp-profit-empty">Waiting for live fills…</div>';
                return;
            }
            el.innerHTML = rows.map(function (r) {
                var dlt = Number(r.delta_usd || 0);
                var cls = dlt > 0 ? 'pos' : (dlt < 0 ? 'neg' : '');
                var ts = String(r.ts || '').replace('T', ' ').slice(11, 19);
                return '<div class="fp-profit-row"><div class="t">' + escHtml(ts) + '</div><div class="m"><span class="tag">'
                    + escHtml(r.strategy || 'trade') + '</span>' + escHtml(r.message || '') + '</div><div class="d ' + cls + '">'
                    + (dlt ? ((dlt > 0 ? '+' : '') + dlt.toFixed(2)) : '—') + '</div></div>';
            }).join('');
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        buildSmartLinks();
        wireVisitTracking();
        wireSoundSystem();
        const runWhenIdle = (fn) => {
            if (typeof requestIdleCallback !== 'undefined') {
                requestIdleCallback(fn, { timeout: 4000 });
            } else {
                setTimeout(fn, 300);
            }
        };
        runWhenIdle(() => {
            loadNews();
            const mon = new ProfitDaemonMonitor();
            mon.start();
        });
    });
})();
