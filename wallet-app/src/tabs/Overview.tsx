import type { WalletSummary } from '../api/client';
import { NetworkFace } from '../components/NetworkFace';

type Props = {
  summary: WalletSummary | null;
  loading: boolean;
  error: string | null;
};

export function Overview({ summary, loading, error }: Props) {
  return (
    <div class="wallet-tab-panel">
      {error && <div class="wallet-error" role="alert">{error}</div>}
      <NetworkFace
        network={summary?.network}
        trophyCounts={summary?.trophy_counts}
        loading={loading}
      />
      <section class="wallet-panel" aria-label="Quick actions">
        <div style={{ padding: '16px' }}>
          <div style={{ fontWeight: 600, marginBottom: '8px' }}>Wallet v2 preview</div>
          <p style={{ margin: 0, color: 'var(--wallet-muted)', fontSize: '0.9rem', lineHeight: 1.5 }}>
            Overview loads from <code style={{ fontFamily: 'var(--wallet-font-mono)' }}>/api/wallet/v2/summary</code> only.
            Deposit address, send preview, and tab bundles load on first tab visit.
          </p>
          {summary?.explorer_base_url && (
            <p style={{ margin: '12px 0 0', fontSize: '0.85rem' }}>
              <a href="/explorer" style={{ color: 'var(--wallet-accent)' }}>Open full explorer →</a>
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
