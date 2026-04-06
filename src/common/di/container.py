from dishka import (
    AsyncContainer,
    Container,
    Provider,
    make_async_container,
    make_container,
)


class DynamicContainer:
    __slots__ = ("_container", "_sync_container")

    def __init__(self) -> None:
        self._container: AsyncContainer | None = None
        self._sync_container: Container | None = None

    def add_providers(self, *providers: Provider) -> None:
        self._rebuild_container(*providers)
        self._rebuild_sync_container(*providers)

    def _rebuild_container(self, *providers: Provider) -> None:
        new_container = make_async_container(*providers)
        new_container.parent_container = self._container
        self._container = new_container

    def _rebuild_sync_container(self, *providers: Provider) -> None:
        new_sync_container = make_container(*providers)
        new_sync_container.parent_container = self._sync_container
        self._sync_container = new_sync_container

    def get_container(self) -> AsyncContainer:
        if not self._container:
            raise RuntimeError("Container is not initialized")
        return self._container

    def get_sync_container(self) -> Container:
        if not self._sync_container:
            raise RuntimeError("Container is not initialized")
        return self._sync_container


container = DynamicContainer()
