import { SiteFeaturesHub } from '../components/SiteFeaturesHub';

type Props = {
  onOpenShop?: () => void;
  onOpenExchange?: () => void;
  onOpenCasino?: () => void;
};

export function PortalHub({ onOpenShop, onOpenExchange, onOpenCasino }: Props) {
  return (
    <div class="wallet-tab-panel">
      <section class="wallet-panel wallet-portal-hero">
        <div style={{ padding: '16px' }}>
          <div class="wallet-portal-title">Command Center Portal</div>
          <p style={{ margin: '8px 0 12px', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            Battle · Trophies · Game · Quests · Podcast · Exchange — one hub with MN2 rewards.
          </p>
          <a
            href="/command-center"
            class="wallet-discord-btn wallet-discord-btn-primary wallet-portal-cta"
          >
            Open Command Center →
          </a>
        </div>
      </section>

      <section class="wallet-panel" style={{ marginTop: '12px' }}>
        <div class="wallet-panel-header">
          <div>
            <div class="wallet-panel-title">Site Features Hub</div>
            <div class="wallet-panel-subtitle">All site sections from your wallet</div>
          </div>
        </div>
        <div style={{ padding: '0 12px 16px' }}>
          <SiteFeaturesHub
            emphasizePrimary
            onOpenShop={onOpenShop}
            onOpenExchange={onOpenExchange}
            onOpenCasino={onOpenCasino}
          />
        </div>
      </section>
    </div>
  );
}
