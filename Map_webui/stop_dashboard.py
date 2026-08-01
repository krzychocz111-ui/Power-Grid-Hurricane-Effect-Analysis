import json
import subprocess
import time
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PID_FILE = BASE_DIR / ".dashboard_pids.json"
WEB_PORTS = set(range(5000, 5121))
UNO_PORT = 2002


def read_pid_file():
    if not PID_FILE.exists():
        return {}
    try:
        return json.loads(PID_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def listening_pids_by_port():
    completed = subprocess.run(
        ["netstat", "-ano"],
        text=True,
        capture_output=True,
        check=False,
    )
    ports = {}
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        local = parts[1]
        state = parts[3].upper()
        pid_text = parts[4]
        if state != "LISTENING" or ":" not in local:
            continue
        try:
            port = int(local.rsplit(":", 1)[1])
            pid = int(pid_text)
        except ValueError:
            continue
        ports.setdefault(port, set()).add(pid)
    return ports


def stop_pid(pid):
    completed = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        text=True,
        capture_output=True,
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode == 0:
        print(f"Stopped PID {pid}.")
    else:
        print(f"Could not stop PID {pid}: {output}")


def request_shutdown(port):
    for method in ("POST", "GET"):
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/shutdown", method=method
            )
            with urllib.request.urlopen(request, timeout=3) as response:
                if response.status == 200:
                    print(f"Asked dashboard on port {port} to shut down.")
                    return True
        except Exception:
            pass
    return False


def main():
    pid_file = read_pid_file()
    ports = listening_pids_by_port()

    for port in sorted(ports):
        if port in WEB_PORTS:
            request_shutdown(port)

    time.sleep(1.0)
    ports = listening_pids_by_port()

    pids = set()
    for key in ("dashboard_pid", "libreoffice_pid"):
        pid = pid_file.get(key)
        if isinstance(pid, int):
            pids.add(pid)

    for port, port_pids in ports.items():
        if port in WEB_PORTS or port == UNO_PORT:
            pids.update(port_pids)

    if not pids:
        print("No dashboard or LibreOffice listener processes found.")
    else:
        print("Stopping dashboard-related processes...")
        for pid in sorted(pids):
            stop_pid(pid)

    try:
        PID_FILE.unlink()
    except FileNotFoundError:
        pass

    print("Done. You can start the dashboard again with start_all.py.")


if __name__ == "__main__":
    main()
