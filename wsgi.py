# WSGI entry point for uWSGI
# This file is used by uWSGI to load the Flask application

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Change to project directory
os.chdir(project_root)

# Import and create Flask app with error handling
# CRITICAL FIX: Monkey-patch print to ignore BlockingIOError BEFORE any imports
import sys
import builtins

# Store original print
_original_print = builtins.print

# Safe print that ignores BlockingIOError
def _safe_print(*args, **kwargs):
    """Print that silently ignores BlockingIOError (errno 11)"""
    try:
        _original_print(*args, **kwargs)
    except (BlockingIOError, OSError) as e:
        errno = getattr(e, 'errno', None)
        if errno == 11:  # Resource temporarily unavailable
            # Silently ignore - this is expected in uWSGI non-blocking mode
            pass
        else:
            # For other errors, try to print (might fail again, but that's OK)
            try:
                _original_print(*args, **kwargs)
            except:
                pass
    except:
        # Ignore all other exceptions from print
        pass

# Replace built-in print with safe version BEFORE any imports
builtins.print = _safe_print

try:
    from src.app import create_app
    # Don't print to stderr during app creation - it can block in uWSGI
    application = create_app()
except (BlockingIOError, OSError) as e:
    # Handle blocking write errors (errno 11) specifically
    errno = getattr(e, 'errno', None)
    if errno == 11:  # Resource temporarily unavailable (EAGAIN/EWOULDBLOCK)
        # This is a non-blocking write error - try to create app again with minimal output
        try:
            # Suppress stdout/stderr temporarily
            import contextlib
            with open(os.devnull, 'w') as devnull:
                with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    from src.app import create_app
                    application = create_app()
        except:
            # If that fails, create minimal app
            from flask import Flask
            application = Flask(__name__)
            @application.route('/')
            def error():
                return "Application initialization blocked by write error (errno 11). Please check logs.", 500
    else:
        # Other OSError - log to file
        import traceback
        error_message = str(e)
        try:
            log_dir = os.path.join(project_root, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            error_log = os.path.join(log_dir, 'wsgi_error.log')
            with open(error_log, 'a') as f:
                f.write(f"[wsgi] OSError (errno {errno}) creating application: {error_message}\n")
                traceback.print_exc(file=f)
        except:
            pass
        from flask import Flask
        application = Flask(__name__)
        @application.route('/')
        def error():
            return f"Application creation failed: {error_message}", 500
except Exception as e:
    import traceback
    error_message = str(e)  # Capture error message before it goes out of scope
    # Only log to file, not stderr (which can block)
    try:
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        error_log = os.path.join(log_dir, 'wsgi_error.log')
        with open(error_log, 'a') as f:
            f.write(f"[wsgi] ERROR creating application: {error_message}\n")
            traceback.print_exc(file=f)
    except:
        pass  # If we can't even log, continue anyway
    # Create a minimal app so uWSGI doesn't fail completely
    from flask import Flask
    application = Flask(__name__)
    @application.route('/')
    def error():
        return f"Application creation failed: {error_message}", 500

# uWSGI looks for 'application' variable
if __name__ == "__main__":
    application.run()
