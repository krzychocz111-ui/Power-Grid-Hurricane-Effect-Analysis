import os
import sys
import time
import socket
import webbrowser
import subprocess
import json
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FILES_DIR = BASE_DIR / "files"

LIBREOFFICE_EXE = r"C:\Program Files\LibreOffice\program\soffice.exe"
LIBREOFFICE_PYTHON = r"C:\Program Files\LibreOffice\program\python.exe"

PREFERRED_WEB_PORT = 5000
UNO_PORT = 2002
PID_FILE = BASE_DIR / ".dashboard_pids.json"

# Separate LibreOffice automation profile
LO_PROFILE_DIR = BASE_DIR / "lo_profile"
LO_PROFILE_URI = LO_PROFILE_DIR.as_uri()


def delete_stale_lock_files():
    patterns = [
        ".~lock.*.ods#",
        ".~lock.*.xlsx#",
        ".~lock.*.xls#",
    ]
    deleted = []

    if not FILES_DIR.exists():
        print(f"Files directory does not exist: {FILES_DIR}")
        return deleted

    for pattern in patterns:
        for path in FILES_DIR.glob(pattern):
            try:
                path.unlink()
                deleted.append(path)
            except Exception as e:
                print(f"Could not delete lock file {path}: {e}")

    if deleted:
        print("Deleted lock files:")
        for p in deleted:
            print(f"  {p}")
    else:
        print("No stale lock files found.")

    return deleted


def wait_for_port(host: str, port: int, timeout: float = 20.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.4)
    return False


def port_is_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def find_free_port(start_port: int = PREFERRED_WEB_PORT, attempts: int = 20) -> int:
    for port in range(start_port, start_port + attempts):
        if not port_is_open("127.0.0.1", port):
            return port
    raise RuntimeError(f"Could not find a free dashboard port near {start_port}.")


def write_pid_file(web_port: int, dashboard_proc, lo_proc):
    payload = {
        "base_dir": str(BASE_DIR),
        "web_port": web_port,
        "dashboard_pid": dashboard_proc.pid if dashboard_proc is not None else None,
        "libreoffice_pid": lo_proc.pid if lo_proc is not None else None,
        "updated_at": time.time(),
    }
    PID_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def remove_pid_file():
    try:
        PID_FILE.unlink()
    except FileNotFoundError:
        pass


def read_app_info(port: int):
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/app-info", timeout=5
        ) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def start_libreoffice_listener():
    if port_is_open("127.0.0.1", UNO_PORT):
        print(f"LibreOffice listener is already ready on port {UNO_PORT}.")
        return None

    LO_PROFILE_DIR.mkdir(exist_ok=True)

    cmd = [
        LIBREOFFICE_EXE,
        "--headless",
        f'--accept=socket,host=127.0.0.1,port={UNO_PORT};urp;',
        "--nologo",
        "--nodefault",
        "--norestore",
        f"-env:UserInstallation={LO_PROFILE_URI}",
    ]

    print("Starting LibreOffice listener...")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(BASE_DIR),
    )

    if wait_for_port("127.0.0.1", UNO_PORT, timeout=20):
        print(f"LibreOffice listener is ready on port {UNO_PORT}.")
    else:
        proc.terminate()
        raise RuntimeError("LibreOffice listener did not start in time.")

    return proc


def start_dashboard_app(port: int):
    cmd = [LIBREOFFICE_PYTHON, "app.py"]

    print(f"Starting dashboard app on port {port}...")
    env = os.environ.copy()
    env["DASHBOARD_PORT"] = str(port)
    proc = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        env=env,
    )

    if wait_for_port("127.0.0.1", port, timeout=20) and proc.poll() is None:
        app_info = read_app_info(port)
        if not app_info or Path(app_info.get("base_dir", "")) != BASE_DIR:
            proc.terminate()
            raise RuntimeError(
                f"Port {port} is not serving this dashboard folder. "
                f"Expected {BASE_DIR}, got {app_info}."
            )
        print(f"Dashboard app is ready on port {port}.")
        print(f"Serving files from {BASE_DIR}.")
    else:
        if proc.poll() is None:
            proc.terminate()
        raise RuntimeError("Dashboard app did not start in time.")

    return proc


def main():
    delete_stale_lock_files()

    lo_proc = start_libreoffice_listener()
    if port_is_open("127.0.0.1", PREFERRED_WEB_PORT):
        print(f"Port {PREFERRED_WEB_PORT} is already in use.")
        print("Run this first to stop the old dashboard:")
        print(f"  {LIBREOFFICE_PYTHON} stop_dashboard.py")
        return
    web_port = PREFERRED_WEB_PORT
    dashboard_proc = start_dashboard_app(web_port)
    write_pid_file(web_port, dashboard_proc, lo_proc)
    web_url = f"http://127.0.0.1:{web_port}/"

    print(f"Opening browser: {web_url}")
    webbrowser.open(web_url)

    print("Everything started.")
    print("Close this window or press Ctrl+C to stop.")

    try:
        while True:
            # If either child exits unexpectedly, stop.
            if lo_proc is not None and lo_proc.poll() is not None:
                print("LibreOffice listener exited.")
                break
            if dashboard_proc.poll() is not None:
                print("Dashboard app exited.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")

    for proc, name in [(dashboard_proc, "Dashboard"), (lo_proc, "LibreOffice")]:
        if proc is not None and proc.poll() is None:
            print(f"Terminating {name}...")
            proc.terminate()

    time.sleep(1)

    for proc, name in [(dashboard_proc, "Dashboard"), (lo_proc, "LibreOffice")]:
        if proc is not None and proc.poll() is None:
            print(f"Killing {name}...")
            proc.kill()

    remove_pid_file()


if __name__ == "__main__":
    main()
