"""
Purpose:
- Entry point for the language backend service.
- Exposes compile, run, and AI suggestion APIs for the IDE frontend.
"""

import sys
from pathlib import Path

# Ensure this directory is first on sys.path so local packages (lexer, ast_parse, …)
# win over stdlib names like `parser` regardless of uvicorn's working directory.
_backend_dir = Path(__file__).resolve().parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from compiler_service import ai_suggest as ai_suggest_pipeline
from compiler_service import compile_source, run_source
from config import APP_DESCRIPTION, APP_NAME, APP_VERSION


# A unified request model keeps all endpoints consistent for clients.
class CodeRequest(BaseModel):
    """Represents source code sent by frontend/editor clients."""

    code: str = Field(..., description="Language source code input.")

    @validator("code")
    def strip_non_empty(cls, value: str) -> str:
        """Reject whitespace-only paste; normalize leading/trailing spaces."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Code must not be empty.")
        return stripped


# Structured response schemas make API behavior predictable for integration.
class ApiResponse(BaseModel):
    """Base response contract returned by all backend endpoints."""

    success: bool
    endpoint: str
    message: str
    input: dict
    output: dict


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
)

# CORS: allow local Vite dev server and typical production origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health() -> dict:
    """Basic health check route for local verification and uptime checks."""
    return {
        "success": True,
        "service": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
    }


@app.get("/health")
def health_detailed() -> dict:
    """Explicit health endpoint for IDE connection indicator."""
    return {
        "ok": True,
        "service": APP_NAME,
        "version": APP_VERSION,
    }


@app.post("/compile", response_model=ApiResponse)
def compile_code(payload: CodeRequest) -> ApiResponse:
    """
    Lex, parse, analyze, and lower source to IR and bytecode.

    Returns structured JSON suitable for the IDE (tokens, AST, pipeline artifacts).
    """
    result = compile_source(payload.code)
    if not result.get("ok"):
        return ApiResponse(
            success=False,
            endpoint="/compile",
            message=result.get("error", "Compilation failed."),
            input={"code": payload.code},
            output={"stage": result.get("stage"), "detail": result},
        )

    return ApiResponse(
        success=True,
        endpoint="/compile",
        message="Compilation completed.",
        input={"code": payload.code},
        output={
            "status": "ok",
            "tokens": result["tokens"],
            "ast": result["ast"],
            "semantic": result["semantic"],
            "ir": result["ir"],
            "ir_optimized": result["ir_optimized"],
            "bytecode": result["bytecode"],
        },
    )


@app.post("/run", response_model=ApiResponse)
def run_code(payload: CodeRequest) -> ApiResponse:
    """
    Compile and execute bytecode on the stack VM; return stdout/stderr-shaped fields.
    """
    result = run_source(payload.code)
    if not result.get("ok"):
        return ApiResponse(
            success=False,
            endpoint="/run",
            message=result.get("error", "Run failed."),
            input={"code": payload.code},
            output={
                "stage": result.get("stage"),
                "semantic": result.get("semantic"),
                "detail": result,
            },
        )

    return ApiResponse(
        success=True,
        endpoint="/run",
        message="Execution finished.",
        input={"code": payload.code},
        output={
            "status": "ok",
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_code": result["exit_code"],
            "variables": result["variables"],
            "print_output": result["print_output"],
        },
    )


@app.post("/ai-suggest", response_model=ApiResponse)
def ai_suggest(payload: CodeRequest) -> ApiResponse:
    """
    Optional classifier-based hints when `ai/models/` contains a trained checkpoint.
    """
    out = ai_suggest_pipeline(payload.code)
    return ApiResponse(
        success=True,
        endpoint="/ai-suggest",
        message="AI suggestion response.",
        input={"code": payload.code},
        output=out,
    )
