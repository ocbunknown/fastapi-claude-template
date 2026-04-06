from typing import Any, Callable

from pydantic import ConfigDict, PrivateAttr

from src.application.common.events.base import Event


class BrokerEvent(Event):
    subject: str = ""
    _reply: str = PrivateAttr(default="")
    _headers: dict[str, Any] | None = PrivateAttr(default=None)


class StreamEvent(BrokerEvent):
    _stream: str | None = PrivateAttr(default=None)
    _timeout: float | None = PrivateAttr(default=None)


def rebuild_broker_event[T: BrokerEvent](
    subject: str = "",
    subject_namespace: str | None = None,
    separator: str = ".",
    reply: str = "",
    headers: dict[str, Any] | None = None,
) -> Callable[[type[T]], type[T]]:
    def _wrapper(cls: type[T]) -> type[T]:
        updated_subject = subject
        updated_reply = reply
        updated_headers = headers

        class UpdatedEvent(cls):  # type: ignore[valid-type, misc]
            model_config = ConfigDict(populate_by_name=True)
            subject: str = updated_subject
            _reply: str = PrivateAttr(default=updated_reply)
            if updated_headers is not None:
                _headers: dict[str, Any] = PrivateAttr(
                    default_factory=lambda: dict(updated_headers)
                )

            def model_post_init(self, *args: Any, **kwargs: Any) -> None:
                super().model_post_init(*args, **kwargs)
                if subject_namespace:
                    if self.subject:
                        self.subject = f"{subject_namespace}{separator}{self.subject}"
                    else:
                        self.subject = subject_namespace
                elif not self.subject and subject:
                    self.subject = subject

        UpdatedEvent.__name__ = cls.__name__
        UpdatedEvent.__qualname__ = cls.__qualname__
        UpdatedEvent.__module__ = cls.__module__
        return UpdatedEvent  # type: ignore[return-value]

    return _wrapper


def rebuild_stream_event[T: StreamEvent](
    subject: str = "",
    subject_namespace: str | None = None,
    separator: str = ".",
    stream: str | None = None,
    timeout: float | None = None,
    headers: dict[str, Any] | None = None,
) -> Callable[[type[T]], type[T]]:
    def _wrapper(cls: type[T]) -> type[T]:
        updated_subject = subject
        updated_stream = stream
        updated_timeout = timeout
        updated_headers = headers

        class UpdatedEvent(cls):  # type: ignore[valid-type, misc]
            model_config = ConfigDict(populate_by_name=True)
            subject: str = updated_subject
            if updated_stream is not None:
                _stream: str = PrivateAttr(default=updated_stream)
            if updated_timeout is not None:
                _timeout: float = PrivateAttr(default=updated_timeout)
            if updated_headers is not None:
                _headers: dict[str, Any] = PrivateAttr(
                    default_factory=lambda: dict(updated_headers)
                )

            def model_post_init(self, *args: Any, **kwargs: Any) -> None:
                super().model_post_init(*args, **kwargs)
                if subject_namespace:
                    if self.subject:
                        self.subject = f"{subject_namespace}{separator}{self.subject}"
                    else:
                        self.subject = subject_namespace
                elif not self.subject and subject:
                    self.subject = subject

        UpdatedEvent.__name__ = cls.__name__
        UpdatedEvent.__qualname__ = cls.__qualname__
        UpdatedEvent.__module__ = cls.__module__
        return UpdatedEvent  # type: ignore[return-value]

    return _wrapper
