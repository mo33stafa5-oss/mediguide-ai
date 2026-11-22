import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .routers import admin, chat, documents, health, ocr_worker, predict, prescriptions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = FastAPI(title="MediGuide AI API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in get_settings().allowed_origins.split(",")],
                   allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"], allow_credentials=False)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.update({"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Cache-Control": resp.headers.get("Cache-Control", "no-store")})
    return resp


def _err(status: int, code: str, message: str, extra: dict | None = None):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, **(extra or {})}})


@app.exception_handler(StarletteHTTPException)
async def http_exc(_: Request, exc: StarletteHTTPException):
    d = exc.detail
    if isinstance(d, dict) and "code" in d:
        return _err(exc.status_code, d["code"], d["message"])
    return _err(exc.status_code, "http_error", str(d))


@app.exception_handler(RequestValidationError)
async def validation_exc(_: Request, exc: RequestValidationError):
    fields = [{"field": ".".join(str(x) for x in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]  # never echo input values
    return _err(422, "validation_error", "Invalid request.", {"fields": fields})


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    logging.getLogger("mediguide").error("unhandled %s", type(exc).__name__)  # type only: no medical data in logs
    return _err(500, "internal_error", "Unexpected server error.")


for r in (health, predict, chat, documents, prescriptions, admin, ocr_worker):
    app.include_router(r.router)
