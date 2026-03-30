import asyncio
import signal
import sys
from contextlib import asynccontextmanager, suppress
from typing import Any, AsyncIterator, Callable, Coroutine


class BaseWebsocketApplication:
    def __init__(self) -> None:
        self._startup_handlers: list[Callable[[], Coroutine[Any, Any, None]]] = []
        self._shutdown_handlers: list[Callable[[], Coroutine[Any, Any, None]]] = []
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._is_running: bool = False
        self._shutdown_event: asyncio.Event | None = None
        self._shutdown_timeout = 30.0
        self._force_exit_timeout = 5.0
        self._signal_handlers_installed = False

    def on_startup(
        self, handler: Callable[[], Coroutine[Any, Any, None]]
    ) -> Callable[[], Coroutine[Any, Any, None]]:
        self._startup_handlers.append(handler)
        return handler

    def on_shutdown(
        self, handler: Callable[[], Coroutine[Any, Any, None]]
    ) -> Callable[[], Coroutine[Any, Any, None]]:
        self._shutdown_handlers.append(handler)
        return handler

    def create_task(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    def _setup_signal_handlers(self) -> None:
        if self._signal_handlers_installed:
            return

        loop = asyncio.get_running_loop()

        def signal_handler(sig: signal.Signals) -> None:
            if self._shutdown_event and not self._shutdown_event.is_set():
                self._shutdown_event.set()

        if sys.platform != "win32":
            signals_to_handle = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
        else:
            signals_to_handle = (signal.SIGTERM, signal.SIGINT)

        for sig in signals_to_handle:
            loop.add_signal_handler(sig, signal_handler, sig)

        self._signal_handlers_installed = True

    def _remove_signal_handlers(self) -> None:
        if not self._signal_handlers_installed:
            return

        loop = asyncio.get_running_loop()

        if sys.platform != "win32":
            signals_to_handle = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
        else:
            signals_to_handle = (signal.SIGTERM, signal.SIGINT)

        for sig in signals_to_handle:
            loop.remove_signal_handler(sig)

        self._signal_handlers_installed = False

    async def _run_startup_handlers(self) -> None:
        if not self._startup_handlers:
            return

        for handler in self._startup_handlers:
            await handler()

    async def _run_shutdown_handlers(self) -> None:
        if not self._shutdown_handlers:
            return

        for handler in reversed(self._shutdown_handlers):
            try:
                await asyncio.wait_for(handler(), timeout=self._shutdown_timeout)
            except (TimeoutError, Exception):
                pass

    async def _cancel_background_tasks(self) -> None:
        if not self._background_tasks:
            return

        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        if self._background_tasks:
            with suppress(asyncio.CancelledError, TimeoutError):
                await asyncio.wait_for(
                    asyncio.gather(*self._background_tasks, return_exceptions=True),
                    timeout=self._force_exit_timeout,
                )

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        if self._is_running:
            raise RuntimeError("Application is already running")

        self._shutdown_event = asyncio.Event()

        try:
            self._is_running = True
            self._setup_signal_handlers()
            await self._run_startup_handlers()
            yield
        finally:
            await self._cancel_background_tasks()
            await self._run_shutdown_handlers()
            self._remove_signal_handlers()
            self._is_running = False
            self._shutdown_event = None

    async def _run(self, main_task: Coroutine[Any, Any, None] | None = None) -> None:
        async with self.lifespan():
            assert self._shutdown_event is not None

            if main_task:
                self.create_task(main_task)

            await self._shutdown_event.wait()

    def run(self, main_task: Coroutine[Any, Any, None] | None = None) -> None:
        with suppress(KeyboardInterrupt):
            asyncio.run(self._run(main_task))
