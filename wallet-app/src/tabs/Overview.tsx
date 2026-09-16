import type { WalletSummary } from '../api/client';
import { MasternodeMap } from '../components/MasternodeMap';
import { NetworkFace } from '../components/NetworkFace';
import { NetworkStatsRichList } from '../components/NetworkStatsRichList';
import { TrophySlot } from '../components/TrophySlot';

type Props = {
  summary: WalletSummary | null;
  loading: boolean;
  error: string | null;
  onOpenUpgrades?: () => void;
  onOpenPortal?: () => void;
  onOpenRewards?: () => void;
  onOpenEarn?: () => void;
  onOpenShop?: () => void;
  onOpenExchange?: () => void;
};

export function Overview({
  summary,
  loading,
  error,
  onOpenUpgrades,
  onOpenPortal,
  onOpenRewards,
  onOpenEarn,
  onOpenShop,
  onOpenExchange,
}: Props) {
  const net = summary?.network;

  return (
    <div class="wallet-tab-panel wallet-overview-expanded">
      {error && <div class="wallet-error" role="alert">{error}</div>}

      <section class="wallet-overview-hero-row" aria-label="Primary wallet actions">
        <button type="button" class="wallet-hero-cta wallet-hero-cta--portal" onClick={onOpenPortal}>
          <span class="wallet-hero-cta-icon" aria-hidden="true">🌀</span>
          <span class="wallet-hero-cta-label">Portal</span>
          <span class="wallet-hero-cta-sub">Command Center hub</span>
        </button>
        <button type="button" class="wallet-hero-cta wallet-hero-cta--rewards" onClick={onOpenRewards}>
          <span class="wallet-hero-cta-icon" aria-hidden="true">💎</span>
          <span class="wallet-hero-cta-label">Rewards</span>
          <span class="wallet-hero-cta-sub">Unified points &amp; quests</span>
        </button>
        <button type="button" class="wallet-hero-cta wallet-hero-cta--earn" onClick={onOpenEarn}>
          <span class="wallet-hero-cta-icon" aria-hidden="true">⚡</span>
          <span class="wallet-hero-cta-label">Earn</span>
          <span class="wallet-hero-cta-sub">Micro MN2 clicks</span>
        </button>
        <button type="button" class="wallet-hero-cta" onClick={onOpenShop}>
          <span class="wallet-hero-cta-icon" aria-hidden="true">🛒</span>
          <span class="wallet-hero-cta-label">Shop</span>
          <span class="wallet-hero-cta-sub">Trophies &amp; boosts</span>
        </button>
        <button type="button" class="wallet-hero-cta" onClick={onOpenExchange}>
          <span class="wallet-hero-cta-icon" aria-hidden="true">💱</span>
          <span class="wallet-hero-cta-label">Exchange</span>
          <span class="wallet-hero-cta-sub">25-crypto swap</span>
        </button>
      </section>

      <NetworkFace
        network={net}
        trophyCounts={summary?.trophy_counts}
        loading={loading}
      />
      <div class="wallet-overview-row">
        <TrophySlot trophyCounts={summary?.trophy_counts} loading={loading} />
        <MasternodeMap
          totalHint={net?.masternode_count}
          enabledHint={net?.masternode_enabled}
        />
      </div>
      <NetworkStatsRichList network={net} loading={loading} />
      <section class="wallet-panel wallet-overview-cta" aria-label="Quick actions">
        <div style={{ padding: '16px', display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontWeight: 600, marginBottom: '4px' }}>250 wallet upgrades</div>
            <p style={{ margin: 0, color: 'var(--wallet-muted)', fontSize: '0.85rem' }}>
              Lazy-loaded catalog — speed, network, trophies, security, and more.
            </p>
          </div>
          {onOpenUpgrades && (
            <button type="button" class="wallet-discord-btn" onClick={onOpenUpgrades}>
              Browse upgrades
            </button>
          )}
          {summary?.explorer_base_url && (
            <a href="/explorer" class="wallet-link">Full explorer →</a>
          )}
          <a href="/wallets?tab=settings#mobile-download" class="wallet-link">
            Download mobile app →
          </a>
        </div>
      </section>
    </div>
  );
}
