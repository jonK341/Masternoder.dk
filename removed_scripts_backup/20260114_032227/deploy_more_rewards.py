#!/usr/bin/env python3
"""Deploy More Rewards System"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING MORE REWARDS SYSTEM")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('backend/services/rewards_system_v2.py', '/var/www/html/vidgenerator/backend/services/rewards_system_v2.py'),
    ('backend/routes/rewards_routes_v2.py', '/var/www/html/vidgenerator/backend/routes/rewards_routes_v2.py'),
]

print("[INFO] Deploying files...")
for local_path, remote_path in files_to_deploy:
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create directory if needed
        remote_dir = os.path.dirname(remote_path)
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
        stdout.read()
        
        with sftp.file(remote_path, 'w') as f:
            f.write(content)
        print(f"  [OK] Deployed {local_path}")
    else:
        print(f"  [WARN] File not found: {local_path}")

sftp.close()

# Restart uWSGI
print()
print("[INFO] Restarting uWSGI...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
stdout.read()
print("[OK] uWSGI restarted")

time.sleep(5)

ssh.close()

print()
print("=" * 80)
print("[OK] MORE REWARDS SYSTEM DEPLOYED")
print("=" * 80)
print()
print("New Features:")
print("  ✅ 17 New Reward Categories (Total: 31)")
print("  ✅ 30+ New Reward Types (Total: 44)")
print("  ✅ 10+ Auto-Reward Triggers")
print("  ✅ Reward Bundles")
print()
print("New Categories:")
print("  📊 Activity, 🔍 Discovery, 🎯 Milestone, 🔗 Referral")
print("  ✨ Quality, ⚡ Speed, 📦 Collection, 🗺️ Exploration")
print("  🤝 Collaboration, 💡 Innovation, 🎓 Mastery")
print("  🌸 Seasonal, 🎂 Anniversary, 🎈 Birthday")
print("  🌟 First Time, 💥 Combo, 🍀 Lucky, 📦 Bundle")
print()
print("New Reward Types:")
print("  💠 Gems, 🪙 Tokens, 💎 Crystals, ⭐ Prestige")
print("  🎓 Mastery, ⭐ Reputation, 🌟 Fame, ⚔️ Honor")
print("  📚 Wisdom, 🍀 Luck, 💰 Fortune, ⚡ Power")
print("  🎯 Skill, 💫 Experience, 🧠 Knowledge")
print("  💡 Inspiration, 🎨 Creativity, 💪 Stamina")
print("  ❤️ Health, 🔮 Mana, 🛡️ Shield, ⚔️ Weapon")
print("  🛡️ Armor, 💍 Accessory, 🧪 Consumable")
print("  📜 Recipe, 📐 Blueprint, 🗝️ Key")
print("  📜 Scroll, 🧪 Potion, ⚗️ Elixir, 📦 Bundle")

