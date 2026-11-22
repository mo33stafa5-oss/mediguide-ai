from fastapi import HTTPException


class ApiError(HTTPException):
    """Structured error: {"error": {"code": ..., "message": ...}}"""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(status_code=status, detail={"code": code, "message": message})


def not_configured(what: str, hint: str) -> ApiError:
    return ApiError(503, "service_not_configured", f"{what} is not configured. {hint}")
