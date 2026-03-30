from src.api.common.mediator import MediatorImpl

from . import auth, user


def setup_handlers(mediator: MediatorImpl) -> None:
    mediator.register(auth.RegisterQuery, auth.RegisterHandler)
    mediator.register(auth.LoginQuery, auth.LoginHandler)
    mediator.register(auth.LogoutQuery, auth.LogoutHandler)
    mediator.register(auth.RefreshTokenQuery, auth.RefreshTokenHandler)
    mediator.register(auth.ConfirmRegisterQuery, auth.ConfirmRegisterHandler)
    mediator.register(auth.PermissionQuery, auth.PermissionHandler)
    mediator.register(user.CreateUserQuery, user.CreateUserHandler)
    mediator.register(user.SelectUserQuery, user.SelectUserHandler)
    mediator.register(user.SelectManyUserQuery, user.SelectManyUserHandler)
    mediator.register(user.UpdateUserQuery, user.UpdateUserHandler)
