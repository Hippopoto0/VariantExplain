from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
from pydantic import BaseModel
import logging

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

class HealthResponse(BaseModel):
    status: str

@app.get("/health")
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring."""
    return HealthResponse(status="healthy")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
