# Database-health “120 % grøn” — checkliste, rettigheder og tunge API-test

## Todo 1 — `DATABASE_URL` + systemd (start her)

1. **På serveren** (SSH): `cd /var/www/html && sudo bash scripts/verify_server_env_db.sh`  
   - Bekræfter at `/var/www/html/.env` findes og at `DATABASE_URL` er sat (masket i output).  
   - Viser om `uwsgi-vidgenerator` / `uwsgi-vidgenerator-5001` har `EnvironmentFile` mod `.env` (som i repo: `systemd/uwsgi-vidgenerator.service`).  
   - Løser SQLite-sti under `WEB_ROOT` og tjekker mappe/fil.  
   - Kalder `http://127.0.0.1:5000/api/health/database` og viser HTTP-kode.

2. **Efter ændring af `.env`** (herunder `DATABASE_URL`):  
   `sudo systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001`  
   (og `python-proxy` hvis I bruger den.)

3. **Lokalt** (deploy): sørg for at **prod-`.env`** på serveren matcher den tænkte DB-sti — `deploy.py` kan uploade `.env`; vær varsom så du ikke overskriver prod med en dev-fil.

---

**Mål:** `GET /api/health/database` returnerer **200**, `success: true`, `status: healthy`, `database.connected: true`, og **ingen** kritiske tabeller i `missing_tables` (se `backend/routes/health_routes.py` → `tables_to_check`).

**Bemærk:** `GET /api/health/system` er et **andet** endpoint (MN2, unified_points, caching …). Grøn **database-health** garanterer **ikke** grøn **system-health**.

---

## 0. Forudsætning: uWSGI svarer på :5000

Hvis `curl http://127.0.0.1:5000/api/health` **timeout’er** eller `uwsgi-vidgenerator` **exit 1** i loop: **fix uWSGI først** — se `docs/UWSGI_EXIT1_TROUBLESHOOTING.md` og kør `bash scripts/uwsgi_diagnose_server.sh` på serveren.

**Repo-fix:** `uwsgi_common.ini` / `uwsgi_5001.ini` skal deployes med **LF** (Unix); CRLF kan få uWSGI til at fejle på Linux.

---

## 1. Teknisk: hvad endpointet faktisk gør

1. `SELECT 1` mod SQLAlchemy-sessionen (forbindelse + pool).
2. For hver tabel i listen: `SELECT COUNT(*) FROM <table> LIMIT 1` (eksistens + læsbarhed).

Tabeller der tjekkes: de der findes i `src/db/models.py` (fx `user_accounts`, `user_profiles`, `player_levels`, `shop_purchases`, …) — se `tables_to_check` i `backend/routes/health_routes.py`.

**Smoke (server):** `BASE_URL=http://127.0.0.1:5000 bash scripts/smoke_db_health_flows.sh`

**503** på `/api/health/database` kommer typisk fra **undtagelse i det ydre `try`** (forbindelse fejler, SQLite ulåselig, forkert `DATABASE_URL`, proces uden læserettighed til fil).

---

## 2. Filsystem- og procesrettigheder (OS / deployment)

| Perspektiv | Tjek | Handling |
|------------|------|----------|
| **DATABASE_URL** | Peger på korrekt fil/DSN i prod | `/var/www/html/.env` indlæses af systemd (`EnvironmentFile`); genstart uwsgi efter ændring. |
| **SQLite-fil** | `www-data` kan **læse og skrive** | `chown`/`chgrp` så uwsgi-brugeren ejer eller er i gruppe; `chmod 664` på `.db` ofte; **aldrig** `chmod 777` som standard. |
| **`instance/`** | Katalog eksisterer og er skrivbart | `mkdir -p`, `chown` konsistent med app-bruger. |
| **Lock / “database is locked”** | Ingen langvarige skrivetransaktioner der blokerer | Undgå at køre tunge migrationer samtidig med peak-trafik; WAL-mode kan hjælpe (SQLite). |
| **Disk fuld** | Fri plads på mount for DB | `df -h`; 503 kan følge af fuld disk. |
| **Backup** | Kopier DB med stoppet skriv eller VSS/snapshot | Rettigheder på backup-filer: kun root/backup-bruger. |

---

## 3. Juridisk og “copyrights” / dataansvar (perspektiver)

| Område | Hvad huskes |
|--------|-------------|
| **Persondata (GDPR)** | Brugerprofiler, IP, fingerprints i `user`/onboarding — **formål**, **sletning**, **export** hvor krævet. |
| **Brugerindhold** | Tekst/billeder brugeren skaber — vilkår skal klargøre licens til hosting/visning. |
| **Tredjeparts API’er** | PayPal, LLM, Runway osv. — overhold **deres** vilkår; gem ikke nøgler i DB i klartekst. |
| **Ophavsret** | Genereret/indlæst medie — spor **kilde** og **rettighed** før bulk-lagring i DB eller filsystem. |
| **Handels- og betalingsdata** | Shop/køb — PCI: gem ikke fulde kortdata; brug udbyderens tokens. |
| **Audit / logs** | Health og fejl må ikke logge **hemmeligheder** eller unødig PII (maskér DB-URL i support-logs). |

Dette påvirker **ikke** SQL `SELECT 1`, men påvirker **tillid**, **compliance** og **hvad** I må gemme i de tabeller health tjekker.

**Todo “legal” (hurtig afkrydsning):** Opdatér privacy-/cookie-tekst hvis I gemmer fingerprint; dokumentér databehandler for PayPal; undgå API-nøgler i DB/logs; gennemgå shop-/galleri-metadata for tredjepartsrettigheder.

---

## 4. Top 5 tunge / kritiske API-kald (testrækkefølge)

**Idé:** Start med **opret-bruger** (create), derefter flows der **skriver** til de samme lag som health-tabellerne (shop, points, sync).

| # | Flow | Metode / sti | Hvorfor “tung” / relevant |
|---|------|----------------|-----------------------------|
| **1** | **Create / onboarding** | `POST /api/user/create` | Første skriv til bruger-DB (`ensure_user_account` / `ensure_user_profile`); matcher “create-knap”-oplevelsen. |
| **2** | **Shop-køb** | `POST /api/game/shop/purchase` eller `POST /api/shop-v3/purchase` | Rammer `shop_purchases`, `user_inventory`, `shop_items`. |
| **3** | **Synk / bulk state** | `POST /api/sync/now` eller `POST /api/game/save-all-stats` | Mange JSON→DB-skriv; afslører lock/timeout. |
| **4** | **Points-increment** | `POST /api/points/json/increment` | Direkte pres på points-/ledger-relateret data. |
| **5** | **Betaling (ekstern + DB)** | `POST /api/paypal/create-order` (+ evt. capture/webhook) | Kombinerer ekstern API og metadata; fejl her må ikke korrupte DB. |

**Testprocedure (kort):**

1. Kald `GET /api/health/database` **før** og **efter** hvert trin — stadig 200 og `missing_tables: []`.
2. Brug **samme** `DATABASE_URL** som prod i staging, eller test på prod med **lav risiko**-data.
3. Ved fejl: læs **uwsgi.log**, tjek **SQLite** fejltekst, **rettigheder**, **migrations** (`schema_migrations`).

---

## 5. Migrationer og skema

- Kør relevante scripts (`scripts/shop_purchase_migration.py` m.fl.) så **alle** tabeller i `tables_to_check` findes.
- Tom tabel er OK — `COUNT(*)` skal bare køre.

---

## 6. Når alt er “120 %”

- [ ] `/api/health/database` → **200**, `missing_tables` tom (eller bevidst accepteret liste dokumenteret).
- [ ] Create + shop + sync + points + PayPal-order **testet** uden DB-fejl.
- [ ] Rettigheder og backup verificeret på server.
- [ ] Juridiske noter (GDPR/vilkår) ajour for de data I gemmer.

Opdater `docs/MASTERNODES_UDREDNING_SESSION_REPORT.md` med dato og resultat når I har kørt testene.
