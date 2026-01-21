"""HTTP endpoint to trigger sheets sync."""

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import logging

logger = logging.getLogger(__name__)


async def trigger_sync(request):
    """Endpoint to trigger the sheets sync."""
    try:
        from ads_mcp.sheets_sync.run_sync import run_sync
        run_sync()
        return JSONResponse({"status": "success", "message": "Sync completed"})
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


async def health_check(request):
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


routes = [
    Route("/sync-sheets", trigger_sync, methods=["GET", "POST"]),
    Route("/health", health_check, methods=["GET"]),
]

sync_app = Starlette(routes=routes)
