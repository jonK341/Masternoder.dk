export type TrophyCounts = {
  total: number;
  top25_owned: number;
  shop_items: number;
};

export type NetworkSnapshot = {
  block_height: number | null;
  connections: number | null;
  mempool_tx: number | null;
  mempool_bytes?: number | null;
  mn2_usd_price: number | null;
  pool_apr_percent: number | null;
  masternode_count?: number | null;
  sync_ok?: boolean | null;
};

export type WalletSummary = {
  success: boolean;
  user_id?: string;
  mn2_balance?: number;
  liquid_mn2?: number;
  held_mn2?: number;
  withdrawable_mn2?: number;
  mn2_usd_price?: number;
  trophy_counts?: TrophyCounts;
  network?: NetworkSnapshot;
  wallet_v2_enabled?: boolean;
  wallet_fun_mode?: boolean;
  explorer_base_url?: string;
};

export async function fetchSummary(): Promise<WalletSummary> {
  const params = new URLSearchParams({
    sections: 'balance,trophy_counts,flags,network',
  });
  const res = await fetch(`/api/wallet/v2/summary?${params}`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Summary failed (${res.status})`);
  }
  return res.json() as Promise<WalletSummary>;
}
