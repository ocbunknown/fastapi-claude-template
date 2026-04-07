from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request, status

from src.application.common.interfaces.request_bus import RequestBus
from src.application.v1.results import StatusResult
from src.application.v1.services.auth import TokensExpire
from src.application.v1.usecases.auth import (
    ConfirmRegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
)
from src.common.di import Depends
from src.presentation.http.common.responses import OkResponse
from src.presentation.http.v1 import contracts
from src.settings.core import Settings

public_auth_router = APIRouter(prefix="/auth", tags=["Public"], route_class=DishkaRoute)


@public_auth_router.post(
    "/register",
    status_code=status.HTTP_200_OK,
    response_model=contracts.Status,
)
async def register_endpoint(
    body: contracts.Register,
    request_bus: Depends[RequestBus],
) -> OkResponse[contracts.Status]:
    result: StatusResult = await request_bus.send(
        RegisterRequest(
            login=body.login,
            password=body.password,
            fingerprint=body.fingerprint,
        )
    )
    return OkResponse(contracts.Status(status=result.status))


@public_auth_router.post(
    "/register/confirm",
    status_code=status.HTTP_200_OK,
    response_model=contracts.Token,
)
async def confirm_register_endpoint(
    body: contracts.VerificationCode,
    request_bus: Depends[RequestBus],
    settings: Depends[Settings],
) -> OkResponse[contracts.Token]:
    result: TokensExpire = await request_bus.send(
        ConfirmRegisterRequest(code=body.code)
    )
    response = OkResponse(contracts.Token(token=result.tokens.access))
    response.set_cookie(
        "refresh_token",
        value=result.tokens.refresh,
        expires=result.refresh_expire,
        httponly=True,
        secure=settings.app.production,
        samesite="lax",
    )
    return response


@public_auth_router.post(
    "/login",
    response_model=contracts.Token,
    status_code=status.HTTP_200_OK,
)
async def login_endpoint(
    body: contracts.Login,
    request_bus: Depends[RequestBus],
    settings: Depends[Settings],
) -> OkResponse[contracts.Token]:
    result: TokensExpire = await request_bus.send(
        LoginRequest(
            login=body.login,
            password=body.password,
            fingerprint=body.fingerprint,
        )
    )
    response = OkResponse(contracts.Token(token=result.tokens.access))
    response.set_cookie(
        "refresh_token",
        value=result.tokens.refresh,
        expires=result.refresh_expire,
        httponly=True,
        secure=settings.app.production,
        samesite="lax",
    )
    return response


@public_auth_router.post(
    "/refresh",
    response_model=contracts.Token,
    status_code=status.HTTP_200_OK,
)
async def refresh_endpoint(
    request: Request,
    body: contracts.Fingerprint,
    request_bus: Depends[RequestBus],
    settings: Depends[Settings],
) -> OkResponse[contracts.Token]:
    result: TokensExpire = await request_bus.send(
        RefreshTokenRequest(
            fingerprint=body.fingerprint,
            refresh_token=request.cookies.get("refresh_token", ""),
        )
    )
    response = OkResponse(contracts.Token(token=result.tokens.access))
    response.set_cookie(
        "refresh_token",
        value=result.tokens.refresh,
        expires=result.refresh_expire,
        httponly=True,
        secure=settings.app.production,
        samesite="lax",
    )
    return response
