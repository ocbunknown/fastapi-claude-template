from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_nats import PullBasedJetStreamBroker

from src.settings.core import Settings


def create_taskiq_broker(settings: Settings) -> PullBasedJetStreamBroker:
    return PullBasedJetStreamBroker(
        servers=settings.nats.servers,
        queue="taskiq.template",
        subject="taskiq.template",
        user=settings.nats.user or None,
        password=settings.nats.password or None,
    )


def create_taskiq_scheduler(
    broker: PullBasedJetStreamBroker,
) -> TaskiqScheduler:
    return TaskiqScheduler(
        broker=broker,
        sources=[LabelScheduleSource(broker)],
    )
