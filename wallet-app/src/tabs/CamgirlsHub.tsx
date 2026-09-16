import { useCallback, useEffect, useState } from 'preact/hooks';
import {
  fetchCamgirlsCatalog,
  fetchCamgirlsUpgrades,
  fetchCamgirlsUpgradesProgress,
  postCamgirlTip,
  unlockCamgirlUpgrade,
  type CamgirlPerformer,
  type CamgirlUpgrade,
  type CamgirlsUpgradesProgress,
} from '../api/client';

type Panel = 'performers' | 'upgrades';

const CATEGORY_LABELS: Record<string, string> = {
  studio: 'Studio',
  chat: 'Chat',
  gifts: 'Gifts',
  lighting: 'Lighting',
  wardrobe: 'Wardrobe',
  rewards: 'Rewards',
  network: 'Network',
  premium: 'Premium',
};

export function CamgirlsHub() {
  const panelFromQuery = (): Panel => {
    const p = new URLSearchParams(window.location.search).get('panel');
    return p === 'upgrades' ? 'upgrades' : 'performers';
  };

  const [panel, setPanel] = useState<Panel>(panelFromQuery);
  const [performers, setPerformers] = useState<CamgirlPerformer[]>([]);
  const [upgrades, setUpgrades] = useState<CamgirlUpgrade[]>([]);
  const [progress, setProgress] = useState<CamgirlsUpgradesProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradesLoaded, setUpgradesLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState<string | null>(null);
  const [tipping, setTipping] = useState<string | null>(null);
  const [tipFlash, setTipFlash] = useState<string | null>(null);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    let cancelled = false;
    fetchCamgirlsCatalog()
      .then((data) => {
        if (!cancelled) {
          setPerformers(data.performers || []);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, []);

  const loadUpgrades = useCallback(() => {
    if (upgradesLoaded) return Promise.resolve();
    setError(null);
    return Promise.all([fetchCamgirlsUpgrades(), fetchCamgirlsUpgradesProgress()])
      .then(([catalog, prog]) => {
        setUpgrades(catalog.upgrades || []);
        setProgress(prog);
        setUpgradesLoaded(true);
      })
      .catch((err: Error) => setError(err.message));
  }, [upgradesLoaded]);

  useEffect(() => {
    if (panel === 'upgrades') loadUpgrades();
  }, [panel, loadUpgrades]);

  const switchPanel = (p: Panel) => {
    setPanel(p);
    const url = new URL(window.location.href);
    if (p === 'upgrades') {
      url.searchParams.set('panel', 'upgrades');
    } else {
      url.searchParams.delete('panel');
    }
    window.history.replaceState({}, '', url.pathname + url.search);
  };

  const unlocked = new Set(progress?.unlocked_ids || []);
  const available = new Set(progress?.available_ids || []);

  const handleTip = async (performer: CamgirlPerformer) => {
    if (tipping) return;
    const min = performer.tip_min_mn2 ?? 5;
    const raw = window.prompt(`Tip ${performer.name} (min ${min} MN2):`, String(min));
    if (raw == null) return;
    const amount = parseFloat(raw);
    if (!Number.isFinite(amount) || amount < min) {
      setTipFlash(`Minimum tip is ${min} MN2`);
      window.setTimeout(() => setTipFlash(null), 3000);
      return;
    }
    setTipping(performer.id);
    setTipFlash(null);
    try {
      const result = await postCamgirlTip(performer.id, amount);
      if (result.success) {
        setTipFlash(`Tipped ${amount} MN2 → balance ${result.camgirl_balance?.toFixed(4) ?? '—'}`);
        setPerformers((prev) => prev.map((p) => (
          p.id === performer.id
            ? { ...p, mn2_balance: result.camgirl_balance ?? p.mn2_balance }
            : p
        )));
      } else {
        setTipFlash(result.error || result.message || 'Tip failed');
      }
    } catch (err: unknown) {
      setTipFlash(err instanceof Error ? err.message : 'Tip failed');
    } finally {
      setTipping(null);
      window.setTimeout(() => setTipFlash(null), 4000);
    }
  };

  const handleUnlock = async (upgrade: CamgirlUpgrade) => {
    if (unlocking || unlocked.has(upgrade.id)) return;
    setUnlocking(upgrade.id);
    try {
      const result = await unlockCamgirlUpgrade(upgrade.id);
      if (result.progress) setProgress(result.progress);
      else await loadUpgrades();
    } finally {
      setUnlocking(null);
    }
  };

  const filteredUpgrades = filter === 'all'
    ? upgrades
    : upgrades.filter((u) => u.category === filter);

  return (
    <div class="wallet-tab-panel">
      <section class="wallet-panel wallet-exchange-hero">
        <div style={{ padding: '16px' }}>
          <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>Camgirls Studio</div>
          <p style={{ margin: '8px 0 0', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            25 performers — SFW wallet cards link to the full studio experience. 250 section upgrades.
          </p>
          <a href="/camgirls" class="wallet-discord-btn wallet-discord-btn-primary" style={{ marginTop: '12px', display: 'inline-flex' }}>
            Open full studio →
          </a>
        </div>
      </section>

      <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
        <button
          type="button"
          class={`wallet-discord-btn${panel === 'performers' ? ' wallet-discord-btn-primary' : ''}`}
          onClick={() => switchPanel('performers')}
        >
          Performers (25)
        </button>
        <button
          type="button"
          class={`wallet-discord-btn${panel === 'upgrades' ? ' wallet-discord-btn-primary' : ''}`}
          onClick={() => switchPanel('upgrades')}
        >
          Upgrades (250)
        </button>
      </div>

      {panel === 'performers' && (
        <>
          {loading ? (
            <div class="wallet-skeleton" style={{ height: '200px', marginTop: '12px' }} />
          ) : error ? (
            <div class="wallet-error wallet-error--inline" role="alert">{error}</div>
          ) : (
            <>
              {tipFlash && (
                <div style={{ marginTop: '12px', fontSize: '0.85rem', color: 'var(--wallet-accent)' }}>{tipFlash}</div>
              )}
              <div class="wallet-shop-grid" style={{ marginTop: '12px' }}>
                {performers.map((p) => (
                  <div key={p.id} class="wallet-shop-card" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <img
                      src={p.avatar_url || '/static/camgirls/avatar-demo.svg'}
                      alt=""
                      width={48}
                      height={48}
                      style={{ borderRadius: 'var(--wallet-radius)' }}
                    />
                    <span class="wallet-shop-card-name">
                      {p.name}
                      {p.online ? (
                        <span style={{ color: 'var(--wallet-accent)', marginLeft: '6px', fontSize: '0.7rem' }}>● online</span>
                      ) : null}
                    </span>
                    <span class="wallet-shop-card-desc">{p.tagline}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--wallet-muted)' }}>
                      {p.tier} · unlock {p.price_mn2} MN2
                    </span>
                    <span style={{ fontFamily: 'var(--wallet-font-mono)', fontSize: '0.85rem', color: 'var(--wallet-accent)' }}>
                      {(p.mn2_balance ?? 0).toFixed(4)} MN2
                    </span>
                    {p.wallet_user_id && (
                      <span style={{ fontSize: '0.65rem', color: 'var(--wallet-muted)', wordBreak: 'break-all' }}>
                        {p.wallet_user_id}
                      </span>
                    )}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                      <button
                        type="button"
                        class="wallet-discord-btn wallet-discord-btn-primary"
                        disabled={tipping === p.id}
                        onClick={() => handleTip(p)}
                      >
                        {tipping === p.id ? 'Tipping…' : 'Tip'}
                      </button>
                      <a href={p.studio_path || '/camgirls'} class="wallet-discord-btn" style={{ textDecoration: 'none' }}>
                        Studio
                      </a>
                      {p.explorer_url ? (
                        <a href={p.explorer_url} class="wallet-discord-btn" style={{ textDecoration: 'none' }} target="_blank" rel="noopener noreferrer">
                          Explorer
                        </a>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}

      {panel === 'upgrades' && (
        <section class="wallet-panel" style={{ marginTop: '12px' }}>
          <div class="wallet-panel-header" style={{ flexWrap: 'wrap', gap: '8px' }}>
            <div>
              <div class="wallet-panel-title">Section upgrades</div>
              <div class="wallet-panel-subtitle">
                {progress ? `${progress.unlocked_count}/${progress.total} unlocked` : 'Loading…'}
              </div>
            </div>
            <select
              value={filter}
              onChange={(e) => setFilter((e.target as HTMLSelectElement).value)}
              style={{
                background: 'var(--wallet-bg-elevated)',
                border: 'var(--wallet-border)',
                color: 'var(--wallet-text)',
                padding: '6px 10px',
                borderRadius: 'var(--wallet-radius)',
              }}
            >
              <option value="all">All categories</option>
              {(progress?.by_category ? Object.keys(progress.by_category) : []).map((cat) => (
                <option key={cat} value={cat}>{CATEGORY_LABELS[cat] || cat}</option>
              ))}
            </select>
          </div>
          {!upgradesLoaded ? (
            <div style={{ padding: '16px' }}>
              <div class="wallet-skeleton" style={{ height: '120px' }} />
            </div>
          ) : (
            <div style={{ maxHeight: '480px', overflowY: 'auto', padding: '8px 16px 16px' }}>
              {filteredUpgrades.slice(0, 80).map((u) => {
                const isUnlocked = unlocked.has(u.id);
                const canUnlock = available.has(u.id);
                return (
                  <div
                    key={u.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '10px 0',
                      borderBottom: '1px solid var(--wallet-border)',
                      fontSize: '0.85rem',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600 }}>{u.name}</div>
                      <div style={{ color: 'var(--wallet-muted)', fontSize: '0.75rem' }}>{u.id} · {u.tier}</div>
                    </div>
                    {isUnlocked ? (
                      <span style={{ color: 'var(--wallet-accent)' }}>Unlocked</span>
                    ) : canUnlock ? (
                      <button
                        type="button"
                        class="wallet-discord-btn wallet-discord-btn-primary"
                        disabled={unlocking === u.id}
                        onClick={() => handleUnlock(u)}
                      >
                        Unlock
                      </button>
                    ) : (
                      <span style={{ color: 'var(--wallet-muted)', fontSize: '0.75rem' }}>Locked</span>
                    )}
                  </div>
                );
              })}
              {filteredUpgrades.length > 80 && (
                <p style={{ color: 'var(--wallet-muted)', fontSize: '0.8rem', marginTop: '12px' }}>
                  Showing first 80 — filter by category to browse all 250.
                </p>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
