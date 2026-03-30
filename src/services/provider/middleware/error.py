import typing as t
from http import HTTPStatus

import src.services.provider.errors as err
from src.services.provider.middleware.base import (
    BaseRequestMiddleware,
    CallNextMiddlewareType,
)
from src.services.provider.response import Response
from src.services.provider.types import RequestMethodType


async def _check_response(response: Response) -> Response:
    status_code = response.status
    if HTTPStatus.OK <= status_code <= HTTPStatus.IM_USED:
        return response

    content = await response.read()

    url = str(response.url)
    if status_code == HTTPStatus.BAD_REQUEST:
        raise err.BadRequestError(
            status_code=status_code, content=content, message="Bad request", url=url
        )
    if status_code == HTTPStatus.TOO_MANY_REQUESTS:
        raise err.TooManyRequestsError(
            status_code=status_code,
            content=content,
            message="Too many requests",
            url=url,
        )
    if status_code == HTTPStatus.NOT_FOUND:
        raise err.NotFoundError(
            status_code=status_code, content=content, message="Not found", url=url
        )
    if status_code == HTTPStatus.CONFLICT:
        raise err.ConflictError(
            status_code=status_code, content=content, message="Conflict", url=url
        )
    if status_code == HTTPStatus.UNAUTHORIZED:
        raise err.UnauthorizedError(
            status_code=status_code,
            content=content,
            message="Auth is required",
            url=url,
        )
    if status_code == HTTPStatus.FORBIDDEN:
        raise err.ForbiddenError(
            status_code=status_code,
            content=content,
            message="You have no permissions",
            url=url,
        )
    if status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE:
        raise err.EntityTooLarge(
            status_code=status_code,
            content=content,
            message="Too large content",
            url=url,
        )
    if status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
        raise err.ServerError(
            status_code=status_code,
            content=content,
            message="Server is disabled or you are banned",
            url=url,
        )

    raise err.APIError(
        status_code=status_code, content=content, message="Unknown Error", url=url
    )


class RequestErrorMiddleware(BaseRequestMiddleware):
    async def __call__(
        self,
        call_next: CallNextMiddlewareType,
        method: RequestMethodType,
        url_or_endpoint: str,
        **kw: t.Any,
    ) -> Response:
        response = await call_next(method=method, url_or_endpoint=url_or_endpoint, **kw)

        return await _check_response(response)
