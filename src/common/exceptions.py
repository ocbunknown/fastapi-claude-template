from typing import Any, Dict, Optional


class AppException(Exception):
    def __init__(
        self,
        message: str = "App Exception",
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.content = {"message": message}
        self.headers = headers

    def as_dict(self) -> Dict[str, Any]:
        return self.__dict__


class DetailedError(AppException):
    def __init__(
        self,
        message: str,
        headers: Optional[Dict[str, Any]] = None,
        **additional: Any,
    ) -> None:
        super().__init__(
            message=message,
            headers=headers,
        )
        self.content |= additional

    def __str__(self) -> str:
        return f"{type(self).__name__}: {self.content}\nHeaders: {self.headers or ''}"


class UnAuthorizedError(DetailedError): ...


class NotFoundError(DetailedError): ...


class BadRequestError(DetailedError): ...


class TooManyRequestsError(DetailedError): ...


class ServiceUnavailableError(DetailedError): ...


class BadGatewayError(DetailedError): ...


class ForbiddenError(DetailedError): ...


class ServiceNotImplementedError(DetailedError): ...


class ConflictError(DetailedError): ...
