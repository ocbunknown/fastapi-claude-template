from dishka import Provider, Scope, from_context

from src.settings.core import Settings


class SettingsProvider(Provider):
    scope = Scope.APP
    settings = from_context(provides=Settings)
