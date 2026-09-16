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

export type TrophyEdition = {
  edition_no: number;
  edition_key: string;
  legacy_stack?: boolean;
  item_id: string;
  item_name?: string;
  serial_key?: string;
  series?: string;
  on_chain_mint: boolean;
  acquired_via?: string;
  hold_until?: string;
  proof_hash?: string;
  anchor_status?: 'pending' | 'committed' | 'anchored' | 'none';
  anchor_commitment?: string;
  anchor_txid?: string;
  anchor_explorer_url?: string;
  serial_number?: string;
  license_number?: string;
  trading_profile?: {
    license_number?: string;
    listing_status?: string;
    royalty_bps?: number;
    auction_listable?: boolean;
    peer_transfer?: boolean;
  };
  block_height?: number;
  platform_trophy?: boolean;
  battle_stats?: {
    serial_number?: string;
    power?: number;
    defense?: number;
    speed?: number;
    luck?: number;
    smile?: number;
    combat_rating?: number;
    rarity?: string;
    mood?: string;
  };
  image_url?: string | null;
  gif_url?: string | null;
  sound_url?: string | null;
  trade_actions?: {
    auction_list?: string;
    peer_transfer?: string | null;
    shop_detail?: string;
  };
};

export type WalletTrophiesResponse = {
  success: boolean;
  guest?: boolean;
  user_id?: string;
  message?: string;
  on_chain_mint: boolean;
  platform_ledger?: boolean;
  editions: TrophyEdition[];
  catalog_preview?: Array<{
    id: string;
    name?: string;
    effective_price_usd?: number;
    shop_url?: string;
    image_url?: string | null;
  }>;
  counts?: {
    total_editions: number;
    top25_owned: number;
    top25_total: number;
    unique_skus: number;
    catalog_skus?: number;
  };
  shop_trophies_url?: string;
  auction_url?: string;
};

export type TrophyMonitor4dResponse = {
  success: boolean;
  guest?: boolean;
  network?: NetworkSnapshot;
  highlight?: {
    item_id?: string;
    item_name?: string;
    edition_no?: number;
    edition_key?: string;
    gif_url?: string | null;
    image_url?: string | null;
    label?: string;
    battle_url?: string;
    license_number?: string;
    acquired_via?: string;
    per_edition_media?: boolean;
    battle_stats?: { combat_rating?: number; mood?: string };
  } | null;
  trophies?: Array<{
    item_id: string;
    item_name?: string;
    edition_no?: number;
    edition_key?: string;
    gif_url?: string | null;
    image_url?: string | null;
    sound_url?: string | null;
    hold_until?: string;
    highlight?: boolean;
    acquired_via?: string;
    license_number?: string;
    per_edition_media?: boolean;
    battle_stats?: { combat_rating?: number; mood?: string };
  }>;
  block_teaser?: {
    height?: number;
    item_id?: string;
    name?: string;
    gif_url?: string;
    explorer_url?: string;
    effective_price_usd?: number;
    claimed?: boolean;
  } | null;
  counts?: Record<string, number>;
};

export async function fetchTrophyMonitor4d(): Promise<TrophyMonitor4dResponse> {
  const res = await fetch('/api/wallet/v2/trophy-monitor/4d', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`4D monitor failed (${res.status})`);
  }
  return res.json() as Promise<TrophyMonitor4dResponse>;
}

export async function battleBlockTrophy(edition_key: string): Promise<{
  success: boolean;
  error?: string;
  result?: string;
  rewards?: { battle_points?: number; game_points?: number };
  message?: string;
  scores?: { attacker?: number; defender?: number; margin?: number };
}> {
  const res = await fetch('/api/shop/block-trophy/battle', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ edition_key }),
  });
  const data = await res.json();
  if (!res.ok && !data.error) {
    throw new Error(`Battle failed (${res.status})`);
  }
  return data;
}

export async function shareTrophyDiscord(edition_key: string): Promise<{ success: boolean; error?: string }> {
  const res = await fetch('/api/shop/trophies/share-discord', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ edition_key }),
  });
  const data = await res.json();
  if (!res.ok && !data.error) throw new Error(`Share failed (${res.status})`);
  return data;
}

export async function burnTrophyEdition(item_id: string, edition_no: number): Promise<{ success: boolean; error?: string; credit_mn2?: number }> {
  const res = await fetch('/api/shop/trophies/burn', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ item_id, edition_no }),
  });
  const data = await res.json();
  if (!res.ok && !data.error) throw new Error(`Burn failed (${res.status})`);
  return data;
}

export async function transferTrophyEdition(payload: {
  recipient_id: string;
  item_id: string;
  edition_no: number;
  note?: string;
}): Promise<{ success: boolean; error?: string; message?: string }> {
  const res = await fetch('/api/shop/trophies/transfer', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok && !data.error) {
    throw new Error(`Transfer failed (${res.status})`);
  }
  return data;
}

export type StakingTrophyGrant = {
  interval_id: string;
  user_id: string;
  block_height: number;
  edition_key?: string;
  license_number?: string;
  gif_url?: string;
  battle_stats?: { combat_rating?: number; mood?: string };
  per_edition_gif?: boolean;
  reward_mn2?: number;
  granted_at?: string;
};

export type WalletStakingResponse = {
  success: boolean;
  guest?: boolean;
  message?: string;
  user_id?: string;
  platform_trophy_rewards?: boolean;
  on_chain_mint?: boolean;
  stake?: {
    staked?: number;
    total_earned?: number;
    estimated_next_interval_reward?: number;
  };
  trophy_grants?: {
    success?: boolean;
    grants: StakingTrophyGrant[];
    count?: number;
  };
  upgrade?: {
    id: string;
    unlocked: boolean;
    label: string;
    description: string;
  };
  links?: Record<string, string>;
};

export async function fetchWalletStaking(): Promise<WalletStakingResponse> {
  const res = await fetch('/api/wallet/v2/staking', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Staking failed (${res.status})`);
  }
  return res.json() as Promise<WalletStakingResponse>;
}

export async function fetchWalletTrophies(series?: string): Promise<WalletTrophiesResponse> {
  const params = new URLSearchParams();
  if (series) params.set('series', series);
  const qs = params.toString();
  const res = await fetch(`/api/wallet/v2/trophies${qs ? `?${qs}` : ''}`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Trophies failed (${res.status})`);
  }
  return res.json() as Promise<WalletTrophiesResponse>;
}

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
  fulfillment_ledger?: {
    total: number;
    pending: number;
    fulfilled: number;
    order_list_api: string;
    fulfillment_status_api: string;
  };
  fulfillment_status?: string;
  fulfillment_source?: string;
  fulfillment_sources?: string[];
  buyer_signal?: boolean;
  mn2_coin_offer_status?: string;
  fulfillment_order_lines?: Array<{
    id: string;
    label: string;
    status: string;
    fulfilled_at?: string | null;
  }>;
  message?: string;
  error?: string;
};

export type DiscordFulfillmentStatus = {
  success: boolean;
  user_id?: string;
  guest?: boolean;
  linked?: boolean;
  discord_id?: string;
  in_order_list?: boolean;
  fulfillment_status?: string;
  order_lines?: Array<{
    id: string;
    label: string;
    status: string;
    fulfilled_at?: string | null;
  }>;
  mn2_balance?: number;
  source?: string;
  sources?: string[];
  buyer_signal?: boolean;
  mn2_coin_offer_status?: string;
  order_list_api?: string;
  message?: string;
};

export async function fetchDiscordFulfillmentStatus(): Promise<DiscordFulfillmentStatus> {
  const res = await fetch('/api/wallet/v2/discord/fulfillment-status', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Discord fulfillment status failed (${res.status})`);
  }
  return res.json() as Promise<DiscordFulfillmentStatus>;
}

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

export type IntegrationUnit = {
  id?: string;
  label?: string;
  path?: string;
  api?: string;
  wallet_tab?: string;
  asset_count?: number;
  mn2_balance?: number | null;
  recent_jobs_count?: number;
  trophy_skus?: number;
  item_count?: number;
  episode_count?: number;
  channel_count?: number;
  online_count?: number;
  message_count?: number;
  performer_count?: number;
  upgrade_count?: number;
};

export type IntegrationHub = {
  success: boolean;
  user_id?: string;
  units?: Record<string, IntegrationUnit>;
  tab_groups?: Record<string, string[]>;
};

export type NewsItem = {
  id: string;
  title: string;
  summary?: string;
  date?: string;
  category?: string;
  href?: string;
  featured?: boolean;
};

export type PodcastEpisode = {
  id: string;
  title: string;
  description?: string;
  duration_sec?: number;
  published_at?: string;
  channel_id?: string;
};

export type ChatUser = {
  user_id: string;
  display_name?: string;
  status?: string;
  last_seen?: string;
};

export type ChatMessage = {
  id: string;
  user_id: string;
  display_name?: string;
  text: string;
  created_at?: string;
  rating_avg?: number;
  rating_count?: number;
};

export type NetworkChatStatus = {
  success: boolean;
  enabled?: boolean;
  user_id?: string;
  guest?: boolean;
  room_id?: string;
  online_count?: number;
  online_users?: ChatUser[];
  messages?: ChatMessage[];
  message_count?: number;
  engagement_disclaimer?: string;
  rewards?: {
    earned_today_mn2?: number;
    global_daily_cap_mn2?: number;
    message_post_mn2?: number;
    rating_given_mn2?: number;
    heartbeat_mn2?: number;
  };
  message?: string;
};

export type CamgirlPerformer = {
  id: string;
  name: string;
  tagline?: string;
  bio?: string;
  tier?: string;
  price_mn2?: number;
  tip_min_mn2?: number;
  wallet_user_id?: string;
  mn2_balance?: number;
  deposit_address?: string | null;
  explorer_url?: string | null;
  avatar_url?: string;
  online?: boolean;
  studio_path?: string;
};

export type CamgirlWalletDetail = {
  success: boolean;
  camgirl_id?: string;
  wallet_user_id?: string;
  mn2_balance?: number;
  name?: string;
  tip_min_mn2?: number;
  deposit_address?: string | null;
  explorer_url?: string | null;
  error?: string;
};

export type CamgirlTipResult = {
  success: boolean;
  camgirl_id?: string;
  wallet_user_id?: string;
  amount_mn2?: number;
  camgirl_balance?: number;
  error?: string;
  message?: string;
  tip_min_mn2?: number;
};

export type CamgirlUpgrade = {
  id: string;
  name: string;
  effect?: string;
  category: string;
  tier: string;
  unlock?: WalletUpgradeUnlock;
};

export type CamgirlsCatalog = {
  success: boolean;
  total: number;
  online_count?: number;
  performers: CamgirlPerformer[];
  studio_url?: string;
};

export type CamgirlsUpgradesCatalog = {
  success: boolean;
  total: number;
  categories: string[];
  upgrades: CamgirlUpgrade[];
};

export type CamgirlsUpgradesProgress = {
  success: boolean;
  user_id: string;
  guest?: boolean;
  unlocked_count: number;
  available_count?: number;
  locked_count: number;
  total: number;
  unlocked_ids: string[];
  available_ids?: string[];
  locked_ids: string[];
  by_category?: Record<string, { unlocked: number; available?: number; locked?: number; total: number }>;
  progress_hints?: Record<string, string>;
};

export type CamgirlAiFeatureAnimation = {
  type: string;
  asset_url: string;
  duration_ms: number;
};

export type CamgirlAiFeaturePayment = {
  price_mn2: number;
  tip_min_mn2?: number;
  unlock_upgrade_id?: string | null;
  effective_price_mn2?: number;
  unlocked_via_upgrade?: boolean;
};

export type CamgirlAiFeatureSound = {
  url: string;
  volume_default: number;
};

export type CamgirlAiFeature = {
  id: string;
  name: string;
  category: string;
  performer_ids: string[];
  animation: CamgirlAiFeatureAnimation;
  payment: CamgirlAiFeaturePayment;
  sound: CamgirlAiFeatureSound;
  description?: string;
  performer_match?: boolean;
};

export type CamgirlsAiFeaturesCatalog = {
  success: boolean;
  total: number;
  categories: string[];
  features: CamgirlAiFeature[];
};

export type CamgirlAiFeatureTriggerResult = {
  success: boolean;
  feature_id?: string;
  name?: string;
  category?: string;
  performer_id?: string;
  paid_mn2?: number;
  unlocked_via_upgrade?: boolean;
  playback?: {
    animation: CamgirlAiFeatureAnimation;
    sound: CamgirlAiFeatureSound;
    triggered_at?: string;
  };
  error?: string;
  message?: string;
};

export async function fetchIntegrationHub(): Promise<IntegrationHub> {
  const res = await fetch('/api/wallet/v2/integration/hub', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Integration hub failed (${res.status})`);
  return res.json() as Promise<IntegrationHub>;
}

export async function fetchPlatformNews(limit = 10): Promise<{ success: boolean; news: NewsItem[]; count: number }> {
  const res = await fetch(`/api/news/platform?limit=${limit}`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`News failed (${res.status})`);
  return res.json() as Promise<{ success: boolean; news: NewsItem[]; count: number }>;
}

export async function fetchPodcastEpisodes(limit = 8): Promise<{ success: boolean; episodes: PodcastEpisode[] }> {
  const res = await fetch(`/api/podcast/episodes?limit=${limit}`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Podcast failed (${res.status})`);
  const data = await res.json() as { success?: boolean; episodes?: PodcastEpisode[] };
  return { success: Boolean(data.success), episodes: data.episodes || [] };
}

export async function fetchNetworkChatStatus(): Promise<NetworkChatStatus> {
  const res = await fetch('/api/wallet/v2/network-chat/status', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Network chat failed (${res.status})`);
  return res.json() as Promise<NetworkChatStatus>;
}

export async function postNetworkChatMessage(text: string, displayName?: string): Promise<{
  success: boolean;
  message?: ChatMessage;
  reward?: { mn2_awarded?: number };
  error?: string;
}> {
  const res = await fetch('/api/wallet/v2/network-chat/message', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ text, display_name: displayName }),
  });
  return res.json() as Promise<{
    success: boolean;
    message?: ChatMessage;
    reward?: { mn2_awarded?: number };
    error?: string;
  }>;
}

export async function postNetworkChatRating(messageId: string, stars: number): Promise<{
  success: boolean;
  message?: ChatMessage;
  reward?: { mn2_awarded?: number };
  error?: string;
}> {
  const res = await fetch('/api/wallet/v2/network-chat/rating', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ message_id: messageId, stars }),
  });
  return res.json() as Promise<{
    success: boolean;
    message?: ChatMessage;
    reward?: { mn2_awarded?: number };
    error?: string;
  }>;
}

export async function postNetworkChatHeartbeat(displayName?: string): Promise<{ success: boolean }> {
  const res = await fetch('/api/wallet/v2/network-chat/heartbeat', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ display_name: displayName }),
  });
  return res.json() as Promise<{ success: boolean }>;
}

export type LedgerOutreachLead = {
  ledger_row_id: string;
  ledger_rank?: number;
  display_name?: string;
  discord_id?: string;
  youtube_id?: string;
  facebook_id?: string;
  user_id?: string;
  priority_score?: number;
  buyer_score?: number;
  sources?: string[];
  assigned_camgirl_id?: string;
  mn2_coin_offer_status?: string;
};

export async function fetchCamgirlsLedgerQueue(limit = 25): Promise<{
  success: boolean;
  total: number;
  queue: LedgerOutreachLead[];
}> {
  const res = await fetch(`/api/wallet/v2/camgirls/ledger/queue?limit=${limit}`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Ledger queue failed (${res.status})`);
  return res.json() as Promise<{ success: boolean; total: number; queue: LedgerOutreachLead[] }>;
}

export async function postCamgirlLedgerOffer(
  ledgerRowId: string,
  mn2Amount: number,
  priceUsd: number,
  rail: 'paypal' | 'usdt' | 'usdc',
  performerId?: string,
): Promise<{ success: boolean; offer?: unknown; error?: string }> {
  const res = await fetch('/api/wallet/v2/camgirls/ledger/offer', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      ledger_row_id: ledgerRowId,
      mn2_amount: mn2Amount,
      price_usd: priceUsd,
      rail,
      performer_id: performerId,
    }),
  });
  return res.json() as Promise<{ success: boolean; offer?: unknown; error?: string }>;
}

export async function fetchCamgirlsCatalog(): Promise<CamgirlsCatalog> {
  const res = await fetch('/api/wallet/v2/camgirls/catalog', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Camgirls catalog failed (${res.status})`);
  return res.json() as Promise<CamgirlsCatalog>;
}

export async function fetchCamgirlWallet(camgirlId: string): Promise<CamgirlWalletDetail> {
  const res = await fetch(`/api/wallet/v2/camgirls/${encodeURIComponent(camgirlId)}/wallet`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  return res.json() as Promise<CamgirlWalletDetail>;
}

export async function postCamgirlTip(camgirlId: string, amountMn2: number): Promise<CamgirlTipResult> {
  const res = await fetch(`/api/wallet/v2/camgirls/${encodeURIComponent(camgirlId)}/tip`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ amount_mn2: amountMn2 }),
  });
  return res.json() as Promise<CamgirlTipResult>;
}

export async function fetchCamgirlsUpgrades(category?: string): Promise<CamgirlsUpgradesCatalog> {
  const params = category ? `?category=${encodeURIComponent(category)}` : '';
  const res = await fetch(`/api/wallet/v2/camgirls/upgrades${params}`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Camgirls upgrades failed (${res.status})`);
  return res.json() as Promise<CamgirlsUpgradesCatalog>;
}

export async function fetchCamgirlsUpgradesProgress(): Promise<CamgirlsUpgradesProgress> {
  const res = await fetch('/api/wallet/v2/camgirls/upgrades/progress', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Camgirls progress failed (${res.status})`);
  return res.json() as Promise<CamgirlsUpgradesProgress>;
}

export async function unlockCamgirlUpgrade(upgradeId: string): Promise<{
  success: boolean;
  upgrade_id?: string;
  name?: string;
  progress?: CamgirlsUpgradesProgress;
  error?: string;
  message?: string;
}> {
  const res = await fetch('/api/wallet/v2/camgirls/upgrades/unlock', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ upgrade_id: upgradeId }),
  });
  return res.json() as Promise<{
    success: boolean;
    upgrade_id?: string;
    name?: string;
    progress?: CamgirlsUpgradesProgress;
    error?: string;
    message?: string;
  }>;
}

export async function fetchCamgirlsAiFeatures(
  category?: string,
  performerId?: string,
): Promise<CamgirlsAiFeaturesCatalog> {
  const params = new URLSearchParams();
  if (category) params.set('category', category);
  if (performerId) params.set('performer_id', performerId);
  const qs = params.toString();
  const res = await fetch(`/api/wallet/v2/camgirls/ai-features${qs ? `?${qs}` : ''}`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`Camgirls AI features failed (${res.status})`);
  return res.json() as Promise<CamgirlsAiFeaturesCatalog>;
}

export async function fetchCamgirlAiFeature(
  featureId: string,
  performerId?: string,
): Promise<{ success: boolean; feature?: CamgirlAiFeature; error?: string }> {
  const params = performerId ? `?performer_id=${encodeURIComponent(performerId)}` : '';
  const res = await fetch(`/api/wallet/v2/camgirls/ai-features/${encodeURIComponent(featureId)}${params}`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  return res.json() as Promise<{ success: boolean; feature?: CamgirlAiFeature; error?: string }>;
}

export async function triggerCamgirlAiFeature(
  featureId: string,
  performerId?: string,
): Promise<CamgirlAiFeatureTriggerResult> {
  const res = await fetch(`/api/wallet/v2/camgirls/ai-features/${encodeURIComponent(featureId)}/trigger`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ performer_id: performerId }),
  });
  return res.json() as Promise<CamgirlAiFeatureTriggerResult>;
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
