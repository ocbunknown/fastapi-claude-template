from dishka import AsyncContainer, Provider, make_async_container

from src.application.provider import ApplicationProvider
from src.database.psql.provider import DatabaseProvider
from src.infrastructure.broker.provider import BrokerProvider
from src.infrastructure.provider import InfrastructureProvider
from src.settings.core import Settings
from src.settings.provider import SettingsProvider


def build_container(settings: Settings, *extra: Provider) -> AsyncContainer:
    return make_async_container(
        SettingsProvider(),
        InfrastructureProvider(),
        DatabaseProvider(),
        BrokerProvider(),
        ApplicationProvider(),
        *extra,
        context={Settings: settings},
    )
