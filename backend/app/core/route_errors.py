from fastapi import Request
from fastapi.responses import JSONResponse

from .model_api import ModelError


async def model_error_response(_request: Request, error: ModelError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(error)})
