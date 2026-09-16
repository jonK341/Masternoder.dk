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

export type DiscordNotificationPrefs = {
  balance_alerts: boolean;
  trophy_drops: boolean;
  block_trophy_mint: boolean;
  battle_results: boolean;
};

export type DiscordStatus = {
  success: boolean;
  user_id?: string;
  guest?: boolean;
  linked?: boolean;
  discord_id?: string | null;
  username?: string | null;
  avatar_url?: string | null;
  mn2_balance?: number;
  casino_vip_eligible?: boolean;
  min_mn2_for_vip?: number;
  hosting_customer?: boolean;
  hosting_vip_eligible?: boolean;
  hosting_vip_message?: string;
  roles_available?: string[];
  linked_role_oauth_url?: string | null;
  linked_role_configured?: boolean;
  oauth_login_configured?: boolean;
  oauth_login_start_path?: string | null;
  manual_link_supported?: boolean;
  profile_discord_path?: string;
  server_invite_url?: string | null;
  notification_prefs?: DiscordNotificationPrefs;
  notification_prefs_note?: string;
  share_supported?: boolean;
  message?: string;
  error?: string;
};

export async function fetchDiscordStatus(): Promise<DiscordStatus> {
  const res = await fetch('/api/wallet/v2/discord/status', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Discord status failed (${res.status})`);
  }
  return res.json() as Promise<DiscordStatus>;
}

export async function linkDiscordManual(
  userId: string,
  discordId: string,
): Promise<{ success: boolean; error?: string }> {
  const res = await fetch('/api/discord/link', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ user_id: userId, discord_id: discordId }),
  });
  const data = (await res.json()) as { success: boolean; error?: string };
  if (!res.ok && !data.error) {
    return { success: false, error: `Link failed (${res.status})` };
  }
  return data;
}

export async function unlinkDiscord(
  userId: string,
): Promise<{ success: boolean; error?: string }> {
  const res = await fetch('/api/discord/link/unlink', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ user_id: userId }),
  });
  const data = (await res.json()) as { success: boolean; error?: string };
  if (!res.ok && !data.error) {
    return { success: false, error: `Unlink failed (${res.status})` };
  }
  return data;
}
