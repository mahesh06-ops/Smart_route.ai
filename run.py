"""
Startup script for Smart Route AI.
Executes the FastAPI server via Uvicorn.
Usage:
    python run.py
"""
import sys
import uvicorn
from src.config.settings import settings


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
    print("=" * 65)

    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level="info" if not settings.DEBUG else "debug"
    )


if __name__ == "__main__":
    main()
