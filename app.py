"""
ASGI Entrypoint for Smart Route AI.
"""
from backend.main import app

if __name__ == "__main__":
    import uvicorn
    from src.config.settings import settings
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
