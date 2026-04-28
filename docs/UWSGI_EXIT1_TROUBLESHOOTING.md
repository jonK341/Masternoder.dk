# uWSGI exit 1 / curl timeout mod 127.0.0.1:5000

Symptomer: `systemctl` viser **Main process exited, status=1** i loop; `curl` til `/api/health` **forbinder** men får **0 bytes** eller timeout.

## 1. Hurtig diagnose (på serveren)

```bash
cd /var/www/html && sudo bash scripts/uwsgi_diagnose_server.sh
```

Tjek især: **CRLF i `uwsgi.ini` / `uwsgi_common.ini`**, **Python import af `wsgi` som `www-data`**, og **sidste linjer i `uwsgi.log`**.

## 2. CRLF (Windows line endings)

Hvis `grep` finder `\r` i ini-filer:

```bash
sed -i 's/\r$//' /var/www/html/uwsgi.ini /var/www/html/uwsgi_common.ini /var/www/html/uwsgi_5001.ini
sudo systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
```

## 3. Forgrundskørsel (se den rigtige fejl)

```bash
sudo systemctl stop uwsgi-vidgenerator
sudo -u www-data bash -c 'cd /var/www/html && /usr/bin/uwsgi --ini /var/www/html/uwsgi.ini'
```

Stop med Ctrl+C når fejlen er læst.

## 4. Typiske årsager

| Årsag | Tegn | Handling |
|--------|------|----------|
| **plugin `python3` mangler** | uwsgi klager over plugin | `apt install uwsgi-plugin-python3` (eller distro-ækvivalent) |
| **Bind conflict** | Address already in use | `ss -tlnp \| grep 5000`; stop duplikat/ gammel master |
| **OOM** | journal: killed / OOM | Sænk `processes`/`threads` i `uwsgi_common.ini` eller tilføj swap |
| **Import fejl** | Traceback i forgrund | `pip install -r requirements.txt` i den Python uwsgi bruger |
| **pidfile / log** | Permission denied | `chown www-data` på `/var/www/html`, logfil |

## 5. Efter fix

```bash
sudo systemctl start uwsgi-vidgenerator
curl -sS -m 10 http://127.0.0.1:5000/api/health
curl -sS -m 25 http://127.0.0.1:5000/api/health/database
```

Derefter: `bash scripts/verify_server_env_db.sh`.
