import type { NetworkSnapshot } from '../api/client';

type Props = {
  network: NetworkSnapshot | null | undefined;
  loading: boolean;
};

type StatRow = { key: string; label: string; value: string };

function fmt(n: number | null | undefined, digits = 2): string {
  if (n == null || Number.isNaN(n)) return '—';
  if (Number.isInteger(n)) return String(n);
  return n.toFixed(digits);
}

function fmtBool(v: boolean | null | undefined): string {
  if (v == null) return '—';
  return v ? 'yes' : 'no';
}

function buildRows(network: NetworkSnapshot | null | undefined): StatRow[] {
  const n = network;
  const syncLabel = n?.sync_ok == null ? '—' : n.sync_ok ? 'reachable' : 'degraded';
  const ver = [n?.daemon_version, n?.daemon_subversion].filter(Boolean).join(' ') || '—';
  const verify = n?.verification_progress != null
    ? `${(n.verification_progress * 100).toFixed(2)}%`
    : '—';

  return [
    { key: 'block_height', label: 'Block height', value: fmt(n?.block_height, 0) },
    { key: 'headers', label: 'Headers', value: fmt(n?.headers, 0) },
    { key: 'connections', label: 'Peer connections', value: fmt(n?.connections, 0) },
    { key: 'mempool_tx', label: 'Mempool transactions', value: fmt(n?.mempool_tx, 0) },
    { key: 'mempool_bytes', label: 'Mempool bytes', value: fmt(n?.mempool_bytes, 0) },
    { key: 'mn2_usd_price', label: 'MN2 / USD', value: n?.mn2_usd_price != null ? `$${n.mn2_usd_price}` : '—' },
    { key: 'pool_apr_percent', label: 'Staking pool APR', value: n?.pool_apr_percent != null ? `${n.pool_apr_percent}%` : '—' },
    { key: 'pool_total_staked', label: 'Pool total staked', value: fmt(n?.pool_total_staked, 4) },
    { key: 'masternode_count', label: 'Masternode count', value: fmt(n?.masternode_count, 0) },
    { key: 'masternode_enabled', label: 'Masternodes enabled', value: fmt(n?.masternode_enabled, 0) },
    { key: 'difficulty', label: 'Difficulty', value: fmt(n?.difficulty, 4) },
    { key: 'network_hashps', label: 'Network hash rate', value: fmt(n?.network_hashps, 2) },
    { key: 'staking_weight', label: 'Staking weight', value: fmt(n?.staking_weight, 2) },
    { key: 'expected_stake_time_sec', label: 'Expected stake time (s)', value: fmt(n?.expected_stake_time_sec, 0) },
    { key: 'circulating_supply', label: 'Circulating supply', value: fmt(n?.circulating_supply, 2) },
    { key: 'chain', label: 'Chain', value: n?.chain ?? '—' },
    { key: 'daemon_version', label: 'Daemon version', value: ver },
    { key: 'verification_progress', label: 'Verification progress', value: verify },
    { key: 'median_time', label: 'Median block time', value: n?.median_time != null ? String(n.median_time) : '—' },
    { key: 'sync_ok', label: 'Daemon sync', value: syncLabel },
    { key: 'rpc_degraded', label: 'RPC failover active', value: fmtBool(n?.rpc_degraded) },
    { key: 'peer_health', label: 'Peer health', value: typeof n?.peer_health === 'object' ? JSON.stringify(n.peer_health) : String(n?.peer_health ?? '—') },
    { key: 'staking_health', label: 'Staking health', value: typeof n?.staking_health === 'object' ? JSON.stringify(n.staking_health) : String(n?.staking_health ?? '—') },
  ];
}

export function NetworkStatsRichList({ network, loading }: Props) {
  const rows = buildRows(network);

  return (
    <section class="wallet-panel wallet-rich-stats" aria-label="Network statistics">
      <div class="wallet-panel-header">
        <div>
          <div class="wallet-panel-title">Network statistics</div>
          <div class="wallet-panel-subtitle">All KPIs from summary network bundle</div>
        </div>
      </div>
      <ul class="wallet-rich-stats-list">
        {rows.map((row) => (
          <li class="wallet-rich-stats-row" key={row.key}>
            <span class="wallet-rich-stats-label">{row.label}</span>
            {loading ? (
              <span class="wallet-skeleton wallet-rich-stats-value-skel" />
            ) : (
              <span class="wallet-rich-stats-value">{row.value}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
