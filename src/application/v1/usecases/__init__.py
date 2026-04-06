from src.application.common.mediator import MediatorImpl

from . import auth, user


def setup_use_cases(mediator: MediatorImpl) -> None:
    mediator.register(auth.RegisterRequest, auth.RegisterUseCase)
    mediator.register(auth.LoginRequest, auth.LoginUseCase)
    mediator.register(auth.LogoutRequest, auth.LogoutUseCase)
    mediator.register(auth.RefreshTokenRequest, auth.RefreshTokenUseCase)
    mediator.register(auth.ConfirmRegisterRequest, auth.ConfirmRegisterUseCase)
    mediator.register(auth.PermissionRequest, auth.PermissionUseCase)
    mediator.register(user.CreateUserRequest, user.CreateUserUseCase)
    mediator.register(user.SelectUserRequest, user.SelectUserUseCase)
    mediator.register(user.SelectManyUserRequest, user.SelectManyUserUseCase)
    mediator.register(user.UpdateUserRequest, user.UpdateUserUseCase)
