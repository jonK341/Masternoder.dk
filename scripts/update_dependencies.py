#!/usr/bin/env python3
"""
Update Dependencies
Ensures all required dependencies are in requirements.txt
"""
import os
import re

REQUIREMENTS_FILE = "requirements.txt"

# Required dependencies for production
REQUIRED_DEPS = {
    # Core
    'Flask==2.2.5',
    'click>=8.0.0',
    'Flask-SQLAlchemy==3.0.5',
    'SQLAlchemy==1.4.23',
    'requests==2.31.0',
    'python-dotenv>=1.0.1',
    'Werkzeug==2.2.3',
    
    # Production
    'gunicorn>=21.2.0',
    'uwsgi>=2.0.23',
    'paramiko>=3.3.0',
    'scp>=0.14.0',
    
    # Video Processing
    'moviepy>=1.0.3',
    'ffmpeg-python>=0.2.0',
    'Pillow>=10.0.0',
    'opencv-python>=4.8.0',
    'numpy>=1.24.0',
    
    # Web Scraping
    'beautifulsoup4>=4.12.0',
    'duckduckgo-search>=5.3.1',
    'lxml>=4.9.0',
    
    # AI
    'openai>=1.52.0',
    'tenacity>=8.2.3',
    'transformers>=4.30.0',
    'torch>=2.0.0',
    
    # TTS
    'elevenlabs>=0.2.26',
    
    # Google OAuth
    'google-auth>=2.20.0',
    'google-auth-oauthlib>=1.0.0',
    'google-auth-httplib2>=0.1.1',
    
    # Monitoring
    'psutil>=5.9.0',
    
    # Testing
    'pytest>=7.4.0',
    'pytest-cov>=4.1.0',
    'pytest-flask>=1.3.0',
    'pytest-mock>=3.12.0',
    
    # Real-Time
    'flask-socketio>=5.3.6',
    'python-socketio>=5.10.0',
    'eventlet>=0.33.3',
    
    # Caching
    'redis>=5.0.1',
    'flask-caching>=2.1.0',
    'hiredis>=2.2.3',
    
    # Background Tasks
    'celery>=5.3.4',
    
    # Analytics
    'prometheus-client>=0.19.0',
    
    # ML/AI
    'scikit-learn>=1.3.2',
    'pandas>=2.1.4',
    'scipy>=1.11.4',
    
    # API
    'flask-restx>=1.3.0',
    'flask-cors>=4.0.0',
    'flask-compress>=1.14',
    
    # Security
    'flask-limiter>=3.5.0',
    'flask-talisman>=1.1.0',
    'cryptography>=41.0.7',
    
    # Database
    'alembic>=1.13.1',
    'sqlalchemy-utils>=0.41.1',
    
    # Logging
    'sentry-sdk[flask]>=1.40.0',
    'structlog>=23.2.0',
    
    # Debugging
    'ipython>=8.18.0',
    'ipdb>=0.13.13',
    'pdb++>=0.10.3',
    'memory-profiler>=0.61.0',
    'line-profiler>=4.1.1',
    'py-spy>=0.3.14',
    'pyinstrument>=5.4.0',
}


def parse_requirements(content: str) -> set:
    """Parse requirements.txt and return set of package names"""
    packages = set()
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            # Extract package name (before == or >=)
            match = re.match(r'^([a-zA-Z0-9_-]+[a-zA-Z0-9_.-]*)', line)
            if match:
                packages.add(match.group(1).lower())
    return packages


def get_package_name(dep: str) -> str:
    """Extract package name from dependency string"""
    match = re.match(r'^([a-zA-Z0-9_-]+[a-zA-Z0-9_.-]*)', dep)
    if match:
        return match.group(1).lower()
    return dep.lower()


def update_requirements():
    """Update requirements.txt with all required dependencies"""
    print("="*80)
    print("UPDATING DEPENDENCIES")
    print("="*80)
    print()
    
    # Read existing requirements
    if os.path.exists(REQUIREMENTS_FILE):
        with open(REQUIREMENTS_FILE, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        existing_packages = parse_requirements(existing_content)
    else:
        existing_content = ""
        existing_packages = set()
    
    # Find missing dependencies
    missing_deps = []
    for dep in REQUIRED_DEPS:
        pkg_name = get_package_name(dep)
        if pkg_name not in existing_packages:
            missing_deps.append(dep)
    
    if not missing_deps:
        print("  [OK] All required dependencies are present")
        print()
        return True
    
    # Add missing dependencies
    print(f"  [INFO] Adding {len(missing_deps)} missing dependencies...")
    print()
    
    # Append to requirements file
    with open(REQUIREMENTS_FILE, 'a', encoding='utf-8') as f:
        f.write("\n# ============================================\n")
        f.write("# ADDITIONAL PRODUCTION DEPENDENCIES\n")
        f.write("# ============================================\n")
        for dep in missing_deps:
            f.write(f"{dep}\n")
            print(f"  [ADDED] {dep}")
    
    print()
    print("="*80)
    print("DEPENDENCIES UPDATED")
    print("="*80)
    print(f"Added: {len(missing_deps)} dependencies")
    print()
    
    return True


if __name__ == "__main__":
    update_requirements()
