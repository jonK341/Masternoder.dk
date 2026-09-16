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
  pool_total_staked?: number | null;
  masternode_count?: number | null;
  masternode_enabled?: number | null;
  sync_ok?: boolean | null;
  difficulty?: number | null;
  network_hashps?: number | null;
  staking_weight?: number | null;
  expected_stake_time_sec?: number | null;
  circulating_supply?: number | null;
  daemon_version?: number | null;
  daemon_subversion?: string | null;
  chain?: string | null;
  verification_progress?: number | null;
  headers?: number | null;
  median_time?: number | null;
  staking_health?: unknown;
  peer_health?: unknown;
  rpc_degraded?: boolean | null;
  source?: Record<string, string>;
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
  linked_role_connect_path?: string | null;
  linked_role_verification_path?: string;
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

export type WalletUpgradeUnlock = {
  type: string;
  value: string | number;
  label?: string;
};

export type WalletUpgrade = {
  id: string;
  name: string;
  effect: string;
  category: string;
  tier: 'common' | 'rare' | 'epic';
  unlock: WalletUpgradeUnlock;
};

export type UpgradesCatalog = {
  success: boolean;
  version: number;
  total: number;
  categories: string[];
  upgrades: WalletUpgrade[];
};

export type UpgradeEffectsSummary = {
  summary_cache_ttl_bonus?: number;
  network_kpi_refresh_bonus?: number;
  trophy_preview_bonus?: number;
  send_preview_cache_bonus?: number;
  monitor_refresh_bonus?: number;
  desktop_tray_poll_bonus?: number;
  discord_notify_bonus?: number;
  security_checklist_bonus?: number;
  earn_cap_bonus_pct?: number;
  fun_mode_unlock?: boolean;
  unlocked_effect_count?: number;
};

export type UpgradesProgress = {
  success: boolean;
  user_id: string;
  guest?: boolean;
  wallet_level: number;
  mn2_spent: number;
  trophy_count?: number;
  clicks_today?: number;
  upgrade_count?: number;
  unlocked_count: number;
  available_count?: number;
  locked_count: number;
  total: number;
  unlocked_ids: string[];
  available_ids?: string[];
  locked_ids: string[];
  progress_hints?: Record<string, string>;
  by_category: Record<string, { unlocked: number; available?: number; locked?: number; total: number }>;
  effects_summary?: UpgradeEffectsSummary;
};

export type UnlockUpgradeResult = {
  success: boolean;
  upgrade_id?: string;
  name?: string;
  effects?: Record<string, unknown>;
  unlocked_at?: string;
  progress?: UpgradesProgress;
  error?: string;
  message?: string;
  progress_hint?: string;
};

export type MasternodeNode = {
  rank: number | null;
  addr: string | null;
  status: string;
  online: boolean;
  activetime?: number | null;
  lastpaid?: number | null;
};

export type MasternodeMapData = {
  success: boolean;
  total: number;
  enabled: number;
  nodes: MasternodeNode[];
  rpc_error?: string;
};

export async function fetchUpgrades(category?: string): Promise<UpgradesCatalog> {
  const params = category ? `?category=${encodeURIComponent(category)}` : '';
  const res = await fetch(`/api/wallet/v2/upgrades${params}`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Upgrades failed (${res.status})`);
  return res.json() as Promise<UpgradesCatalog>;
}

export async function fetchUpgradesProgress(): Promise<UpgradesProgress> {
  const res = await fetch('/api/wallet/v2/upgrades/progress', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Upgrades progress failed (${res.status})`);
  return res.json() as Promise<UpgradesProgress>;
}

export async function unlockWalletUpgrade(upgradeId: string): Promise<UnlockUpgradeResult> {
  const res = await fetch('/api/wallet/v2/upgrades/unlock', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ upgrade_id: upgradeId }),
  });
  const data = (await res.json()) as UnlockUpgradeResult;
  if (!res.ok && !data.message && !data.error) {
    return { success: false, error: `Unlock failed (${res.status})` };
  }
  return data;
}

export async function fetchMasternodeMap(limit = 48): Promise<MasternodeMapData> {
  const res = await fetch(`/api/wallet/v2/network/masternodes?limit=${limit}`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Masternode map failed (${res.status})`);
  return res.json() as Promise<MasternodeMapData>;
}

export type SiteFeature = {
  id: string;
  name: string;
  icon: string;
  path: string;
  category: string;
  primary?: boolean;
  description?: string;
};

export type SiteFeaturesResponse = {
  success: boolean;
  total: number;
  primary_ids: string[];
  categories: string[];
  features: SiteFeature[];
};

export type RewardsPoints = {
  xp_total?: number;
  level?: number;
  coins?: number;
  trophy_points?: number;
  quest_points?: number;
  battle_points?: number;
  mn2_balance?: number;
};

export type RewardsSnapshot = {
  success: boolean;
  user_id?: string;
  guest?: boolean;
  message?: string;
  profile_points_url?: string;
  quests_url?: string;
  command_center_url?: string;
  points?: RewardsPoints;
  points_error?: string;
};

export type ExchangeBalance = {
  symbol?: string;
  asset?: string;
  balance?: number;
};

export type ExchangeWallet = {
  success?: boolean;
  balances?: ExchangeBalance[];
  holdings?: ExchangeBalance[];
  mn2_balance?: number;
  asset_count?: number;
  open_orders?: number;
};

export async function fetchSiteFeatures(): Promise<SiteFeaturesResponse> {
  const res = await fetch('/api/wallet/v2/site-features', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Site features failed (${res.status})`);
  return res.json() as Promise<SiteFeaturesResponse>;
}

export async function fetchRewardsSnapshot(): Promise<RewardsSnapshot> {
  const res = await fetch('/api/wallet/v2/rewards/snapshot', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Rewards snapshot failed (${res.status})`);
  return res.json() as Promise<RewardsSnapshot>;
}

export type EarnEvent = {
  event_id: string;
  unit_id?: string;
  name?: string;
  description?: string;
  category?: string;
  unit?: string;
  base_amount?: number;
  next_amount_mn2?: number;
  clicks_today?: number;
  max_clicks_per_day?: number;
  earned_today_mn2?: number;
  daily_cap_mn2?: number;
  cooldown_seconds?: number;
  cooldown_remaining_sec?: number;
  available?: boolean;
  blocked_reason?: string | null;
};

export type EarnGameLink = {
  id: string;
  name: string;
  description?: string;
  path: string;
  icon?: string;
  embed?: string;
};

export type EarnStatus = {
  success: boolean;
  enabled?: boolean;
  user_id?: string;
  guest?: boolean;
  day?: string;
  earned_today_mn2?: number;
  global_daily_cap_mn2?: number;
  remaining_today_mn2?: number;
  engagement_disclaimer?: string;
  captcha_hook_enabled?: boolean;
  events?: EarnEvent[];
  game_links?: EarnGameLink[];
  message?: string;
};

export type EarnClickResult = {
  success: boolean;
  event_id?: string;
  unit_id?: string;
  mn2_awarded?: number;
  earned_today_mn2?: number;
  global_daily_cap_mn2?: number;
  clicks_today?: number;
  cooldown_seconds?: number;
  duplicate?: boolean;
  error?: string;
  cooldown_remaining_sec?: number;
};

export async function fetchEarnStatus(): Promise<EarnStatus> {
  const res = await fetch('/api/wallet/v2/earn/status', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Earn status failed (${res.status})`);
  return res.json() as Promise<EarnStatus>;
}

export async function postEarnClick(eventId: string): Promise<EarnClickResult> {
  const res = await fetch('/api/wallet/v2/earn/click', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ event_id: eventId }),
  });
  const data = (await res.json()) as EarnClickResult;
  if (!res.ok && !data.error) {
    return { success: false, error: `Click failed (${res.status})` };
  }
  return data;
}

export type CasinoFeaturedGame = {
  id: string;
  label?: string;
  icon?: string;
  tag?: string;
  blurb?: string;
};

export type CasinoVipStatus = {
  unlocked?: boolean;
  enabled?: boolean;
  level?: number | null;
  vip_tier?: string | null;
  user_xp?: number;
  xp_to_unlock?: number;
  title?: string;
};

export type CasinoSnapshot = {
  success: boolean;
  user_id?: string;
  guest?: boolean;
  message?: string;
  casino_url?: string;
  casino_lobby_url?: string;
  mn2_balance?: number;
  casino_coins?: number;
  fiat_balance?: number;
  bets_today?: number;
  max_bets_per_day?: number;
  featured_games?: CasinoFeaturedGame[];
  featured_games_count?: number;
  vip?: CasinoVipStatus;
  discord_vip_eligible?: boolean;
  discord_linked?: boolean;
  min_mn2_for_vip?: number | null;
  responsible_gaming_disclaimer?: string;
  real_money_enabled?: boolean;
  casino_error?: string;
};

export async function fetchCasinoSnapshot(): Promise<CasinoSnapshot> {
  const res = await fetch('/api/wallet/v2/casino/snapshot', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Casino snapshot failed (${res.status})`);
  return res.json() as Promise<CasinoSnapshot>;
}

export async function fetchExchangeWallet(): Promise<ExchangeWallet> {
  const res = await fetch('/api/exchange/wallet', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Exchange wallet failed (${res.status})`);
  return res.json() as Promise<ExchangeWallet>;
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
