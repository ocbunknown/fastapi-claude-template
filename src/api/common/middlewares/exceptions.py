from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import ORJSONResponse

from src.common.exceptions import AppException, ForbiddenError
from src.common.logger import log


async def handle_exception_middleware(
    request: Request,
    exc: Exception,
) -> Response:
    if isinstance(exc, AppException):
        exception = exc
    else:
        exception = ForbiddenError(message="Something went wrong")

    params = {
        "request": {
            "method": request.method,
            "url": str(request.url.path),
        },
        "exception": exception,
    }
    log.info(params)
    request_id = request.state.request_id or uuid4().hex

    error_data = exception.as_dict()
    error_data["content"] |= {"ticket": request_id}
    log.info(error_data)

    return ORJSONResponse(**error_data)
