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

    const POOL = [
        { href: '/generator', label: 'Generator', icon: '🎬', tags: ['create', 'morning'] },
        { href: '/game', label: 'Game', icon: '🎮', tags: ['play', 'evening'] },
        { href: '/battle', label: 'Battle', icon: '⚔️', tags: ['compete'] },
        { href: '/starmap25/', label: 'Star Map 25', icon: '🗺️', tags: ['explore'] },
        { href: '/profile', label: 'Profile', icon: '👤', tags: ['account'] },
        { href: '/shop', label: 'Shop', icon: '🛒', tags: ['economy'] },
        { href: '/quests', label: 'Quests', icon: '📜', tags: ['progress'] },
        { href: '/trophies', label: 'Trophies', icon: '🏆', tags: ['collect'] },
        { href: '/agents', label: 'AI Agents', icon: '🤖', tags: ['agents'] },
        { href: '/lab', label: 'Lab', icon: '🔬', tags: ['agents'] },
        { href: '/debugger', label: 'Debugger', icon: '🔧', tags: ['dev'] },
        { href: '/gallery', label: 'Gallery', icon: '🖼️', tags: ['create'] },
        { href: '/chat', label: 'Chat', icon: '💬', tags: ['social'] },
        { href: '/news', label: 'News page', icon: '📰', tags: ['read'] },
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
            const [platformRes, feedRes] = await Promise.all([
                fetch(`${BASE}/api/news/platform?limit=5`).then((r) => r.json()).catch(() => ({ news: [] })),
                fetch(`${BASE}/api/aggregators/intelligence/news?limit=5`).then((r) => r.json()).catch(() => ({ news: [] })),
            ]);
            const platform = (platformRes && platformRes.news) || [];
            const external = (feedRes && feedRes.news) || [];
            if (!platform.length && !external.length) {
                ul.innerHTML = '<li class="fp-muted">Ingen nyheder lige nu.</li>';
                return;
            }
            ul.textContent = '';
            platform.forEach((n) => {
                const li = document.createElement('li');
                li.className = 'fp-news-platform';
                const a = document.createElement('a');
                a.href = n.href || '/news/';
                a.textContent = (n.title || 'Platform update');
                const meta = document.createElement('span');
                meta.className = 'fp-news-meta';
                meta.textContent = 'MasterNoder · ' + (n.date || '').slice(0, 10);
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
            if (platform.length && external.length) {
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

    document.addEventListener('DOMContentLoaded', () => {
        buildSmartLinks();
        loadNews();
        wireVisitTracking();
        wireSoundSystem();
        const sm = new StarMap4D('fp-starmap4d');
        sm.load();
    });
})();
