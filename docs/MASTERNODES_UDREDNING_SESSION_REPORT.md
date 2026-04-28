# Masternodes udredning, session-rapport og prioriteringer

**Genereret:** 2026-04-19  
**Senest opdateret:** 2026-04-20 — `database_health` bruger nu kun tabeller fra `src/db/models.py`; deploy `health_routes.py` + kør `scripts/smoke_db_health_flows.sh` på serveren.  
**Planreference:** session history / udredning (planfil ikke ændret).  
**Primær prod-URL i repo:** `https://masternoder.dk` — afstem **masternodes.dk** vs **masternoder.dk** i DNS/panel hvis begge nævnes.

---

## 0. Seneste check (genprobe)

| Check | Resultat | Noter |
|------|----------|--------|
| **DNS `masternoder.dk`** | **OK** | `A` → `140.82.39.124` (PowerShell `Resolve-DnsName`) |
| **DNS `masternodes.dk`** | **Fejl** | *Navnet på fjernenheden kunne ikke fortolkes* — intet A/AAAA fra denne maskine |
| **`GET https://masternoder.dk/api/health`** | **200** | Svar ~77 bytes |
| **`GET https://masternoder.dk/api/health/system`** | **Timeout** | 25s — ingen respons i tid |
| **`GET https://masternoder.dk/api/health/database`** | **503** | HTTP 503 |
| **`https://masternodes.dk/`** | **DNS-fejl** | Samme som DNS-check |
| **Surface C:** | **~194,8 GB fri** / ~475,7 GB total | `Win32_LogicalDisk` |

**Konklusion:** Basis-health er **grøn**; **`/api/health/system`** kan stadig timeout (MN2 m.m.). **`/api/health/database` 503:** deploy nyeste `backend/routes/health_routes.py` (tabeller matcher nu `models.py`) og genstart uwsgi; derefter `curl` igen eller `bash scripts/smoke_db_health_flows.sh` på serveren.

---

## 1. Aim (north star)

**Hvad “working” betyder:** En bruger kan følge en **direkte** synlig sti **UI → HTTPS API → DB (læs/skriv) → samme tilstand synlig i UI** på en **kendt prod-URL**, med **latens** der føles “instant” for lette GETs og acceptabel for tunge flows — uden 5xx på kernepaths.

**Definition of done (denne runde):** `GET /api/health` og `GET /api/health/system` returnerer **200** med `overall: healthy` (eller dokumenteret, accepteret degradation med årsag), og et **synligt UI-flow** (fx profil/shop/galleri) bekræfter persistens mod DB.

---

## 2. Udredning (checkliste A–H)

| Område | Tjek | Forventet | Resultat | Noter / evidens |
|--------|------|-----------|----------|-----------------|
| **A** | Panel: 60 GB disk, 2 vCPU | Synligt efter upgrade | Ikke verificeret | Kræver leverandørpanel. |
| **A** | VM root-disk vs. 60 GB | `df -h` stemmer | Ikke kørt | Kræver SSH. |
| **A** | RAM | Rimelig ift. tjenester | Ikke målt | `uwsgi_common.ini`: 4 processer × 2 threads — verificér RAM på server. |
| **B** | Fri plads | Ingen partition 100% | Ikke målt | Kræver SSH (`df -h`, `df -i`). |
| **B** | Største forbrugere | Kortlagt før sletning | Ikke målt | Logs, DB, Docker, cache — præcision før delete. |
| **C** | 2 CPU synlige | `nproc` / `lscpu` | Ikke målt | SSH. |
| **C** | Load | Ikke konstant 100% | Ikke målt | `uptime` / `top`. |
| **D** | DNS `masternodes.dk` | Resolverer | **Afvigelse** | Probe: **ingen DNS** (host ukendt). Tjek om domænet findes eller er stavefejl. |
| **D** | DNS `masternoder.dk` | Resolverer | **OK** | `A` → `140.82.39.124`. |
| **D** | HTTPS | Gyldigt cert | **OK** | `GET /api/health` over HTTPS returnerer 200. |
| **E** | App sund | `GET /api/health` 200 | **OK** | **200** (genprobe). |
| **E** | App “system” health | `GET /api/health/system` 200 | **Afvigelse** | **Timeout** (25s) — endpoint tungt eller hænger. |
| **E** | DB fra app | `GET /api/health/database` | **Afvigelse** | **503** — DB-check fejler eller app returnerer 503. |
| **F** | Logrotation | Konfigureret | Ikke verificeret | `uwsgi_common.ini`: `logto`, `log-maxsize`, `log-backupcount`. |
| **F** | Backup | Strategi + test | Ikke verificeret | Dokumentér uden for repo. |
| **G** | Firewall / SSH | Minimalt eksponeret | Ikke verificeret | Panel + server. |
| **G** | Deploy-hemmeligheder | Ikke i git | Forbedret i repo | SSH deploy: `DEPLOY_PASS` påkrævet; se `deploy_ssh_env.py`. |
| **H** | UI→URL→DB→UI GO/NO-GO | Samlet GO | **DELVIS NO-GO** | Basis-API svarer; DB/“system”-health ikke grøn — fuld E2E afventer DB + evt. `/system`-fix. |

**Anbefalet rækkefølge:** A → B → D → E → H (hurtigt GO/NO-GO), derefter F → G for fin orden.

---

## 3. Service inventory + service check (tabel E)

Forventet stack (repo: `/var/www/html` på Linux-VPS):

| Service | Check-metode | Forventet | Resultat | Noter |
|---------|--------------|-----------|----------|--------|
| **nginx** | `systemctl is-active nginx` | active | Ukendt | TLS → upstream 127.0.0.1:5000/5001. |
| **uwsgi (hoved)** | `systemctl is-active uwsgi-vidgenerator` | active | Ukendt | `uwsgi.ini` → `127.0.0.1:5000`. |
| **uwsgi (5001)** | `systemctl is-active uwsgi-vidgenerator-5001` | active | Ukendt | `uwsgi_5001.ini` → `127.0.0.1:5001`. |
| **python-proxy** | `systemctl is-active python-proxy` | active | Ukendt | Nævnt i `deploy.py` restart-liste. |
| **Flask** | `GET /api/health` (ekstern) | 200 | **200** | Genprobe OK. |
| **System health** | `GET /api/health/system` | 200, overall healthy | **Timeout** | Komponenter i kode: database, unified_points, mn2_rpc, m.fl. — undersøg på server. |
| **DB health** | `GET /api/health/database` | 200 | **503** | Ret DB-forbindelse eller app-fejl. |
| **MN2 daemon** (valgfri) | Health `mn2_rpc` | healthy | Ukendt | `MN2_RPC_*` + `masternoder2d`; se `docs/MN2_OPS.md`. |
| **Docker** | `docker ps` | Kun hvis brugt | Typisk N/A | Ikke kerne i dette repo-snit. |

**systemd-referencer i repo:** `systemd/uwsgi-vidgenerator.service`, `systemd/uwsgi-vidgenerator-5001.service` (EnvironmentFile `-/var/www/html/.env`).

---

## 4. Hosting alignment

| Sted | Rolle |
|------|--------|
| **Lokalt (Surface)** | Udvikling, tests, `deploy.py` med `DEPLOY_PASS` i miljø. |
| **VPS** | Prod: nginx, uwsgi, `.env`, DB-sti via `DATABASE_URL`, chdir `/var/www/html`. |
| **60 GB / 2 vCPU** | Bekræft i panel + `df`/`nproc` på VM efter upgrade. |

VPS-opgradering **løser ikke** automatisk lav plads på **Surface C:** — separate puljer.

---

## 5. Disk status (Surface)

Planen nævnte **~9,98 MB** fri på Surface som kritisk — det skal **bekræftes lokalt** (Indstillinger → Lagring eller `Get-CimInstance Win32_LogicalDisk`).

Seneste måling (genprobe): **C:** ca. **194,8 GB fri** af ~**475,7 GB** total. Planens **~9,98 MB** kritisk-niveau gælder **ikke** for denne måling — **bekræft** på din maskine hvis du er i tvivl.

**Read-only triage (før sletning):** Inventar af største mapper under brugerprofil eller projekter; ingen destruktive deletes uden backup.

---

## 6. Priority list (P0 → P2) + single WIP

| Prioritet | Item |
|-----------|------|
| **P0** | Afklar **masternodes.dk** vs **masternoder.dk** (DNS/panel). |
| **P0** | **SSH:** `systemctl status`, `df -h`, `curl localhost:5000/api/health` — luk A–E med evidens. |
| **P0** | **Health:** `/api/health` er OK; ret **`/api/health/system` (timeout)** og **`/api/health/database` (503)** — DB, rettigheder, MN2, worker/harakiri, nginx timeout. |
| **P0** | **Direkte sti** UI→API→DB→UI når health er OK. |
| **P1** | Logrotation, backup på VM (60 GB er begrænset). |
| **P1** | Hardening: flakes, monitoring. |
| **P2** | Gallery trim-regler efter filliste på server. |

**Single WIP:** Indtil **`/api/health/system`** og **`/api/health/database`** er **stabile 200**, forbliver **H** delvis NO-GO; prioriter **serverdiagnose** (logs, DB, timeouts).

---

## 7. Session digest (session-historian)

Korte temaer fra Cursor agent-historik (ingen rå hemmeligheder):

- **Deploy / SSH / secrets:** Prod DB-sti, rettigheder, fjernelse af hardcoded deploy-password, `DEPLOY_PASS` + `deploy_ssh_env` — [Deploy and DB secrets](f0b9e340-1969-4728-9c6b-8b5a7f9da1f4).
- **Unified points / deploy:** Hvilke filer der skal med `deploy.py` — [Unified points + deploy](edc12740-24cd-4d92-8156-a4d8c82c3b2c).
- **Separat VPS (explorer/subdomæne):** Mongo, nginx, 502, SSL — [Explorer VPS / Mongo / SSL](fd84f397-c743-48ae-9ded-363871b32550).
- **Gallery / API:** Konsolidering mod `/api` — [API `/api` + gallery routes](ccf6a5db-fea5-431e-be4b-44909bf4605a).

**Begrænsning:** Kun Cursor-transcripts i projektmappen; **~96** jsonl-filer observeret (overslagsantal).

---

## 8. Graded tests (UI→DB→UI)

| Test | Grade | Evidence | Tag |
|------|-------|----------|-----|
| `GET /api/health` (prod) | **B / pass** | **200**, ~77 B body | masternoder |
| `GET /api/health/system` (prod) | **D / fail** | **Timeout** 25s | masternoder |
| `GET /api/health/database` (prod) | **D / fail** | **503** | masternoder |
| Health routes i kodebase | A / pass | `backend/routes/health_routes.py` | local |
| E2E browser UI→DB→UI | Ikke kørt | Afventer DB + system health | — |

**Rubrik:** Correctness og latency vægtes højest; **system**- og **database**-endpoints skal fixes før fuld GO.

---

## 9. Gallery policy (valgfri)

- **Cache:** `GALLERY_CACHE_TTL_SEC` (default 30 i `.env.example`) — justér efter load vs. friskhed.
- **Kvalitet:** `GALLERY_QUALITY_MIN_SCORE`, `GALLERY_QUALITY_STRICT_MIN` — strammere = færre “støj”-poster.
- **Admin:** `GALLERY_ADMIN_TOKEN` til bulk-metadata — kun hvis nødvendigt i prod.
- **Trim:** Ingen automatisk sletning uden **inventory** af faktiske upload/output-mapper på server.

---

## 10. Scope (udførelse)

| Emne | Værdi |
|------|--------|
| Tidsvindue historik | ~30 dages signal (mtime på transcripts; præcis dato ikke i JSONL-linjer). |
| URL | Primært `https://masternoder.dk`; bekræft **masternodes.dk** separat. |
| Repo | `Masternoder.dk` |

---

## 11. Næste skridt (kort)

1. Bekræft **Surface** fri plads lokalt.  
2. **SSH** til VPS og kør A–E med kommandoer i tabellerne.  
3. Ret **`/api/health/system` (timeout)** og **`/api/health/database` (503)** — DB-sti/rettigheder, `uwsgi.log` / nginx `proxy_read_timeout`, MN2-kald der blokerer.  
4. Gentag **graded tests** og markér **GO** på H når E2E er grøn.

---

*Denne fil er den samlede “combined output” fra planen; opdater rækker med **Resultat** når du har SSH/panel-evidens.*
