from typing import Any, ClassVar, Dict, Optional

from starlette import status


class AppException(Exception):
    """
    Base class for every application-level error.

    Subclasses declare their HTTP mapping and Sentry policy as class
    attributes, so the exception itself is the single source of truth
    for how it should be handled.

    - ``status_code`` — HTTP status returned by the exception handler.
                        Lives on the class so you don't need a parallel
                        type→status mapping in the handler registration.

    - ``expected``    — ``True`` means "normal business outcome" (auth
                        failure, not found, validation, rate limit,
                        conflict, ...). Handlers log it at INFO/WARNING
                        and Sentry is expected to drop it via
                        ``before_send`` so you don't drown in non-events.
                        ``False`` means a real incident — logged at ERROR
                        with ``exc_info`` so Sentry captures it. Default
                        is ``False`` on the base class (safer: unknown
                        subclasses reach Sentry until you opt them out).
                        ``DetailedError`` flips it to ``True`` for the
                        business-error branch of the hierarchy.
    """

    status_code: ClassVar[int] = status.HTTP_500_INTERNAL_SERVER_ERROR
    expected: ClassVar[bool] = False

    def __init__(
        self,
        message: str = "App Exception",
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.content: Dict[str, Any] = {"message": message}
        self.headers = headers

    def as_dict(self) -> Dict[str, Any]:
        return {"content": dict(self.content), "headers": self.headers}


class DetailedError(AppException):
    expected: ClassVar[bool] = True

    def __init__(
        self,
        message: str,
        headers: Optional[Dict[str, Any]] = None,
        **additional: Any,
    ) -> None:
        super().__init__(message=message, headers=headers)
        self.content |= additional

    def __str__(self) -> str:
        return f"{type(self).__name__}: {self.content}\nHeaders: {self.headers or ''}"


class UnAuthorizedError(DetailedError):
    status_code: ClassVar[int] = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(DetailedError):
    status_code: ClassVar[int] = status.HTTP_403_FORBIDDEN


class NotFoundError(DetailedError):
    status_code: ClassVar[int] = status.HTTP_404_NOT_FOUND


class BadRequestError(DetailedError):
    status_code: ClassVar[int] = status.HTTP_400_BAD_REQUEST


class ConflictError(DetailedError):
    status_code: ClassVar[int] = status.HTTP_409_CONFLICT


class TooManyRequestsError(DetailedError):
    status_code: ClassVar[int] = status.HTTP_429_TOO_MANY_REQUESTS


class BadGatewayError(DetailedError):
    status_code: ClassVar[int] = status.HTTP_502_BAD_GATEWAY
    expected: ClassVar[bool] = False


class ServiceUnavailableError(DetailedError):
    status_code: ClassVar[int] = status.HTTP_503_SERVICE_UNAVAILABLE
    expected: ClassVar[bool] = False


class ServiceNotImplementedError(DetailedError):
    status_code: ClassVar[int] = status.HTTP_501_NOT_IMPLEMENTED
    expected: ClassVar[bool] = False
