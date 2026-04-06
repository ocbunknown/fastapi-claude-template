from typing import Callable

from dishka import Provider, Scope, provide

from src.application.common.interfaces.cache import StrCache
from src.application.common.interfaces.event_bus import EventBus
from src.application.common.interfaces.hasher import Hasher
from src.application.common.interfaces.jwt import JWT
from src.application.common.interfaces.mediator import Mediator
from src.application.common.mediator import MediatorImpl
from src.application.v1.services import AuthService, ServiceGateway
from src.application.v1.usecases import setup_use_cases
from src.database.psql import DBGateway

type DatabaseFactory = Callable[[], DBGateway]


class ApplicationProvider(Provider):
    scope = Scope.APP

    @provide
    def auth_service(self, jwt: JWT, cache: StrCache) -> AuthService:
        return AuthService(jwt=jwt, cache=cache)

    @provide
    def service_gateway(self, auth: AuthService) -> ServiceGateway:
        return ServiceGateway(auth=auth)

    @provide
    def mediator(
        self,
        hasher: Hasher,
        cache: StrCache,
        services: ServiceGateway,
        database_factory: DatabaseFactory,
        event_bus: EventBus,
    ) -> Mediator:
        return (
            MediatorImpl.builder()
            .dependencies(
                hasher=hasher,
                cache=cache,
                services=services,
                database=database_factory,
                event_bus=event_bus,
            )
            .use_cases(setup_use_cases)
            .build()
        )
