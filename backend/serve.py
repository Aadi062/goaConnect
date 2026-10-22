"""
GoaConnect - Background Server Launcher
Starts uvicorn as a detached background process that keeps running
even after this script exits. No blocking. No CANCELED errors.
"""
import os, subprocess, sys, time, urllib.request, json

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8000

ENV = {
    **os.environ,
    "DATABASE_URL": "sqlite+aiosqlite:///./goaConnect_dev.db",
    "SECRET_KEY":   "goaConnect-dev-secret-key-32chars",
    "ENVIRONMENT":  "development",
    "LOG_LEVEL":    "info",
    "ALLOWED_ORIGINS": "http://localhost:5173,http://localhost:3000",
    "PYTHONPATH":   HERE,
}

LOG = os.path.join(HERE, "server.log")

print(f"Starting GoaConnect server on port {PORT}...")
print(f"Log file: {LOG}")

# Open log file for server stdout/stderr
log_fh = open(LOG, "w")

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app",
     "--host", "0.0.0.0",
     "--port", str(PORT),
     "--log-level", "info"],
    cwd=HERE,
    env=ENV,
    stdout=log_fh,
    stderr=log_fh,
    # Detach from this process so it keeps running
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        if sys.platform == "win32" else 0,
    start_new_session=True if sys.platform != "win32" else False,
)

# Save PID so we can stop it later
pid_file = os.path.join(HERE, "server.pid")
with open(pid_file, "w") as f:
    f.write(str(proc.pid))

# Wait for it to be ready (max 12 seconds)
print("Waiting for server to be ready...")
for i in range(24):
    time.sleep(0.5)
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1)
        data = json.loads(r.read())
        print(f"\nServer is UP after {(i+1)*0.5:.1f}s")
        print(f"  Status:  {data['status']}")
        print(f"  Service: {data['service']}")
        break
    except Exception:
        print(".", end="", flush=True)
else:
    print("\nERROR: server did not respond. Check server.log")
    sys.exit(1)

print(f"\n{'='*55}")
print(f"  GoaConnect is running!")
print(f"{'='*55}")
print(f"  API:      http://localhost:{PORT}")
print(f"  Docs:     http://localhost:{PORT}/docs")
print(f"  Health:   http://localhost:{PORT}/health")
print(f"  PID:      {proc.pid}  (saved to server.pid)")
print(f"  Log:      server.log")
print(f"{'='*55}")
print(f"  Users:    admin   / Admin@GoaConnect1")
print(f"            analyst / Analyst@GoaConnect1")
print(f"{'='*55}")
print(f"  To stop:  python stop_server.py")
print()
