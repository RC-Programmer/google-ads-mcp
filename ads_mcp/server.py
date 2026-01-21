# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Entry point for the MCP server."""
import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse
from ads_mcp.coordinator import mcp
# The following imports are necessary to register the tools with the `mcp`
# object, even though they are not directly used in this file.
from ads_mcp.tools import search, core  # noqa: F401


async def trigger_sync(request):
    """Endpoint to trigger the sheets sync."""
    try:
        from ads_mcp.sheets_sync.run_sync import run_sync
        run_sync()
        return JSONResponse({"status": "success", "message": "Sync completed"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


async def health_check(request):
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


def run_server() -> None:
    """Run the MCP server with SSE transport for remote connections."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        port = int(os.environ.get("PORT", "8080"))
        
        # Get the MCP SSE app
        mcp_app = mcp.sse_app()
        
        # Create combined app with sync endpoint
        app = Starlette(
            routes=[
                Route("/sync-sheets", trigger_sync, methods=["GET", "POST"]),
                Route("/health", health_check, methods=["GET"]),
                Mount("/", app=mcp_app),
            ]
        )
        
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    run_server()
