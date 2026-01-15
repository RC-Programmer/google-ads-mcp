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
from starlette.middleware import Middleware
from starlette.applications import Starlette
from starlette.routing import Mount
from ads_mcp.coordinator import mcp
# The following imports are necessary to register the tools with the `mcp`
# object, even though they are not directly used in this file.
from ads_mcp.tools import search, core  # noqa: F401


class HostHeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Override host header to localhost to bypass validation
            headers = dict(scope.get("headers", []))
            new_headers = []
            for key, value in scope.get("headers", []):
                if key == b"host":
                    new_headers.append((key, b"localhost"))
                else:
                    new_headers.append((key, value))
            scope = dict(scope)
            scope["headers"] = new_headers
        await self.app(scope, receive, send)


def run_server() -> None:
    """Run the MCP server with SSE transport for remote connections."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    
    if transport == "sse":
        port = int(os.environ.get("PORT", "8080"))
        sse_app = mcp.sse_app()
        
        # Wrap with middleware to fix host header
        app = HostHeaderMiddleware(sse_app)
        
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    run_server()