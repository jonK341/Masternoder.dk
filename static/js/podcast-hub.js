(function () {
    'use strict';

    const USER_ID = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
    const API = (path, opts) => fetch(path, opts).then(r => r.json());

    function qs(sel) { return document.querySelector(sel); }
    function qsa(sel) { return document.querySelectorAll(sel); }

    let currentEpisode = null;
    let audioCtx = null;
    let analyser = null;
    let vizRAF = null;
    let vizMode = 'bars';
    let audioSourceNode = null;
    let episodeQueue = JSON.parse(localStorage.getItem('podcast_queue') || '[]');

    qsa('.podcast-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            qsa('.podcast-tab').forEach(b => b.classList.remove('active'));
            qsa('.podcast-panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            qs('#panel-' + btn.dataset.tab).classList.add('active');
            location.hash = btn.dataset.tab;
        });
    });

    function openTabFromHash() {
        const h = (location.hash || '').replace('#', '');
        if (!h) return;
        const tab = h.startsWith('news') ? 'news' : h;
        const btn = qs('.podcast-tab[data-tab="' + tab + '"]');
        if (btn) btn.click();
    }

    async function runSoundCheck(repair) {
        const banner = qs('#sound-banner');
        if (!banner) return;
        try {
            const url = '/api/podcast/sound-check' + (repair ? '?repair=1' : '');
            const r = await API(repair ? url : url, repair ? { method: 'POST' } : undefined);
            if (!r.success) { banner.textContent = 'Sound check failed'; banner.className = 'podcast-sound-banner warn'; return; }
            const msg = `🔊 Audio: ${r.ok}/${r.total} episodes ready` + (r.missing ? ` · ${r.missing} pending repair` : '');
            banner.textContent = msg;
            banner.className = 'podcast-sound-banner ' + (r.missing ? 'warn' : 'ok');
            if (r.missing > 0 && !repair) {
                const fix = await API('/api/podcast/sound-check?repair=1', { method: 'POST' });
                if (fix.ok === fix.total) {
                    banner.textContent = `🔊 All ${fix.total} episodes — sound verified & repaired`;
                    banner.className = 'podcast-sound-banner ok';
                }
            }
        } catch (e) {
            banner.textContent = 'Sound check unavailable';
            banner.className = 'podcast-sound-banner warn';
        }
    }

    function setupVisualizer(audio) {
        const canvas = qs('#podcast-visualizer');
        if (!canvas || !audio) return;
        try {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            if (audioCtx.state === 'suspended') audioCtx.resume();
            if (!analyser) {
                analyser = audioCtx.createAnalyser();
                analyser.fftSize = 128;
            }
            if (!audioSourceNode) {
                audioSourceNode = audioCtx.createMediaElementSource(audio);
                audioSourceNode.connect(analyser);
                analyser.connect(audioCtx.destination);
            }
            const buf = new Uint8Array(analyser.frequencyBinCount);
            const ctx = canvas.getContext('2d');
            const draw = () => {
                vizRAF = requestAnimationFrame(draw);
                analyser.getByteFrequencyData(buf);
                const w = canvas.width;
                const h = canvas.height;
                ctx.fillStyle = 'rgba(6, 16, 24, 0.35)';
                ctx.fillRect(0, 0, w, h);
                if (vizMode === 'bubbles') {
                    for (let i = 0; i < buf.length; i += 3) {
                        const v = buf[i] / 255;
                        const x = (i / buf.length) * w + Math.sin(Date.now() / 400 + i) * 8;
                        const r = 4 + v * 22;
                        const g = ctx.createRadialGradient(x, h / 2, 0, x, h / 2, r);
                        g.addColorStop(0, '#ffd54f');
                        g.addColorStop(0.6, '#4fc3f7');
                        g.addColorStop(1, 'transparent');
                        ctx.fillStyle = g;
                        ctx.beginPath();
                        ctx.arc(x, h / 2 - v * 30, r, 0, Math.PI * 2);
                        ctx.fill();
                    }
                } else {
                    const barW = w / buf.length;
                    for (let i = 0; i < buf.length; i++) {
                        const bh = (buf[i] / 255) * h * 0.9;
                        const g = ctx.createLinearGradient(0, h, 0, h - bh);
                        g.addColorStop(0, '#1e88e5');
                        g.addColorStop(0.5, '#4fc3f7');
                        g.addColorStop(1, '#ffd54f');
                        ctx.fillStyle = g;
                        ctx.fillRect(i * barW, h - bh, barW - 2, bh);
                    }
                }
            };
            if (vizRAF) cancelAnimationFrame(vizRAF);
            draw();
        } catch (e) {
            /* visualizer optional */
        }
    }

    function saveQueue() {
        localStorage.setItem('podcast_queue', JSON.stringify(episodeQueue));
        renderQueue();
    }

    function renderQueue() {
        const el = qs('#queue-list');
        if (!el) return;
        if (!episodeQueue.length) { el.hidden = true; return; }
        el.hidden = false;
        el.innerHTML = episodeQueue.map((id, i) =>
            `<li data-idx="${i}">${id} <button type="button" class="podcast-btn queue-remove" data-idx="${i}">×</button></li>`
        ).join('');
        el.querySelectorAll('.queue-remove').forEach(btn => {
            btn.addEventListener('click', () => {
                episodeQueue.splice(Number(btn.dataset.idx), 1);
                saveQueue();
            });
        });
    }

    async function loadChapters(episodeId) {
        const el = qs('#chapters-list');
        if (!el) return;
        const r = await API('/api/podcast/episodes/' + episodeId + '/chapters');
        if (!r.success) { el.innerHTML = ''; return; }
        el.innerHTML = (r.chapters || []).map(ch =>
            `<button type="button" class="podcast-chapter-btn" data-sec="${ch.start_sec}">${ch.title} (${ch.start_sec}s)</button>`
        ).join('');
        el.querySelectorAll('.podcast-chapter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const audio = qs('#audio-player');
                if (audio) { audio.currentTime = Number(btn.dataset.sec) || 0; audio.play().catch(() => {}); }
            });
        });
    }

    async function loadTranscript(episodeId) {
        const box = qs('#transcript-box');
        const pre = qs('#transcript-text');
        if (!box || !pre) return;
        const r = await API('/api/podcast/episodes/' + episodeId + '/transcript');
        if (!r.success) { box.hidden = true; return; }
        pre.textContent = r.transcript || '';
        box.hidden = false;
    }

    async function loadSoundLab() {
        const grid = qs('#sound-lab-grid');
        if (!grid) return;
        const r = await API('/api/podcast/sound-lab');
        if (!r.success) { grid.textContent = 'Sound Lab unavailable.'; return; }
        grid.innerHTML = `
            <p class="episode-meta">${r.ok}/${r.total} ready · ${(r.total_bytes || 0).toLocaleString()} bytes · ffmpeg: ${r.ffmpeg || 'n/a'}</p>
            ${(r.episodes || []).map(e => `
                <div class="sound-lab-row ${e.status}">
                    <strong>${e.title || e.episode_id}</strong>
                    <span>${e.status} · ${e.format || '?'} · ${e.bytes ? (e.bytes / 1024).toFixed(1) + ' KB' : '—'}</span>
                    <a href="${e.play_url}" target="_blank" rel="noopener">Probe</a>
                </div>`).join('')}`;
    }

    async function loadLeaderboard() {
        const el = qs('#leaderboard-table');
        if (!el) return;
        const r = await API('/api/podcast/leaderboard?limit=15');
        if (!r.success) { el.textContent = 'Leaderboard unavailable.'; return; }
        el.innerHTML = `<table class="podcast-lb-table"><thead><tr><th>#</th><th>User</th><th>Score</th><th>💬</th><th>📰</th><th>❤️</th></tr></thead><tbody>` +
            (r.leaderboard || []).map((row, i) =>
                `<tr><td>${i + 1}</td><td>${row.user_id}</td><td>${row.score}</td>
                <td>${row.comments}</td><td>${row.news_comments}</td><td>${row.likes}</td></tr>`
            ).join('') + '</tbody></table>';
    }

    function playNextInQueue() {
        if (!episodeQueue.length) return;
        const next = episodeQueue.shift();
        saveQueue();
        playEpisode(next, false, null);
    }

    async function loadStats() {
        try {
            const s = await API('/api/podcast/stats');
            if (s.success && qs('#stats-bar')) {
                qs('#stats-bar').innerHTML = `
                    <span>${s.channels} channels</span>
                    <span>${s.episodes} episodes</span>
                    <span>${(s.total_views || 0).toLocaleString()} views</span>
                    <span>${(s.total_plays || 0).toLocaleString()} plays</span>
                    <span>🫧 BBCG flavor</span>`;
            }
        } catch (e) {}
    }

    async function loadChannels() {
        const r = await API('/api/podcast/channels');
        const grid = qs('#channels-grid');
        if (!r.success || !grid) return;
        grid.innerHTML = (r.channels || []).map(c => {
            const plats = Object.keys(c.platforms || {}).map(p => `<span class="platform-badge">${p}</span>`).join('');
            return `<div class="podcast-card"><div style="font-size:2rem">${c.icon || '🎙️'}</div>
                <h3>${c.name}</h3><p>${c.tagline || ''}</p><div class="platform-badges">${plats}</div>
                <button type="button" class="podcast-btn podcast-follow-btn" data-channel="${c.id}">+ Follow</button></div>`;
        }).join('');
        grid.querySelectorAll('.podcast-follow-btn').forEach(btn => {
            btn.addEventListener('click', async e => {
                e.stopPropagation();
                const fr = await API('/api/podcast/channels/' + btn.dataset.channel + '/follow', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: USER_ID })
                });
                if (fr.success) btn.textContent = 'Following (' + (fr.follower_count || 0) + ')';
            });
        });
        const sel = qs('#channel-filter');
        if (sel) (r.channels || []).forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id; opt.textContent = c.name; sel.appendChild(opt);
        });
    }

    async function loadEpisodes(channelId) {
        const url = '/api/podcast/episodes?user_id=' + encodeURIComponent(USER_ID) +
            (channelId ? '&channel_id=' + encodeURIComponent(channelId) : '');
        const r = await API(url);
        const list = qs('#episodes-list');
        if (!r.success || !list) return;
        list.innerHTML = (r.episodes || []).map(ep => {
            const locked = ep.requires_premium && !ep.unlocked;
            return `<div class="episode-row${locked ? ' locked' : ''}" data-id="${ep.id}" data-locked="${locked}">
                <div style="flex:1"><strong>${ep.title}</strong>
                <div class="episode-meta">${(ep.view_count || 0).toLocaleString()} views · 💬 ${ep.comment_count || 0} · ❤️ ${ep.like_count || 0}</div></div>
                ${locked ? '🔒' : '▶'}</div>`;
        }).join('');
        list.querySelectorAll('.episode-row').forEach(row => {
            row.addEventListener('click', () => playEpisode(row.dataset.id, row.dataset.locked === 'true', row));
        });
    }

    async function playEpisode(id, locked, rowEl) {
        if (locked) {
            qs('#reward-msg').textContent = 'Premium — unlock in Shop with MN2.';
            qs('#player-area').hidden = false;
            return;
        }
        const r = await API('/api/podcast/episodes/' + id + '?user_id=' + encodeURIComponent(USER_ID));
        if (!r.success) return;
        currentEpisode = r.episode;
        qsa('.episode-row').forEach(rw => rw.classList.remove('playing'));
        if (rowEl) rowEl.classList.add('playing');

        qs('#player-area').hidden = false;
        qs('#episode-social').hidden = false;
        qs('#player-title').textContent = r.episode.title;
        qs('#cover-bubble').textContent = r.episode.generator_intelligence ? '🤖' : '🫧';

        const audio = qs('#audio-player');
        const playUrl = r.episode.audio_play_url || ('/api/podcast/episodes/' + id + '/audio');
        audio.src = playUrl + '?t=' + Date.now();
        audio.load();

        const chk = r.episode.audio_check || {};
        const fmt = chk.format ? ` · ${chk.format}` : '';
        const kb = chk.bytes ? ` · ${(chk.bytes / 1024).toFixed(1)} KB` : '';
        qs('#sound-status').textContent = 'Sound: ' + (chk.status || 'streaming') + fmt + kb + ' · BBCG';

        const speedSel = qs('#playback-speed');
        if (speedSel) audio.playbackRate = parseFloat(speedSel.value) || 1;

        loadChapters(id);
        loadTranscript(id);

        audio.onplay = () => setupVisualizer(audio);
        audio.onerror = async () => {
            qs('#sound-status').textContent = 'Regenerating audio…';
            await API('/api/podcast/sound-check?repair=1', { method: 'POST' });
            audio.src = playUrl + '?t=' + Date.now();
            audio.load();
            audio.play().catch(() => {});
        };

        const playRes = await API('/api/podcast/episodes/' + id + '/play', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID })
        });
        if (playRes.crypto_reward && playRes.crypto_reward.awarded_mn2) {
            qs('#reward-msg').textContent = 'Earned ' + playRes.crypto_reward.awarded_mn2 + ' MN2';
        }

        renderShareButtons(id, r.episode.platform_links || {});
        loadEpisodeSocial(id);
        loadEpisodes(qs('#channel-filter').value);

        audio.onended = async () => {
            const cr = await API('/api/podcast/episodes/' + id + '/listen-complete', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: USER_ID })
            });
            if (cr.crypto_reward && cr.crypto_reward.awarded_mn2) {
                qs('#reward-msg').textContent = 'Listen complete! +' + cr.crypto_reward.awarded_mn2 + ' MN2';
            }
            if (episodeQueue.length) playNextInQueue();
        };
    }

    function renderShareButtons(episodeId, links) {
        const row = qs('#share-row');
        if (!row) return;
        const platforms = [
            { id: 'youtube', label: 'YouTube', icon: '▶️' },
            { id: 'facebook', label: 'Facebook', icon: '📘' },
            { id: 'discord', label: 'Discord', icon: '💬' },
            { id: 'github', label: 'GitHub', icon: '🐙' }
        ];
        row.innerHTML = platforms.map(p => {
            const url = links[p.id] || 'https://masternoder.dk/podcast';
            return `<button class="share-btn" data-platform="${p.id}" data-url="${url}">${p.icon} ${p.label}</button>`;
        }).join('');
        row.querySelectorAll('.share-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                window.open(btn.dataset.url, '_blank');
                const sr = await API('/api/podcast/episodes/' + episodeId + '/share', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: USER_ID, platform: btn.dataset.platform })
                });
                if (sr.crypto_reward && sr.crypto_reward.awarded_mn2) {
                    qs('#reward-msg').textContent = 'Shared! +' + sr.crypto_reward.awarded_mn2 + ' MN2';
                }
            });
        });
    }

    async function loadEpisodeSocial(episodeId) {
        const r = await API('/api/podcast/episodes/' + episodeId + '/comments?user_id=' + encodeURIComponent(USER_ID));
        if (!r.success) return;
        qs('#like-count').textContent = (r.like_count || 0) + ' likes';
        qs('#like-btn').textContent = r.user_liked ? '❤️ Liked' : '❤️ Like';
        qs('#comments-list').innerHTML = (r.comments || []).map(c =>
            `<div class="podcast-comment"><div>${c.content}</div><div class="podcast-comment-meta">${c.user_id}</div></div>`
        ).join('') || '<p style="opacity:0.7">No comments — drop a blue bubble gum komment!</p>';
    }

    async function loadNews() {
        const grid = qs('#news-grid');
        if (!grid) return;
        const r = await API('/api/podcast/news?limit=24');
        if (!r.success) { grid.textContent = 'News unavailable.'; return; }
        grid.innerHTML = (r.news || []).map(n => `
            <div class="news-card" id="news-${n.id}">
                <span class="news-date">${n.date || ''} · ${n.channel || n.category || 'platform'}</span>
                <h4>${n.title || ''}</h4>
                <p>${n.summary || ''}</p>
                <p class="episode-meta">💬 ${n.comment_count || 0} podcast comments</p>
                <div class="news-comment-box">
                    <input type="text" placeholder="Komment on this change…" data-news-id="${n.id}" class="news-comment-input">
                    <button type="button" class="podcast-btn primary news-comment-btn" data-news-id="${n.id}" style="margin-top:8px">Post comment (+MN2)</button>
                </div>
                <div class="news-comments-list" data-news-id="${n.id}"></div>
            </div>`).join('');

        grid.querySelectorAll('.news-comment-btn').forEach(btn => {
            btn.addEventListener('click', () => postNewsComment(btn.dataset.newsId));
        });
        grid.querySelectorAll('.news-comment-input').forEach(inp => {
            inp.addEventListener('keydown', e => { if (e.key === 'Enter') postNewsComment(inp.dataset.newsId); });
        });
        (r.news || []).slice(0, 8).forEach(n => loadNewsComments(n.id));
    }

    async function loadNewsComments(newsId) {
        const r = await API('/api/podcast/news/' + encodeURIComponent(newsId) + '/comments');
        const el = qs('.news-comments-list[data-news-id="' + newsId + '"]');
        if (!el || !r.success) return;
        el.innerHTML = (r.comments || []).slice(0, 5).map(c =>
            `<div class="news-comment"><strong>${c.user_id}</strong>: ${c.content}</div>`
        ).join('');
    }

    async function postNewsComment(newsId) {
        const inp = qs('.news-comment-input[data-news-id="' + newsId + '"]');
        const content = (inp && inp.value || '').trim();
        if (!content) return;
        const r = await API('/api/podcast/news/' + encodeURIComponent(newsId) + '/comments', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID, content })
        });
        if (r.success) {
            if (inp) inp.value = '';
            loadNewsComments(newsId);
            loadActivity();
            loadNews();
        }
    }

    qs('#like-btn') && qs('#like-btn').addEventListener('click', async () => {
        if (!currentEpisode) return;
        const r = await API('/api/podcast/episodes/' + currentEpisode.id + '/like', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID })
        });
        if (r.success) {
            qs('#like-count').textContent = (r.like_count || 0) + ' likes';
            qs('#like-btn').textContent = '❤️ Liked';
        }
    });

    qs('#comment-submit') && qs('#comment-submit').addEventListener('click', async () => {
        if (!currentEpisode) return;
        const content = qs('#comment-input').value.trim();
        if (!content) return;
        const r = await API('/api/podcast/episodes/' + currentEpisode.id + '/comments', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID, content })
        });
        if (r.success) {
            qs('#comment-input').value = '';
            loadEpisodeSocial(currentEpisode.id);
            loadActivity();
        }
    });

    async function loadActivity() {
        const el = qs('#activity-feed');
        if (!el) return;
        const r = await API('/api/podcast/activity?limit=30');
        el.innerHTML = (r.activity || []).map(a =>
            `<div class="podcast-activity-item"><strong>${a.type}</strong> · ${a.user_id || ''} · ${a.preview || ''}</div>`
        ).join('') || '<p>No activity yet.</p>';
    }

    qs('#channel-filter') && qs('#channel-filter').addEventListener('change', e => loadEpisodes(e.target.value));

    qs('#generate-form') && qs('#generate-form').addEventListener('submit', async e => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const prog = qs('#generate-progress');
        prog.hidden = false;
        prog.textContent = 'Generating…';
        const start = await API('/api/podcast/generate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: USER_ID,
                topic: fd.get('topic'), title: fd.get('title'), description: fd.get('description'),
                encode_profile: fd.get('encode_profile'), assigned_agent: fd.get('assigned_agent')
            })
        });
        if (!start.success) { prog.textContent = 'Failed'; return; }
        const poll = setInterval(async () => {
            const p = await API('/api/podcast/generate/' + start.job_id + '/progress');
            prog.textContent = p.status + ' ' + (p.progress || 0) + '%';
            if (p.status === 'completed' || p.status === 'failed') {
                clearInterval(poll);
                if (p.status === 'completed') { loadEpisodes(''); runSoundCheck(true); }
            }
        }, 1500);
    });

    async function loadCrypto() {
        const r = await API('/api/podcast/crypto-rewards?user_id=' + encodeURIComponent(USER_ID));
        const el = qs('#crypto-info');
        if (!el || !r.success) return;
        const rates = r.rates || {};
        el.innerHTML = `<p>Daily: ${(r.daily_earned_mn2 || 0).toFixed(6)} / ${r.daily_cap_mn2} MN2</p>
            <p>Play ${rates.play_mn2} · News comment ${rates.news_comment_mn2} · Comment ${rates.comment_mn2} MN2</p>`;
    }

    qsa('.buy-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const r = await API('/api/podcast/shop/unlock', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: USER_ID, item_id: btn.dataset.item })
            });
            qs('#shop-result').textContent = r.success ? 'Purchased!' : (r.error || 'Failed');
        });
    });

    async function loadCustomers() {
        const r = await API('/api/podcast/customers');
        if (!r.success) return;
        qs('#customers-summary').textContent = `${r.total_partners} partners · ${Number(r.total_listeners || 0).toLocaleString()} listeners`;
        qs('#customers-grid').innerHTML = (r.customers || []).map(c =>
            `<div class="customer-card"><h4>${c.name}</h4><p class="customer-quote">"${c.quote || ''}"</p></div>`
        ).join('');
    }

    qs('#assign-agent-btn') && qs('#assign-agent-btn').addEventListener('click', async () => {
        const r = await API('/api/podcast/assign-agent', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID })
        });
        alert(r.success ? 'Agent assigned!' : (r.error || 'Failed'));
    });

    async function loadAgentProjects() {
        const r = await API('/api/podcast/agent-projects');
        if (!r.success || !qs('#agent-projects')) return;
        qs('#agent-projects').innerHTML = (r.projects || []).slice(0, 8).map(p =>
            `<div class="agent-project">#${p.num} ${p.description}</div>`
        ).join('');
    }

    qs('#playback-speed') && qs('#playback-speed').addEventListener('change', e => {
        const audio = qs('#audio-player');
        if (audio) audio.playbackRate = parseFloat(e.target.value) || 1;
    });

    qs('#viz-mode-btn') && qs('#viz-mode-btn').addEventListener('click', () => {
        vizMode = vizMode === 'bars' ? 'bubbles' : 'bars';
        qs('#viz-mode-btn').textContent = vizMode === 'bubbles' ? '📊 Bar viz' : '🫧 Bubble viz';
    });

    qs('#queue-add-btn') && qs('#queue-add-btn').addEventListener('click', () => {
        if (!currentEpisode || episodeQueue.includes(currentEpisode.id)) return;
        episodeQueue.push(currentEpisode.id);
        saveQueue();
    });

    qs('#queue-play-btn') && qs('#queue-play-btn').addEventListener('click', () => playNextInQueue());

    qs('#sound-repair-btn') && qs('#sound-repair-btn').addEventListener('click', async () => {
        await API('/api/podcast/sound-check?repair=1', { method: 'POST' });
        runSoundCheck(true);
        loadSoundLab();
    });

    runSoundCheck(false);
    loadStats();
    loadChannels();
    loadEpisodes('');
    loadNews();
    loadCrypto();
    loadCustomers();
    loadAgentProjects();
    loadActivity();
    loadSoundLab();
    loadLeaderboard();
    renderQueue();
    openTabFromHash();
})();
