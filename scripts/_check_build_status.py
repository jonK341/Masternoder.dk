#!/usr/bin/env python3
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh

ssh = connect_deploy_ssh()[0]
cmd = r"""
echo "== g++ workers =="
pgrep -a g++ | wc -l
pgrep -a 'cc1plus' | head -3
echo "== stale depends build (03:14) =="
ps -p 679643,679929 -o pid,etime,cmd 2>/dev/null || echo gone
echo "== current fast build =="
ps -p 755559,764975,764977 -o pid,etime,cmd 2>/dev/null || echo gone
if [ -f /var/mn2-build/MasterNoder2/src/masternoder2d ]; then
  ls -la /var/mn2-build/MasterNoder2/src/masternoder2d
  /var/mn2-build/MasterNoder2/src/masternoder2-cli --version 2>/dev/null | head -1
fi
if [ -f /var/mn2-build/dist/masternoder2d.tar.gz ]; then
  ls -la /var/mn2-build/dist/masternoder2d.tar.gz
fi
"""
_, o, e = ssh.exec_command(cmd, timeout=45)
print(o.read().decode())
ssh.close()
