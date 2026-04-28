#!/usr/bin/env python3
"""
Test what's on port 5000 (and optionally 5003): is anything listening? Does HTTP respond?

Usage:
  python scripts/test_port_5000.py              # test 127.0.0.1:5000 (and 5003)
  python scripts/test_port_5000.py --port 5000  # test only 5000
  BASE_URL=http://127.0.0.1:5000 python scripts/test_port_5000.py  # test that URL
"""
import socket
import sys
import argparse

def port_listening(host: str, port: int, timeout: float = 2.0) -> bool:
    """True if something accepts TCP connections on host:port."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except Exception:
        return False


def test_http(url: str, timeout: int = 10) -> tuple:
    """Return (status_code or None, reason_string)."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "test_port_5000/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return (r.status, f"HTTP {r.status} {r.reason}")
    except Exception as e:
        return (None, str(e))


def main():
    ap = argparse.ArgumentParser(description="Test port 5000 (and 5003) for listening and HTTP")
    ap.add_argument("--host", default="127.0.0.1", help="Host (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=None, help="Single port to test (default: 5000 and 5003)")
    ap.add_argument("--url", default=None, help="Full URL to GET (overrides host/port)")
    args = ap.parse_args()

    if args.url:
        # Test single URL
        print(f"Testing URL: {args.url}")
        if not args.url.startswith("http"):
            args.url = "http://" + args.url
        code, msg = test_http(args.url)
        if code is not None:
            print(f"  Response: {msg}")
            print("  -> Server is responding.")
        else:
            print(f"  Error: {msg}")
            print("  -> Cannot connect (connection refused, timeout, or not HTTP).")
        return 0 if code is not None else 1

    ports = [args.port] if args.port is not None else [5000, 5003]
    host = args.host

    print("=" * 60)
    print("Port 5000 / 5003 connectivity test")
    print("=" * 60)
    print(f"Host: {host}")
    print()

    any_ok = False
    for port in ports:
        print(f"Port {port}:")
        listening = port_listening(host, port)
        if not listening:
            print(f"  TCP: nothing listening (connection refused or timeout)")
            print(f"  -> Start the app with: python run.py  (or fix_502.py on server)")
            print()
            continue
        print(f"  TCP: something is listening")
        url = f"http://{host}:{port}/"
        code, msg = test_http(url)
        if code is not None:
            print(f"  HTTP GET {url}: {msg}")
            any_ok = True
        else:
            print(f"  HTTP GET {url}: failed - {msg}")
        print()

    if not any_ok and not any(port_listening(host, p) for p in ports):
        print("Summary: Nothing is listening on port(s) 5000 or 5003.")
        print("  Local: run  python run.py  to start the Flask app.")
        print("  Server: run  python fix_502.py  to start uWSGI on the server.")
        return 1
    return 0 if any_ok else 1


if __name__ == "__main__":
    sys.exit(main())
