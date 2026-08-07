"""
API Server for Smart Campus Multi-Agent System.
Exposes FastAPI REST endpoints for HTML/CSS/JS frontend integration and multi-agent query orchestration.
"""

import os
# pyrefly: ignore [missing-import]
import uvicorn
# pyrefly: ignore [missing-import]
from main import app, ChatRequest, ConfirmRequest

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_server:app", host="0.0.0.0", port=port)
