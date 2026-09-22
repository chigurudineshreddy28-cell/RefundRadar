import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import dashboard, evidence, refunds, transactions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("refund_radar")

app = FastAPI(title="Refund Radar API", version="1.0.0")

# The frontend is plain HTML/CSS/JS served from a local dev server
# (Live Server, `python -m http.server`, or even opened as a file).
# There is no cookie-based auth, so it's safe to allow any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Global error handling
#
# Every error the API returns comes back as {"detail": "<readable text>"}
# so the frontend never has to guess at a shape — no more
# "[object Object]" or raw stack traces reaching the user.
# ============================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        field = error["loc"][-1] if error["loc"] else "field"
        messages.append(f"{field}: {error['msg']}")

    detail = "; ".join(messages) if messages else "Please check the required fields."
    logger.warning("Validation error on %s: %s", request.url.path, detail)

    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our end. Please try again."},
    )


app.include_router(transactions.router)
app.include_router(refunds.router)
app.include_router(evidence.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {"message": "Refund Radar API is running", "docs": "/docs"}
