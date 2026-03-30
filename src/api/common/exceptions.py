from collections.abc import Awaitable
from functools import partial
from typing import Callable

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.requests import Request

from src.api.common.responses import ORJSONResponse
from src.common.exceptions import (
    AppException,
    ServiceNotImplementedError,
    TooManyRequestsError,
)
from src.common.logger import log


def setup_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        TooManyRequestsError, error_handler(status.HTTP_429_TOO_MANY_REQUESTS)
    )
    app.add_exception_handler(
        ServiceNotImplementedError, error_handler(status.HTTP_501_NOT_IMPLEMENTED)
    )
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore
    app.add_exception_handler(Exception, unknown_exception_handler)


async def unknown_exception_handler(request: Request, err: Exception) -> ORJSONResponse:
    log.error("Handle error")
    log.exception(f"Unknown error occurred -> {err.args}")
    return ORJSONResponse(
        {"status": 500, "message": "Unknown Error"},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


async def validation_exception_handler(
    request: Request, err: RequestValidationError
) -> ORJSONResponse:
    log.error(f"Handle error: {type(err).__name__}")
    return ORJSONResponse(
        {
            "status": 400,
            "detail": [err],
            "additional": [err.get("ctx") for err in err._errors],
        },
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def error_handler(
    status_code: int,
) -> Callable[..., Awaitable[ORJSONResponse]]:
    return partial(app_error_handler, status_code=status_code)


async def app_error_handler(
    request: Request, err: AppException, status_code: int
) -> ORJSONResponse:
    return await handle_error(
        request=request,
        err=err,
        status_code=status_code,
    )


async def handle_error(
    request: Request,
    err: AppException,
    status_code: int,
) -> ORJSONResponse:
    log.error(f"Handle error: {type(err).__name__}")
    error_data = err.as_dict()

    return ORJSONResponse(**error_data)
