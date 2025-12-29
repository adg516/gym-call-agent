from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import router as api_router
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.log_level == "DEBUG" else logging.INFO,
    format='%(levelname)s:     %(name)s - %(message)s'
)

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "env": settings.env}

    app.include_router(api_router, prefix="/v1")
    return app

app = create_app()