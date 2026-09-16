import type { NetworkSnapshot, TrophyCounts } from '../api/client';

type Props = {
  network: NetworkSnapshot | null | undefined;
  trophyCounts?: TrophyCounts;
  loading: boolean;
};

function fmt(n: number | null | undefined, fallback = '—'): string {
  if (n == null || Number.isNaN(n)) return fallback;
  return String(n);
}

export function NetworkFace({ network, trophyCounts, loading }: Props) {
  const kpis = [
    { label: 'Block height', value: fmt(network?.block_height) },
    { label: 'Peers', value: fmt(network?.connections) },
    { label: 'Mempool tx', value: fmt(network?.mempool_tx) },
    { label: 'MN2 price', value: network?.mn2_usd_price != null ? `$${network.mn2_usd_price}` : '—' },
    { label: 'Staking APY', value: network?.pool_apr_percent != null ? `${network.pool_apr_percent}%` : '—' },
    { label: 'Masternodes', value: fmt(network?.masternode_count) },
  ];

  return (
    <section class="wallet-panel" aria-label="Network overview" style={{ marginBottom: '12px' }}>
      <div style={{ padding: '14px 16px', borderBottom: 'var(--wallet-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
        <div>
          <div style={{ fontWeight: 700, letterSpacing: '0.02em' }}>Network face</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--wallet-muted)' }}>Live chain KPIs — zero deposit RPC on overview</div>
        </div>
        {trophyCounts && trophyCounts.total > 0 && (
          <span class="wallet-badge" title="Owned trophy editions">
            🏆 {trophyCounts.total}
          </span>
        )}
        {network?.sync_ok === false && (
          <span class="wallet-badge" style={{ color: 'var(--wallet-danger)', borderColor: 'var(--wallet-danger)' }}>
            Sync degraded
          </span>
        )}
      </div>
      <div style={{ padding: '14px 16px' }}>
        {loading ? (
          <div class="wallet-kpi-grid">
            {kpis.map((k) => (
              <div class="wallet-kpi" key={k.label}>
                <div class="wallet-skeleton" style={{ height: '2.5rem' }} />
              </div>
            ))}
          </div>
        ) : (
          <div class="wallet-kpi-grid">
            {kpis.map((k) => (
              <div class="wallet-kpi" key={k.label}>
                <div class="wallet-kpi-label">{k.label}</div>
                <div class="wallet-kpi-value">{k.value}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
