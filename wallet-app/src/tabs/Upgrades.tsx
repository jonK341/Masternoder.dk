import { useCallback, useEffect, useState } from 'preact/hooks';
import {
  fetchUpgrades,
  fetchUpgradesProgress,
  unlockWalletUpgrade,
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
  const [unlocking, setUnlocking] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    return Promise.all([fetchUpgrades(), fetchUpgradesProgress()])
      .then(([catalog, prog]) => {
        setUpgrades(catalog.upgrades || []);
        setProgress(prog);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const unlocked = new Set(progress?.unlocked_ids || []);
  const available = new Set(progress?.available_ids || []);
  const hints = progress?.progress_hints || {};

  const handleUnlock = async (upgrade: WalletUpgrade) => {
    if (unlocking || unlocked.has(upgrade.id)) return;
    setUnlocking(upgrade.id);
    setFlash(null);
    try {
      const result = await unlockWalletUpgrade(upgrade.id);
      if (result.success) {
        setFlash(`Unlocked ${result.name || upgrade.name}`);
        if (result.progress) {
          setProgress(result.progress);
        } else {
          await refresh();
        }
      } else {
        setFlash(result.message || result.error || 'Unlock failed');
      }
    } catch (err: unknown) {
      setFlash(err instanceof Error ? err.message : 'Unlock failed');
    } finally {
      setUnlocking(null);
      window.setTimeout(() => setFlash(null), 3500);
    }
  };

  const filtered = filter === 'all'
    ? upgrades
    : upgrades.filter((u) => u.category === filter);

  const categories = ['all', ...Object.keys(CATEGORY_LABELS)];

  const effects = progress?.effects_summary;
  const hasEffects = effects && (effects.unlocked_effect_count ?? 0) > 0;

  return (
    <div class="wallet-tab-panel">
      {error && <div class="wallet-error" role="alert">{error}</div>}
      {flash && <div class="wallet-upgrade-flash" role="status">{flash}</div>}
      <section class="wallet-panel" style={{ marginBottom: '12px' }}>
        <div style={{ padding: '14px 16px' }}>
          <div style={{ fontWeight: 700 }}>Wallet upgrades</div>
          <p style={{ margin: '8px 0 0', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            {loading
              ? 'Loading catalog…'
              : `${progress?.unlocked_count ?? 0} unlocked · ${progress?.available_count ?? 0} ready · level ${progress?.wallet_level ?? 1}`}
          </p>
          {!loading && hasEffects && (
            <p class="wallet-muted-note" style={{ padding: 0, marginTop: '8px' }}>
              Active bonuses: cache +{effects?.summary_cache_ttl_bonus ?? 0}s
              {(effects?.earn_cap_bonus_pct ?? 0) > 0 && ` · earn cap +${effects?.earn_cap_bonus_pct}%`}
              {effects?.fun_mode_unlock && ' · fun mode'}
            </p>
          )}
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
          <li class="wallet-upgrade-item wallet-skeleton" style={{ height: '72px' }} />
        ) : (
          filtered.map((u) => {
            const isUnlocked = unlocked.has(u.id);
            const isAvailable = available.has(u.id);
            const hint = hints[u.id];
            return (
              <li
                key={u.id}
                class={`wallet-upgrade-item wallet-upgrade-item--${u.tier} ${isUnlocked ? 'wallet-upgrade-item--unlocked' : ''} ${isAvailable ? 'wallet-upgrade-item--available' : ''}`}
              >
                <div class="wallet-upgrade-id">{u.id}</div>
                <div class="wallet-upgrade-body">
                  <div class="wallet-upgrade-name">{u.name}</div>
                  <div class="wallet-upgrade-effect">{u.effect}</div>
                  <div class="wallet-upgrade-meta">
                    <span class={`wallet-tier wallet-tier--${u.tier}`}>{u.tier}</span>
                    <span class="wallet-upgrade-cat">{CATEGORY_LABELS[u.category] || u.category}</span>
                    {!isUnlocked && (hint || u.unlock?.label) && (
                      <span class="wallet-upgrade-lock">{hint || u.unlock.label}</span>
                    )}
                  </div>
                </div>
                <div class="wallet-upgrade-actions">
                  {isUnlocked ? (
                    <span class="wallet-upgrade-status" aria-label="Unlocked">✓</span>
                  ) : isAvailable ? (
                    <button
                      type="button"
                      class="wallet-upgrade-unlock-btn"
                      disabled={unlocking === u.id || !!progress?.guest}
                      onClick={() => handleUnlock(u)}
                    >
                      {unlocking === u.id ? '…' : 'Unlock'}
                    </button>
                  ) : (
                    <span class="wallet-upgrade-status wallet-upgrade-status--locked" aria-label="Locked">○</span>
                  )}
                </div>
              </li>
            );
          })
        )}
      </ul>
      {progress?.guest && !loading && (
        <p class="wallet-muted-note" style={{ padding: '8px 4px' }}>
          Sign in to unlock and persist upgrades.
        </p>
      )}
    </div>
  );
}
