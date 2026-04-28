#!/usr/bin/env python3
"""
Start Flask Application
Simple script to start the Flask application
"""
import sys
import os
import subprocess
import time

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

def main():
    """Start Flask application"""
    print("=" * 70)
    print("STARTING FLASK APPLICATION")
    print("=" * 70)
    print()
    
    # Check if run.py exists
    run_file = os.path.join(BASE_DIR, 'run.py')
    if not os.path.exists(run_file):
        print(f"[ERROR] run.py not found at {run_file}")
        return 1
    
    # Create logs directory
    logs_dir = os.path.join(BASE_DIR, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, 'flask_app.log')
    
    print(f"[INFO] Starting Flask application from: {run_file}")
    print(f"[INFO] Logs will be written to: {log_file}")
    print()
    
    try:
        # Start Flask application
        if os.name == 'nt':  # Windows
            # Use CREATE_NEW_CONSOLE flag to run in separate window
            proc = subprocess.Popen(
                [sys.executable, run_file],
                cwd=BASE_DIR,
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, 'CREATE_NEW_CONSOLE') else 0
            )
        else:  # Unix/Linux
            proc = subprocess.Popen(
                [sys.executable, run_file],
                cwd=BASE_DIR,
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        
        print(f"[OK] Flask application started successfully!")
        print(f"[INFO] Process ID (PID): {proc.pid}")
        print(f"[INFO] Application should be running at: http://localhost:5000")
        print(f"[INFO] Check logs at: {log_file}")
        print()
        print("[INFO] Application is running in background.")
        print("[INFO] To stop, find the process and kill it, or close the console window.")
        print()
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Failed to start Flask application: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
