import { useEffect, useState } from 'preact/hooks';
import { fetchWalletStaking, type WalletStakingResponse } from '../api/client';

export function Staking() {
  const [data, setData] = useState<WalletStakingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchWalletStaking()
      .then((res) => {
        if (!cancelled) {
          setData(res);
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

  const stake = data?.stake;
  const grants = data?.trophy_grants?.grants ?? [];

  return (
    <div class="wallet-tab-panel">
      <section class="wallet-panel wallet-staking-hero">
        <div class="wallet-panel-header">
          <div>
            <div class="wallet-panel-title">Staking &amp; trophy rewards</div>
            <div class="wallet-panel-subtitle">
              Pool MN2 rewards + block smiley trophies for interval winners
            </div>
          </div>
        </div>
        <p class="wallet-trophies-disclaimer">
          Trophies are platform-ledger collectibles with license numbers — not on-chain mint.
          Top staker each interval can win the latest unclaimed block trophy.
        </p>
        {data?.upgrade && (
          <div class="wallet-staking-upgrade">
            <span class="wallet-badge">{data.upgrade.unlocked ? '✓' : '🔒'} {data.upgrade.label}</span>
            <span class="wallet-panel-subtitle">{data.upgrade.description}</span>
          </div>
        )}
      </section>

      {loading && (
        <section class="wallet-panel">
          <div class="wallet-skeleton" style={{ height: '100px' }} />
        </section>
      )}

      {error && (
        <section class="wallet-panel wallet-trophies-error" role="alert">{error}</section>
      )}

      {!loading && !error && data?.guest && (
        <section class="wallet-panel wallet-trophies-empty">
          <p>{data.message || 'Sign in to view staking.'}</p>
        </section>
      )}

      {!loading && !error && !data?.guest && (
        <>
          <section class="wallet-panel">
            <div class="wallet-panel-title">Your stake</div>
            <div class="wallet-kpi-grid" style={{ padding: '12px 0' }}>
              <div class="wallet-kpi">
                <div class="wallet-kpi-label">Staked MN2</div>
                <div class="wallet-kpi-value">{Number(stake?.staked ?? 0).toFixed(4)}</div>
              </div>
              <div class="wallet-kpi">
                <div class="wallet-kpi-label">Total earned</div>
                <div class="wallet-kpi-value">{Number(stake?.total_earned ?? 0).toFixed(4)}</div>
              </div>
              <div class="wallet-kpi">
                <div class="wallet-kpi-label">Est. next interval</div>
                <div class="wallet-kpi-value">{Number(stake?.estimated_next_interval_reward ?? 0).toFixed(6)}</div>
              </div>
            </div>
            <a href="/profile#profile-mn2-wallet-card" class="wallet-link">Manage stake in profile →</a>
          </section>

          <section class="wallet-panel">
            <div class="wallet-panel-header">
              <div class="wallet-panel-title">Block trophy wins</div>
              <div class="wallet-panel-subtitle">From staking interval leader rewards</div>
            </div>
            {grants.length === 0 ? (
              <p class="wallet-muted-note">No staking trophy grants yet. Stay staked to compete each interval.</p>
            ) : (
              <ul class="wallet-staking-grant-list">
                {grants.map((g) => (
                  <li key={`${g.interval_id}-${g.block_height}`} class="wallet-staking-grant-item">
                    {g.gif_url ? (
                      <img src={g.gif_url} alt="" class="wallet-staking-grant-gif" loading="lazy" />
                    ) : null}
                    <strong>Block #{g.block_height}</strong>
                    {g.license_number ? ` · ${g.license_number}` : ''}
                    {g.edition_key ? (
                      <span> · <a href="/wallets?tab=trophies" class="wallet-link">{g.edition_key}</a></span>
                    ) : null}
                    <div class="wallet-panel-subtitle">
                      Interval {g.interval_id} · +{Number(g.reward_mn2 ?? 0).toFixed(6)} MN2 that round
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <div style={{ marginTop: '10px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <a href="/wallets?tab=trophies" class="wallet-discord-btn wallet-discord-btn-primary">My trophies</a>
              <a href="/shop?tab=block-gallery" class="wallet-discord-btn">Block gallery</a>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
