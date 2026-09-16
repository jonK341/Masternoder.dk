import { useCallback, useEffect, useState } from 'preact/hooks';
import {
  fetchDiscordStatus,
  linkDiscordManual,
  unlinkDiscord,
  type DiscordStatus,
} from '../api/client';

const NOTIF_KEYS = [
  { key: 'balance_alerts', label: 'Balance alerts' },
  { key: 'trophy_drops', label: 'Trophy drops' },
  { key: 'block_trophy_mint', label: 'Block trophy mint' },
  { key: 'battle_results', label: 'Battle contest results' },
] as const;

type NotifKey = (typeof NOTIF_KEYS)[number]['key'];

function notifStorageKey(userId: string) {
  return `wallet_discord_notif_${userId || 'guest'}`;
}

function loadLocalNotifs(userId: string): Record<NotifKey, boolean> {
  const defaults: Record<NotifKey, boolean> = {
    balance_alerts: false,
    trophy_drops: false,
    block_trophy_mint: false,
    battle_results: false,
  };
  try {
    const raw = localStorage.getItem(notifStorageKey(userId));
    if (!raw) return defaults;
    const parsed = JSON.parse(raw) as Record<string, boolean>;
    for (const { key } of NOTIF_KEYS) {
      if (typeof parsed[key] === 'boolean') defaults[key] = parsed[key];
    }
  } catch {
    /* ignore */
  }
  return defaults;
}

function saveLocalNotifs(userId: string, prefs: Record<NotifKey, boolean>) {
  try {
    localStorage.setItem(notifStorageKey(userId), JSON.stringify(prefs));
  } catch {
    /* ignore */
  }
}

export function DiscordPanel() {
  const [status, setStatus] = useState<DiscordStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [manualId, setManualId] = useState('');
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [notifs, setNotifs] = useState<Record<NotifKey, boolean>>({
    balance_alerts: false,
    trophy_drops: false,
    block_trophy_mint: false,
    battle_results: false,
  });

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDiscordStatus();
      setStatus(data);
      if (data.user_id) {
        setNotifs(loadLocalNotifs(data.user_id));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load Discord status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const onConnectOAuth = () => {
    if (!status) return;
    const returnUrl = `${window.location.pathname}?tab=settings&panel=discord`;
    if (status.linked_role_connect_path) {
      window.location.href = status.linked_role_connect_path;
      return;
    }
    if (status.linked_role_oauth_url) {
      window.location.href = status.linked_role_oauth_url;
      return;
    }
    if (status.oauth_login_start_path) {
      const hint = status.user_id ? `&user_id_hint=${encodeURIComponent(status.user_id)}` : '';
      window.location.href = `${status.oauth_login_start_path}?redirect=true&return_url=${encodeURIComponent(returnUrl)}${hint}`;
      return;
    }
    window.location.href = status.profile_discord_path || '/profile#discord-link-card';
  };

  const onManualLink = async () => {
    const discordId = manualId.trim();
    if (!discordId || !status?.user_id) {
      setActionMsg('Enter your Discord user ID.');
      return;
    }
    setActionMsg(null);
    try {
      const res = await linkDiscordManual(status.user_id, discordId);
      if (res.success) {
        setActionMsg('Discord linked.');
        setManualId('');
        await reload();
      } else {
        setActionMsg(res.error || 'Link failed');
      }
    } catch (err) {
      setActionMsg(err instanceof Error ? err.message : 'Link failed');
    }
  };

  const onUnlink = async () => {
    if (!status?.user_id) return;
    setActionMsg(null);
    try {
      const res = await unlinkDiscord(status.user_id);
      if (res.success) {
        setActionMsg('Discord unlinked.');
        await reload();
      } else {
        setActionMsg(res.error || 'Unlink failed');
      }
    } catch (err) {
      setActionMsg(err instanceof Error ? err.message : 'Unlink failed');
    }
  };

  const onNotifToggle = (key: NotifKey, checked: boolean) => {
    const next = { ...notifs, [key]: checked };
    setNotifs(next);
    if (status?.user_id) saveLocalNotifs(status.user_id, next);
  };

  if (loading) {
    return (
      <div class="wallet-panel wallet-tab-panel" style={{ padding: '20px' }}>
        <p style={{ color: 'var(--wallet-muted)' }}>Loading Discord…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div class="wallet-panel wallet-tab-panel" style={{ padding: '20px' }}>
        <p style={{ color: 'var(--wallet-danger)' }}>{error}</p>
        <button type="button" onClick={reload}>Retry</button>
      </div>
    );
  }

  if (!status) return null;

  if (status.guest) {
    return (
      <div class="wallet-panel wallet-tab-panel" style={{ padding: '20px' }}>
        <h2 style={{ margin: '0 0 8px', fontSize: '1.1rem' }}>Discord</h2>
        <p style={{ color: 'var(--wallet-muted)' }}>
          Log in to link your Discord account for VIP roles, notifications, and sharing.
        </p>
        <a href="/profile" class="wallet-discord-btn" style={{ display: 'inline-block', marginTop: '12px' }}>
          Go to Profile to sign in
        </a>
      </div>
    );
  }

  return (
    <div class="wallet-panel wallet-tab-panel" style={{ padding: '20px' }}>
      <h2 style={{ margin: '0 0 4px', fontSize: '1.1rem' }}>Discord</h2>
      <p style={{ margin: '0 0 16px', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
        Link Discord for casino VIP, hosting roles, and wallet alerts.
      </p>

      <section style={{ marginBottom: '20px', padding: '14px', background: 'var(--wallet-bg-elevated)', border: 'var(--wallet-border)', borderRadius: 'var(--wallet-radius)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {status.avatar_url ? (
            <img
              src={status.avatar_url}
              alt=""
              width={48}
              height={48}
              style={{ borderRadius: 'var(--wallet-radius)', border: 'var(--wallet-border)' }}
            />
          ) : (
            <div
              style={{
                width: 48,
                height: 48,
                background: '#5865f2',
                borderRadius: 'var(--wallet-radius)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
              }}
            >
              D
            </div>
          )}
          <div style={{ flex: 1, minWidth: 200 }}>
            {status.linked ? (
              <>
                <div style={{ fontWeight: 700 }}>Linked</div>
                <div style={{ fontFamily: 'var(--wallet-font-mono)', fontSize: '0.85rem', color: 'var(--wallet-muted)' }}>
                  {status.username ? `${status.username} · ` : ''}
                  <code>{status.discord_id}</code>
                </div>
                {status.roles_available && status.roles_available.length > 0 ? (
                  <div style={{ marginTop: '6px', fontSize: '0.8rem' }}>
                    Roles: {status.roles_available.map((r) => (
                      <span
                        key={r}
                        style={{
                          display: 'inline-block',
                          marginRight: '6px',
                          padding: '2px 6px',
                          background: 'var(--wallet-accent-dim)',
                          color: 'var(--wallet-accent)',
                          borderRadius: 'var(--wallet-radius)',
                        }}
                      >
                        {r.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                ) : null}
              </>
            ) : (
              <>
                <div style={{ fontWeight: 700 }}>Not linked</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--wallet-muted)' }}>
                  Connect via OAuth or paste your Discord user ID below.
                </div>
              </>
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {!status.linked ? (
              <button type="button" class="wallet-discord-btn wallet-discord-btn-primary" onClick={onConnectOAuth}>
                Connect Discord
              </button>
            ) : (
              <button type="button" class="wallet-discord-btn" onClick={onUnlink}>
                Unlink
              </button>
            )}
            {status.server_invite_url ? (
              <a
                href={status.server_invite_url}
                target="_blank"
                rel="noopener noreferrer"
                class="wallet-discord-btn"
              >
                Join server
              </a>
            ) : null}
          </div>
        </div>
        {actionMsg ? (
          <p style={{ margin: '12px 0 0', fontSize: '0.85rem', color: 'var(--wallet-accent)' }}>{actionMsg}</p>
        ) : null}
      </section>

      {!status.linked && status.manual_link_supported ? (
        <section style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '6px' }}>
            Manual link (Developer Mode → Copy User ID)
          </label>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <input
              type="text"
              value={manualId}
              onInput={(e) => setManualId((e.target as HTMLInputElement).value)}
              placeholder="Discord user ID"
              style={{
                flex: '1 1 200px',
                padding: '8px 10px',
                background: 'var(--wallet-bg-elevated)',
                border: 'var(--wallet-border)',
                borderRadius: 'var(--wallet-radius)',
                color: 'var(--wallet-text)',
                fontFamily: 'var(--wallet-font-mono)',
              }}
            />
            <button type="button" class="wallet-discord-btn wallet-discord-btn-primary" onClick={onManualLink}>
              Link ID
            </button>
          </div>
        </section>
      ) : null}

      <section style={{ marginBottom: '20px' }}>
        <h3 style={{ margin: '0 0 8px', fontSize: '0.95rem' }}>Wallet notifications (opt-in)</h3>
        <p style={{ margin: '0 0 10px', fontSize: '0.8rem', color: 'var(--wallet-muted)' }}>
          {status.notification_prefs_note || 'Notify your linked Discord when events occur.'}
        </p>
        <div style={{ display: 'grid', gap: '8px' }}>
          {NOTIF_KEYS.map(({ key, label }) => (
            <label key={key} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={notifs[key]}
                disabled={!status.linked}
                onChange={(e) => onNotifToggle(key, (e.target as HTMLInputElement).checked)}
              />
              <span style={{ fontSize: '0.9rem' }}>{label}</span>
            </label>
          ))}
        </div>
      </section>

      {status.casino_vip_eligible === false && status.linked ? (
        <p style={{ fontSize: '0.8rem', color: 'var(--wallet-muted)' }}>
          Casino VIP requires {status.min_mn2_for_vip ?? 100} MN2 balance.
        </p>
      ) : null}
    </div>
  );
}
