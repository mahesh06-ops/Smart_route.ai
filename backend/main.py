"""
FastAPI Main Application for Smart Route AI.
Serves API routes, static frontend assets, and handles application lifecycle.
"""
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from src.config.settings import settings
from src.database.database import init_db
from src.utils.logging_config import logger
from backend.api import health_router, route_router, history_router, settings_router, weather_router


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

visa_loaded = False
visa_error_message = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Self-Check & Initialization
    logger.info("=" * 60)
    logger.info("Smart Route AI: Starting system self-check...")
    logger.info(f"Using environment file: {settings.ENV_PATH}")
    
    # Check configured keys (names only, never log secret values)
    maptiler_status = "CONFIGURED" if settings.MAPTILER_API_KEY else "NOT SET"
    weather_status = f"CONFIGURED (Provider: {settings.WEATHER_PROVIDER})" if settings.WEATHER_API_KEY else "NOT SET (Using Open-Meteo fallback)"
    traffic_status = f"CONFIGURED (Provider: {settings.TRAFFIC_PROVIDER})" if settings.TRAFFIC_API_KEY else "NOT SET (Using analytical simulation)"
    
    logger.info(f"API Key MAPTILER_API_KEY: {maptiler_status}")
    logger.info(f"API Key WEATHER_API_KEY : {weather_status}")
    logger.info(f"API Key TRAFFIC_API_KEY : {traffic_status}")

    # Database Reachability
    try:
        init_db()
        logger.info(f"Database reachable & initialized at: {settings.DB_PATH}")
    except Exception as db_err:
        logger.error(f"Database initialization failed: {db_err}")

    # Visa module status
    if visa_loaded:
        logger.info("Visa module: Successfully loaded and mounted at /api/visa")
    else:
        logger.warning(f"Visa module: Not loaded ({visa_error_message})")

    logger.info("Smart Route AI backend is ready to optimize routes.")
    logger.info("=" * 60)
    
    yield

    # Shutdown
    logger.info("Shutting down Smart Route AI backend.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Based Multi-Factor Smart Route Optimization & Recommendation System",
    lifespan=lifespan
)

# Configure CORS: App's own origins on the configured port, allow_credentials=False
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://127.0.0.1:{settings.PORT}",
        f"http://localhost:{settings.PORT}",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(health_router, prefix="/api")
app.include_router(route_router, prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(weather_router, prefix="/api")

# Resilient Visa router mounting
try:
    from visa.visa_api import visa_router
    app.include_router(visa_router, prefix="/api")
    visa_loaded = True
except Exception as e:
    visa_loaded = False
    visa_error_message = str(e)
    logger.error(f"Visa module failed to load: {e}")

# Mount Frontend static files
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = FRONTEND_DIR / "index.html"
        return FileResponse(str(index_file))


# Polished Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": "An internal service error occurred. Please try again or switch to demo mode."}
    )
