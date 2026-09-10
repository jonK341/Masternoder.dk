#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

def main():
    ssh, auth, _ = connect_deploy_ssh()
    _, stdout, _ = ssh.exec_command("wc -l /var/www/html/backend/services/mn2_explorer_data.py && cat /var/www/html/backend/services/mn2_explorer_data.py", timeout=60)
    data = stdout.read()
    out = ROOT / "backend/services/mn2_explorer_data.py"
    # skip first line (wc output) - actually cat includes everything after wc
    text = data.decode("utf-8", errors="replace")
    # find start of python file
    idx = text.find('"""')
    if idx == -1:
        idx = text.find('import ')
    if idx > 0:
        text = text[idx:]
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out} ({len(text.splitlines())} lines) from server ({auth})")
    ssh.close()

if __name__ == "__main__":
    main()
