"""Launch uvicorn in a subprocess, wait for it to be ready, run live tests, then kill it."""
import os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8002

SERVER_ENV = {
    **os.environ,
    "DATABASE_URL": "sqlite+aiosqlite:///./goaConnect_dev.db",
    "SECRET_KEY": "goaConnect-dev-secret-key-32chars",
    "ENVIRONMENT": "development",
    "LOG_LEVEL": "warning",
    "ALLOWED_ORIGINS": "*",
    "PYTHONPATH": HERE,
}

print(f"[runner] Starting uvicorn on port {PORT}...")
server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app",
     "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
    cwd=HERE,
    env=SERVER_ENV,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

for i in range(20):
    time.sleep(0.5)
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1)
        print(f"[runner] Server ready after {(i+1)*0.5:.1f}s")
        break
    except Exception:
        pass
else:
    print("[runner] ERROR: server did not start in time")
    server.kill()
    sys.exit(1)

result = subprocess.run([sys.executable, "live_test.py"], cwd=HERE, env=SERVER_ENV)

server.kill()
print("[runner] Server stopped.")
sys.exit(result.returncode)
