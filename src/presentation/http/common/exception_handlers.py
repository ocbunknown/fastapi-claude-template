from uuid import uuid4

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.requests import Request

from src.application.common.exceptions import AppException
from src.presentation.http.common.responses import ORJSONResponse

log = structlog.get_logger("app.http.errors")


def setup_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unknown_exception_handler)


def _ticket(request: Request) -> str:
    return getattr(request.state, "request_id", None) or uuid4().hex


async def app_exception_handler(request: Request, err: AppException) -> ORJSONResponse:
    ticket = _ticket(request)

    if err.expected:
        log.info(
            "app_exception",
            error=type(err).__name__,
            status_code=err.status_code,
            message=err.content.get("message"),
            ticket=ticket,
        )
    else:
        log.error(
            "app_exception_unexpected",
            error=type(err).__name__,
            status_code=err.status_code,
            message=err.content.get("message"),
            ticket=ticket,
            exc_info=err,
        )

    return ORJSONResponse(
        content={**err.content, "ticket": ticket},
        status_code=err.status_code,
        headers=err.headers,
    )


async def validation_exception_handler(
    request: Request, err: RequestValidationError
) -> ORJSONResponse:
    ticket = _ticket(request)
    log.warning(
        "validation_error",
        ticket=ticket,
        errors=err.errors(),
    )
    return ORJSONResponse(
        {
            "message": "Validation error",
            "detail": err.errors(),
            "ticket": ticket,
        },
        status_code=status.HTTP_400_BAD_REQUEST,
    )


async def unknown_exception_handler(
    request: Request, err: Exception
) -> ORJSONResponse:
    ticket = _ticket(request)
    log.error(
        "unhandled_exception",
        error=type(err).__name__,
        method=request.method,
        path=request.url.path,
        request_id=ticket,
        ticket=ticket,
        exc_info=err,
    )
    return ORJSONResponse(
        {"message": "Internal Server Error", "ticket": ticket},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers={"x-request-id": ticket},
    )
