# Camgirls Phase 4 — explorer coexistence (nginx)

**Decision (2026-06-17):** Platform MVP stays at `https://masternoder.dk/camgirls/`. Explorer stays at `https://camgirls.masternoder.dk/` (eiquidus).

Use this guide only if the product moves to **`camgirls.masternoder.dk/app/`** later.

---

## Target layout

| URL | Backend | Purpose |
|-----|---------|---------|
| `camgirls.masternoder.dk/` | eiquidus `:3000` | Block explorer (unchanged) |
| `camgirls.masternoder.dk/app/` | Flask `:5000/camgirls/` | Performer catalog + MN2 |

---

## nginx snippet (camgirls vhost)

Add **above** the existing explorer `location /` block:

```nginx
# Camgirls platform UI + API proxy (Phase 4)
location /app/ {
    proxy_pass http://127.0.0.1:5000/camgirls/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 120s;
}

location /app/api/ {
    proxy_pass http://127.0.0.1:5000/api/camgirls/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 120s;
}
```

**Note:** Flask already serves API at `/api/camgirls/*` on the main site. If you only proxy `/app/` for HTML, keep API calls on `masternoder.dk` or add a dedicated `/app/api/` block as above.

---

## Apply on server

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -sI https://camgirls.masternoder.dk/app/
```

---

## Frontend base path (if moving)

Update `camgirls.js` fetch paths from `/api/camgirls/` to `/app/api/` **or** set a `<base href="/app/">` and relative API prefix. Current MVP does **not** require this.

---

## References

- [CAMGIRLS_PHASE0.md](CAMGIRLS_PHASE0.md) — URL plan
- [MN2_TODO.md](MN2_TODO.md) — Phase 4 checkbox
