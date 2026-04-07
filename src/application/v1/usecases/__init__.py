from src.application.common.bus import RequestBusImpl

from . import auth, user


def setup_use_cases(request_bus: RequestBusImpl) -> None:
    request_bus.register(auth.RegisterRequest, auth.RegisterUseCase)
    request_bus.register(auth.LoginRequest, auth.LoginUseCase)
    request_bus.register(auth.LogoutRequest, auth.LogoutUseCase)
    request_bus.register(auth.RefreshTokenRequest, auth.RefreshTokenUseCase)
    request_bus.register(auth.ConfirmRegisterRequest, auth.ConfirmRegisterUseCase)
    request_bus.register(auth.PermissionRequest, auth.PermissionUseCase)
    request_bus.register(user.CreateUserRequest, user.CreateUserUseCase)
    request_bus.register(user.SelectUserRequest, user.SelectUserUseCase)
    request_bus.register(user.SelectManyUserRequest, user.SelectManyUserUseCase)
    request_bus.register(user.UpdateUserRequest, user.UpdateUserUseCase)
