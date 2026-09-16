import { useEffect, useState } from 'preact/hooks';
import { fetchMasternodeMap, type MasternodeMapData } from '../api/client';

type Props = {
  /** Fallback counts from summary network snapshot when map not yet loaded. */
  totalHint?: number | null;
  enabledHint?: number | null;
};

export function MasternodeMap({ totalHint, enabledHint }: Props) {
  const [data, setData] = useState<MasternodeMapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchMasternodeMap(48)
      .then((d) => {
        if (!cancelled) {
          setData(d);
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

  const total = data?.total ?? totalHint ?? 0;
  const enabled = data?.enabled ?? enabledHint ?? 0;
  const nodes = data?.nodes ?? [];

  return (
    <section class="wallet-panel wallet-masternode-map" aria-label="Masternodes online">
      <div class="wallet-panel-header">
        <div>
          <div class="wallet-panel-title">Masternodes online</div>
          <div class="wallet-panel-subtitle">
            {loading ? 'Loading fleet…' : `${enabled} enabled / ${total} total`}
          </div>
        </div>
        <a href="/staking-monitor" class="wallet-link wallet-link--sm">Staking monitor →</a>
      </div>
      {error && <div class="wallet-error wallet-error--inline">{error}</div>}
      <div class="wallet-mn-grid" role="list" aria-busy={loading}>
        {loading && nodes.length === 0 ? (
          Array.from({ length: 24 }).map((_, i) => (
            <div class="wallet-mn-node wallet-mn-node--skeleton" key={i} role="listitem" />
          ))
        ) : nodes.length > 0 ? (
          nodes.map((n, i) => (
            <div
              key={n.addr || i}
              class={`wallet-mn-node ${n.online ? 'wallet-mn-node--online' : 'wallet-mn-node--offline'}`}
              role="listitem"
              title={n.addr || `Rank ${n.rank}`}
            >
              <span class="wallet-mn-rank">{n.rank ?? '·'}</span>
            </div>
          ))
        ) : (
          <div class="wallet-mn-empty">
            Masternode list unavailable — network count: {totalHint ?? '—'}
          </div>
        )}
      </div>
      {data?.rpc_error && (
        <div class="wallet-muted-note">RPC: {data.rpc_error}</div>
      )}
    </section>
  );
}
