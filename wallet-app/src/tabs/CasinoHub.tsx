import { useEffect, useState } from 'preact/hooks';
import { fetchCasinoSnapshot, type CasinoFeaturedGame, type CasinoSnapshot } from '../api/client';

function gameHref(gameId: string): string {
  return `/casino/?tab=lobby&game=${encodeURIComponent(gameId)}`;
}

export function CasinoHub() {
  const [snapshot, setSnapshot] = useState<CasinoSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchCasinoSnapshot()
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

  const featured = snapshot?.featured_games || [];

  const renderGame = (game: CasinoFeaturedGame) => (
    <a
      key={game.id}
      href={gameHref(game.id)}
      class="wallet-casino-game-card"
    >
      <span class="wallet-casino-game-icon" aria-hidden="true">{game.icon || '🎰'}</span>
      <span class="wallet-casino-game-name">{game.label || game.id}</span>
      {game.tag && <span class="wallet-casino-game-tag">{game.tag}</span>}
      {game.blurb && <span class="wallet-casino-game-desc">{game.blurb}</span>}
    </a>
  );

  return (
    <div class="wallet-tab-panel">
      <section class="wallet-panel wallet-casino-hero">
        <div style={{ padding: '16px' }}>
          <div class="wallet-casino-title">MN2 Casino</div>
          <p style={{ margin: '8px 0 0', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            Slots, crash, plinko, and more — stake MN2 or play coins. VIP lounge and Discord rewards.
          </p>
          {loading ? (
            <div class="wallet-skeleton" style={{ height: '48px', marginTop: '12px' }} />
          ) : (
            <div class="wallet-casino-balances" style={{ marginTop: '12px' }}>
              <div class="wallet-casino-balance-chip">
                <span class="wallet-casino-balance-label">MN2</span>
                <span class="wallet-casino-balance-value">
                  {(snapshot?.mn2_balance ?? 0).toFixed(8)}
                </span>
              </div>
              <div class="wallet-casino-balance-chip">
                <span class="wallet-casino-balance-label">Casino coins</span>
                <span class="wallet-casino-balance-value">
                  {(snapshot?.casino_coins ?? 0).toLocaleString()}
                </span>
              </div>
              {(snapshot?.fiat_balance ?? 0) > 0 && (
                <div class="wallet-casino-balance-chip">
                  <span class="wallet-casino-balance-label">USD play</span>
                  <span class="wallet-casino-balance-value">
                    ${(snapshot?.fiat_balance ?? 0).toFixed(2)}
                  </span>
                </div>
              )}
            </div>
          )}
          <a
            href={snapshot?.casino_url || '/casino/'}
            class="wallet-discord-btn wallet-discord-btn-primary wallet-casino-cta"
            style={{ marginTop: '14px', display: 'inline-flex' }}
          >
            Play now →
          </a>
        </div>
      </section>

      {error && <div class="wallet-error wallet-error--inline" role="alert">{error}</div>}

      {!loading && snapshot && (
        <>
          <section class="wallet-panel" style={{ marginTop: '12px' }}>
            <div class="wallet-panel-header" style={{ padding: '12px 16px 0' }}>
              <div class="wallet-panel-title">VIP &amp; Discord</div>
            </div>
            <div class="wallet-casino-status-row" style={{ padding: '12px 16px 16px' }}>
              <div class="wallet-casino-status-chip">
                <span class="wallet-casino-status-label">VIP lounge</span>
                <span class={snapshot.vip?.unlocked ? 'wallet-casino-status-on' : 'wallet-casino-status-off'}>
                  {snapshot.vip?.unlocked ? 'Unlocked' : 'Locked'}
                </span>
              </div>
              <div class="wallet-casino-status-chip">
                <span class="wallet-casino-status-label">Discord VIP</span>
                <span class={snapshot.discord_vip_eligible ? 'wallet-casino-status-on' : 'wallet-casino-status-off'}>
                  {snapshot.discord_vip_eligible
                    ? 'Eligible'
                    : snapshot.min_mn2_for_vip
                      ? `Need ${snapshot.min_mn2_for_vip} MN2`
                      : 'Not eligible'}
                </span>
              </div>
              {snapshot.featured_games_count != null && (
                <div class="wallet-casino-status-chip">
                  <span class="wallet-casino-status-label">Featured games</span>
                  <span class="wallet-casino-status-on">{snapshot.featured_games_count}</span>
                </div>
              )}
            </div>
          </section>

          {featured.length > 0 && (
            <section class="wallet-panel" style={{ marginTop: '12px' }}>
              <div class="wallet-panel-header" style={{ padding: '12px 16px 0' }}>
                <div class="wallet-panel-title">Featured games</div>
                <div class="wallet-panel-subtitle">Tap to open in casino lobby</div>
              </div>
              <div class="wallet-casino-games-grid" style={{ padding: '12px 16px 16px' }}>
                {featured.map(renderGame)}
              </div>
            </section>
          )}

          <section class="wallet-panel wallet-casino-disclaimer" style={{ marginTop: '12px' }}>
            <div style={{ padding: '12px 16px', fontSize: '0.78rem', color: 'var(--wallet-muted)', lineHeight: 1.45 }}>
              {snapshot.responsible_gaming_disclaimer}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
