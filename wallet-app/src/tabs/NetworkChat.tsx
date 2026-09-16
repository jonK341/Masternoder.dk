import { useCallback, useEffect, useState } from 'preact/hooks';
import {
  fetchNetworkChatStatus,
  postNetworkChatHeartbeat,
  postNetworkChatMessage,
  postNetworkChatRating,
  type ChatMessage,
  type NetworkChatStatus,
} from '../api/client';

export function NetworkChat() {
  const [status, setStatus] = useState<NetworkChatStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [posting, setPosting] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    return fetchNetworkChatStatus()
      .then((data) => {
        setStatus(data);
        setLoading(false);
        if (!data.guest) {
          postNetworkChatHeartbeat().catch(() => {});
        }
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    refresh();
    const interval = window.setInterval(() => {
      if (!status?.guest) postNetworkChatHeartbeat().catch(() => {});
    }, 60000);
    return () => window.clearInterval(interval);
  }, [refresh, status?.guest]);

  const handleSend = async () => {
    if (!text.trim() || posting) return;
    setPosting(true);
    setFlash(null);
    try {
      const result = await postNetworkChatMessage(text.trim());
      if (result.success) {
        setText('');
        const reward = result.reward?.mn2_awarded;
        if (reward && reward > 0) {
          setFlash(`+${reward} MN2 for activity`);
        }
        await refresh();
      } else {
        const errMsg = typeof result.message === 'string'
          ? result.message
          : result.error || 'Send failed';
        setFlash(errMsg);
      }
    } catch (err: unknown) {
      setFlash(err instanceof Error ? err.message : 'Send failed');
    } finally {
      setPosting(false);
      window.setTimeout(() => setFlash(null), 3000);
    }
  };

  const handleRate = async (msg: ChatMessage, stars: number) => {
    try {
      const result = await postNetworkChatRating(msg.id, stars);
      if (result.success) {
        const reward = result.reward?.mn2_awarded;
        if (reward && reward > 0) setFlash(`+${reward} MN2 for rating`);
        await refresh();
      }
    } catch {
      /* ignore */
    }
  };

  const messages = status?.messages || [];
  const online = status?.online_users || [];

  return (
    <div class="wallet-tab-panel">
      <section class="wallet-panel wallet-exchange-hero">
        <div style={{ padding: '16px' }}>
          <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>Network Chat</div>
          <p style={{ margin: '8px 0 0', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            Chat with users on the MN2 network — earn micro MN2 for messages and ratings.
          </p>
          {status?.rewards && (
            <div style={{ marginTop: '10px', fontSize: '0.8rem', color: 'var(--wallet-muted)' }}>
              Today: {status.rewards.earned_today_mn2?.toFixed(4) ?? '0'} / {status.rewards.global_daily_cap_mn2} MN2
            </div>
          )}
        </div>
      </section>

      <div class="wallet-kpi-grid" style={{ marginTop: '12px' }}>
        <div class="wallet-panel wallet-kpi">
          <div class="wallet-kpi-label">Online</div>
          <div class="wallet-kpi-value">{status?.online_count ?? '—'}</div>
        </div>
        <div class="wallet-panel wallet-kpi">
          <div class="wallet-kpi-label">Messages</div>
          <div class="wallet-kpi-value">{status?.message_count ?? '—'}</div>
        </div>
      </div>

      <section class="wallet-panel" style={{ marginTop: '12px' }}>
        <div class="wallet-panel-header">
          <div class="wallet-panel-title">Online users</div>
        </div>
        <div style={{ padding: '12px 16px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {online.map((u) => (
            <span
              key={u.user_id}
              style={{
                padding: '4px 10px',
                background: 'var(--wallet-bg-elevated)',
                border: 'var(--wallet-border)',
                borderRadius: 'var(--wallet-radius)',
                fontSize: '0.8rem',
              }}
            >
              {u.display_name || u.user_id}
              <span style={{ color: 'var(--wallet-muted)', marginLeft: '6px' }}>{u.status}</span>
            </span>
          ))}
        </div>
      </section>

      <section class="wallet-panel" style={{ marginTop: '12px' }}>
        <div class="wallet-panel-header">
          <div class="wallet-panel-title">Messages</div>
        </div>
        {loading ? (
          <div style={{ padding: '16px' }}>
            <div class="wallet-skeleton" style={{ height: '120px' }} />
          </div>
        ) : error ? (
          <div class="wallet-error wallet-error--inline" role="alert">{error}</div>
        ) : (
          <div style={{ maxHeight: '320px', overflowY: 'auto', padding: '8px 16px' }}>
            {messages.length === 0 ? (
              <p style={{ color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>No messages yet — be the first!</p>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} style={{ borderBottom: '1px solid var(--wallet-border)', padding: '10px 0' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                    {msg.display_name || msg.user_id}
                    <span style={{ color: 'var(--wallet-muted)', fontWeight: 400, marginLeft: '8px', fontSize: '0.75rem' }}>
                      {msg.created_at?.slice(11, 19)}
                    </span>
                  </div>
                  <p style={{ margin: '4px 0 6px', fontSize: '0.9rem' }}>{msg.text}</p>
                  <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => handleRate(msg, star)}
                        disabled={status?.guest}
                        style={{
                          border: 'none',
                          background: 'transparent',
                          cursor: status?.guest ? 'not-allowed' : 'pointer',
                          opacity: (msg.rating_avg || 0) >= star ? 1 : 0.4,
                          fontSize: '0.9rem',
                        }}
                        aria-label={`Rate ${star} stars`}
                      >
                        ★
                      </button>
                    ))}
                    {msg.rating_count ? (
                      <span style={{ fontSize: '0.75rem', color: 'var(--wallet-muted)', marginLeft: '6px' }}>
                        {msg.rating_avg} ({msg.rating_count})
                      </span>
                    ) : null}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {!status?.guest && (
          <div style={{ padding: '12px 16px 16px', borderTop: 'var(--wallet-border)' }}>
            <textarea
              value={text}
              onInput={(e) => setText((e.target as HTMLTextAreaElement).value)}
              placeholder="Say something to the network…"
              rows={2}
              style={{
                width: '100%',
                background: 'var(--wallet-bg-elevated)',
                border: 'var(--wallet-border)',
                borderRadius: 'var(--wallet-radius)',
                color: 'var(--wallet-text)',
                padding: '10px',
                fontFamily: 'inherit',
                resize: 'vertical',
              }}
            />
            <button
              type="button"
              class="wallet-discord-btn wallet-discord-btn-primary"
              style={{ marginTop: '8px' }}
              disabled={posting || !text.trim()}
              onClick={handleSend}
            >
              {posting ? 'Sending…' : 'Send message'}
            </button>
            {flash && (
              <div style={{ marginTop: '8px', fontSize: '0.85rem', color: 'var(--wallet-accent)' }}>{flash}</div>
            )}
          </div>
        )}
        {status?.guest && (
          <div style={{ padding: '12px 16px', color: 'var(--wallet-muted)', fontSize: '0.85rem' }}>
            Sign in to chat and earn micro MN2 rewards.
          </div>
        )}
        {status?.engagement_disclaimer && (
          <div style={{ padding: '0 16px 12px', fontSize: '0.72rem', color: 'var(--wallet-muted)' }}>
            {status.engagement_disclaimer}
          </div>
        )}
      </section>
    </div>
  );
}
