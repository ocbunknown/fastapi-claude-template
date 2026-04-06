import structlog
from dishka.integrations.taskiq import TaskiqProvider, setup_dishka
from taskiq import AsyncBroker, TaskiqEvents, TaskiqScheduler, TaskiqState

from src.entrypoints.container import build_container
from src.infrastructure.logging import setup_logging
from src.settings.core import Settings, load_settings
from src.tasks import setup_tasks
from src.tasks.broker import create_taskiq_broker, create_taskiq_scheduler

log = structlog.get_logger(__name__)


def create_scheduler(settings: Settings) -> tuple[AsyncBroker, TaskiqScheduler]:
    log.info("Initialize scheduler (Taskiq) application")

    broker = create_taskiq_broker(settings)
    scheduler = create_taskiq_scheduler(broker)

    container = build_container(settings, TaskiqProvider())
    setup_dishka(container, broker)

    @broker.on_event(TaskiqEvents.WORKER_SHUTDOWN, TaskiqEvents.CLIENT_SHUTDOWN)
    async def close_container(state: TaskiqState) -> None:
        await container.close()

    setup_tasks(broker)

    return broker, scheduler


settings = load_settings()
setup_logging(settings)
broker, scheduler = create_scheduler(settings)
