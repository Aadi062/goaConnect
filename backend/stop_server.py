"""Stop the GoaConnect background server."""
import os, sys, signal

HERE = os.path.dirname(os.path.abspath(__file__))
pid_file = os.path.join(HERE, "server.pid")

if not os.path.exists(pid_file):
    print("No server.pid found — server may not be running.")
    sys.exit(0)

with open(pid_file) as f:
    pid = int(f.read().strip())

try:
    if sys.platform == "win32":
        import subprocess
        subprocess.call(["taskkill", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL)
    else:
        os.kill(pid, signal.SIGTERM)
    os.remove(pid_file)
    print(f"Server (PID {pid}) stopped.")
except Exception as e:
    print(f"Could not stop PID {pid}: {e}")
