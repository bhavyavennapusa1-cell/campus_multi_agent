"""
API Server for Synapse Multi-Agent System.
Exposes FastAPI REST endpoints for HTML/CSS/JS frontend integration and multi-agent query orchestration.
"""

import os
# pyrefly: ignore [missing-import]
import uvicorn
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from main import app, ChatRequest, ConfirmRequest

# Explicit CORS configuration for deployed frontend origin (Render) and local dev
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
    "https://campus-multi-agent.onrender.com",
    "*"
]

# Ensure CORS middleware is configured
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_server:app", host="0.0.0.0", port=port)
