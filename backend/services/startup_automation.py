"""
Startup Automation
Automatically starts calculator automation when the application starts
"""
import threading
import time

def start_automation_on_startup(app=None):
    """Start calculator automation when application starts"""
    def delayed_start():
        # Wait a bit for application to fully initialize
        time.sleep(15)
        
        try:
            # Import within app context if available
            if app:
                with app.app_context():
                    from backend.services.calculator_automation import calculator_automation
                    
                    print("[StartupAutomation] Starting calculator automation...", flush=True)
                    result = calculator_automation.start()
                    
                    if result.get('success'):
                        print("[StartupAutomation] [OK] Calculator automation started successfully", flush=True)
                        print(f"[StartupAutomation] Interval: {result.get('interval_seconds', 300)} seconds", flush=True)
                    else:
                        print(f"[StartupAutomation] [WARN] Failed to start: {result.get('error', 'Unknown')}", flush=True)
            else:
                from backend.services.calculator_automation import calculator_automation
                
                print("[StartupAutomation] Starting calculator automation...", flush=True)
                result = calculator_automation.start()
                
                if result.get('success'):
                    print("[StartupAutomation] [OK] Calculator automation started successfully", flush=True)
                    print(f"[StartupAutomation] Interval: {result.get('interval_seconds', 300)} seconds", flush=True)
                else:
                    print(f"[StartupAutomation] [WARN] Failed to start: {result.get('error', 'Unknown')}", flush=True)
        except Exception as e:
            print(f"[StartupAutomation] [ERROR] Error starting automation: {e}", flush=True)
            import traceback
            traceback.print_exc()
    
    # Start in background thread
    thread = threading.Thread(target=delayed_start, daemon=True)
    thread.start()

