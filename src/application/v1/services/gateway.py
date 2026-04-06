from src.application.v1.services.auth import AuthService


class ServiceGateway:
    __slots__ = ("_auth",)

    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    @property
    def auth(self) -> AuthService:
        return self._auth
