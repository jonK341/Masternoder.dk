import { useEffect, useState } from 'preact/hooks';
import {
  fetchUpgrades,
  fetchUpgradesProgress,
  type WalletUpgrade,
  type UpgradesProgress,
} from '../api/client';

const CATEGORY_LABELS: Record<string, string> = {
  speed: 'Speed',
  network_visibility: 'Network',
  trophies: 'Trophies',
  send_receive: 'Send / Receive',
  monitors: 'Monitors',
  fun: 'Fun',
  desktop: 'Desktop',
  discord: 'Discord',
  security: 'Security',
};

export function Upgrades() {
  const [upgrades, setUpgrades] = useState<WalletUpgrade[]>([]);
  const [progress, setProgress] = useState<UpgradesProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([fetchUpgrades(), fetchUpgradesProgress()])
      .then(([catalog, prog]) => {
        if (!cancelled) {
          setUpgrades(catalog.upgrades || []);
          setProgress(prog);
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

  const unlocked = new Set(progress?.unlocked_ids || []);
  const filtered = filter === 'all'
    ? upgrades
    : upgrades.filter((u) => u.category === filter);

  const categories = ['all', ...Object.keys(CATEGORY_LABELS)];

  return (
    <div class="wallet-tab-panel">
      {error && <div class="wallet-error" role="alert">{error}</div>}
      <section class="wallet-panel" style={{ marginBottom: '12px' }}>
        <div style={{ padding: '14px 16px' }}>
          <div style={{ fontWeight: 700 }}>Wallet upgrades</div>
          <p style={{ margin: '8px 0 0', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            {loading
              ? 'Loading catalog…'
              : `${progress?.unlocked_count ?? 0} / ${progress?.total ?? upgrades.length} unlocked · level ${progress?.wallet_level ?? 1}`}
          </p>
        </div>
      </section>
      <div class="wallet-upgrade-filters" role="tablist" aria-label="Upgrade categories">
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            class={`wallet-upgrade-filter ${filter === cat ? 'wallet-upgrade-filter--active' : ''}`}
            onClick={() => setFilter(cat)}
          >
            {cat === 'all' ? 'All' : CATEGORY_LABELS[cat] || cat}
          </button>
        ))}
      </div>
      <ul class="wallet-upgrade-list">
        {loading ? (
          <li class="wallet-upgrade-item wallet-skeleton" style={{ height: '64px' }} />
        ) : (
          filtered.slice(0, 100).map((u) => {
            const isUnlocked = unlocked.has(u.id);
            return (
              <li
                key={u.id}
                class={`wallet-upgrade-item wallet-upgrade-item--${u.tier} ${isUnlocked ? 'wallet-upgrade-item--unlocked' : ''}`}
              >
                <div class="wallet-upgrade-id">{u.id}</div>
                <div class="wallet-upgrade-body">
                  <div class="wallet-upgrade-name">{u.name}</div>
                  <div class="wallet-upgrade-effect">{u.effect}</div>
                  <div class="wallet-upgrade-meta">
                    <span class={`wallet-tier wallet-tier--${u.tier}`}>{u.tier}</span>
                    <span class="wallet-upgrade-cat">{CATEGORY_LABELS[u.category] || u.category}</span>
                    {!isUnlocked && u.unlock?.label && (
                      <span class="wallet-upgrade-lock">{u.unlock.label}</span>
                    )}
                  </div>
                </div>
                <span class="wallet-upgrade-status" aria-label={isUnlocked ? 'Unlocked' : 'Locked'}>
                  {isUnlocked ? '✓' : '○'}
                </span>
              </li>
            );
          })
        )}
      </ul>
      {!loading && filtered.length > 100 && (
        <p class="wallet-muted-note" style={{ padding: '8px 4px' }}>
          Showing first 100 of {filtered.length} in this filter. Full catalog: {upgrades.length} upgrades.
        </p>
      )}
    </div>
  );
}
