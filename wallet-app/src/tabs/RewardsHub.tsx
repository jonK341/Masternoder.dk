import { useEffect, useState } from 'preact/hooks';
import { fetchRewardsSnapshot, type RewardsSnapshot } from '../api/client';

export function RewardsHub() {
  const [snapshot, setSnapshot] = useState<RewardsSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchRewardsSnapshot()
      .then((data) => {
        if (!cancelled) {
          setSnapshot(data);
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

  const pts = snapshot?.points;

  return (
    <div class="wallet-tab-panel">
      <section class="wallet-panel wallet-rewards-hero">
        <div style={{ padding: '16px' }}>
          <div class="wallet-rewards-title">Rewards &amp; Unified Points</div>
          <p style={{ margin: '8px 0 12px', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            XP, quest points, trophy score, and MN2 earned across the platform.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            <a href="/profile?tab=points" class="wallet-discord-btn wallet-discord-btn-primary">
              Profile points hub →
            </a>
            <a href="/quests" class="wallet-discord-btn">Quests →</a>
            <a href="/command-center" class="wallet-discord-btn">Command Center →</a>
          </div>
        </div>
      </section>

      <section class="wallet-panel" style={{ marginTop: '12px' }}>
        <div class="wallet-panel-header">
          <div>
            <div class="wallet-panel-title">Your points snapshot</div>
            <div class="wallet-panel-subtitle">From unified points system</div>
          </div>
        </div>
        {loading ? (
          <div style={{ padding: '16px' }}>
            <div class="wallet-skeleton" style={{ height: '120px' }} />
          </div>
        ) : error ? (
          <div class="wallet-error wallet-error--inline" role="alert">{error}</div>
        ) : snapshot?.guest ? (
          <div class="wallet-muted-note">{snapshot.message || 'Sign in to view rewards.'}</div>
        ) : (
          <div class="wallet-kpi-grid" style={{ padding: '14px 16px' }}>
            <div class="wallet-kpi">
              <div class="wallet-kpi-label">Level</div>
              <div class="wallet-kpi-value">{pts?.level ?? 1}</div>
            </div>
            <div class="wallet-kpi">
              <div class="wallet-kpi-label">XP total</div>
              <div class="wallet-kpi-value">{pts?.xp_total ?? 0}</div>
            </div>
            <div class="wallet-kpi">
              <div class="wallet-kpi-label">Coins</div>
              <div class="wallet-kpi-value">{pts?.coins ?? 0}</div>
            </div>
            <div class="wallet-kpi">
              <div class="wallet-kpi-label">Trophy pts</div>
              <div class="wallet-kpi-value">{pts?.trophy_points ?? 0}</div>
            </div>
            <div class="wallet-kpi">
              <div class="wallet-kpi-label">Quest pts</div>
              <div class="wallet-kpi-value">{pts?.quest_points ?? 0}</div>
            </div>
            <div class="wallet-kpi">
              <div class="wallet-kpi-label">Battle pts</div>
              <div class="wallet-kpi-value">{pts?.battle_points ?? 0}</div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
