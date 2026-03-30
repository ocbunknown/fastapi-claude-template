from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request, status
from fastapi import Depends as Require

from src.api.common.interfaces.mediator import Mediator
from src.api.common.responses import OkResponse
from src.api.v1 import dtos
from src.api.v1.handlers import auth
from src.api.v1.permission import Authorization
from src.common.di import Depends
from src.services.internal.auth import Token, TokensExpire
from src.settings.core import Settings

auth_router = APIRouter(
    prefix="/auth", tags=["Authentication"], route_class=DishkaRoute
)


@auth_router.post(
    "/register",
    status_code=status.HTTP_200_OK,
    response_model=Token,
)
async def register_endpoint(
    body: dtos.Register,
    mediator: Depends[Mediator],
    settings: Depends[Settings],
) -> OkResponse[Token]:
    user: dtos.User = await mediator.send(body)
    result: TokensExpire = await mediator.send(
        auth.LoginQuery(
            login=user.login, password=body.password, fingerprint=body.fingerprint
        )
    )
    response = OkResponse(Token(token=result.tokens.access))
    response.set_cookie(
        "refresh_token",
        value=result.tokens.refresh,
        expires=result.refresh_expire,
        httponly=True,
        secure=settings.app.production,
        samesite="lax",
    )

    return response


@auth_router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
)
async def login_endpoint(
    body: auth.LoginQuery,
    mediator: Depends[Mediator],
    settings: Depends[Settings],
) -> OkResponse[Token]:
    result: TokensExpire = await mediator.send(body)
    response = OkResponse(Token(token=result.tokens.access))
    response.set_cookie(
        "refresh_token",
        value=result.tokens.refresh,
        expires=result.refresh_expire,
        httponly=True,
        secure=settings.app.production,
        samesite="lax",
    )

    return response


@auth_router.post(
    "/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
)
async def refresh_endpoint(
    request: Request,
    body: dtos.Fingerprint,
    mediator: Depends[Mediator],
    settings: Depends[Settings],
) -> OkResponse[Token]:
    result: TokensExpire = await mediator.send(
        auth.RefreshTokenQuery(
            data=body, refresh_token=request.cookies.get("refresh_token", "")
        )
    )
    response = OkResponse(Token(token=result.tokens.access))
    response.set_cookie(
        "refresh_token",
        value=result.tokens.refresh,
        expires=result.refresh_expire,
        httponly=True,
        secure=settings.app.production,
        samesite="lax",
    )

    return response


@auth_router.post(
    "/logout",
    response_model=dtos.Status,
    status_code=status.HTTP_200_OK,
)
async def logout_endpoint(
    mediator: Depends[Mediator],
    request: Request,
    user: Annotated[dtos.PrivateUser, Require(Authorization())],
) -> OkResponse[dtos.Status]:
    result: dtos.Status = await mediator.send(
        auth.LogoutQuery(
            user_uuid=user.uuid, refresh_token=request.cookies.get("refresh_token", "")
        )
    )
    response = OkResponse(result)
    response.delete_cookie("refresh_token")

    return response
