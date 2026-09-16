import { DiscordPanel } from './Discord';

type SettingsPanel = 'discord' | 'general';

function panelFromQuery(): SettingsPanel {
  const panel = new URLSearchParams(window.location.search).get('panel');
  return panel === 'discord' ? 'discord' : 'general';
}

export function Settings() {
  const activePanel = panelFromQuery();

  return (
    <div>
      <nav
        aria-label="Settings sections"
        style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '12px',
          flexWrap: 'wrap',
        }}
      >
        <a
          href="/wallets?tab=settings"
          style={{
            padding: '8px 12px',
            border: 'var(--wallet-border)',
            borderRadius: 'var(--wallet-radius)',
            background: activePanel === 'general' ? 'var(--wallet-accent-dim)' : 'transparent',
            color: activePanel === 'general' ? 'var(--wallet-accent)' : 'var(--wallet-muted)',
            textDecoration: 'none',
            fontSize: '0.85rem',
          }}
        >
          General
        </a>
        <a
          href="/wallets?tab=settings&panel=discord"
          style={{
            padding: '8px 12px',
            border: 'var(--wallet-border)',
            borderRadius: 'var(--wallet-radius)',
            background: activePanel === 'discord' ? 'var(--wallet-accent-dim)' : 'transparent',
            color: activePanel === 'discord' ? 'var(--wallet-accent)' : 'var(--wallet-muted)',
            textDecoration: 'none',
            fontSize: '0.85rem',
          }}
        >
          Discord
        </a>
      </nav>

      {activePanel === 'discord' ? (
        <DiscordPanel />
      ) : (
        <div class="wallet-panel wallet-tab-panel" style={{ padding: '20px' }}>
          <h2 style={{ margin: '0 0 8px', fontSize: '1.1rem' }}>Settings</h2>
          <p style={{ color: 'var(--wallet-muted)', margin: '0 0 16px' }}>
            Withdraw security, fiat toggle, and daemon downloads ship in WR-U9.
            Open the <a href="/wallets?tab=settings&panel=discord" style={{ color: 'var(--wallet-accent)' }}>Discord</a> panel to link your account.
          </p>
          <section id="mobile-download" aria-label="Download mobile app" style={{ borderTop: 'var(--wallet-border)', paddingTop: '16px' }}>
            <h3 style={{ margin: '0 0 8px', fontSize: '0.95rem' }}>Download mobile app</h3>
            <p style={{ color: 'var(--wallet-muted)', margin: '0 0 12px', fontSize: '0.85rem' }}>
              Android APK and iOS TestFlight ship with tag <code style={{ color: 'var(--wallet-accent)' }}>wallet-mobile-v0.1.0-preview</code>.
              iPhone users can also Add to Home Screen from Safari on <code>/wallets</code>.
            </p>
            <ul style={{ margin: '0 0 12px', paddingLeft: '1.2rem', color: 'var(--wallet-muted)', fontSize: '0.85rem' }}>
              <li><strong>Android:</strong> build from <code>mobile/wallet-app/</code> or download <code>MasterNoder-Wallet-android-v0.1.0-preview.apk</code> from GitHub Releases after the first tag.</li>
              <li><strong>iOS:</strong> Capacitor shell in <code>mobile/wallet-app/</code> (TestFlight placeholder) or PWA Add to Home Screen.</li>
              <li><strong>Docs:</strong> <code>docs/WALLET_DOWNLOAD.md#android</code> and <code>#ios</code> in this repo.</li>
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
