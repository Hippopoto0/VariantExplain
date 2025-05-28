from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocketDisconnect
from typing import Dict, Any, Literal
from pydantic import BaseModel
import logging
from fastapi import FastAPI, WebSocket, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
from pathlib import Path

state = {
    "filename": None,
    "status": "idle",
}

app = FastAPI(
    title="VariantExplain API",
    description="API for VariantExplain application",
    version="0.1.0"
)

# Define a custom filter class
class OpenAPIFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Access log messages contain the request line in the 'message' attribute.
        # We want to exclude logs where the message contains "GET /openapi.json "
        # (Note the space at the end to avoid filtering other paths that might contain openapi.json)
        # The uvicorn access log format usually includes the method and path like:
        # '"GET /path HTTP/1.1" ...'
        log_message = record.getMessage()
        return "GET /openapi.json " not in log_message and "GET /docs HTTP/1.1" not in log_message and "GET /redoc HTTP/1.1" not in log_message

# Get the uvicorn access logger
# Uvicorn's HTTP access logs are typically handled by the logger named "uvicorn.access"
uvicorn_access_logger = logging.getLogger("uvicorn.access")

# Add our custom filter to this logger
# This filter will be applied to every log record before it's displayed
uvicorn_access_logger.addFilter(OpenAPIFilter())


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint that returns a welcome message."""
    return {"message": "Welcome to VariantExplain API"}

class FileUploadRequest(BaseModel):
    file: UploadFile

class FileUploadResponse(BaseModel):
    filename: str

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)

@app.post("/upload_file")
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    try:
        # Save the uploaded file
        file_path = UPLOAD_DIR / file.filename
        state["filename"] = file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        return FileUploadResponse(filename=file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


class AnalysisResponse(BaseModel):
    message: str

@app.get("/analysis")
async def analysis() -> AnalysisResponse:
    state["status"] = "generating_vep"
    return AnalysisResponse(message="Analysis started")

class StatusPollResponse(BaseModel):
    status: Literal["generating_vep", "fetching_risky_genes", "fetching_trait_info", "finding_associated_studies", "summarising_results"]

@app.get("/status_poll")
async def status_poll() -> StatusPollResponse:
    """Polling endpoint for status updates."""
    return StatusPollResponse(status=state["status"])

class HealthResponse(BaseModel):
    status: str

@app.get("/health")
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring."""
    return HealthResponse(status="healthy")  

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
