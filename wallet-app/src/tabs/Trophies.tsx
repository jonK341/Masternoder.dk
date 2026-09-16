import { useEffect, useState } from 'preact/hooks';
import {
  battleBlockTrophy,
  fetchWalletTrophies,
  equipTrophyOnProfile,
  shareTrophyDiscord,
  transferTrophyEdition,
  type TrophyEdition,
  type WalletTrophiesResponse,
} from '../api/client';

type SeriesFilter = '' | 'top25' | 'block-mint';

const SERIES_CHIPS: { id: SeriesFilter; label: string }[] = [
  { id: '', label: 'All' },
  { id: 'top25', label: 'Top 25' },
  { id: 'block-mint', label: 'Block' },
];

export function Trophies() {
  const [series, setSeries] = useState<SeriesFilter>('');
  const [data, setData] = useState<WalletTrophiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchWalletTrophies(series || undefined)
      .then((res) => {
        if (!cancelled) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message || 'Failed to load trophies');
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [series]);

  const counts = data?.counts;
  const editions = data?.editions ?? [];

  const reload = () => {
    setLoading(true);
    fetchWalletTrophies(series || undefined)
      .then((res) => { setData(res); setLoading(false); })
      .catch((err: Error) => { setError(err.message); setLoading(false); });
  };

  return (
    <div class="wallet-tab-panel wallet-trophies-tab">
      <section class="wallet-panel wallet-trophies-hero">
        <div class="wallet-panel-header">
          <div>
            <div class="wallet-panel-title">Trophy collection</div>
            <div class="wallet-panel-subtitle">
              Platform-ledger trophy editions
            </div>
          </div>
          {counts && counts.total_editions > 0 && (
            <span class="wallet-badge">🏆 {counts.total_editions}</span>
          )}
        </div>
        <p class="wallet-trophies-disclaimer">
          MN2 cannot mint trophies on-chain today. These are licensed digital collectibles
          stored in your shop inventory with edition numbers.
        </p>
        {counts && counts.top25_total > 0 && (
          <div class="wallet-trophies-progress">
            Top 25: <strong>{counts.top25_owned}</strong> / {counts.top25_total} editions
          </div>
        )}
        <div class="wallet-trophy-chips" role="group" aria-label="Trophy series filter">
          {SERIES_CHIPS.map((chip) => (
            <button
              key={chip.id || 'all'}
              type="button"
              class={`wallet-trophy-chip${series === chip.id ? ' wallet-trophy-chip--active' : ''}`}
              onClick={() => setSeries(chip.id)}
            >
              {chip.label}
            </button>
          ))}
        </div>
      </section>

      {loading && (
        <section class="wallet-panel">
          <div class="wallet-skeleton" style={{ height: '120px' }} />
        </section>
      )}

      {error && (
        <section class="wallet-panel wallet-trophies-error" role="alert">
          {error}
        </section>
      )}

      {!loading && !error && data?.guest && (
        <section class="wallet-panel wallet-trophies-empty">
          <p>{data.message || 'Sign in to view your trophy collection.'}</p>
          <a href="/profile" class="wallet-discord-btn wallet-discord-btn-primary">Create account →</a>
        </section>
      )}

      {!loading && !error && !data?.guest && editions.length === 0 && (
        <section class="wallet-panel wallet-trophies-empty">
          <p>No trophies in this series yet.</p>
          <a href="/shop?tab=trophies" class="wallet-discord-btn wallet-discord-btn-primary">
            Browse shop trophies →
          </a>
        </section>
      )}

      {!loading && !error && editions.length > 0 && (
        <section class="wallet-panel" aria-label="Owned trophy editions">
          <div class="wallet-trophy-gallery" role="list">
            {editions.map((ed) => (
              <TrophyEditionCard key={ed.edition_key} edition={ed} onTransferred={reload} />
            ))}
          </div>
        </section>
      )}

      {!loading && !error && data?.catalog_preview && data.catalog_preview.length > 0 && (
        <section class="wallet-panel">
          <div class="wallet-panel-header">
            <div class="wallet-panel-title">Collect more</div>
            <div class="wallet-panel-subtitle">Available in the shop</div>
          </div>
          <div class="wallet-trophy-gallery wallet-trophy-gallery--compact" role="list">
            {data.catalog_preview.map((item) => (
              <a
                key={item.id}
                href={item.shop_url || '/shop?tab=trophies'}
                class="wallet-trophy-gallery-card wallet-trophy-gallery-card--shop"
                role="listitem"
              >
                {item.image_url ? (
                  <img src={item.image_url} alt="" class="wallet-trophy-gallery-img" loading="lazy" />
                ) : (
                  <span class="wallet-trophy-gallery-icon" aria-hidden="true">🏆</span>
                )}
                <span class="wallet-trophy-gallery-name">{item.name || item.id}</span>
                {item.effective_price_usd != null && (
                  <span class="wallet-trophy-gallery-price">
                    ${Number(item.effective_price_usd).toFixed(2)}
                  </span>
                )}
              </a>
            ))}
          </div>
        </section>
      )}

      <section class="wallet-panel wallet-trophies-actions">
        <a href="/shop?tab=trophies" class="wallet-link">Shop trophies</a>
        <span class="wallet-trophies-actions-sep">·</span>
        <a href="/shop?tab=auction" class="wallet-link">Auction house</a>
      </section>
    </div>
  );
}

function TrophyEditionCard({ edition, onTransferred }: { edition: TrophyEdition; onTransferred: () => void }) {
  const title = edition.item_name || edition.item_id;
  const [showTransfer, setShowTransfer] = useState(false);
  const [recipient, setRecipient] = useState('');
  const [transferError, setTransferError] = useState<string | null>(null);
  const [transferring, setTransferring] = useState(false);
  const [battling, setBattling] = useState(false);
  const [battleMsg, setBattleMsg] = useState<string | null>(null);
  const [shareMsg, setShareMsg] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);
  const [equipMsg, setEquipMsg] = useState<string | null>(null);
  const [equipping, setEquipping] = useState(false);
  const canTransfer = !edition.hold_until && !edition.legacy_stack && edition.trade_actions?.peer_transfer;
  const isBlockTrophy = edition.platform_trophy || edition.item_id?.startsWith('block-') || edition.series === 'block_mint';
  const stats = edition.battle_stats;
  const mediaSrc = edition.gif_url || edition.image_url;

  const runEquip = async () => {
    if (!edition.edition_key) return;
    setEquipping(true);
    setEquipMsg(null);
    try {
      const res = await equipTrophyOnProfile(edition.edition_key);
      setEquipMsg(res.success ? 'Featured on profile' : (res.error || 'Equip failed'));
    } catch (err) {
      setEquipMsg((err as Error).message || 'Equip failed');
    } finally {
      setEquipping(false);
    }
  };

  const runShare = async () => {
    if (!edition.edition_key) return;
    setSharing(true);
    setShareMsg(null);
    try {
      const res = await shareTrophyDiscord(edition.edition_key);
      setShareMsg(res.success ? 'Shared to Discord' : (res.error || 'Share failed'));
    } catch (err) {
      setShareMsg((err as Error).message || 'Share failed');
    } finally {
      setSharing(false);
    }
  };

  const runBattle = async () => {
    if (!edition.edition_key) return;
    setBattling(true);
    setBattleMsg(null);
    try {
      const res = await battleBlockTrophy(edition.edition_key);
      if (!res.success) {
        setBattleMsg(res.error || 'Battle failed');
        return;
      }
      const bp = res.rewards?.battle_points ?? 0;
      const gp = res.rewards?.game_points ?? 0;
      setBattleMsg(`${res.message || res.result} (+${bp} ⚔️, +${gp} 🎮)`);
    } catch (err) {
      setBattleMsg((err as Error).message || 'Battle failed');
    } finally {
      setBattling(false);
    }
  };

  const submitTransfer = async () => {
    if (!recipient.trim()) {
      setTransferError('Enter a recipient profile ID');
      return;
    }
    setTransferring(true);
    setTransferError(null);
    try {
      const res = await transferTrophyEdition({
        recipient_id: recipient.trim(),
        item_id: edition.item_id,
        edition_no: edition.edition_no,
      });
      if (!res.success) {
        setTransferError(res.error || res.message || 'Transfer failed');
        return;
      }
      setShowTransfer(false);
      setRecipient('');
      onTransferred();
    } catch (err) {
      setTransferError((err as Error).message || 'Transfer failed');
    } finally {
      setTransferring(false);
    }
  };

  return (
    <article class="wallet-trophy-gallery-card" role="listitem">
      {mediaSrc ? (
        <img src={mediaSrc} alt="" class="wallet-trophy-gallery-img" loading="lazy" />
      ) : (
        <div class="wallet-trophy-gallery-icon-wrap">
          <span class="wallet-trophy-gallery-icon" aria-hidden="true">🏆</span>
        </div>
      )}
      <div class="wallet-trophy-gallery-body">
        <div class="wallet-trophy-gallery-name">{title}</div>
        <div class="wallet-trophy-gallery-meta">
          Edition #{edition.edition_no}
          {edition.serial_number ? ` · ${edition.serial_number}` : edition.serial_key ? ` · ${edition.serial_key}` : ''}
        </div>
        {edition.license_number ? (
          <div class="wallet-trophy-gallery-meta wallet-trophy-license">License {edition.license_number}</div>
        ) : null}
        {stats ? (
          <div class="wallet-trophy-battle-stats" aria-label="Battle stats">
            <span>⚔ {stats.combat_rating ?? '—'}</span>
            <span>PWR {stats.power}</span>
            <span>DEF {stats.defense}</span>
            <span>SPD {stats.speed}</span>
            <span class="wallet-trophy-rarity">{stats.rarity}</span>
          </div>
        ) : null}
        {edition.legacy_stack ? (
          <div class="wallet-trophy-gallery-tag">Legacy stack</div>
        ) : edition.acquired_via ? (
          <div class="wallet-trophy-gallery-tag">via {edition.acquired_via}</div>
        ) : null}
        {edition.hold_until ? (
          <div class="wallet-trophy-gallery-meta">Hold until {edition.hold_until.slice(0, 10)}</div>
        ) : null}
        {edition.anchor_status && edition.anchor_status !== 'none' ? (
          <div class="wallet-trophy-gallery-tag wallet-trophy-gallery-tag--anchor">
            {edition.anchor_status === 'anchored' ? (
              edition.anchor_explorer_url ? (
                <a
                  href={edition.anchor_explorer_url}
                  class="wallet-trophy-anchor-link"
                  title={edition.anchor_txid || edition.anchor_commitment || 'Chain anchor'}
                >
                  ⛓ Anchored on-chain
                </a>
              ) : (
                '⛓ Anchored'
              )
            ) : edition.anchor_status === 'committed' ? (
              '⛓ Anchor committed'
            ) : (
              '⛓ Anchor pending'
            )}
          </div>
        ) : null}
        <div class="wallet-trophy-gallery-ctas">
          {edition.edition_key ? (
            <a
              href={`/trophy/proof?edition_key=${encodeURIComponent(edition.edition_key)}`}
              class="wallet-trophy-cta"
              target="_blank"
              rel="noopener"
            >
              Proof
            </a>
          ) : null}
          <a
            href={edition.trade_actions?.shop_detail || '/shop?tab=trophies'}
            class="wallet-trophy-cta"
          >
            View
          </a>
          <a
            href={edition.trade_actions?.auction_list || '/shop?tab=auction'}
            class="wallet-trophy-cta"
          >
            List
          </a>
          {canTransfer && (
            <button
              type="button"
              class="wallet-trophy-cta wallet-trophy-cta--btn"
              onClick={() => setShowTransfer((v) => !v)}
            >
              Transfer
            </button>
          )}
          {isBlockTrophy && edition.edition_key && (
            <button
              type="button"
              class="wallet-trophy-cta wallet-trophy-cta--btn wallet-trophy-cta--battle"
              disabled={battling}
              onClick={runBattle}
            >
              {battling ? 'Fighting…' : 'Battle'}
            </button>
          )}
          {edition.edition_key && (
            <button
              type="button"
              class="wallet-trophy-cta wallet-trophy-cta--btn"
              disabled={sharing}
              onClick={runShare}
            >
              {sharing ? 'Sharing…' : 'Share'}
            </button>
          )}
          {edition.edition_key && (
            <button
              type="button"
              class="wallet-trophy-cta wallet-trophy-cta--btn"
              disabled={equipping}
              onClick={runEquip}
            >
              {equipping ? 'Saving…' : 'Feature'}
            </button>
          )}
        </div>
        {battleMsg ? <div class="wallet-trophy-gallery-meta wallet-trophy-battle-msg">{battleMsg}</div> : null}
        {shareMsg ? <div class="wallet-trophy-gallery-meta wallet-trophy-battle-msg">{shareMsg}</div> : null}
        {equipMsg ? <div class="wallet-trophy-gallery-meta wallet-trophy-battle-msg">{equipMsg}</div> : null}
        {showTransfer && (
          <div class="wallet-trophy-transfer-modal">
            <label class="wallet-trophy-transfer-label">
              Recipient profile ID
              <input
                type="text"
                class="wallet-trophy-transfer-input"
                value={recipient}
                onInput={(e) => setRecipient((e.target as HTMLInputElement).value)}
                placeholder="user_id"
              />
            </label>
            {transferError && <div class="wallet-trophies-error" role="alert">{transferError}</div>}
            <button
              type="button"
              class="wallet-discord-btn wallet-discord-btn-primary"
              disabled={transferring}
              onClick={submitTransfer}
            >
              {transferring ? 'Sending…' : 'Send edition'}
            </button>
          </div>
        )}
      </div>
    </article>
  );
}
