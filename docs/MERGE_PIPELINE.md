# Merge pipeline (start to ship) <!-- pragma: allowlist secret -->

End-to-end flow for landing work on **main** and on the **live server** without a stuck merge.

## 1. Branch → PR

1. Branch from latest `main`: `git fetch origin main && git checkout -b cursor/<topic>-4403 origin/main`
2. Push and open a PR targeting `main`.
3. Wait for **Python Package using Conda** CI on the PR (flake8 E9/F63/F7 + `tests/ci_unit_tests.txt` subset).

## 2. Preflight before merge

```bash
bash scripts/merge_preflight.sh
bash scripts/merge_preflight.sh --server   # also checks /var/www/html for MERGE_HEAD
```

| Check | Healthy |
|--------|---------|
| Local `MERGE_HEAD` | absent |
| PR `mergeStateStatus` | `CLEAN` |
| PR `mergeable` | `MERGEABLE` |
| Server `.git/MERGE_HEAD` | absent |

If a PR is **CONFLICTING**, rebase or merge `origin/main` locally, resolve, push the branch (do not merge on GitHub until green).

## 3. Merge order (Nov 2026 backlog)

| PR | Content | Notes |
|----|---------|--------|
| #140 / #141 | Agent roster + root URLs | **Merged** |
| #143 | `container_deploy.sh` venv pip | **Merged** |
| #137 | `GET /api/mn2/masternode/hosting/config` alias | Was open; folded into integration branch |
| #138 | `scripts/mn2_fleet_audit.py` + fleet ops | Was open; folded into integration branch |
| #139 | Remove agent-tech stubs / duplicate pages | Was **CONFLICTING**; rebased onto main |

Integration branch `cursor/merge-pipeline-complete-4403` combines **#139 + #137 + #138** with conflicts resolved.

## 4. After merge to `main`

On server (`/var/www/html`):

```bash
bash scripts/container_deploy.sh
```

That runs: `git pull --ff-only` → venv pip (slim deps) → DB migrations → uwsgi/nginx restart.

If pull fails on **untracked files that block merge**, remove only duplicates of tracked paths, then pull again.

Optional full stack (torch, playwright, etc.):

```bash
INSTALL_REQUIREMENTS_YES=1 INSTALL_REQUIREMENTS_FILE=requirements.txt \
  python scripts/install_requirements_on_server.py -y
```

Keep **Flask/Werkzeug** pins aligned between the slim server deps file and `requirements.txt` when the server uses Python 3.12+.

## 5. Verify

```bash
BASE_URL=https://example.com python scripts/test_url_timing.py
bash scripts/merge_preflight.sh --server
curl -s http://127.0.0.1:5000/api/health
```

## 6. Close superseded PRs

After the integration PR merges, **close** #137–#139 with a link to the merge commit to avoid double-merge attempts.
