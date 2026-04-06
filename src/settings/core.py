import os
from pathlib import Path
from typing import Final, Literal, Optional, Union

from pydantic_settings import BaseSettings, SettingsConfigDict

_PathLike = Union[os.PathLike[str], str, Path]


LOG_LEVEL = os.getenv("APP_LOG_LEVEL", "DEBUG")
PROJECT_NAME = os.getenv("APP_TITLE", "app")
PROJECT_VERSION = os.getenv("APP_VERSION", "0.0.1")

LOGGING_FORMAT: Final[str] = "%(asctime)s %(name)s %(levelname)s -> %(message)s"
DATETIME_FORMAT: Final[str] = "%Y.%m.%d %H:%M"


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def path(*paths: _PathLike, base_path: Optional[_PathLike] = None) -> str:
    if base_path is None:
        base_path = root_dir()

    return os.path.join(base_path, *paths)


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_prefix="DB_",
        extra="ignore",
        env_file="./.env",
    )

    uri: str = ""
    name: str = ""
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    connection_pool_size: int = 10
    connection_max_overflow: int = 90
    connection_pool_pre_ping: bool = True

    @property
    def url(self) -> str:
        if "sqlite" in self.uri:
            return self.uri.format(self.name)
        return self.uri.format(
            self.user,
            self.password,
            self.host,
            self.port,
            self.name,
        )


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="./.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="APP_",
        extra="ignore",
    )
    root_path: str = "/api"
    title: str = "Example"
    debug: bool = True
    version: str = "0.0.1"
    production: bool = True
    swagger: bool = True
    log_level: str = "DEBUG"


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_prefix="REDIS_",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 6379
    password: Optional[str] = None


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_prefix="SERVER_",
        extra="ignore",
    )

    methods: list[
        Literal[
            "*",
            "GET",
            "POST",
            "DELETE",
            "PATCH",
            "PUT",
            "HEAD",
            "TRACE",
            "OPTIONS",
        ]
    ] = ["*"]
    headers: list[str] = ["*"]
    origins: list[str] = ["*"]
    type: Literal["uvicorn", "granian"] = "granian"
    host: str = "127.0.0.1"
    port: int = 8080
    workers: int | Literal["auto"] = "auto"
    threads: int = 1
    log: bool = False


class CipherSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="./.env",
        case_sensitive=False,
        env_prefix="CIPHER_",
        extra="ignore",
    )
    algorithm: str = ""
    secret_key: str = ""
    public_key: str = ""
    access_token_expire_seconds: int = 0
    refresh_token_expire_seconds: int = 0


class NatsSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="./.env",
        case_sensitive=False,
        env_prefix="NATS_",
        extra="ignore",
    )

    servers: list[str] = []
    user: str = ""
    password: str = ""


class Settings(BaseSettings):
    app: AppSettings
    db: DatabaseSettings
    redis: RedisSettings
    server: ServerSettings
    ciphers: CipherSettings
    nats: NatsSettings


def load_settings(
    db: Optional[DatabaseSettings] = None,
    redis: Optional[RedisSettings] = None,
    server: Optional[ServerSettings] = None,
    ciphers: Optional[CipherSettings] = None,
    app: Optional[AppSettings] = None,
    nats: Optional[NatsSettings] = None,
) -> Settings:
    return Settings(
        db=db or DatabaseSettings(),
        redis=redis or RedisSettings(),
        server=server or ServerSettings(),
        ciphers=ciphers or CipherSettings(),
        app=app or AppSettings(),
        nats=nats or NatsSettings(),
    )
