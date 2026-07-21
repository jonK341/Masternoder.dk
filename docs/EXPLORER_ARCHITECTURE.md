# MN2 Explorer — Architecture

How the Crypto Hub (`/explorer/`), Flask APIs, eiquidus, and the MN2 daemon fit together.

## System diagram (P6 #215)

```mermaid
flowchart TB
  subgraph Browser
    Hub["/explorer/ Crypto Hub"]
    Detail["/explorer/tx|address|block"]
  end

  subgraph Flask
    Overview["GET /api/mn2/network-overview"]
    Search["GET /api/mn2/explorer/search"]
    Data["mn2_explorer_data.py"]
    Chainz["mn2_chainz.network_overview"]
  end

  subgraph DataSources
    RPC["masternoder2d RPC :9332"]
    Eqi["eiquidus /ext/*"]
    ChainzAPI["Chainz public API"]
  end

  Hub --> Overview
  Hub --> Search
  Detail --> Data
  Overview --> Chainz
  Chainz --> RPC
  Chainz --> Eqi
  Chainz --> ChainzAPI
  Data --> Eqi
  Data --> RPC
  Search --> Data
```

**Priority chain for tiles:** local eiquidus (when `explorer_use_local_stats`) → daemon RPC → Chainz fallback. Each field records its origin in `source`.

**URL shapes:** in-page hub routes (`/explorer/address/…`) vs full block explorer (`explorer_base_url` from config).

---

## Search sequence (P6 #216)

```mermaid
sequenceDiagram
  participant U as User
  participant H as Crypto Hub
  participant API as /api/mn2/explorer/search
  participant C as classify_search
  participant P as Detail page

  U->>H: Submit search (tx / address / height)
  H->>API: GET ?q=
  API->>C: classify query
  C-->>API: type + path
  API-->>H: { path: /explorer/tx/… }
  H->>P: window.location = path
  Note over H,P: On API failure, client falls back to regex routes
```

Classifier rules (`mn2_explorer_data.classify_search`):

| Input | Type | Route |
|-------|------|-------|
| 64-char hex | tx | `/explorer/tx/<txid>` |
| MN/J address | address | `/explorer/address/<addr>` |
| Integer | block height | `/explorer/block/<height>` |
| 64-char hex (block hash) | block | `/explorer/block/<hash>` |

Deep links from profile/shop: `/explorer/?tab=explorer&q=<address>` prefills search.

---

## Related docs

- [MN2_EXPLORER_PLAN.md](MN2_EXPLORER_PLAN.md) — phase plan
- [EXPLORER_OPS_P4.md](EXPLORER_OPS_P4.md) — deploy & ops
- [EXPLORER_RUNBOOKS.md](EXPLORER_RUNBOOKS.md) — incident runbooks
- [EXPLORER_FAQ.md](EXPLORER_FAQ.md) — user-facing FAQ
- [EXPLORER_CONTRIBUTING.md](EXPLORER_CONTRIBUTING.md) — adding tiles
