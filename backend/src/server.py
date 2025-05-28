import json
import os
import logging
from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocketDisconnect
from typing import Dict, Any, Literal, Optional
from pydantic import BaseModel
from pathlib import Path
import threading
import traceback
import logging
from fastapi import FastAPI, WebSocket, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
from pathlib import Path

import threading

# status one of Literal["idle", "generating_vep", "fetching_risky_genes", "fetching_trait_info", "finding_associated_studies", "summarising_results"]

state = {
    "filename": None,
    "status": "idle",
    "result": None,
    "error": None,
    "analysis_running": False
}
state_lock = threading.Lock()

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

def run_analysis_thread(filename):
    from parse import VCFParser
    from rag import RAG
    import traceback
    import time
    import json
    import os
    
    def update_state(status, result=None, error=None):
        with state_lock:
            state["status"] = status
            if result is not None:
                state["result"] = result
            if error is not None:
                state["error"] = error
    
    def get_progress():
        progress_file = "generated_annotation/rag_progress.json"
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error reading progress file: {e}")
        return {}
    
    try:
        # Initialize state
        with state_lock:
            state.update({
                "status": "starting",
                "result": None,
                "error": None,
                "analysis_running": True,
                "start_time": time.time()
            })
        
        # Parse VCF file
        file_path = UPLOAD_DIR / filename
        parser = VCFParser(str(file_path))
        
        # Initialize RAG
        rag = RAG()
        
        # Process VEP data - this will update progress to vep_annotation
        update_state("vep_annotation")
        
        # Process VEP data - this will update the progress file
        results = rag.process_vep_data(parser.annotation)
        
        # Check if processing completed successfully
        progress = get_progress()
        if progress.get("status") == "completed" and progress.get("step") == "fetch_pubmed_abstracts":
            update_state("completed", result=results)
        else:
            update_state("completed", result=results)  # Still mark as completed even if progress file is missing
        
    except Exception as e:
        error_msg = f"Error: {e}\n{traceback.format_exc()}"
        logging.error(error_msg)
        update_state("error", error=error_msg)
    finally:
        with state_lock:
            state["analysis_running"] = False
            if state.get("status") != "error":
                state["status"] = "completed"

@app.get("/analysis")
async def analysis() -> AnalysisResponse:
    with state_lock:
        if state.get("analysis_running", False):
            return AnalysisResponse(message="Analysis already running")
        filename = state.get("filename")
        if not filename:
            return AnalysisResponse(message="No file uploaded")
        # Start thread
        thread = threading.Thread(target=run_analysis_thread, args=(filename,), daemon=True)
        thread.start()
        state["status"] = "vep_annotation"
        state["analysis_running"] = True
    return AnalysisResponse(message="Analysis started")

from typing import Optional
class StatusPollResponse(BaseModel):
    status: Literal[
        "idle", 
        "starting",
        "vep_annotation",
        "find_damaging_variants",
        "fetch_gwas_associations",
        "fetch_pubmed_abstracts",
        # "starting",
        # "generating_vep", 
        # "find_damaging_variants",
        # "fetch_gwas_associations",
        # "fetch_pubmed_abstracts",
        # "fetching_risky_genes", 
        # "fetching_trait_info", 
        # "finding_associated_studies", 
        # "summarising_results",
        "completed",
        "error"
    ]
    progress: Optional[float] = 0
    step: Optional[str] = None
    current: Optional[int] = 0
    total: Optional[int] = 0
    message: Optional[str] = None

@app.get("/status_poll")
async def status_poll() -> StatusPollResponse:
    """Polling endpoint for status updates."""
    with state_lock:
        current_status = state["status"]
    
    # Initialize response with current status
    response = StatusPollResponse(status=current_status)
    
    # Try to read progress from rag_progress.json
    try:
        progress_path = "generated_annotation/rag_progress.json"
        if os.path.exists(progress_path):
            with open(progress_path, 'r') as f:
                progress_data = json.load(f)
                
                # Update status based on progress data if available
                progress_status = progress_data.get('status')
                if progress_status == 'in_progress':
                    # If we're in progress, use the step from progress data as the status
                    step = progress_data.get('step')
                    if step and step != current_status and step in StatusPollResponse.__annotations__['status'].__args__:
                        with state_lock:
                            state["status"] = step
                        response.status = step
                
                # Update progress information
                response.step = progress_data.get('step')
                response.current = progress_data.get('current', 0)
                response.total = progress_data.get('total', 1)
                response.progress = progress_data.get('percentage', 0)
                response.message = f"{response.step}: {response.progress}%"
                
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding progress file: {e}")
    except Exception as e:
        logging.error(f"Error reading progress file: {e}")
    
    return response

class HealthResponse(BaseModel):
    status: str

@app.get("/health")
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring."""
    return HealthResponse(status="healthy")  

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
