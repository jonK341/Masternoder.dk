#!/usr/bin/env python3
"""Setup local Python environment for IDE"""
import os
import sys
import subprocess
import venv

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("SETTING UP LOCAL PYTHON ENVIRONMENT")
print("=" * 80)
print()

# Check if virtual environment exists
venv_path = os.path.join(os.getcwd(), '.venv')
if not os.path.exists(venv_path):
    print("[INFO] Creating virtual environment...")
    venv.create(venv_path, with_pip=True)
    print("[OK] Virtual environment created")
else:
    print("[OK] Virtual environment already exists")

# Determine pip path
if sys.platform == 'win32':
    pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
    python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
else:
    pip_path = os.path.join(venv_path, 'bin', 'pip')
    python_path = os.path.join(venv_path, 'bin', 'python')

# Install Flask and dependencies
print()
print("[INFO] Installing Flask and dependencies...")
try:
    # Install Flask first
    print("  Installing Flask...")
    subprocess.run([python_path, '-m', 'pip', 'install', '--upgrade', 'pip'], check=False, capture_output=True)
    subprocess.run([pip_path, 'install', 'Flask'], check=False, capture_output=True)
    
    # Install other key dependencies
    key_packages = ['Werkzeug', 'click', 'Flask-SQLAlchemy']
    for package in key_packages:
        print(f"  Installing {package}...")
        subprocess.run([pip_path, 'install', package], check=False, capture_output=True)
    
    print("[OK] Dependencies installed")
except Exception as e:
    print(f"[WARN] Error installing dependencies: {e}")

# Create/update .vscode/settings.json
print()
print("[INFO] Configuring VS Code settings...")
vscode_dir = os.path.join(os.getcwd(), '.vscode')
if not os.path.exists(vscode_dir):
    os.makedirs(vscode_dir)

settings_file = os.path.join(vscode_dir, 'settings.json')
python_path_normalized = python_path.replace('\\', '/')
settings = {
    "python.defaultInterpreterPath": python_path_normalized,
    "python.analysis.extraPaths": [
        "${workspaceFolder}",
        "${workspaceFolder}/src",
        "${workspaceFolder}/backend"
    ],
    "python.analysis.autoImportCompletions": True,
    "python.linting.enabled": True,
    "python.linting.pylintEnabled": False,
    "python.linting.flake8Enabled": False
}

import json
with open(settings_file, 'w', encoding='utf-8') as f:
    json.dump(settings, f, indent=2)

print(f"[OK] VS Code settings configured: {settings_file}")
print(f"   Python interpreter: {python_path_normalized}")

# Create .python-version if using pyenv
print()
print("[INFO] Creating .python-version file...")
python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
with open('.python-version', 'w', encoding='utf-8') as f:
    f.write(python_version)
print(f"[OK] Created .python-version: {python_version}")

print()
print("=" * 80)
print("[OK] LOCAL ENVIRONMENT SETUP COMPLETE")
print("=" * 80)
print()
print("Next steps:")
print(f"1. Restart your IDE/editor")
print(f"2. Select the Python interpreter: {python_path_normalized}")
print("3. The Flask import should now be resolved")
print()
