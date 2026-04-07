from typing import Self, cast, get_args

from src.application.common.events.base import Event
from src.application.common.interfaces.broker import BrokerType
from src.application.common.interfaces.event_bus import EventBus
from src.application.common.interfaces.wrapper import EventWrapper
from src.common.tools.types import is_typevar


class EventBusImpl(EventBus):
    __slots__ = ("_brokers_registry", "_brokers")

    def __init__(self) -> None:
        self._brokers_registry: dict[type[Event], BrokerType] = {}
        self._brokers: set[BrokerType] = set()

    @classmethod
    def builder(cls) -> Self:
        return cls()

    def brokers(self, *brokers: BrokerType) -> Self:
        self._brokers = set(brokers)
        return self

    def build(self) -> Self:
        for broker in self._brokers:
            self._brokers_registry[self._resolve_event(broker)] = broker
        return self

    async def send(self, message: Event) -> None:
        broker = self._resolve_broker(message)
        await broker.publish(broker.build_message(message))

    async def send_wrapped(
        self,
        wrapper: EventWrapper,
        message: Event,
    ) -> None:
        broker = self._resolve_broker(message)
        await wrapper.execute(broker, message)

    def _resolve_broker(self, event: Event) -> BrokerType:
        event_subclasses = Event.__subclasses__()
        for event_subclass in event_subclasses:
            if issubclass(type(event), event_subclass):
                return self._brokers_registry[event_subclass]

        raise ValueError(f"Broker for event {event} not found")

    def _resolve_event(self, broker: BrokerType) -> type[Event]:
        event = get_args(broker.__orig_bases__[0])[0]  # type: ignore
        if is_typevar(event):
            raise TypeError(f"Event type {event} is a TypeVar")

        return cast(type[Event], event)
