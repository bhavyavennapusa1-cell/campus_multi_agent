"""
API Server for Smart Campus Multi-Agent System.
Exposes FastAPI REST endpoints for HTML/CSS/JS frontend integration and multi-agent query orchestration.
"""

from main import app, ChatRequest, ConfirmRequest

if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
