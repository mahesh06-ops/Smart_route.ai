"""
Startup script for Smart Route AI.
Executes the FastAPI server via Uvicorn.
Usage:
    python run.py
"""
import sys
import socket
import subprocess
import uvicorn
from src.config.settings import settings


def is_port_in_use(host: str, port: int) -> bool:
    """Checks whether the specified host and port are already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except socket.error:
            return True


def get_process_on_port(port: int) -> str:
    """Attempts to identify the PID holding the port on Windows."""
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1)"],
            text=True,
            timeout=5
        ).strip()
        if out:
            proc_name = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-Process -Id {out} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName)"],
                text=True,
                timeout=5
            ).strip()
            return f"PID {out} ({proc_name})"
    except Exception:
        pass
    return "Unknown process"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 65)
    print(">> SMART ROUTE AI - Intelligent Route Optimization Platform")
    print(f"   Tagline : {settings.TAGLINE}")
    print(f"   Host    : http://{settings.HOST}:{settings.PORT}")
    print(f"   Docs    : http://{settings.HOST}:{settings.PORT}/docs")
    print(f"   Debug   : {settings.DEBUG} (reload={'True' if settings.DEBUG else 'False'})")
    print("=" * 65)

    if is_port_in_use(settings.HOST, settings.PORT):
        holder = get_process_on_port(settings.PORT)
        print(f"\n[ERROR] Port {settings.PORT} is already in use by {holder}!")
        print(f"Please stop the existing process before starting the server.")
        print(f"To terminate on Windows: Stop-Process -Id <PID> -Force\n")
        sys.exit(1)

    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )


if __name__ == "__main__":
    main()
